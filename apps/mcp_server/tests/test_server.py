from datetime import date, datetime
from decimal import Decimal

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from qp_mcp.server import _jsonable, _normalize_table


def test_jsonable_converts_db_types() -> None:
    assert _jsonable(Decimal("12.50")) == 12.5
    assert _jsonable(date(2018, 1, 2)) == "2018-01-02"
    assert _jsonable(datetime(2018, 1, 2, 3, 4, 5)) == "2018-01-02T03:04:05"
    assert _jsonable("x") == "x"


def test_normalize_table_accepts_marts_names() -> None:
    assert _normalize_table("MARTS.fct_orders") == "fct_orders"
    assert _normalize_table(" dim_date ") == "dim_date"


def test_normalize_table_rejects_others() -> None:
    with pytest.raises(ToolError):
        _normalize_table("raw.orders")
