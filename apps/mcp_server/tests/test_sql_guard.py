import pytest

from qp_mcp.sql_guard import MAX_ROWS, UnsafeSQLError, guard_sql

# ---------- queries that must be ALLOWED ----------

ALLOWED = [
    "SELECT count(*) FROM fct_orders",
    "select * from marts.fct_orders where order_status = 'delivered'",
    "SELECT customer_state, sum(payment_value) FROM fct_orders GROUP BY 1 ORDER BY 2 DESC",
    """
    WITH monthly AS (
        SELECT date_trunc('month', purchase_date) AS m, sum(payment_value) AS revenue
        FROM fct_orders WHERE order_status = 'delivered' GROUP BY 1
    )
    SELECT m, revenue, revenue - lag(revenue) OVER (ORDER BY m) AS change FROM monthly
    """,
    """
    SELECT d.month_start, count(*) FROM fct_orders o
    JOIN dim_date d ON d.date_day = o.purchase_date GROUP BY 1
    """,
    "SELECT category FROM fct_order_items UNION SELECT category FROM dim_products",
    "SELECT 1",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_allowed_queries_pass(sql: str) -> None:
    result = guard_sql(sql)
    assert "LIMIT" in result.sql.upper()


def test_limit_added_when_missing() -> None:
    result = guard_sql("SELECT * FROM fct_orders")
    assert result.limit_applied
    assert f"LIMIT {MAX_ROWS}" in result.sql


def test_small_limit_kept() -> None:
    result = guard_sql("SELECT * FROM fct_orders LIMIT 10")
    assert not result.limit_applied
    assert "LIMIT 10" in result.sql


def test_large_limit_capped() -> None:
    result = guard_sql("SELECT * FROM fct_orders LIMIT 100000")
    assert result.limit_applied
    assert f"LIMIT {MAX_ROWS}" in result.sql


def test_tables_reported() -> None:
    result = guard_sql(
        "SELECT * FROM fct_orders o JOIN dim_customers c ON c.customer_id = o.customer_id"
    )
    assert result.tables == ("dim_customers", "fct_orders")


# ---------- queries that must be BLOCKED ----------

BLOCKED = [
    "",
    "DROP TABLE fct_orders",
    "DELETE FROM fct_orders",
    "UPDATE fct_orders SET payment_value = 0",
    "INSERT INTO fct_orders (order_id) VALUES ('x')",
    "TRUNCATE fct_orders",
    "CREATE TABLE hacked AS SELECT 1",
    "ALTER TABLE fct_orders ADD COLUMN x int",
    "GRANT ALL ON fct_orders TO public",
    "SET statement_timeout = 0",
    "COPY fct_orders TO '/tmp/out.csv'",
    "SELECT 1; DROP TABLE fct_orders",
    "SELECT * FROM raw.orders",
    "SELECT * FROM staging.stg_orders",
    "SELECT * FROM information_schema.tables",
    "SELECT * FROM pg_catalog.pg_user",
    "SELECT * FROM pg_user",
    "SELECT * FROM some_unknown_table",
    "SELECT pg_sleep(10)",
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT current_setting('data_directory')",
    "SELECT * INTO hacked FROM fct_orders",
    "SELECT * FROM fct_orders FOR UPDATE",
    "WITH d AS (DELETE FROM fct_orders RETURNING *) SELECT * FROM d",
]


@pytest.mark.parametrize("sql", BLOCKED)
def test_blocked_queries_raise(sql: str) -> None:
    with pytest.raises(UnsafeSQLError):
        guard_sql(sql)


def test_error_message_helps_repair() -> None:
    with pytest.raises(UnsafeSQLError, match="Allowed tables"):
        guard_sql("SELECT * FROM orders")
