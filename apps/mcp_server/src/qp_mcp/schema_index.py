"""Vector + keyword index over the marts schema: tables, columns and business metrics.

build:  reads dbt manifest.json (descriptions), information_schema (types) and
        metrics.yml; embeds each item locally with fastembed; stores everything in the
        meta schema (schema_docs + metrics) so runtime tools only need the database.
search: hybrid retrieval (pgvector cosine + Postgres full text) fused with RRF.
"""

from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
import argparse
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import psycopg
import yaml
from fastembed import TextEmbedding
from pgvector.psycopg import register_vector

from qp_mcp.config import settings

EMBED_DIM = 384  # bge-small-en-v1.5
RRF_K = 60  # standard Reciprocal Rank Fusion constant

DDL = f"""
CREATE TABLE IF NOT EXISTS meta.schema_docs (
    id          bigserial PRIMARY KEY,
    kind        text NOT NULL CHECK (kind IN ('table', 'column', 'metric')),
    table_name  text NOT NULL,
    name        text,              -- column name or metric name; null for tables
    data_type   text,
    content     text NOT NULL,     -- the text that was embedded
    embedding   vector({EMBED_DIM}) NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE meta.schema_docs ADD COLUMN IF NOT EXISTS description text;
ALTER TABLE meta.schema_docs
    ADD COLUMN IF NOT EXISTS content_tsv tsvector
    GENERATED ALWAYS AS (
            to_tsvector('english', replace(replace(content, '_', ' '), '.', ' '))
    ) STORED;
CREATE INDEX IF NOT EXISTS schema_docs_embedding_idx
    ON meta.schema_docs USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS schema_docs_tsv_idx
    ON meta.schema_docs USING gin (content_tsv);
CREATE TABLE IF NOT EXISTS meta.metrics (
    name        text PRIMARY KEY,
    label       text NOT NULL,
    description text NOT NULL,
    table_name  text NOT NULL,     -- e.g. marts.fct_orders
    expression  text NOT NULL,     -- e.g. sum(payment_value)
    filter      text,              -- e.g. order_status = 'delivered'
    unit        text,
    synonyms    text[] NOT NULL DEFAULT '{{}}'
);
"""


@dataclass(frozen=True)
class Doc:
    kind: str
    table_name: str
    name: str | None
    data_type: str | None
    content: str
    description: str | None = None


@dataclass(frozen=True)
class Hit:
    kind: str
    table_name: str
    name: str | None
    content: str
    score: float


@lru_cache(maxsize=1)
def get_model() -> TextEmbedding:
    """Load the embedding model from the local cache; download only if it's missing."""
    kwargs = {
        "model_name": settings.embedding_model,
        "cache_dir": str(settings.embedding_cache_dir),
    }
    try:
        return TextEmbedding(**kwargs, local_files_only=True)
    except Exception:
        return TextEmbedding(**kwargs)


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def load_manifest_models() -> dict[str, dict[str, Any]]:
    manifest = json.loads(settings.dbt_manifest_path.read_text(encoding="utf-8"))
    return {
        node["name"]: node
        for node in manifest["nodes"].values()
        if node["resource_type"] == "model" and node["schema"] == "marts"
    }


def load_db_columns(conn: psycopg.Connection) -> dict[str, list[tuple[str, str]]]:
    rows = conn.execute(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'marts'
        ORDER BY table_name, ordinal_position
        """
    ).fetchall()
    columns: dict[str, list[tuple[str, str]]] = {}
    for table, column, dtype in rows:
        columns.setdefault(table, []).append((column, dtype))
    return columns


def load_metrics() -> list[dict[str, Any]]:
    return yaml.safe_load(settings.metrics_path.read_text(encoding="utf-8"))["metrics"]


def build_docs(
    models: dict[str, dict[str, Any]],
    columns: dict[str, list[tuple[str, str]]],
    metrics: list[dict[str, Any]],
) -> list[Doc]:
    """Pure function: turn metadata into the text documents we embed."""
    docs: list[Doc] = []
    for table, cols in columns.items():
        node = models.get(table, {})
        col_meta = node.get("columns", {})
        table_desc = _clean(node.get("description"))
        col_list = ", ".join(c for c, _ in cols)
        docs.append(
            Doc(
                "table",
                table,
                None,
                None,
                f"Table marts.{table}: {table_desc} Columns: {col_list}.",
                table_desc,
            )
        )
        for col, dtype in cols:
            desc = _clean(col_meta.get(col, {}).get("description"))
            docs.append(
                Doc(
                    "column",
                    table,
                    col,
                    dtype,
                    f"Column marts.{table}.{col} ({dtype}): {desc}".strip(),
                    desc,
                )
            )
    for m in metrics:
        table = m["table"].split(".")[-1]
        synonyms = ", ".join(m.get("synonyms", []))
        desc = _clean(m["description"])
        docs.append(
            Doc(
                "metric",
                table,
                m["name"],
                None,
                f"Metric {m['name']} ({m['label']}): {desc} "
                f"Synonyms: {synonyms}. Computed on marts.{table}.",
                desc,
            )
        )
    return docs


def build_index() -> tuple[int, int]:
    metrics = load_metrics()
    with psycopg.connect(settings.admin_dsn) as conn:
        register_vector(conn)
        conn.execute(DDL)
        docs = build_docs(load_manifest_models(), load_db_columns(conn), metrics)
        vectors = list(get_model().passage_embed([d.content for d in docs]))
        with conn.cursor() as cur:
            cur.execute("TRUNCATE meta.schema_docs")
            cur.executemany(
                """
                INSERT INTO meta.schema_docs
                    (kind, table_name, name, data_type, description, content, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (d.kind, d.table_name, d.name, d.data_type, d.description, d.content, v)
                    for d, v in zip(docs, vectors, strict=True)
                ],
            )
            cur.execute("TRUNCATE meta.metrics")
            cur.executemany(
                """
                INSERT INTO meta.metrics
                    (name, label, description, table_name, expression, filter, unit, synonyms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        m["name"],
                        m["label"],
                        _clean(m["description"]),
                        m["table"],
                        m["expression"],
                        m.get("filter"),
                        m.get("unit"),
                        m.get("synonyms", []),
                    )
                    for m in metrics
                ],
            )
    return len(docs), len(metrics)


def _keyword_query(text: str) -> str:
    """Build an OR style tsquery from plain words, e.g. 'which | states | late'.
    Only letters are kept, so user input can never inject tsquery syntax.
    Postgres removes stop words and stems the rest ('states' -> 'state').
    """
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return " | ".join(words)


def search(query: str, k: int = 12) -> list[Hit]:
    """Hybrid search: vector similarity + keyword match, merged with RRF.
    Runs as the read only role: this is what the agent calls at runtime.
    """
    qvec = next(iter(get_model().query_embed(query)))
    params = {"qvec": qvec, "tsq": _keyword_query(query) or "none", "k": k, "rrf": RRF_K}
    with psycopg.connect(settings.reader_dsn) as conn:
        register_vector(conn)
        rows = conn.execute(
            """
            WITH vec AS (
                SELECT id, row_number() OVER (ORDER BY embedding <=> %(qvec)s) AS rnk
                FROM meta.schema_docs
                ORDER BY embedding <=> %(qvec)s
                LIMIT 40
            ),
            kw AS (
                SELECT id, row_number() OVER (ORDER BY ts_rank_cd(content_tsv, q) DESC) AS rnk
                FROM meta.schema_docs, to_tsquery('english', %(tsq)s) AS q
                WHERE content_tsv @@ q
                ORDER BY ts_rank_cd(content_tsv, q) DESC
                LIMIT 40
            )
            SELECT d.kind, d.table_name, d.name, d.content,
                (coalesce(1.0 / (%(rrf)s + vec.rnk), 0)
                + coalesce(1.0 / (%(rrf)s + kw.rnk), 0))::float8 AS score
            FROM meta.schema_docs d
            LEFT JOIN vec ON vec.id = d.id
            LEFT JOIN kw  ON kw.id  = d.id
            WHERE vec.id IS NOT NULL OR kw.id IS NOT NULL
            ORDER BY score DESC
            LIMIT %(k)s
            """,
            params,
        ).fetchall()
    return [
        Hit(kind, table, name, content, float(score)) for kind, table, name, content, score in rows
    ]


def main() -> None:
    parser = argparse.ArgumentParser(prog="qp-index", description="Schema vector index")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="Rebuild meta.schema_docs and meta.metrics")
    s = sub.add_parser("search", help="Find schema items relevant to a question")
    s.add_argument("query")
    s.add_argument("-k", type=int, default=8)
    args = parser.parse_args()
    if args.cmd == "build":
        n_docs, n_metrics = build_index()
        print(f"Indexed {n_docs} documents and {n_metrics} metrics into the meta schema")
    else:
        for h in search(args.query, args.k):
            label = f"{h.table_name}.{h.name}" if h.name else h.table_name
            print(f"{h.score:.4f}  {h.kind:<7} {label}")


if __name__ == "__main__":
    main()
