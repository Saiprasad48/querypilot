"""The data that flows through the graph. Each node returns a partial update."""

import operator
from typing import Annotated, Any, Literal, TypedDict


class Turn(TypedDict):
    question: str  # the standalone version of the question
    sql: str
    summary: str


class AgentState(TypedDict, total=False):
    question: str  # exactly what the user typed
    standalone_question: str  # rewritten by the router to include follow up context
    # route
    intent: Literal["data_question", "write_request", "off_topic", "ambiguous", "private_data"]
    complexity: Literal["simple", "complex"]
    clarification: str
    # retrieve
    schema_context: str
    # write_sql / validate / execute
    plan: str
    sql: str
    attempts: int
    error: str | None
    sql_executed: str
    columns: list[str]
    rows: list[list[Any]]
    # analyze / decline / fail
    answer: dict[str, Any]
    # per turn telemetry (reset at the start of every question)
    steps: list[dict[str, Any]]
    usage: list[dict[str, Any]]
    # conversation memory: one entry per finished turn, appended across the thread
    history: Annotated[list[Turn], operator.add]
