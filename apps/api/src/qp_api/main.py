"""FastAPI application: wires the agent graph, Postgres checkpointer, and routes."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from qp_mcp.schema_index import get_model

from qp_api.agent.graph import build_graph
from qp_api.config import settings
from qp_api.routes import ask, health

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # A pool lets concurrent requests save checkpoints without sharing one connection.
    get_model()  # load the embedding model now, not during the first user's request
    pool = ConnectionPool(
        conninfo=settings.app_db_dsn,
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    )
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()  # creates checkpoint tables on first run; safe to repeat
    app.state.pool = pool
    app.state.graph = build_graph(checkpointer=checkpointer)
    yield
    pool.close()


app = FastAPI(title="QueryPilot API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Client-Id"],
    expose_headers=["X-RateLimit-Remaining", "Retry-After"],
)
app.include_router(health.router)
app.include_router(ask.router)
