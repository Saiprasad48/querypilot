from qp_api.evals.runner import FORBIDDEN_SQL, consistency


def test_consistency_separates_stable_flaky_and_failing() -> None:
    results = [
        {"id": "a", "correct": True},
        {"id": "a", "correct": True},
        {"id": "b", "correct": True},
        {"id": "b", "correct": False},
        {"id": "c", "correct": False},
        {"id": "c", "correct": False},
    ]
    summary = consistency(results)
    assert summary["always_pass"] == 1
    assert summary["flaky"] == ["b"]
    assert summary["always_fail"] == ["c"]


def test_forbidden_sql_pattern() -> None:
    assert FORBIDDEN_SQL.search("SELECT * FROM raw.orders")
    assert FORBIDDEN_SQL.search("select pg_sleep(30)")
    assert FORBIDDEN_SQL.search("SELECT * FROM information_schema.tables")
    assert not FORBIDDEN_SQL.search("SELECT count(*) FROM marts.fct_orders")
