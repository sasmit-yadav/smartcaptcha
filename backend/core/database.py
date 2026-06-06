"""
Backend Database Layer - PostgreSQL.
Follows Phase 3.2 roadmap schema exactly.
Connection string via DATABASE_URL env var.
"""

import os
import json
import time
import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_values

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:sas%401234@localhost:5432/smartcaptcha",
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


def init_db():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Drop old tables to recreate with full ML feature columns
        cursor.execute("DROP TABLE IF EXISTS events CASCADE")
        cursor.execute("DROP TABLE IF EXISTS sessions CASCADE")
        cursor.execute("DROP TABLE IF EXISTS api_keys CASCADE")
        cursor.execute("DROP TABLE IF EXISTS projects CASCADE")
        cursor.execute("DROP TABLE IF EXISTS raw_events CASCADE")
        
        # Create projects table (Phase 3.2)
        cursor.execute("""
            CREATE TABLE projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                owner_id UUID NOT NULL,
                name VARCHAR(100) NOT NULL,
                allowed_domains TEXT[],
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Create api_keys table (Phase 3.2)
        cursor.execute("""
            CREATE TABLE api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id),
                key_hash VARCHAR(256) UNIQUE NOT NULL,
                key_prefix VARCHAR(12) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        # Create sessions table (Phase 3.2 + extended fields + event_count)
        cursor.execute("""
            CREATE TABLE sessions (
                id VARCHAR(36) PRIMARY KEY,
                project_id UUID REFERENCES projects(id),
                device_type VARCHAR(20),
                screen_width INT,
                screen_height INT,
                user_agent TEXT,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                label VARCHAR(10),
                risk_score FLOAT,
                event_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Create events table with individual ML feature columns (matches old SQLite structure)
        cursor.execute("""
            CREATE TABLE events (
                id BIGSERIAL PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL REFERENCES sessions(id),
                event_type VARCHAR(10) NOT NULL,
                t BIGINT,
                x INTEGER,
                y INTEGER,
                dist REAL,
                ang REAL,
                vel REAL,
                total_dist REAL,
                target TEXT,
                click_interval INTEGER,
                is_double BOOLEAN,
                tw INTEGER,
                th INTEGER,
                k TEXT,
                iki INTEGER,
                hold INTEGER,
                scroll_y INTEGER,
                scroll_vel REAL,
                scroll_rev BOOLEAN,
                scroll_pause BOOLEAN,
                state TEXT,
                action TEXT,
                force REAL,
                duration INTEGER,
                gesture TEXT,
                swipe_dist REAL,
                swipe_vel REAL,
                payload JSONB NOT NULL,
                received_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Create indexes
        for idx_sql in [
            "CREATE INDEX idx_events_session ON events(session_id)",
            "CREATE INDEX idx_events_type ON events(event_type)",
            "CREATE INDEX idx_events_received ON events(received_at)",
            "CREATE INDEX idx_sessions_created ON sessions(created_at)",
            "CREATE INDEX idx_sessions_label ON sessions(label)",
            "CREATE INDEX idx_sessions_project ON sessions(project_id)",
        ]:
            cursor.execute(idx_sql)
        conn.commit()
        print("[DB] PostgreSQL initialized (full ML feature schema)")
    finally:
        release_connection(conn)


def insert_session(session_data: dict, project_id: str = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Convert Unix timestamp (ms) to PostgreSQL timestamp
        start_time = session_data.get('startTime', 0)
        if start_time:
            from datetime import datetime
            start_timestamp = datetime.fromtimestamp(start_time / 1000)
        else:
            start_timestamp = None
        
        cursor.execute("""
            INSERT INTO sessions (
                id, project_id, device_type, screen_width, screen_height,
                user_agent, started_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(id) DO NOTHING
        """, (
            session_data.get('sessionId', ''),
            project_id,
            session_data.get('deviceType', 'unknown'),
            session_data.get('screenWidth', 0),
            session_data.get('screenHeight', 0),
            session_data.get('userAgent', ''),
            start_timestamp,
        ))
        conn.commit()
    finally:
        release_connection(conn)


def update_session_end(session_id: str, duration_ms: int = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if duration_ms:
            # Calculate ended_at from duration
            cursor.execute("""
                UPDATE sessions 
                SET ended_at = started_at + (interval '1 millisecond' * %s)
                WHERE id = %s
            """, (duration_ms, session_id))
        else:
            cursor.execute(
                "UPDATE sessions SET ended_at = NOW() WHERE id = %s",
                (session_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def insert_events_batch(session_id: str, events: list):
    if not events:
        return 0
    conn = get_connection()
    try:
        cursor = conn.cursor()
        rows = []
        for e in events:
            etype = e.get('type', 'unknown')
            rows.append((
                session_id, etype, e.get('t'),
                e.get('x'), e.get('y'), e.get('dist'), e.get('ang'),
                e.get('vel') if etype == 'mm' else None,
                e.get('totalDist'),
                e.get('target'), e.get('interval'), e.get('double'),
                e.get('tw'), e.get('th'),
                e.get('k'), e.get('iki'), e.get('hold'),
                e.get('y') if etype == 'sc' else None,
                e.get('vel') if etype == 'sc' else None,
                e.get('rev'), e.get('pause'),
                e.get('state'),
                e.get('action'), e.get('force'), e.get('duration'),
                e.get('gesture'), e.get('swipeDist'), e.get('swipeVel'),
                json.dumps(e),
            ))
        execute_values(
            cursor,
            """INSERT INTO events (
                session_id, event_type, t,
                x, y, dist, ang, vel, total_dist,
                target, click_interval, is_double, tw, th,
                k, iki, hold,
                scroll_y, scroll_vel, scroll_rev, scroll_pause,
                state,
                action, force, duration, gesture, swipe_dist, swipe_vel,
                payload
            ) VALUES %s""",
            rows,
            template="""(%s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s,
                %s, %s, %s, %s, %s, %s,
                %s::jsonb)""",
        )
        cursor.execute(
            "UPDATE sessions SET event_count = event_count + %s WHERE id = %s",
            (len(events), session_id),
        )
        conn.commit()
        return len(rows)
    finally:
        release_connection(conn)


def get_session_stats():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sessions")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM events")
        with_events = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(event_count), 0) FROM sessions")
        total_events = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE created_at > NOW() - INTERVAL '1 hour'")
        recent = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM events")
        raw_events = cursor.fetchone()[0]
        return {
            "total_sessions": total,
            "sessions_with_events": with_events,
            "total_events": total_events,
            "raw_event_rows": raw_events,
            "sessions_last_hour": recent,
            "database": "postgresql",
        }
    finally:
        release_connection(conn)
