"""How the agent reaches its tools.

Today: in process calls into the qp_mcp package (fast, easy to debug).
Later: an MCP client implementation of the same interface, chosen by config.
"""

from __future__ import annotations

from typing import Any, Protocol

from mcp.server.mcpserver.exceptions import ToolError
from qp_mcp import server as mcp_tools


class ToolCallError(Exception):
    """A tool rejected the call. The message is written to be shown to the model for repair."""


class Tools(Protocol):
    def search_schema(self, question: str) -> dict[str, Any]: ...
    def run_sql(self, sql: str) -> dict[str, Any]: ...


class InProcessTools:
    def search_schema(self, question: str) -> dict[str, Any]:
        try:
            return mcp_tools.search_schema(question)
        except ToolError as e:
            raise ToolCallError(str(e)) from e

    def run_sql(self, sql: str) -> dict[str, Any]:
        try:
            return mcp_tools.run_sql(sql)
        except ToolError as e:
            raise ToolCallError(str(e)) from e


def format_schema(ctx: dict[str, Any]) -> str:
    """Turn search_schema output into compact prompt text."""
    lines: list[str] = []
    for table in ctx.get("tables", []):
        lines.append(f"TABLE {table['table']}: {table['description']}")
        for col in table["columns"]:
            desc = f": {col['description']}" if col["description"] else ""
            lines.append(f"  {col['name']} ({col['type']}){desc}")
    if ctx.get("metrics"):
        lines.append("")
        lines.append("BUSINESS METRICS (use these definitions exactly):")
        for m in ctx["metrics"]:
            lines.append(f"  {m['name']}: {m['description']} SQL: {m['reference_sql']}")
    return "\n".join(lines)
