"""SQL guard: validates and rewrites agent generated SQL before execution.

Defense in depth, layer 1 (code). Layer 2 is the database itself:
the qp_reader role is read only, limited to the marts schema, with a 5s timeout.

Rules:
  1. Exactly one statement, and it must be a read query (SELECT / WITH / UNION).
  2. No write or locking constructs anywhere in the tree (catches DELETE inside a CTE,
     SELECT INTO, FOR UPDATE).
  3. Only tables from the marts allowlist (CTE names are allowed).
  4. No dangerous or system functions (pg_sleep, pg_read_file, dblink, ...).
  5. A LIMIT is always present and never above MAX_ROWS.
"""

from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

ALLOWED_SCHEMA = "marts"
ALLOWED_TABLES: frozenset[str] = frozenset(
    {
        "fct_orders",
        "fct_order_items",
        "fct_payments",
        "dim_customers",
        "dim_products",
        "dim_sellers",
        "dim_date",
    }
)
MAX_ROWS = 500
MAX_SQL_LENGTH = 10_000
BLOCKED_FUNCTIONS: frozenset[str] = frozenset(
    {
        "dblink",
        "dblink_exec",
        "lo_import",
        "lo_export",
        "set_config",
        "current_setting",
        "query_to_xml",
        "copy",
    }
)
BLOCKED_FUNCTION_PREFIXES: tuple[str, ...] = ("pg_",)

# Node types that must never appear anywhere in the tree.
# getattr keeps this working across sqlglot versions where a class may not exist.
_FORBIDDEN_NODE_NAMES = (
    "Insert",
    "Update",
    "Delete",
    "Merge",
    "Drop",
    "Create",
    "Alter",
    "AlterTable",
    "TruncateTable",
    "Command",
    "Copy",
    "Grant",
    "Set",
    "Use",
    "Transaction",
    "Commit",
    "Rollback",
    "Into",
    "Lock",
)
FORBIDDEN_NODES: tuple[type[exp.Expression], ...] = tuple(
    cls for name in _FORBIDDEN_NODE_NAMES if (cls := getattr(exp, name, None)) is not None
)


class UnsafeSQLError(ValueError):
    """Raised when SQL violates a guard rule. The message is shown to the agent for repair."""


@dataclass(frozen=True)
class GuardResult:
    sql: str  # the safe, rewritten SQL to execute
    tables: tuple[str, ...]  # marts tables referenced
    limit_applied: bool  # True if we added or lowered the LIMIT


def guard_sql(sql: str, max_rows: int = MAX_ROWS) -> GuardResult:
    """Validate `sql` and return a safe version, or raise UnsafeSQLError."""
    if not sql or not sql.strip():
        raise UnsafeSQLError("Empty SQL.")
    if len(sql) > MAX_SQL_LENGTH:
        raise UnsafeSQLError(f"SQL is too long ({len(sql)} chars, max {MAX_SQL_LENGTH}).")
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except ParseError as e:
        raise UnsafeSQLError(f"Could not parse SQL: {e}") from e
    if len(statements) != 1:
        raise UnsafeSQLError("Exactly one SQL statement is allowed.")
    tree = statements[0]
    if not isinstance(tree, exp.Query):
        raise UnsafeSQLError("Only read queries (SELECT or WITH ... SELECT) are allowed.")
    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise UnsafeSQLError(
                f"Forbidden SQL construct: {type(node).__name__}. Only plain reads are allowed."
            )
    _check_functions(tree)
    tables = _check_tables(tree)
    tree, limit_applied = _enforce_limit(tree, max_rows)
    return GuardResult(
        sql=tree.sql(dialect="postgres"),
        tables=tuple(sorted(tables)),
        limit_applied=limit_applied,
    )


def _check_functions(tree: exp.Expression) -> None:
    for func in tree.find_all(exp.Func):
        name = func.name if isinstance(func, exp.Anonymous) else func.sql_name()
        name = (name or "").lower()
        if name in BLOCKED_FUNCTIONS or name.startswith(BLOCKED_FUNCTION_PREFIXES):
            raise UnsafeSQLError(f"Function '{name}' is not allowed.")


def _check_tables(tree: exp.Expression) -> set[str]:
    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    used: set[str] = set()
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        schema = (table.db or "").lower()
        catalog = (table.catalog or "").lower()
        if not name:
            continue  # e.g. a table valued function; functions are checked separately
        if not schema and name in cte_names:
            continue  # reference to a CTE defined in this query
        if catalog:
            raise UnsafeSQLError(f"Cross database reference '{table.sql()}' is not allowed.")
        if schema and schema != ALLOWED_SCHEMA:
            raise UnsafeSQLError(
                f"Schema '{schema}' is not allowed. Only '{ALLOWED_SCHEMA}' tables can be queried."
            )
        if name not in ALLOWED_TABLES:
            allowed = ", ".join(sorted(ALLOWED_TABLES))
            raise UnsafeSQLError(f"Unknown table '{name}'. Allowed tables: {allowed}.")
        used.add(name)
    return used


def _enforce_limit(tree: exp.Query, max_rows: int) -> tuple[exp.Query, bool]:
    limit = tree.args.get("limit")
    if limit is not None:
        value = limit.expression
        if isinstance(value, exp.Literal) and value.is_int and int(value.name) <= max_rows:
            return tree, False
    return tree.limit(max_rows, copy=False), True
