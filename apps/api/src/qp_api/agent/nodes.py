"""Graph nodes. Each takes the current state and returns a partial update."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel
from qp_mcp.sql_guard import UnsafeSQLError, guard_sql

from qp_api.agent.prompts import ANALYST_SYSTEM, ROUTER_SYSTEM, SQL_SYSTEM
from qp_api.agent.schemas import Analysis, RouteDecision, SQLDraft
from qp_api.agent.state import AgentState, Turn
from qp_api.agent.tools import InProcessTools, ToolCallError, Tools, format_schema
from qp_api.cache import cache_key, llm_cache
from qp_api.config import settings
from qp_api.llm import smart_breaker, structured_chain

tools: Tools = InProcessTools()
HISTORY_TURNS = 3  # how many previous turns the model sees


# ---------- helpers ----------
def _structured(
    role: str, schema: type[BaseModel], messages: list[tuple[str, str]], call: str
) -> tuple[Any, dict[str, Any]]:
    """Call the model for `role` with structured output; cached in Redis; usage recorded."""
    requested = role
    # The key covers everything that affects the output: prompt, schema, configured models.
    key = cache_key(
        requested,
        schema.model_json_schema(),
        settings.qp_model_fast,
        settings.qp_model_smart,
        messages,
    )
    if settings.llm_cache_enabled and (hit := llm_cache.get(key)):
        return schema.model_validate(hit["parsed"]), {
            "call": call,
            "role": requested,
            "model": hit["model"],
            "input_tokens": 0,
            "output_tokens": 0,
            "cached": True,
        }
    if role == "smart" and not smart_breaker.allow():
        role = "fast"  # breaker open: skip the smart model entirely for now
    result = structured_chain(role, schema).invoke(messages)
    parsed = result["parsed"]
    if parsed is None:
        raise ValueError(f"{call}: could not parse model output: {result.get('parsing_error')}")
    raw = result["raw"]
    model_name = raw.response_metadata.get("model_name", "unknown")
    if role == "smart":
        smart_breaker.record(model_name)
    if settings.llm_cache_enabled:
        llm_cache.set(key, {"parsed": parsed.model_dump(), "model": model_name})
    meta = raw.usage_metadata or {}
    return parsed, {
        "call": call,
        "role": requested if role == requested else f"{requested}>{role}",
        "model": model_name,
        "input_tokens": meta.get("input_tokens", 0),
        "output_tokens": meta.get("output_tokens", 0),
        "cached": False,
    }


def _question(state: AgentState) -> str:
    """The question every step should work on: the rewritten one if available."""
    return state.get("standalone_question") or state["question"]


def history_text(state: AgentState) -> str:
    """Recent turns as prompt text, or an empty string for the first question."""
    turns = state.get("history", [])[-HISTORY_TURNS:]
    if not turns:
        return ""
    lines = ["Recent conversation:"]
    for t in turns:
        lines.append(f"User: {t['question']}")
        if t["sql"]:
            lines.append(f"SQL used: {t['sql']}")
        lines.append(f"Answer: {t['summary']}")
    return "\n".join(lines) + "\n\n"


def _add_usage(state: AgentState, usage: dict[str, Any]) -> list[dict[str, Any]]:
    return [*state.get("usage", []), usage]


def _remember(state: AgentState, summary: str, sql: str = "") -> list[Turn]:
    return [{"question": _question(state), "sql": sql, "summary": summary}]


def _empty_answer(summary: str) -> dict[str, Any]:
    return {
        "summary": summary,
        "key_numbers": [],
        "chart": {"type": "table", "x": None, "y": [], "title": ""},
        "caveats": [],
        "followups": [],
    }


SMALL_SAMPLE = 30
_COUNT_COLUMN = re.compile(r"(count|orders|customers|items|reviews|_n$|^n_|num_)")
_RATE_COLUMN = re.compile(r"(rate|avg|average|share|ratio|pct|percent|mean)")


def small_sample_caveats(columns: list[str], rows: list[list[Any]]) -> list[str]:
    """Deterministic caveats for groups whose rate or average rests on fewer than 30 records.
    Only applies to grouped results that contain both a count column and a rate/average
    column; a single total like "267 orders" is not a sample size problem.
    """
    if len(rows) < 2 or not any(_RATE_COLUMN.search(c.lower()) for c in columns):
        return []
    count_idx = [i for i, c in enumerate(columns) if _COUNT_COLUMN.search(c.lower())]
    label_idx = next(
        (i for i, v in enumerate(rows[0]) if i not in count_idx and isinstance(v, str)), None
    )
    caveats = []
    for row in rows:
        for i in count_idx:
            value = row[i]
            if (
                isinstance(value, int | float)
                and not isinstance(value, bool)
                and value < SMALL_SAMPLE
            ):
                label = row[label_idx] if label_idx is not None else "One group"
                noun = columns[i].replace("_", " ")
                caveats.append(f"{label} is based on only {int(value)} {noun}, a small sample.")
    return caveats


# ---------- nodes ----------
def route(state: AgentState) -> dict[str, Any]:
    human = f"{history_text(state)}New message: {state['question']}"
    decision, usage = _structured(
        "fast", RouteDecision, [("system", ROUTER_SYSTEM), ("human", human)], "route"
    )
    return {
        "intent": decision.intent,
        "complexity": decision.complexity,
        "clarification": decision.clarification,
        "standalone_question": decision.standalone_question or state["question"],
        "usage": _add_usage(state, usage),
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
    elif intent == "private_data":
        text = (
            "QueryPilot only shares aggregated statistics, not records about individual "
            "customers or sellers. I can summarize them instead, for example customers per "
            "city or the share of revenue from top customers."
        )
    else:
        text = (
            "I can only answer questions about the Olist ecommerce data: orders, customers, "
            "products, sellers, payments and reviews from 2016 to 2018."
        )
    return {"answer": _empty_answer(text), "history": _remember(state, text)}


def retrieve(state: AgentState) -> dict[str, Any]:
    ctx = tools.search_schema(_question(state))
    return {"schema_context": format_schema(ctx), "attempts": 0, "error": None}


def write_sql(state: AgentState) -> dict[str, Any]:
    is_repair = bool(state.get("error"))
    # smart model (with fast fallback) for complex questions and for every repair attempt
    role = "smart" if state.get("complexity") == "complex" or is_repair else "fast"
    human = f"{history_text(state)}Question: {_question(state)}"
    if is_repair:
        human += (
            f"\n\nYour previous SQL:\n{state['sql']}\n\n"
            f"failed with this error:\n{state['error']}\n\nWrite a corrected query."
        )
    draft, usage = _structured(
        role,
        SQLDraft,
        [("system", SQL_SYSTEM + state["schema_context"]), ("human", human)],
        "repair_sql" if is_repair else "write_sql",
    )
    return {
        "plan": draft.plan,
        "sql": draft.sql,
        "attempts": state.get("attempts", 0) + 1,
        "usage": _add_usage(state, usage),
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
    except ToolCallError as e:  # expected failures: guard, database error, timeout
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
        f"Question: {_question(state)}\n\n"
        f"SQL used:\n{state['sql_executed']}\n\n"
        f"Result (JSON, first 50 rows):\n{result_json}"
    )
    analysis, usage = _structured(
        "fast", Analysis, [("system", ANALYST_SYSTEM), ("human", human)], "analyze"
    )
    answer = analysis.model_dump()
    answer["caveats"] = small_sample_caveats(state.get("columns", []), rows) + answer["caveats"]
    return {
        "answer": answer,
        "usage": _add_usage(state, usage),
        "history": _remember(state, analysis.summary, state["sql_executed"]),
    }


def fail(state: AgentState) -> dict[str, Any]:
    text = (
        f"I couldn't produce a working query after {state.get('attempts', 0)} attempts. "
        f"Last error: {state.get('error')}"
    )
    return {"answer": _empty_answer(text), "history": _remember(state, text)}
