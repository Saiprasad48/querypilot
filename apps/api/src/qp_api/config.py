"""Typed settings for the API and agent, loaded from env vars or the repo .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")
    # Model specs are "provider:model", e.g. "google_genai:gemini-2.5-flash"
    qp_model_fast: str = "google_genai:gemini-3.5-flash-lite"
    qp_model_smart: str = "google_genai:gemini-3.8-flash"
    # SecretStr: shown as ********** if settings are ever printed or logged
    google_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None


settings = Settings()
