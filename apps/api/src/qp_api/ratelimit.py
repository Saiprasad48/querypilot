"""Fixed window rate limits in Redis.

Per client: N per minute and M per day. Global: a daily cap across everyone, which protects
the free LLM quota. If Redis is unavailable we fail OPEN (allow) and log a warning.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import redis

from qp_api.cache import get_redis
from qp_api.config import settings

logger = logging.getLogger("qp_api")

@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining_today: int
    retry_after_s: int = 0
    reason: str = ""

class RateLimiter:
    def __init__(
        self,
        client: redis.Redis | None = None,
        per_minute: int | None = None,
        per_day: int | None = None,
        global_per_day: int | None = None,
    ) -> None:
        self._client = client
        self.per_minute = per_minute or settings.rate_limit_per_minute
        self.per_day = per_day or settings.rate_limit_per_day
        self.global_per_day = global_per_day or settings.rate_limit_global_per_day
    @property
    def client(self) -> redis.Redis:
        return self._client or get_redis()
    def hit(self, client_id: str, now: float | None = None) -> RateLimitResult:
        """Count one question for `client_id` and say whether it is allowed."""
        now = time.time() if now is None else now
        day = time.strftime("%Y%m%d", time.gmtime(now))
        until_minute_end = 60 - int(now % 60)
        until_midnight_utc = 86400 - int(now % 86400)
        windows = [
            (f"rl:{client_id}:m:{int(now // 60)}", self.per_minute, 60, until_minute_end, "per minute"),
            (f"rl:{client_id}:d:{day}", self.per_day, 86400, until_midnight_utc, "daily"),
            (f"rl:global:d:{day}", self.global_per_day, 86400, until_midnight_utc, "global daily"),
        ]
        try:
            pipe = self.client.pipeline()
            for key, _, ttl, _, _ in windows:
                pipe.incr(key)
                pipe.expire(key, ttl, nx=True)  # set the TTL only when the window starts
            counts = pipe.execute()[0::2]
        except redis.RedisError as e:
            logger.warning("Rate limiter unavailable, allowing request: %s", e)
            return RateLimitResult(allowed=True, remaining_today=self.per_day)
        remaining = max(self.per_day - counts[1], 0)
        for (_, limit, _, retry_after, label), count in zip(windows, counts, strict=True):
            if count > limit:
                return RateLimitResult(
                    False, remaining, retry_after, f"{label} limit of {limit} questions reached"
                )
        return RateLimitResult(True, remaining)

rate_limiter = RateLimiter()