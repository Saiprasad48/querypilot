"""Graph nodes. Each takes the current state and returns a partial update."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel
from qp_mcp.sql_guard import UnsafeSQLError, guard_sql

from qp_api.agent.prompts import ANALYST_SYSTEM, ROUTER_SYSTEM, SQL_SYSTEM
from qp_api.agent.schemas import Analysis, RouteDecision, SQLDraft
from qp_api.agent.state import AgentState
from qp_api.agent.tools import InProcessTools, Tools, format_schema
from qp_api.config import settings
from qp_api.llm import get_chat_model

tools: Tools = InProcessTools()


@lru_cache(maxsize=1)
def _fast() -> BaseChatModel:
    return get_chat_model(settings.qp_model_fast)


@lru_cache(maxsize=1)
def _smart() -> BaseChatModel:
    return get_chat_model(settings.qp_model_smart)


def _structured(
    model: BaseChatModel,
    schema: type[BaseModel],
    messages: list[tuple[str, str]],
    call: str,
) -> tuple[Any, dict[str, Any]]:
    """Call a model with structured output and capture token usage."""
    result = model.with_structured_output(schema, include_raw=True).invoke(messages)
    parsed = result["parsed"]
    if parsed is None:
        raise ValueError(
            f"{call}: could not parse model output: {result.get('parsing_error')}"
        )
    meta = result["raw"].usage_metadata or {}
    usage = {
        "call": call,
        "model": getattr(model, "model", "unknown"),
        "input_tokens": meta.get("input_tokens", 0),
        "output_tokens": meta.get("output_tokens", 0),
    }
    return parsed, usage


def _empty_answer(summary: str) -> dict[str, Any]:
    return {
        "summary": summary,
        "key_numbers": [],
        "chart": {"type": "table", "x": None, "y": [], "title": ""},
        "caveats": [],
        "followups": [],
    }


def route(state: AgentState) -> dict[str, Any]:
    decision, usage = _structured(
        _fast(),
        RouteDecision,
        [("system", ROUTER_SYSTEM), ("human", state["question"])],
        "route",
    )
    return {
        "intent": decision.intent,
        "complexity": decision.complexity,
        "clarification": decision.clarification,
        "usage": [usage],
    }


def decline(state: AgentState) -> dict[str, Any]:
    intent = state.get("intent")
    if intent == "ambiguous" and state.get("clarification"):
        text = state["clarification"]
    elif intent == "write_request":
        text = (
            "QueryPilot is read only, so I can't change data. I can analyze it instead, "
            "for example by counting or comparing those records."
        )
    else:
        text = (
            "I can only answer questions about the Olist ecommerce data: orders, customers, "
            "products, sellers, payments and reviews from 2016 to 2018."
        )
    return {"answer": _empty_answer(text)}


def retrieve(state: AgentState) -> dict[str, Any]:
    ctx = tools.search_schema(state["question"])
    return {"schema_context": format_schema(ctx), "attempts": 0, "error": None}


def write_sql(state: AgentState) -> dict[str, Any]:
    is_repair = bool(state.get("error"))
    # escalate to the smart model for complex questions and for every repair attempt
    model = _smart() if state.get("complexity") == "complex" or is_repair else _fast()
    human = f"Question: {state['question']}"
    if is_repair:
        human += (
            f"\n\nYour previous SQL:\n{state['sql']}\n\n"
            f"failed with this error:\n{state['error']}\n\nWrite a corrected query."
        )
    draft, usage = _structured(
        model,
        SQLDraft,
        [("system", SQL_SYSTEM + state["schema_context"]), ("human", human)],
        "repair_sql" if is_repair else "write_sql",
    )
    return {
        "plan": draft.plan,
        "sql": draft.sql,
        "attempts": state.get("attempts", 0) + 1,
        "usage": [usage],
    }


def validate(state: AgentState) -> dict[str, Any]:
    try:
        guarded = guard_sql(state["sql"])
    except UnsafeSQLError as e:
        return {"error": f"SQL guard rejected the query: {e}"}
    return {"sql": guarded.sql, "error": None}


def execute(state: AgentState) -> dict[str, Any]:
    try:
        result = tools.run_sql(state["sql"])
    except Exception as e:  # tool errors carry a message written for repair
        return {"error": str(e)}
    return {
        "sql_executed": result["sql_executed"],
        "columns": result["columns"],
        "rows": result["rows"],
        "error": None,
    }


def analyze(state: AgentState) -> dict[str, Any]:
    rows = state.get("rows", [])
    result_json = json.dumps(
        {
            "columns": state.get("columns", []),
            "rows": rows[:50],
            "total_rows": len(rows),
        },
        default=str,
    )
    human = (
        f"Question: {state['question']}\n\n"
        f"SQL used:\n{state['sql_executed']}\n\n"
        f"Result (JSON, first 50 rows):\n{result_json}"
    )
    analysis, usage = _structured(
        _fast(), Analysis, [("system", ANALYST_SYSTEM), ("human", human)], "analyze"
    )
    return {"answer": analysis.model_dump(), "usage": [usage]}


def fail(state: AgentState) -> dict[str, Any]:
    return {
        "answer": _empty_answer(
            f"I couldn't produce a working query after {state.get('attempts', 0)} attempts. "
            f"Last error: {state.get('error')}"
        )
    }
