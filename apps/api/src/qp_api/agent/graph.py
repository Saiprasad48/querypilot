"""Wires the nodes into a LangGraph state machine with bounded repair loops."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from qp_api.agent import nodes
from qp_api.agent.state import AgentState

MAX_ATTEMPTS = 3  # first try + 2 repairs


def new_turn(question: str) -> dict[str, Any]:
    """Graph input for a new question in a thread: reset per turn fields, keep history."""
    return {
        "question": question,
        "standalone_question": "",
        "clarification": "",
        "plan": "",
        "sql": "",
        "sql_executed": "",
        "attempts": 0,
        "error": None,
        "columns": [],
        "rows": [],
        "answer": {},
        "steps": [],
        "usage": [],
    }


def _timed(name: str, fn: Callable[[AgentState], dict[str, Any]]):
    """Wrap a node so every turn records which node ran and how long it took."""

    def wrapper(state: AgentState) -> dict[str, Any]:
        started = time.perf_counter()
        update = fn(state)
        ms = round((time.perf_counter() - started) * 1000)
        return {**update, "steps": [*state.get("steps", []), {"node": name, "ms": ms}]}

    return wrapper


def after_route(state: AgentState) -> str:
    return "retrieve" if state.get("intent") == "data_question" else "decline"


def after_check(state: AgentState, success: str) -> str:
    if not state.get("error"):
        return success
    return "write_sql" if state.get("attempts", 0) < MAX_ATTEMPTS else "fail"


def after_validate(state: AgentState) -> str:
    return after_check(state, "execute")


def after_execute(state: AgentState) -> str:
    return after_check(state, "analyze")


def build_graph(checkpointer: Any = None):
    g = StateGraph(AgentState)
    for name in [
        "route",
        "decline",
        "retrieve",
        "write_sql",
        "validate",
        "execute",
        "analyze",
        "fail",
    ]:
        g.add_node(name, _timed(name, getattr(nodes, name)))
    g.add_edge(START, "route")
    g.add_conditional_edges("route", after_route, ["retrieve", "decline"])
    g.add_edge("retrieve", "write_sql")
    g.add_edge("write_sql", "validate")
    g.add_conditional_edges(
        "validate", after_validate, ["execute", "write_sql", "fail"]
    )
    g.add_conditional_edges("execute", after_execute, ["analyze", "write_sql", "fail"])
    g.add_edge("analyze", END)
    g.add_edge("decline", END)
    g.add_edge("fail", END)
    return g.compile(checkpointer=checkpointer)
