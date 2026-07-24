"""
Backend Database Layer - PostgreSQL.
Follows Phase 3.2 roadmap schema exactly.
Connection string via DATABASE_URL env var.
"""

import os
import json
import time
import random
import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_values

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Set it to your PostgreSQL connection string (e.g. in a local .env "
        "or the Render dashboard in production). Credentials must never be hardcoded."
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


def _coerce_bool(val):
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('true', '1', 'yes')
    return bool(val)


def _event_bool(event: dict, *keys, default=None):
    for key in keys:
        if key in event and event[key] is not None:
            return _coerce_bool(event[key])
    return default


def _migrate_events_columns(cursor):
    """Ensure ML feature columns exist on databases created before the full schema."""
    columns = [
        ("is_double", "BOOLEAN"),
        ("scroll_rev", "BOOLEAN"),
        ("scroll_pause", "BOOLEAN"),
        ("scroll_y", "INTEGER"),
        ("scroll_vel", "REAL"),
        ("click_interval", "INTEGER"),
        ("hover_duration", "INTEGER"),  # V2 telemetry
        ("overshoot_ratio", "REAL"),   # V2 telemetry
    ]
    for name, col_type in columns:
        cursor.execute(
            f"ALTER TABLE events ADD COLUMN IF NOT EXISTS {name} {col_type}"
        )


def _migrate_session_features_columns(cursor):
    """Ensure richer V2 ML feature columns exist without resetting collected data."""
    columns = [
        ("mouse_vel_p10", "REAL"),
        ("mouse_vel_p50", "REAL"),
        ("mouse_vel_p90", "REAL"),
        ("mouse_accel_mean", "REAL"),
        ("mouse_accel_std", "REAL"),
        ("mouse_accel_max", "REAL"),
        ("mouse_angle_std", "REAL"),
        ("mouse_angle_p90", "REAL"),
        ("mouse_path_efficiency", "REAL"),
        ("mouse_idle_gap_count", "INTEGER"),
        ("mouse_event_ratio", "REAL"),
        ("click_interval_std", "REAL"),
        ("click_interval_min", "REAL"),
        ("click_interval_p90", "REAL"),
        ("double_click_count", "INTEGER"),
        ("key_count", "INTEGER"),
        ("iki_p10", "REAL"),
        ("iki_p50", "REAL"),
        ("iki_p90", "REAL"),
        ("hold_std", "REAL"),
        ("hold_p90", "REAL"),
        ("backspace_count", "INTEGER"),
        ("scroll_vel_std", "REAL"),
        ("scroll_rev_count", "INTEGER"),
        ("scroll_pause_count", "INTEGER"),
        ("focus_event_count", "INTEGER"),
        ("touch_event_count", "INTEGER"),
        ("event_rate", "REAL"),
        ("pause_count", "INTEGER"),
        ("pause_ratio", "REAL"),
        ("mouse_curvature_std", "REAL"),
        ("mouse_jerk_std", "REAL"),
        ("movement_entropy", "REAL"),
        ("avg_hover_duration", "REAL"),
        ("hover_duration_std", "REAL"),
        ("avg_overshoot_ratio", "REAL"),
        ("overshoot_ratio_std", "REAL"),
        # V5 neuromotor (STEP3_STEP8_IMPLEMENTATION_SPEC.md §3.2 power law + §3.4 keystroke)
        ("mouse_powerlaw_beta", "REAL"),
        ("mouse_powerlaw_r2", "REAL"),
        ("key_dwell_cv", "REAL"),
        ("key_flight_cv", "REAL"),
        ("key_digraph_std", "REAL"),
        # V5b neuromotor tremor (§3.3, gated on §3.1 sampling upgrade)
        ("mouse_tremor_band_ratio", "REAL"),
        ("mouse_tremor_peak_freq", "REAL"),
    ]
    for name, col_type in columns:
        cursor.execute(
            f"ALTER TABLE session_features ADD COLUMN IF NOT EXISTS {name} {col_type}"
        )


def init_db():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # By default do NOT drop existing tables to avoid data loss in production.
        # Allow explicit reset by setting RESET_DB_ON_START=1 in the environment (development only).
        reset_db = os.getenv("RESET_DB_ON_START", "0") == "1"
        if reset_db:
            cursor.execute("DROP TABLE IF EXISTS events CASCADE")
            cursor.execute("DROP TABLE IF EXISTS sessions CASCADE")
            cursor.execute("DROP TABLE IF EXISTS api_keys CASCADE")
            cursor.execute("DROP TABLE IF EXISTS projects CASCADE")
            cursor.execute("DROP TABLE IF EXISTS raw_events CASCADE")
        
        # Create projects table (Phase 3.2)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                owner_id UUID NOT NULL,
                name VARCHAR(100) NOT NULL,
                allowed_domains TEXT[],
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Create api_keys table (Phase 3.2)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id),
                key_hash VARCHAR(256) UNIQUE NOT NULL,
                key_prefix VARCHAR(12) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE,
                last_used_at TIMESTAMP
            )
        """)
        # Safe auto-migration for existing tables
        cursor.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMP")

        # Site/secret key split (siteverify token flow). Existing keys (created
        # before this column existed) are backfilled to 'legacy' — they keep
        # working on predict/telemetry but are never accepted as secret keys.
        cursor.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS key_type VARCHAR(10)")
        cursor.execute("UPDATE api_keys SET key_type = 'legacy' WHERE key_type IS NULL")
        cursor.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP")

        # Dashboard auth refresh tokens (opaque, hashed, rotatable)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                token_hash VARCHAR(64) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                revoked_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                user_agent TEXT,
                ip TEXT
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_auth_refresh_user ON auth_refresh_tokens (user_id)"
        )
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_password_reset_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                token_hash VARCHAR(64) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                user_agent TEXT,
                ip TEXT
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_auth_reset_user ON auth_password_reset_tokens (user_id)"
        )
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_email_verify_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                token_hash VARCHAR(64) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                user_agent TEXT,
                ip TEXT
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_auth_verify_user ON auth_email_verify_tokens (user_id)"
        )
        cursor.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS has_password BOOLEAN DEFAULT TRUE"
        )
        cursor.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_linked BOOLEAN DEFAULT FALSE"
        )
        cursor.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP"
        )
        cursor.execute(
            """
            UPDATE users
            SET email_verified_at = COALESCE(email_verified_at, created_at, NOW())
            WHERE email_verified_at IS NULL
            """
        )
        # Google-only accounts (no password login) are treated as Google-linked.
        cursor.execute(
            """
            UPDATE users
            SET google_linked = TRUE
            WHERE COALESCE(has_password, TRUE) = FALSE AND COALESCE(google_linked, FALSE) = FALSE
            """
        )

        # Create sessions table (Phase 3.2 + extended fields + event_count + V2 telemetry)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
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
                webdriver_flag BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cursor.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_label_check")
        # Create events table with individual ML feature columns (matches old SQLite structure + V2 telemetry)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
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
                hover_duration INTEGER,
                overshoot_ratio REAL,
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
        # Create session_features table for ML training (V2 + V3 + V4 features)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_features (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL REFERENCES sessions(id),
                avg_mouse_vel REAL,
                std_mouse_vel REAL,
                max_mouse_vel REAL,
                total_distance REAL,
                avg_angle_change REAL,
                click_count INTEGER,
                avg_click_interval REAL,
                avg_iki REAL,
                std_iki REAL,
                avg_hold REAL,
                scroll_count INTEGER,
                avg_scroll_vel REAL,
                session_duration REAL,
                event_count INTEGER,
                mouse_vel_p10 REAL,
                mouse_vel_p50 REAL,
                mouse_vel_p90 REAL,
                mouse_accel_mean REAL,
                mouse_accel_std REAL,
                mouse_accel_max REAL,
                mouse_angle_std REAL,
                mouse_angle_p90 REAL,
                mouse_path_efficiency REAL,
                mouse_idle_gap_count INTEGER,
                mouse_event_ratio REAL,
                click_interval_std REAL,
                click_interval_min REAL,
                click_interval_p90 REAL,
                double_click_count INTEGER,
                key_count INTEGER,
                iki_p10 REAL,
                iki_p50 REAL,
                iki_p90 REAL,
                hold_std REAL,
                hold_p90 REAL,
                backspace_count INTEGER,
                scroll_vel_std REAL,
                scroll_rev_count INTEGER,
                scroll_pause_count INTEGER,
                focus_event_count INTEGER,
                touch_event_count INTEGER,
                event_rate REAL,
                pause_count INTEGER,
                pause_ratio REAL,
                mouse_curvature_std REAL,
                mouse_jerk_std REAL,
                movement_entropy REAL,
                avg_hover_duration REAL,
                hover_duration_std REAL,
                avg_overshoot_ratio REAL,
                overshoot_ratio_std REAL,
                webdriver_flag BOOLEAN,
                device_type VARCHAR(20),
                label VARCHAR(10),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Create indexes if they do not already exist
        indexes = [
            ("idx_events_session", "CREATE INDEX idx_events_session ON events(session_id)"),
            ("idx_events_type", "CREATE INDEX idx_events_type ON events(event_type)"),
            ("idx_events_received", "CREATE INDEX idx_events_received ON events(received_at)"),
            ("idx_sessions_created", "CREATE INDEX idx_sessions_created ON sessions(created_at)"),
            ("idx_sessions_label", "CREATE INDEX idx_sessions_label ON sessions(label)"),
            ("idx_sessions_project", "CREATE INDEX idx_sessions_project ON sessions(project_id)"),
        ]
        for idx_name, idx_sql in indexes:
            cursor.execute("SELECT to_regclass(%s)", (idx_name,))
            exists = cursor.fetchone()[0]
            if not exists:
                cursor.execute(idx_sql)
        _migrate_events_columns(cursor)
        _migrate_session_features_columns(cursor)
        
        # Migrate sessions table for V2 telemetry
        cursor.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS webdriver_flag BOOLEAN DEFAULT FALSE")

        # Migrate session_features table for V2 telemetry
        cursor.execute("ALTER TABLE session_features ADD COLUMN IF NOT EXISTS webdriver_flag BOOLEAN DEFAULT FALSE")

        # Which API key (site key) a predict-logged session came from — lets
        # siteverify's project-binding check trace a session back to its key.
        cursor.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS api_key_id UUID REFERENCES api_keys(id)")

        # Single-use verification tokens (siteverify). jti PK + ON CONFLICT DO
        # NOTHING at consume time gives replay protection without a lookup
        # query on the hot /api/predict path.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consumed_tokens (
                jti VARCHAR(64) PRIMARY KEY,
                consumed_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Session ECDSA public keys for /api/predict signing (multi-dyno safe).
        # In-memory alone breaks under Heroku multi-dyno / rolling restart.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signing_session_keys (
                project_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                public_jwk JSONB NOT NULL,
                fingerprint TEXT NOT NULL,
                issued_at DOUBLE PRECISION NOT NULL,
                expires_at DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (project_id, session_id)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signing_keys_expires
            ON signing_session_keys (expires_at)
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signing_spent_nonces (
                project_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                nonce TEXT NOT NULL,
                valid_until DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (project_id, session_id, nonce)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signing_nonces_valid
            ON signing_spent_nonces (valid_until)
        """)

        conn.commit()
        print("[DB] PostgreSQL initialized (telemetry schema)")
    finally:
        release_connection(conn)


def upsert_signing_session_key(
    project_id: str,
    session_id: str,
    public_jwk: dict,
    fingerprint: str,
    issued_at: float,
    expires_at: float,
) -> None:
    """Persist a browser ECDSA public key so any dyno can verify signatures."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO signing_session_keys (
                project_id, session_id, public_jwk, fingerprint, issued_at, expires_at
            ) VALUES (%s, %s, %s::jsonb, %s, %s, %s)
            ON CONFLICT (project_id, session_id) DO UPDATE SET
                public_jwk = EXCLUDED.public_jwk,
                fingerprint = EXCLUDED.fingerprint,
                issued_at = EXCLUDED.issued_at,
                expires_at = EXCLUDED.expires_at
            """,
            (
                str(project_id),
                session_id,
                json.dumps(public_jwk),
                fingerprint,
                issued_at,
                expires_at,
            ),
        )
        conn.commit()
    finally:
        release_connection(conn)


def load_signing_session_key(project_id: str, session_id: str):
    """Return (public_jwk, fingerprint, issued_at, expires_at) or None."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT public_jwk, fingerprint, issued_at, expires_at
            FROM signing_session_keys
            WHERE project_id = %s AND session_id = %s
            """,
            (str(project_id), session_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        public_jwk, fingerprint, issued_at, expires_at = row
        if isinstance(public_jwk, str):
            public_jwk = json.loads(public_jwk)
        return public_jwk, fingerprint, float(issued_at), float(expires_at)
    finally:
        release_connection(conn)


def claim_signing_nonce(
    project_id: str, session_id: str, nonce: str, valid_until: float
) -> bool:
    """Atomically mark a nonce spent. Returns False if already used (replay)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Drop expired nonces for this session opportunistically.
        cursor.execute(
            """
            DELETE FROM signing_spent_nonces
            WHERE project_id = %s AND session_id = %s AND valid_until < %s
            """,
            (str(project_id), session_id, time.time()),
        )
        cursor.execute(
            """
            INSERT INTO signing_spent_nonces (
                project_id, session_id, nonce, valid_until
            ) VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING nonce
            """,
            (str(project_id), session_id, nonce, valid_until),
        )
        claimed = cursor.fetchone() is not None
        conn.commit()
        return claimed
    finally:
        release_connection(conn)


def count_signing_nonces(project_id: str, session_id: str) -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM signing_spent_nonces
            WHERE project_id = %s AND session_id = %s AND valid_until >= %s
            """,
            (str(project_id), session_id, time.time()),
        )
        return int(cursor.fetchone()[0])
    finally:
        release_connection(conn)


def insert_session(session_data: dict, project_id: str = None, label: str = None):
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
                user_agent, started_at, webdriver_flag, label
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(id) DO NOTHING
        """, (
            session_data.get('sessionId', ''),
            project_id,
            session_data.get('deviceType', 'unknown'),
            session_data.get('screenWidth', 0),
            session_data.get('screenHeight', 0),
            session_data.get('userAgent', ''),
            start_timestamp,
            session_data.get('webdriverFlag', False),
            label,
        ))
        conn.commit()
    finally:
        release_connection(conn)


def insert_session_prediction(session_id: str, project_id: str, device_type: str, user_agent: str, risk_score: float, webdriver_flag: bool, label: str, api_key_id: str = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (
                id, project_id, device_type, user_agent, started_at, webdriver_flag, label, risk_score, api_key_id
            ) VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, %s)
            ON CONFLICT(id) DO UPDATE SET
                risk_score = EXCLUDED.risk_score,
                label = EXCLUDED.label,
                api_key_id = EXCLUDED.api_key_id
        """, (
            session_id,
            project_id,
            device_type,
            user_agent,
            webdriver_flag,
            label,
            risk_score,
            api_key_id,
        ))
        conn.commit()
    finally:
        release_connection(conn)


def consume_token_jti(jti: str) -> bool:
    """
    Mark a verification-token jti as consumed. Returns True if this call
    consumed it (first use), False if it was already consumed (replay).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO consumed_tokens (jti) VALUES (%s) ON CONFLICT DO NOTHING",
            (jti,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        release_connection(conn)


def prune_consumed_tokens(older_than_seconds: int = 900):
    """Opportunistic cleanup of consumed_tokens rows past the token TTL window."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM consumed_tokens WHERE consumed_at < NOW() - (%s || ' seconds')::interval",
            (older_than_seconds,),
        )
        conn.commit()
    finally:
        release_connection(conn)


def maybe_prune_consumed_tokens(probability: float = 0.01, older_than_seconds: int = 900):
    """Call from a hot path to prune consumed_tokens without a scheduled job — fires probabilistically so most requests skip the extra query."""
    if random.random() < probability:
        prune_consumed_tokens(older_than_seconds)


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
        # events.session_id has a NOT NULL FK to sessions(id). Ensure the row
        # exists so telemetry never 500s on a session/start that failed,
        # raced, or was never sent (telemetry is fire-and-forget by design).
        cursor.execute(
            "INSERT INTO sessions (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
            (session_id,),
        )
        rows = []
        for e in events:
            etype = e.get('type', 'unknown')

            def _coerce_int(val):
                if val is None:
                    return None
                try:
                    return int(round(float(val)))
                except Exception:
                    return None

            x_val = _coerce_int(e.get('x'))
            y_val = _coerce_int(e.get('y'))
            scroll_y_val = _coerce_int(e.get('y')) if etype == 'sc' else None

            is_double_val = None
            if etype == 'cl':
                is_double_val = _event_bool(
                    e, 'is_double', 'double', default=False
                )

            scroll_rev_val = None
            scroll_pause_val = None
            if etype == 'sc':
                scroll_rev_val = _event_bool(
                    e, 'scroll_rev', 'rev', default=False
                )
                scroll_pause_val = _event_bool(
                    e, 'scroll_pause', 'pause', default=False
                )

            rows.append((
                session_id, etype, e.get('t'),
                x_val, y_val, e.get('dist'), e.get('ang'),
                e.get('vel') if etype == 'mm' else None,
                e.get('totalDist'),
                e.get('target'), e.get('interval'), is_double_val,
                e.get('tw'), e.get('th'),
                e.get('k'), e.get('iki'), e.get('hold'),
                scroll_y_val,
                e.get('vel') if etype == 'sc' else None,
                scroll_rev_val, scroll_pause_val,
                e.get('hoverDuration'),  # V2 telemetry
                e.get('overshootRatio'),  # V2 telemetry
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
                hover_duration, overshoot_ratio,
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
                %s, %s,
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
