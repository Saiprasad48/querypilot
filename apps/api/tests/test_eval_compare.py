from qp_api.evals.compare import results_match


def test_order_and_small_float_differences_do_not_matter() -> None:
    ref = (["state", "rate"], [["AL", 0.22222], ["MA", 0.19944]])
    pred = (["customer_state", "late_delivery_rate"], [["MA", 0.1994], ["AL", 0.2222]])
    assert results_match(*ref, *pred) == (True, "match")

def test_extra_predicted_columns_are_allowed() -> None:
    ref = (["state", "rate"], [["AL", 0.2222]])
    pred = (["state", "delivered_orders", "rate"], [["AL", 198, 0.2222]])
    assert results_match(*ref, *pred)[0]

def test_wrong_values_fail() -> None:
    ref = (["revenue"], [[15422461.77]])
    pred = (["revenue"], [[15400000.00]])
    ok, reason = results_match(*ref, *pred)
    assert not ok and "revenue" in reason

def test_row_count_mismatch_fails() -> None:
    ref = (["is_late", "score"], [[True, 2.27], [False, 4.29]])
    pred = (["is_late", "score"], [[True, 2.27], [False, 4.29], [None, 3.5]])
    ok, reason = results_match(*ref, *pred)
    assert not ok and "rows" in reason

def test_dates_and_timestamps_compare_by_day() -> None:
    ref = (["month"], [["2018-01-01"]])
    pred = (["month"], [["2018-01-01T00:00:00"]])
    assert results_match(*ref, *pred)[0]

def test_year_month_strings_match_first_day_of_month() -> None:
    ref = (["month", "orders"], [["2017-01-01", 800], ["2017-02-01", 1780]])
    pred = (["order_month", "order_count"], [["2017-02", 1780], ["2017-01", 800]])
    assert results_match(*ref, *pred)[0]