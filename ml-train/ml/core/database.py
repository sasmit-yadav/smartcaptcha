"""Offline database access for the ml-train pipeline.

This is deliberately a minimal, read/write-features-only module — the full
schema management (table creation, migrations, ingestion) lives in
sdk-backend/core/database.py, which is the single production owner of the
database. ml-train only needs a connection to read `sessions`/`events` and
read/write `session_features`.

DATABASE_URL resolution order:
1. Already present in the environment.
2. ml-train/.env
3. sdk-backend/.env (the production service's local env file — same DB)
"""

import os
from pathlib import Path

import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

_ML_TRAIN_ROOT = Path(__file__).resolve().parents[2]   # ml-train/
_REPO_ROOT = _ML_TRAIN_ROOT.parent                     # repo root

load_dotenv(_ML_TRAIN_ROOT / ".env")
load_dotenv(_REPO_ROOT / "sdk-backend" / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Put it in ml-train/.env (or rely on "
        "sdk-backend/.env). Credentials must never be hardcoded."
    )

_conn_pool = None


def _get_pool():
    global _conn_pool
    if _conn_pool is None or _conn_pool.closed:
        _conn_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1, maxconn=5, dsn=DATABASE_URL
        )
    return _conn_pool


def get_connection():
    return _get_pool().getconn()


def release_connection(conn):
    _get_pool().putconn(conn)


def init_db():
    """Sanity-check that the tables ml-train depends on exist.

    Unlike sdk-backend's init_db(), this never creates or migrates anything —
    schema ownership stays with the production service. It only fails fast
    with a clear message if the offline pipeline is pointed at a database
    that isn't the real one.
    """
    required = ("sessions", "events", "session_features")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ANY(%s)
            """,
            (list(required),),
        )
        found = {row[0] for row in cursor.fetchall()}
        cursor.close()
        missing = set(required) - found
        if missing:
            raise RuntimeError(
                f"Database is missing required tables: {sorted(missing)}. "
                "ml-train expects the production schema (owned by sdk-backend)."
            )
    finally:
        release_connection(conn)
