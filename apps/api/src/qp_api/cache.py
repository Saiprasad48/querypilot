"""Redis helpers: one shared client and an LLM response cache that never breaks a request."""

from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache
from typing import Any

import redis

from qp_api.config import settings

logger = logging.getLogger("qp_api")

@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(
        settings.redis_url, decode_responses=True, socket_timeout=1, socket_connect_timeout=1
    )

def cache_key(*parts: Any) -> str:
    """Stable key from any JSON serializable parts (prompt, model, schema...)."""
    raw = json.dumps(parts, sort_keys=True, default=str)
    return "llm:" + hashlib.sha256(raw.encode()).hexdigest()

class LLMCache:
    """Stores structured LLM outputs. If Redis fails, it logs and behaves like a cache miss."""
    def __init__(self, client: redis.Redis | None = None, ttl_s: int | None = None) -> None:
        self._client = client
        self.ttl_s = ttl_s or settings.llm_cache_ttl_s
    @property
    def client(self) -> redis.Redis:
        return self._client or get_redis()
    def get(self, key: str) -> dict[str, Any] | None:
        try:
            raw = self.client.get(key)
        except redis.RedisError as e:
            logger.warning("LLM cache read failed, continuing without cache: %s", e)
            return None
        return json.loads(raw) if raw else None
    def set(self, key: str, value: dict[str, Any]) -> None:
        try:
            self.client.set(key, json.dumps(value, default=str), ex=self.ttl_s)
        except redis.RedisError as e:
            logger.warning("LLM cache write failed: %s", e)

llm_cache = LLMCache()