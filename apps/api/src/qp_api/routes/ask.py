"""Ask endpoint: runs the agent and streams progress as Server Sent Events.

Event order:  thread -> step (per node) -> sql -> rows -> answer -> usage -> done
On failure:   ... -> error -> done
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from qp_api.agent.graph import new_turn
from qp_api.ratelimit import rate_limiter
from qp_api.sse import sse

logger = logging.getLogger("qp_api")
router = APIRouter(prefix="/api", tags=["agent"])
MAX_ROWS_TO_CLIENT = 200

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    thread_id: str | None = Field(default=None, max_length=64)

def _run(graph: Any, question: str, thread_id: str) -> Iterator[str]:
    config = {"configurable": {"thread_id": thread_id}}
    yield sse("thread", {"thread_id": thread_id})
    final: dict[str, Any] = {}
    try:
        for mode, chunk in graph.stream(
            new_turn(question), config, stream_mode=["updates", "values"]
        ):
            if mode == "values":
                final = chunk
                continue
            for node, update in chunk.items():
                step = (update.get("steps") or [{}])[-1]
                yield sse("step", {"node": node, "ms": step.get("ms"), "error": update.get("error")})
                if node == "execute" and not update.get("error"):
                    rows = update["rows"]
                    yield sse("sql", {"sql": update["sql_executed"]})
                    yield sse(
                        "rows",
                        {
                            "columns": update["columns"],
                            "rows": rows[:MAX_ROWS_TO_CLIENT],
                            "row_count": len(rows),
                        },
                    )
        usage = final.get("usage", [])
        yield sse(
            "answer",
            {
                "question": question,
                "standalone_question": final.get("standalone_question"),
                "intent": final.get("intent"),
                "answer": final.get("answer", {}),
            },
        )
        yield sse(
            "usage",
            {
                "calls": usage,
                "input_tokens": sum(u["input_tokens"] for u in usage),
                "output_tokens": sum(u["output_tokens"] for u in usage),
                "steps": final.get("steps", []),
            },
        )
    except Exception:
        logger.exception("agent run failed for thread %s", thread_id)
        yield sse("error", {"message": "Something went wrong while answering. Please try again."})
    yield sse("done", {})

_CLIENT_ID = re.compile(r"[A-Za-z0-9_-]{8,64}")

def _client_id(request: Request) -> str:
    """Prefer the browser's anonymous ID header; fall back to the IP address."""
    header = request.headers.get("x-client-id", "")
    if _CLIENT_ID.fullmatch(header):
        return f"c:{header}"
    return f"ip:{request.client.host if request.client else 'unknown'}"

@router.post("/ask")
def ask(req: AskRequest, request: Request) -> StreamingResponse:
    limit = rate_limiter.hit(_client_id(request))
    if not limit.allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: {limit.reason}. Try again in {limit.retry_after_s} s.",
            headers={"Retry-After": str(limit.retry_after_s)},
        )
    thread_id = req.thread_id or str(uuid4())
    return StreamingResponse(
        _run(request.app.state.graph, req.question.strip(), thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-RateLimit-Remaining": str(limit.remaining_today),
        },
    )

@router.get("/threads/{thread_id}")
def get_thread(thread_id: str, request: Request) -> dict[str, Any]:
    state = request.app.state.graph.get_state({"configurable": {"thread_id": thread_id}})
    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"thread_id": thread_id, "history": state.values.get("history", [])}