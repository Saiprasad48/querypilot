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
    return init_chat_model(
        model, model_provider=provider, temperature=0, **creds, **kwargs
    )

def fast_model(**kwargs: Any) -> BaseChatModel:
    return get_chat_model(settings.qp_model_fast, **kwargs)

def smart_model(**kwargs: Any) -> BaseChatModel:
    return get_chat_model(settings.qp_model_smart, **kwargs)

@lru_cache(maxsize=32)
def structured_chain(
    role: Literal["fast", "smart"], schema: type[BaseModel]
) -> Runnable:
    """A model that returns `schema` (plus the raw message), with fallback for 'smart'.
    smart: try the smart model once (no retries, short timeout); on ANY error
           (429 quota, 503 overload, timeout) fall back to the fast model.
    fast:  the fast model with a couple of retries.
    """
    fast = get_chat_model(settings.qp_model_fast, max_retries=2, timeout=60)
    fast_chain = fast.with_structured_output(schema, include_raw=True)
    if role == "fast":
        return fast_chain
    smart = get_chat_model(settings.qp_model_smart, max_retries=0, timeout=60)
    smart_chain = smart.with_structured_output(schema, include_raw=True)
    return smart_chain.with_fallbacks([fast_chain])

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