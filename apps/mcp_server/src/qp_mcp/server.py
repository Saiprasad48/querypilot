"""QueryPilot MCP server: safe, read only tools over the Olist marts warehouse.

Every database call runs as qp_reader (read only, marts only, 5s timeout),
and every agent written query passes through the SQL guard first.

Run:  qp-mcp           (stdio, for Claude Desktop and local agents)
      qp-mcp --http    (streamable HTTP, for deployment)
"""

from __future__ import annotations

import argparse
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import psycopg
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from qp_mcp.config import settings
from qp_mcp.schema_index import search
from qp_mcp.sql_guard import ALLOWED_TABLES, MAX_ROWS, UnsafeSQLError, guard_sql

mcp = MCPServer(
    "querypilot",
    instructions=(
        "Tools for answering business questions about the Olist ecommerce warehouse "
        "(Brazil, Sep 2016 to Oct 2018, all money in BRL). Workflow: call search_schema "
        "first; use get_metric for business terms like revenue or AOV and follow its "
        "definition exactly; then call run_sql with a single SELECT over marts tables."
    ),
)

# ---------- helpers ----------


def _connect() -> psycopg.Connection:
    return psycopg.connect(settings.reader_dsn, autocommit=True)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def _normalize_table(table: str) -> str:
    name = table.strip().lower().removeprefix("marts.")
    if name not in ALLOWED_TABLES:
        raise ToolError(f"Unknown table '{table}'. Available: {', '.join(sorted(ALLOWED_TABLES))}.")
    return name


def _table_info(table: str) -> dict[str, Any]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT kind, name, data_type, description
            FROM meta.schema_docs
            WHERE table_name = %s AND kind IN ('table', 'column')
            ORDER BY id
            """,
            (table,),
        ).fetchall()
    description = next((r[3] for r in rows if r[0] == "table"), "")
    columns = [
        {"name": name, "type": dtype, "description": desc or ""}
        for kind, name, dtype, desc in rows
        if kind == "column"
    ]
    return {"table": f"marts.{table}", "description": description, "columns": columns}


def _metric(name: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT name, label, description, table_name, expression, filter, unit
            FROM meta.metrics WHERE name = %s
            """,
            (name,),
        ).fetchone()
    if row is None:
        return None
    name, label, desc, table, expression, filt, unit = row
    reference_sql = f"SELECT {expression} AS {name} FROM {table}"
    if filt:
        reference_sql += f" WHERE {filt}"
    return {
        "name": name,
        "label": label,
        "description": desc,
        "table": table,
        "expression": expression,
        "filter": filt,
        "unit": unit,
        "reference_sql": reference_sql,
    }


def _execute(sql: str) -> tuple[list[str], list[list[Any]], float]:
    started = time.perf_counter()
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(sql)
            columns = [d.name for d in cur.description or []]
            rows = [[_jsonable(v) for v in row] for row in cur.fetchall()]
    except psycopg.errors.QueryCanceled as e:
        raise ToolError("Query timed out (5 s limit). Aggregate more or add filters.") from e
    except psycopg.Error as e:
        detail = e.diag.message_primary if e.diag else str(e)
        raise ToolError(f"Database error: {detail}") from e
    return columns, rows, (time.perf_counter() - started) * 1000


# ---------- tools ----------


@mcp.tool()
def search_schema(question: str, max_tables: int = 3) -> dict[str, Any]:
    """Find the tables, columns and business metrics relevant to a question.
    Call this first for every new question. Returns the best matching tables with ALL
    their columns (name, type, description) plus any matching metric definitions.
    """
    hits = search(question, k=20)
    table_scores: dict[str, float] = {}
    for h in hits:
        table_scores[h.table_name] = table_scores.get(h.table_name, 0.0) + h.score
    top_tables = sorted(table_scores, key=lambda t: table_scores[t], reverse=True)[:max_tables]
    metric_names = list(dict.fromkeys(h.name for h in hits if h.kind == "metric" and h.name))
    metrics = [m for m in (_metric(n) for n in metric_names) if m is not None]
    return {"tables": [_table_info(t) for t in top_tables], "metrics": metrics}


@mcp.tool()
def describe_table(table: str) -> dict[str, Any]:
    """Show a marts table's columns, types, descriptions and 3 sample rows."""
    name = _normalize_table(table)
    info = _table_info(name)
    columns, rows, _ = _execute(guard_sql(f"SELECT * FROM marts.{name} LIMIT 3").sql)
    info["sample_rows"] = [dict(zip(columns, r, strict=True)) for r in rows]
    return info


@mcp.tool()
def list_metrics() -> list[dict[str, str]]:
    """List every defined business metric (name, label, description)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT name, label, description FROM meta.metrics ORDER BY name"
        ).fetchall()
    return [{"name": n, "label": lbl, "description": d} for n, lbl, d in rows]


@mcp.tool()
def get_metric(name: str) -> dict[str, Any]:
    """Get the official definition of a business metric plus reference SQL.
    Always use this definition instead of inventing a formula. Unknown names return
    an error listing the available metrics.
    """
    metric = _metric(name.strip().lower())
    if metric is None:
        available = ", ".join(m["name"] for m in list_metrics())
        raise ToolError(f"Unknown metric '{name}'. Available: {available}.")
    return metric


@mcp.tool()
def run_sql(sql: str) -> dict[str, Any]:
    """Run ONE read only SELECT over marts tables and return the rows as JSON.
    The query is validated first: only marts tables, no writes, no system functions,
    and a LIMIT of at most 500 rows is enforced. Errors explain how to fix the query.
    """
    try:
        guarded = guard_sql(sql)
    except UnsafeSQLError as e:
        raise ToolError(f"Blocked by SQL guard: {e}") from e
    columns, rows, elapsed_ms = _execute(guarded.sql)
    return {
        "sql_executed": guarded.sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "row_limit": MAX_ROWS,
        "limit_applied": guarded.limit_applied,
        "elapsed_ms": round(elapsed_ms, 1),
    }


@mcp.tool()
def explain_sql(sql: str) -> dict[str, Any]:
    """Estimate a query's cost without running it. Use before very heavy queries."""
    try:
        guarded = guard_sql(sql)
    except UnsafeSQLError as e:
        raise ToolError(f"Blocked by SQL guard: {e}") from e
    _, rows, _ = _execute(f"EXPLAIN (FORMAT JSON) {guarded.sql}")
    plan = rows[0][0][0]["Plan"]
    cost = float(plan["Total Cost"])
    return {
        "total_cost": cost,
        "estimated_rows": plan["Plan Rows"],
        "too_expensive": cost > settings.max_query_cost,
        "cost_threshold": settings.max_query_cost,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="qp-mcp", description="QueryPilot MCP server")
    parser.add_argument("--http", action="store_true", help="Serve over streamable HTTP")
    args = parser.parse_args()
    mcp.run(transport="streamable-http" if args.http else "stdio")


if __name__ == "__main__":
    main()
