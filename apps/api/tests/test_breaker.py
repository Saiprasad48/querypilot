from qp_api.llm import SmartModelBreaker


def test_breaker_opens_when_fallback_answered() -> None:
    breaker = SmartModelBreaker(smart_model_id="gemini-3.8-flash", cooldown_s=60)
    assert breaker.allow()
    breaker.record("gemini-3.5-flash-lite")  # the fallback answered, so smart failed
    assert not breaker.allow()

def test_breaker_stays_closed_when_smart_answers() -> None:
    breaker = SmartModelBreaker(smart_model_id="gemini-3.8-flash", cooldown_s=60)
    breaker.record("gemini-3.8-flash")
    assert breaker.allow()