"""Measure the smart model's latency with retries off, under different thinking settings."""

import time

from qp_api.config import settings
from qp_api.llm import get_chat_model

PROMPT = (
    "Write one PostgreSQL query: the top 5 customer_state values by late delivery rate in 2018 "
    "from marts.fct_orders(customer_state text, is_late boolean, order_status text, "
    "purchase_date date). Only count delivered orders. Return only the SQL."
)
VARIANTS = [
    ("default", {}),
    ("thinking_level=low", {"thinking_level": "low"}),
    ("thinking_budget=0", {"thinking_budget": 0}),
]
for label, extra in VARIANTS:
    started = time.perf_counter()
    try:
        model = get_chat_model(settings.qp_model_smart, max_retries=0, **extra)
        reply = model.invoke(PROMPT)
        meta = reply.usage_metadata or {}
        reasoning = meta.get("output_token_details", {}).get("reasoning", 0)
        print(
            f"{label:<22} {time.perf_counter() - started:5.1f}s  "
            f"out={meta.get('output_tokens')} reasoning={reasoning}"
        )
    except Exception as e:  # noqa: BLE001  (diagnostic script: report any failure)
        print(f"{label:<22} ERROR {type(e).__name__}: {str(e)[:250]}")
    time.sleep(5)  # stay gentle with free tier rate limits
