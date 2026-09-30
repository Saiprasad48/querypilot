"""Check that both configured models respond. Prints token usage."""

from qp_api.config import settings
from qp_api.llm import get_chat_model

for label, spec in [
    ("fast", settings.qp_model_fast),
    ("smart", settings.qp_model_smart),
]:
    reply = get_chat_model(spec).invoke("Reply with exactly: QueryPilot online")
    print(f"{label:<5} {spec:<40} -> {reply.text!r}  usage={reply.usage_metadata}")
