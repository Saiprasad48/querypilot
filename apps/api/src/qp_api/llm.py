"""One place to create chat models, so switching providers is a config change."""

from __future__ import annotations

import logging
import warnings
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

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
