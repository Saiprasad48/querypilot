from qp_api.agent.graph import (
    MAX_ATTEMPTS,
    after_execute,
    after_route,
    after_validate,
    new_turn,
)
from qp_api.agent.nodes import history_text, small_sample_caveats
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
                "columns": [{"name": "order_id", "type": "text", "description": "Order id."}],
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


def test_new_turn_resets_per_turn_fields_but_not_history() -> None:
    turn = new_turn("What about 2017?")
    assert turn["question"] == "What about 2017?"
    assert turn["steps"] == [] and turn["usage"] == [] and turn["error"] is None
    assert "history" not in turn  # history must survive across turns


def test_history_text_shows_recent_turns_only() -> None:
    history = [{"question": f"q{i}", "sql": f"SELECT {i}", "summary": f"a{i}"} for i in range(5)]
    text = history_text({"history": history})
    assert "q4" in text and "q2" in text
    assert "q1" not in text  # only the last 3 turns
    assert history_text({}) == ""


def test_small_sample_caveat_flags_only_small_groups() -> None:
    columns = ["customer_state", "delivered_orders", "late_delivery_rate"]
    rows = [["AL", 198, 0.2071], ["RR", 18, 0.1667], ["PI", 258, 0.1667]]
    caveats = small_sample_caveats(columns, rows)
    assert caveats == ["RR is based on only 18 delivered orders, a small sample."]


def test_no_caveat_for_single_totals_or_results_without_rates() -> None:
    assert small_sample_caveats(["orders"], [[12]]) == []
    assert small_sample_caveats(["state", "orders"], [["AL", 5], ["RR", 3]]) == []
