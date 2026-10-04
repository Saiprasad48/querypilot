"""Execution accuracy: does the agent's result contain the reference result?

Rules:
  * row order does not matter, and row counts must be equal
  * numbers are compared rounded to 2 decimals (0.22222 == 0.2222)
  * every reference column must match some predicted column's values;
    extra predicted columns are allowed (e.g. an added count next to a rate)
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_MONTH = re.compile(r"^\d{4}-\d{2}$")

def normalize(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int | float | Decimal):
        return round(float(value), 2) + 0.0  # + 0.0 turns -0.0 into 0.0
    text = str(value).strip()
    if _MONTH.match(text):
        return f"{text}-01"  # "2017-01" means the same month as "2017-01-01"
    return text[:10] if _DATE.match(text) else text.lower()

def _column(rows: list[list[Any]], index: int) -> list[Any]:
    return sorted((normalize(r[index]) for r in rows), key=repr)

def results_match(
    ref_columns: list[str],
    ref_rows: list[list[Any]],
    pred_columns: list[str],
    pred_rows: list[list[Any]],
    only: list[str] | None = None,
) -> tuple[bool, str]:
    """`only` limits which reference columns must match, for questions where a label column
    may be validly formatted several ways (true/false vs 'late'/'on_time')."""
    if len(ref_rows) != len(pred_rows):
        return False, f"expected {len(ref_rows)} rows, got {len(pred_rows)}"

    predicted = [_column(pred_rows, i) for i in range(len(pred_columns))]
    used: set[int] = set()
    for j, name in enumerate(ref_columns):
        if only and name not in only:
            continue
        expected = _column(ref_rows, j)
        match = next(
            (i for i, values in enumerate(predicted) if i not in used and values == expected),
            None,
        )
        if match is None:
            return False, f"no result column matches expected column '{name}'"
        used.add(match)
    return True, "match"