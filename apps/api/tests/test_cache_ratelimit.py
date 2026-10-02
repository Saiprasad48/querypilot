import fakeredis

from qp_api.cache import LLMCache, cache_key
from qp_api.ratelimit import RateLimiter

T = 1_800_000_000.0  # a fixed timestamp at the start of a minute

def _redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis(decode_responses=True)

def test_per_minute_limit_blocks_then_resets_next_minute() -> None:
    limiter = RateLimiter(client=_redis(), per_minute=2, per_day=10, global_per_day=100)
    assert limiter.hit("alice", T).allowed
    assert limiter.hit("alice", T).allowed
    blocked = limiter.hit("alice", T)
    assert not blocked.allowed
    assert "per minute" in blocked.reason
    assert 0 < blocked.retry_after_s <= 60
    assert limiter.hit("alice", T + 60).allowed  # new minute window
    assert limiter.hit("bob", T).allowed  # other clients are unaffected

def test_global_daily_cap_applies_across_clients() -> None:
    limiter = RateLimiter(client=_redis(), per_minute=100, per_day=100, global_per_day=3)
    for client in ["a", "b", "c"]:
        assert limiter.hit(client, T).allowed
    assert not limiter.hit("d", T).allowed

def test_llm_cache_roundtrip_and_stable_keys() -> None:
    cache = LLMCache(client=_redis(), ttl_s=60)
    messages = [("system", "rules"), ("human", "question")]
    key = cache_key("fast", messages)
    assert key == cache_key("fast", messages)  # same input, same key
    assert key != cache_key("smart", messages)  # any change, new key
    assert cache.get(key) is None
    cache.set(key, {"parsed": {"sql": "SELECT 1"}, "model": "m"})
    assert cache.get(key) == {"parsed": {"sql": "SELECT 1"}, "model": "m"}