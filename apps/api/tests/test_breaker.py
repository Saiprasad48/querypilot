from qp_api.llm import ModelBreaker, failed_tiers

IDS = {
    "smart": "gemini-3.8-flash",
    "fast": "gemini-3.5-flash-lite",
    "backup": "openai/gpt-oss-120b",
}


def test_breaker_trips_then_recovers_after_cooldown() -> None:
    breaker = ModelBreaker(cooldown_s=60)
    assert breaker.allow(now=1000)
    breaker.trip(now=1000)
    assert not breaker.allow(now=1030)
    assert breaker.allow(now=1061)


def test_failed_tiers_follow_the_fallback_chain() -> None:
    assert failed_tiers("smart", "gemini-3.8-flash", IDS) == []
    assert failed_tiers("smart", "gemini-3.5-flash-lite", IDS) == ["smart"]
    assert failed_tiers("smart", "openai/gpt-oss-120b", IDS) == ["smart", "fast"]
    assert failed_tiers("fast", "openai/gpt-oss-120b", IDS) == ["fast"]
    assert failed_tiers("fast", "some-unknown-model", IDS) == []
