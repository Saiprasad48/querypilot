"""Typed settings loaded from environment variables, falling back to the repo .env file."""

from __future__ import annotations

import os
from pathlib import Path

from psycopg.conninfo import make_conninfo
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = os.environ.get("QP_ENV_FILE") or REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")
    postgres_sslmode: str = "prefer"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    warehouse_db: str = "warehouse"
    # admin: used only by offline jobs (index builder). Never used by the agent.
    postgres_user: str = "qp_admin"
    postgres_password: str = ""
    # reader: the only account the agent and MCP tools use at runtime
    reader_user: str = "qp_reader"
    reader_password: str = ""
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_cache_dir: Path = REPO_ROOT / ".cache" / "fastembed"
    max_query_cost: float = 500_000.0  # explain_sql flags plans above this cost
    dbt_manifest_path: Path = REPO_ROOT / "data" / "dbt" / "target" / "manifest.json"
    metrics_path: Path = REPO_ROOT / "data" / "semantic" / "metrics.yml"

    @property
    def admin_dsn(self) -> str:
        return make_conninfo(
            host=self.postgres_host,
            port=self.postgres_port,
            dbname=self.warehouse_db,
            user=self.postgres_user,
            password=self.postgres_password,
            sslmode=self.postgres_sslmode,
        )

    @property
    def reader_dsn(self) -> str:
        # public is on the path only so pgvector's type and operators resolve;
        # table access is still limited by grants and the SQL guard.
        return make_conninfo(
            host=self.postgres_host,
            port=self.postgres_port,
            dbname=self.warehouse_db,
            user=self.reader_user,
            password=self.reader_password,
            sslmode=self.postgres_sslmode,
            options="-c search_path=marts,public",
        )


settings = Settings()
