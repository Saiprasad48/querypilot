"""Liveness and readiness probes for the hosting platform."""

from typing import Any

import psycopg
from fastapi import APIRouter, Request, Response
from qp_mcp.config import settings as warehouse_settings

router = APIRouter(tags=["health"])

@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: the process is up. Never touches dependencies."""
    return {"status": "ok"}

@router.get("/readyz")
def readyz(request: Request, response: Response) -> dict[str, Any]:
    """Readiness: both databases answer. Returns 503 if either is down."""
    checks: dict[str, str] = {}
    try:
        with psycopg.connect(warehouse_settings.reader_dsn, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        checks["warehouse"] = "ok"
    except psycopg.Error as e:
        checks["warehouse"] = f"error: {type(e).__name__}"
    try:
        with request.app.state.pool.connection(timeout=3) as conn:
            conn.execute("SELECT 1")
        checks["app_db"] = "ok"
    except Exception as e:  # noqa: BLE001  (pool raises several error types; report any)
        checks["app_db"] = f"error: {type(e).__name__}"

    ready = all(v == "ok" for v in checks.values())
    response.status_code = 200 if ready else 503
    return {"ready": ready, "checks": checks}