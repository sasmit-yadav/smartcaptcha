"""
Migration: Add CHECK constraint for label column to support 'client' and 'demo' labels.
Run this after database initialization to ensure the constraint exists.
"""

import os
import psycopg2
from psycopg2 import pool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.xroqpyuenhowuaueiiwu:sasyrao%401234@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
)

_conn_pool = None


def _get_pool():
    global _conn_pool
    if _conn_pool is None or _conn_pool.closed:
        _conn_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=2, maxconn=20, dsn=DATABASE_URL
        )
    return _conn_pool


def get_connection():
    return _get_pool().getconn()


def release_connection(conn):
    _get_pool().putconn(conn)


def migrate():
    """Add CHECK constraint for label column to support 'client' and 'demo' labels."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # PostgreSQL doesn't support ALTER TABLE to add CHECK constraint with IF NOT EXISTS
        # So we try to add it and ignore if it already exists
        try:
            cursor.execute("""
                ALTER TABLE sessions 
                ADD CONSTRAINT sessions_label_check 
                CHECK (label IN ('human', 'bot', 'client', 'demo'))
            """)
            conn.commit()
            print("[Migration] Added CHECK constraint for label column")
        except Exception as e:
            # Constraint likely already exists, ignore
            print(f"[Migration] Constraint may already exist: {e}")
    finally:
        release_connection(conn)


if __name__ == "__main__":
    migrate()
