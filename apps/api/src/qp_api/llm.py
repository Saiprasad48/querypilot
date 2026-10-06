"""One place to create chat models, so switching providers is a config change."""

from __future__ import annotations

import logging
import time
import warnings
from functools import lru_cache
from typing import Any, Literal

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from qp_api.config import settings

warnings.filterwarnings("ignore", message=r".*uses fixed sampling defaults.*")
logging.getLogger("google_genai.models").setLevel(logging.ERROR)


def get_chat_model(spec: str, **kwargs: Any) -> BaseChatModel:
    """Build a chat model from a 'provider:model' spec, passing the right credentials."""
    provider, sep, model = spec.partition(":")
    if not sep or not model:
        raise ValueError(f"Model spec must look like 'provider:model', got {spec!r}")
    creds: dict[str, Any] = {}
    if provider == "google_genai" and settings.google_api_key:
        creds["google_api_key"] = settings.google_api_key.get_secret_value()
    elif provider == "groq" and settings.groq_api_key:
        creds["api_key"] = settings.groq_api_key.get_secret_value()
    elif provider == "anthropic" and settings.anthropic_api_key:
        creds["api_key"] = settings.anthropic_api_key.get_secret_value()
    return init_chat_model(model, model_provider=provider, temperature=0, **creds, **kwargs)


def fast_model(**kwargs: Any) -> BaseChatModel:
    return get_chat_model(settings.qp_model_fast, **kwargs)


def smart_model(**kwargs: Any) -> BaseChatModel:
    return get_chat_model(settings.qp_model_smart, **kwargs)


Tier = Literal["smart", "fast", "backup"]
CHAINS: dict[str, tuple[str, ...]] = {
    "smart": ("smart", "fast", "backup"),
    "fast": ("fast", "backup"),
    "backup": ("backup",),
}


@lru_cache(maxsize=32)
def structured_chain(role: Tier, schema: type[BaseModel]) -> Runnable:
    """A model that returns `schema` (plus the raw message), with layered fallbacks.
    smart: smart -> fast -> backup;  fast: fast -> backup;  backup: backup only.
    """

    def build(spec: str, retries: int) -> Runnable:
        model = get_chat_model(spec, max_retries=retries, timeout=60)
        return model.with_structured_output(schema, include_raw=True)

    backup = build(settings.qp_model_backup, 1) if settings.qp_model_backup else None
    if role == "backup":
        if backup is None:
            raise ValueError("No backup model configured (QP_MODEL_BACKUP)")
        return backup
    fast = build(settings.qp_model_fast, 1)
    if backup is not None:
        fast = fast.with_fallbacks([backup])
    if role == "fast":
        return fast
    return build(settings.qp_model_smart, 0).with_fallbacks([fast])


def tier_ids() -> dict[str, str]:
    """Model id per tier, without the provider prefix."""
    return {
        "smart": settings.qp_model_smart.partition(":")[2],
        "fast": settings.qp_model_fast.partition(":")[2],
        "backup": (settings.qp_model_backup or "").partition(":")[2],
    }


def failed_tiers(role: str, answered_model: str, ids: dict[str, str]) -> list[str]:
    """Tiers that were tried and failed before `answered_model` answered.
    If the answering model is unknown, nothing is marked as failed.
    """
    failed: list[str] = []
    for tier in CHAINS[role]:
        if ids.get(tier) and answered_model.endswith(ids[tier]):
            return failed
        failed.append(tier)
    return []


class ModelBreaker:
    """Circuit breaker for one model tier: after a failure, skip it for `cooldown_s`."""

    def __init__(self, cooldown_s: float = 300) -> None:
        self.cooldown_s = cooldown_s
        self._open_until = 0.0

    def allow(self, now: float | None = None) -> bool:
        return (time.monotonic() if now is None else now) >= self._open_until

    def trip(self, now: float | None = None) -> None:
        self._open_until = (time.monotonic() if now is None else now) + self.cooldown_s


breakers: dict[str, ModelBreaker] = {"smart": ModelBreaker(), "fast": ModelBreaker()}


class SmartModelBreaker:
    """Circuit breaker: after the smart model fails (we got the fallback's answer),
    skip it for `cooldown_s` seconds instead of wasting a request on every call."""

    def __init__(self, smart_model_id: str | None = None, cooldown_s: float = 300) -> None:
        self.smart_model_id = smart_model_id or settings.qp_model_smart.partition(":")[2]
        self.cooldown_s = cooldown_s
        self._open_until = 0.0

    def allow(self) -> bool:
        return time.monotonic() >= self._open_until

    def record(self, answered_by: str) -> None:
        """Call after every smart attempt with the model name that actually answered."""
        if self.smart_model_id not in answered_by:
            self._open_until = time.monotonic() + self.cooldown_s


smart_breaker = SmartModelBreaker()
