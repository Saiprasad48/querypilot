"""Structured outputs the LLM must return. Pydantic validates every response."""

from typing import Literal

from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    intent: Literal["data_question", "write_request", "off_topic", "ambiguous"]
    complexity: Literal["simple", "complex"] = Field(
        description="simple: one table with basic filters or aggregates. "
        "complex: joins, comparisons over time, rankings within groups, or several steps."
    )
    clarification: str = Field(
        default="", description="Only if ambiguous: one short question to ask the user."
    )
    standalone_question: str = Field(
        default="",
        description="The new message rewritten as a fully self contained question, using the "
        "conversation history if it is a follow up. Copy it unchanged if already standalone.",
    )

class SQLDraft(BaseModel):
    plan: str = Field(description="2 to 4 short steps describing the approach.")
    sql: str = Field(description="One PostgreSQL SELECT query over marts tables.")

class ChartSpec(BaseModel):
    type: Literal["bar", "line", "number", "table"]
    x: str | None = Field(default=None, description="Result column for the x axis.")
    y: list[str] = Field(default_factory=list, description="Result columns to plot.")
    title: str = ""

class Analysis(BaseModel):
    summary: str = Field(
        description="2 to 4 sentences answering the question, using only numbers in the result."
    )
    key_numbers: list[str] = Field(
        default_factory=list, description="Up to 5 short facts, e.g. 'SP: 5.0% late'."
    )
    chart: ChartSpec
    caveats: list[str] = Field(default_factory=list)
    followups: list[str] = Field(
        default_factory=list,
        description="Up to 3 natural follow up questions answerable with data from "
        "Sep 2016 to Oct 2018.",
    )