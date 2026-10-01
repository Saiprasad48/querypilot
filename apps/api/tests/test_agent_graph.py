from qp_api.agent.graph import MAX_ATTEMPTS, after_execute, after_route, after_validate
from qp_api.agent.tools import format_schema


def test_route_sends_only_data_questions_to_retrieve() -> None:
    assert after_route({"intent": "data_question"}) == "retrieve"
    for intent in ["write_request", "off_topic", "ambiguous"]:
        assert after_route({"intent": intent}) == "decline"


def test_repair_loop_is_bounded() -> None:
    assert after_validate({"error": None, "attempts": 1}) == "execute"
    assert after_validate({"error": "bad", "attempts": 1}) == "write_sql"
    assert after_execute({"error": "bad", "attempts": MAX_ATTEMPTS}) == "fail"
    assert after_execute({"error": None, "attempts": 2}) == "analyze"


def test_format_schema_includes_columns_and_metrics() -> None:
    ctx = {
        "tables": [
            {
                "table": "marts.fct_orders",
                "description": "One row per order.",
                "columns": [
                    {"name": "order_id", "type": "text", "description": "Order id."}
                ],
            }
        ],
        "metrics": [
            {
                "name": "revenue",
                "description": "Paid.",
                "reference_sql": "SELECT sum(x)",
            }
        ],
    }
    text = format_schema(ctx)
    assert "marts.fct_orders" in text
    assert "order_id (text): Order id." in text
    assert "revenue" in text and "SELECT sum(x)" in text
