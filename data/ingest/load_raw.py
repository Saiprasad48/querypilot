"""Load the Olist CSVs into the warehouse `raw` schema.

ELT approach: every column is loaded as TEXT exactly as it appears in the source.
Typing, cleaning and business logic happen later in dbt staging models.

Uses Postgres COPY (streamed) instead of row inserts, so ~1.5M rows load in seconds.
The whole load runs in one transaction: it either fully succeeds or changes nothing.
"""

from __future__ import annotations
import csv
import os
import re
import sys
import time
from pathlib import Path
import psycopg
from dotenv import load_dotenv
from psycopg import sql

ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = ROOT / "data" / "raw" / "olist"

# raw table name -> source file
TABLES: dict[str, str] = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

def conninfo() -> str:
    """Build the admin connection string from .env."""
    load_dotenv(ROOT / ".env")
    return psycopg.conninfo.make_conninfo(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("WAREHOUSE_DB", "warehouse"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )

def clean_name(name: str) -> str:
    """Normalize a CSV header into a safe snake_case column name."""
    return re.sub(r"[^a-z0-9_]", "_", name.strip().lower())

def read_header(path: Path) -> list[str]:
    # utf-8-sig strips the byte order mark some of these files start with
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [clean_name(c) for c in next(csv.reader(f))]

def count_csv_rows(path: Path) -> int:
    # csv.reader handles review comments that contain line breaks
    with path.open(encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # minus header

def load_table(cur: psycopg.Cursor, table: str, path: Path) -> int:
    cols = read_header(path)
    target = sql.Identifier("raw", table)
    cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(target))
    cur.execute(
        sql.SQL("CREATE TABLE {} ({}, _loaded_at timestamptz NOT NULL DEFAULT now())").format(
            target,
            sql.SQL(", ").join(sql.SQL("{} text").format(sql.Identifier(c)) for c in cols),
        )
    )
    copy_stmt = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true)").format(
        target, sql.SQL(", ").join(map(sql.Identifier, cols))
    )
    with path.open("rb") as f, cur.copy(copy_stmt) as copy:
        while chunk := f.read(1 << 20):  # stream in 1 MB chunks
            copy.write(chunk)
    cur.execute(sql.SQL("SELECT count(*) FROM {}").format(target))
    return cur.fetchone()[0]

def main() -> int:
    missing = [f for f in TABLES.values() if not (CSV_DIR / f).exists()]
    if missing:
        print(f"Missing files in {CSV_DIR}:")
        for f in missing:
            print(f"  {f}")
        return 1
    started = time.perf_counter()
    total = 0
    print(f"{'table':<22}{'rows':>12}{'csv rows':>12}{'secs':>8}")
    with psycopg.connect(conninfo()) as conn, conn.cursor() as cur:
        for table, filename in TABLES.items():
            path = CSV_DIR / filename
            t0 = time.perf_counter()
            loaded = load_table(cur, table, path)
            expected = count_csv_rows(path)
            print(f"raw.{table:<18}{loaded:>12,}{expected:>12,}{time.perf_counter() - t0:>8.1f}")
            if loaded != expected:
                raise RuntimeError(f"Row count mismatch for {table}: {loaded} vs {expected}")
            total += loaded
        # leaving the `with` block commits the transaction
    print(f"\nLoaded {total:,} rows into {len(TABLES)} tables in {time.perf_counter() - started:.1f}s")
    return 0

if __name__ == "__main__":
    sys.exit(main())