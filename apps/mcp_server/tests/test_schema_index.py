from qp_mcp.schema_index import _keyword_query, build_docs


def test_build_docs_covers_tables_columns_and_metrics() -> None:
    models = {
        "fct_orders": {
            "description": "One row per order.",
            "columns": {"order_id": {"description": "Unique order identifier."}},
        }
    }
    columns = {"fct_orders": [("order_id", "text"), ("payment_value", "numeric")]}
    metrics = [
        {
            "name": "revenue",
            "label": "Revenue",
            "description": "Total paid for delivered orders.",
            "table": "marts.fct_orders",
            "synonyms": ["sales", "gmv"],
        }
    ]
    docs = build_docs(models, columns, metrics)
    kinds = [d.kind for d in docs]
    assert kinds.count("table") == 1
    assert kinds.count("column") == 2
    assert kinds.count("metric") == 1
    assert "payment_value" in docs[0].content  # table doc lists its columns
    assert "Unique order identifier." in docs[1].content
    assert "sales" in docs[-1].content


def test_keyword_query_is_safe_or_query() -> None:
    assert _keyword_query("Which states, have late!") == "which | states | have | late"
    assert _keyword_query("'; DROP TABLE x; --") == "drop | table | x"
