"""Typed settings for the API and agent, loaded from env vars or the repo .env file."""

from __future__ import annotations

from pathlib import Path

from psycopg.conninfo import make_conninfo
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")
    # Model specs are "provider:model", e.g. "google_genai:gemini-2.5-flash"
    qp_model_fast: str = "google_genai:gemini-3.5-flash-lite"
    qp_model_smart: str = "google_genai:gemini-3.8-flash"
    qp_model_backup: str | None = None  # another provider, used when the fast model fails
    # SecretStr: shown as ********** if settings are ever printed or logged
    google_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    # app database (conversation checkpoints)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    app_db: str = "app"
    app_db_user: str = "qp_app"
    app_db_password: SecretStr = SecretStr("")
    cors_origins: list[str] = ["http://localhost:3000"]
    @property
    def app_db_dsn(self) -> str:
        return make_conninfo(
            host=self.postgres_host,
            port=self.postgres_port,
            dbname=self.app_db,
            user=self.app_db_user,
            password=self.app_db_password.get_secret_value(),
        )
    # Redis: LLM cache and rate limits
    redis_url: str = "redis://localhost:6379/0"
    llm_cache_enabled: bool = True
    llm_cache_ttl_s: int = 7 * 24 * 3600
    rate_limit_per_minute: int = 5
    rate_limit_per_day: int = 25
    rate_limit_global_per_day: int = 400

settings = Settings()
