# QueryPilot API: FastAPI + LangGraph agent + in process MCP tools.
# Build from the repo root:  docker build -f apps/api/Dockerfile -t querypilot-api .

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Non root user: the app never needs root at runtime
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/.cache \
    && chown -R app:app /app
WORKDIR /app
COPY --chown=app:app apps/mcp_server /app/apps/mcp_server
COPY --chown=app:app apps/api /app/apps/api
USER app

WORKDIR /app/apps/api
RUN uv sync --locked --no-dev
ENV PATH="/app/apps/api/.venv/bin:$PATH"

# Download the embedding model at BUILD time, so the running app never needs
# huggingface.co and the first question isn't slowed by a download.
RUN python -c "from qp_mcp.schema_index import get_model; get_model()"

EXPOSE 8000
# Render sets $PORT. --proxy-headers makes the real client IP visible behind
# Render's proxy, which the per client rate limiter relies on.
CMD ["sh", "-c", "uvicorn qp_api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*' --workers 1"]