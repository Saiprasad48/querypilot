"""The data that flows through the graph. Each node returns a partial update."""

import operator
from typing import Annotated, Any, Literal, TypedDict


class AgentState(TypedDict, total=False):
    question: str
    # route
    intent: Literal["data_question", "write_request", "off_topic", "ambiguous"]
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
    # telemetry: operator.add means each node's list is APPENDED, not replaced
    steps: Annotated[list[dict[str, Any]], operator.add]
    usage: Annotated[list[dict[str, Any]], operator.add]
