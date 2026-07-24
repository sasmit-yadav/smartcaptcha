"""
Production API Key Management System for SDK Backend
Handles API key generation, verification, and lifecycle management
"""

import secrets
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Set it to your PostgreSQL connection string (e.g. in a local .env "
        "or the Render dashboard in production). Credentials must never be hardcoded."
    )


class APIKeyManager:
    """Production-grade API key management with security best practices"""
    
    KEY_PREFIXES = {
        'live': 'vp_live_',
        'test': 'vp_test_',
        'admin': 'vp_admin_',
        'site': 'vp_site_',
        'secret': 'vp_secret_',
    }

    # Key types accepted as a "site key" (browser-facing, predict + telemetry).
    # Legacy vf_live_/vf_test_ keys keep working here indefinitely.
    SITE_KEY_TYPES = ('site', 'live', 'test', 'legacy', 'admin')

    @staticmethod
    def generate_api_key(key_type: str = 'live') -> tuple[str, str]:
        """
        Generate a secure API key and its hash

        Args:
            key_type: Type of key ('live', 'test', 'admin', 'site', 'secret')

        Returns:
            Tuple of (api_key, key_hash)
        """
        prefix = APIKeyManager.KEY_PREFIXES.get(key_type, 'vp_live_')
        random_part = secrets.token_urlsafe(32)
        api_key = f"{prefix}{random_part}"

        # SHA-256 hash for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        return api_key, key_hash

    @staticmethod
    def verify_api_key(api_key: str) -> Optional[Dict]:
        """
        Verify an API key and return associated project/customer info

        Args:
            api_key: The API key to verify

        Returns:
            Dict with project/customer info if valid, None otherwise
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_prefix = api_key[:10]  # First 10 chars for identification

        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        ak.id as key_id,
                        ak.project_id,
                        ak.is_active,
                        ak.key_type,
                        ak.expires_at,
                        p.name as project_name,
                        p.owner_id,
                        p.allowed_domains,
                        u.email as owner_email,
                        u.company_name,
                        u.is_admin
                    FROM api_keys ak
                    JOIN projects p ON ak.project_id = p.id
                    JOIN users u ON p.owner_id = u.id
                    WHERE ak.key_hash = %s
                    AND ak.key_prefix = %s
                    AND ak.is_active = TRUE
                    AND (ak.expires_at IS NULL OR ak.expires_at > NOW())
                    AND u.is_active = TRUE
                """, (key_hash, key_prefix))

                result = cursor.fetchone()
                if not result:
                    return None
                info = dict(result)
                info['key_type'] = info.get('key_type') or 'legacy'
                return info

        finally:
            conn.close()

    @staticmethod
    def create_api_key(project_id: str, key_type: str = 'live', created_by: str = None) -> Dict:
        """
        Create a new API key for a project

        Args:
            project_id: UUID of the project
            key_type: Type of key ('live', 'test', 'admin', 'site', 'secret')
            created_by: User ID who created the key

        Returns:
            Dict with the new API key info
        """
        api_key, key_hash = APIKeyManager.generate_api_key(key_type)
        key_prefix = api_key[:10]

        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    INSERT INTO api_keys (project_id, key_hash, key_prefix, key_type)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, created_at, is_active
                """, (project_id, key_hash, key_prefix, key_type))

                result = cursor.fetchone()
                conn.commit()

                return {
                    'id': str(result['id']),
                    'api_key': api_key,
                    'key_prefix': key_prefix,
                    'project_id': project_id,
                    'created_at': result['created_at'].isoformat(),
                    'is_active': result['is_active'],
                    'key_type': key_type
                }

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create API key: {e}")
        finally:
            conn.close()

    @staticmethod
    def create_key_pair(project_id: str) -> Dict:
        """
        Create a site key + secret key pair for a project (the recommended
        way for new integrations — plaintexts are only ever returned once).
        """
        site_key = APIKeyManager.create_api_key(project_id, key_type='site')
        secret_key = APIKeyManager.create_api_key(project_id, key_type='secret')
        return {'site_key': site_key, 'secret_key': secret_key}

    @staticmethod
    def rotate_api_key(key_id: str, project_id: str, grace_hours: float = 0) -> Dict:
        """
        Rotate an API key: create a new key of the same type, and expire the
        old one after `grace_hours` (0 = immediately).

        Args:
            key_id: UUID of the key being rotated
            project_id: project the key must belong to (ownership check at call site)
            grace_hours: hours before the old key stops working; 0 deactivates now

        Returns:
            Dict with the new key info and the old key's id/expiry
        """
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT id, project_id, key_type FROM api_keys WHERE id = %s AND project_id = %s",
                    (key_id, project_id),
                )
                old_key = cursor.fetchone()
                if not old_key:
                    raise Exception("API key not found")

                key_type = old_key['key_type'] or 'legacy'
                new_key = APIKeyManager.create_api_key(project_id, key_type=key_type)

                if grace_hours and grace_hours > 0:
                    cursor.execute(
                        "UPDATE api_keys SET expires_at = NOW() + (%s || ' hours')::interval WHERE id = %s",
                        (grace_hours, key_id),
                    )
                else:
                    cursor.execute(
                        "UPDATE api_keys SET is_active = FALSE, expires_at = NOW() WHERE id = %s",
                        (key_id,),
                    )
                conn.commit()

                return {'new_key': new_key, 'old_key_id': key_id, 'grace_hours': grace_hours}
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to rotate API key: {e}")
        finally:
            conn.close()

    @staticmethod
    def list_api_keys(project_id: str) -> List[Dict]:
        """
        List all API keys for a project

        Args:
            project_id: UUID of the project

        Returns:
            List of API key info (without actual keys)
        """
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        id,
                        key_prefix,
                        created_at,
                        is_active,
                        last_used_at,
                        key_type,
                        expires_at
                    FROM api_keys
                    WHERE project_id = %s
                    ORDER BY created_at DESC
                """, (project_id,))

                results = cursor.fetchall()
                rows = []
                for row in results:
                    d = dict(row)
                    d['key_type'] = d.get('key_type') or 'legacy'
                    rows.append(d)
                return rows

        finally:
            conn.close()
    
    @staticmethod
    def revoke_api_key(key_id: str, project_id: Optional[str] = None) -> bool:
        """
        Revoke (deactivate) an API key.

        Args:
            key_id: UUID of the API key
            project_id: If provided, the revoke only applies if the key
                belongs to this project (ownership check at the call site).

        Returns:
            True if successful
        """
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor() as cursor:
                if project_id:
                    cursor.execute("""
                        UPDATE api_keys
                        SET is_active = FALSE
                        WHERE id = %s AND project_id = %s
                    """, (key_id, project_id))
                else:
                    cursor.execute("""
                        UPDATE api_keys
                        SET is_active = FALSE
                        WHERE id = %s
                    """, (key_id,))
                conn.commit()
                return cursor.rowcount > 0

        finally:
            conn.close()

    @staticmethod
    def get_key_project_id(key_id: str) -> Optional[str]:
        """Look up which project an API key belongs to (for ownership checks)."""
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT project_id FROM api_keys WHERE id = %s", (key_id,))
                row = cursor.fetchone()
                return str(row['project_id']) if row else None
        finally:
            conn.close()
    
    @staticmethod
    def update_last_used(key_id: str):
        """
        Update the last_used_at timestamp for an API key
        
        Args:
            key_id: UUID of the API key
        """
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE api_keys 
                    SET last_used_at = NOW() 
                    WHERE id = %s
                """, (key_id,))
                conn.commit()
                
        finally:
            conn.close()


class UserManager:
    """User management for customer dashboard"""

    _DUMMY_PASSWORD_HASH = None

    @staticmethod
    def _dummy_hash() -> str:
        import bcrypt
        if UserManager._DUMMY_PASSWORD_HASH is None:
            UserManager._DUMMY_PASSWORD_HASH = bcrypt.hashpw(
                b"timing-equalization-dummy", bcrypt.gensalt(rounds=12)
            ).decode()
        return UserManager._DUMMY_PASSWORD_HASH

    @staticmethod
    def create_user(email: str, password: str, full_name: str = None,
                   company_name: str = None, is_admin: bool = False) -> Dict:
        """Create a new user with email/password (bcrypt)."""
        import bcrypt
        from core.password_policy import normalize_email, validate_email, validate_password

        email_ok, email_err = validate_email(email)
        if not email_ok:
            raise ValueError(email_err or "Invalid email")
        email = normalize_email(email)

        pw_ok, pw_err = validate_password(password, email=email)
        if not pw_ok:
            raise ValueError(pw_err or "Invalid password")

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode()

        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    INSERT INTO users (email, password_hash, full_name, company_name, is_admin, has_password, google_linked)
                    VALUES (%s, %s, %s, %s, %s, TRUE, FALSE)
                    RETURNING id, email, full_name, company_name, is_admin, created_at,
                              TRUE AS has_password, FALSE AS google_linked
                """, (email, password_hash, full_name, company_name, is_admin))
                result = cursor.fetchone()
                conn.commit()
                user = dict(result)
                cursor.execute("""
                    INSERT INTO projects (owner_id, name, allowed_domains)
                    VALUES (%s, %s, %s)
                """, (user["id"], "Default Workspace", ["*"]))
                conn.commit()
                return user
        except Exception as e:
            conn.rollback()
            msg = str(e).lower()
            if "unique" in msg or "duplicate" in msg:
                raise ValueError(
                    "An account with this email may already exist. Try logging in instead."
                )
            # has_password column may be missing until migrate — surface clearly in logs
            raise ValueError("Unable to create account. Please try again.")
        finally:
            conn.close()

    @staticmethod
    def verify_user(email: str, password: str) -> Optional[Dict]:
        """Verify email/password with timing-equalized bcrypt."""
        import bcrypt
        from core.password_policy import normalize_email

        email = normalize_email(email)
        if not email or password is None:
            bcrypt.checkpw(b"x", UserManager._dummy_hash().encode())
            return None

        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, email, password_hash, full_name, company_name, is_admin, is_active,
                           COALESCE(has_password, TRUE) AS has_password,
                           COALESCE(google_linked, FALSE) AS google_linked
                    FROM users
                    WHERE email = %s AND is_active = TRUE
                """, (email,))
                result = cursor.fetchone()
                if not result:
                    bcrypt.checkpw(password.encode("utf-8"), UserManager._dummy_hash().encode())
                    return None
                try:
                    ok = bcrypt.checkpw(password.encode("utf-8"), result["password_hash"].encode("utf-8"))
                except ValueError:
                    ok = False
                if not result.get("has_password", True):
                    return None
                if not ok:
                    return None
                user_dict = dict(result)
                del user_dict["password_hash"]
                return user_dict
        finally:
            conn.close()

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict]:
        """Load a public user profile by id (no password hash)."""
        if not user_id:
            return None
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, email, full_name, company_name, is_admin, is_active,
                           COALESCE(has_password, TRUE) AS has_password,
                           COALESCE(google_linked, FALSE) AS google_linked,
                           created_at
                    FROM users
                    WHERE id = %s::uuid AND is_active = TRUE
                    """,
                    (str(user_id),),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def change_password(
        user_id: str,
        new_password: str,
        *,
        current_password: Optional[str] = None,
    ) -> Dict:
        """
        Change or set account password.
        - If the account already has a password, current_password is required.
        - Google-only accounts (has_password=False) may set a first password without current.
        Revokes other sessions via caller (refresh tokens).
        """
        import bcrypt
        from core.password_policy import validate_password

        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, email, password_hash, full_name, company_name, is_admin,
                           COALESCE(has_password, TRUE) AS has_password,
                           COALESCE(google_linked, FALSE) AS google_linked
                    FROM users
                    WHERE id = %s::uuid AND is_active = TRUE
                    """,
                    (str(user_id),),
                )
                row = cursor.fetchone()
                if not row:
                    raise ValueError("Account not found")

                has_password = bool(row.get("has_password", True))
                email = row["email"]

                pw_ok, pw_err = validate_password(new_password, email=email)
                if not pw_ok:
                    raise ValueError(pw_err or "Invalid password")

                if has_password:
                    if not current_password:
                        raise ValueError("Current password is required")
                    try:
                        ok = bcrypt.checkpw(
                            current_password.encode("utf-8"),
                            row["password_hash"].encode("utf-8"),
                        )
                    except ValueError:
                        ok = False
                    if not ok:
                        raise ValueError("Current password is incorrect")
                    if secrets.compare_digest(current_password, new_password):
                        raise ValueError("New password must be different from your current password")
                else:
                    # Setting a first password on a Google-linked account
                    if current_password:
                        raise ValueError("This account has no password yet — leave current password blank")

                new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode()
                cursor.execute(
                    """
                    UPDATE users
                    SET password_hash = %s, has_password = TRUE
                    WHERE id = %s::uuid
                    RETURNING id, email, full_name, company_name, is_admin,
                              TRUE AS has_password,
                              COALESCE(google_linked, FALSE) AS google_linked
                    """,
                    (new_hash, str(user_id)),
                )
                updated = cursor.fetchone()
                conn.commit()
                return dict(updated)
        except ValueError:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise ValueError("Unable to update password. Please try again.")
        finally:
            conn.close()

    @staticmethod
    def get_or_create_google_user(email: str, name: str = None) -> Dict:
        """Get or create user for Google OAuth login."""
        import bcrypt
        from core.password_policy import normalize_email, validate_email

        email_ok, _ = validate_email(email or "")
        if not email_ok:
            raise ValueError("Google account did not provide a valid email")
        email = normalize_email(email)

        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, email, full_name, company_name, is_admin, is_active,
                           COALESCE(has_password, TRUE) AS has_password,
                           COALESCE(google_linked, FALSE) AS google_linked
                    FROM users
                    WHERE email = %s
                """, (email,))
                result = cursor.fetchone()
                if result:
                    user_dict = dict(result)
                    if not user_dict.get("google_linked"):
                        cursor.execute(
                            """
                            UPDATE users SET google_linked = TRUE
                            WHERE id = %s
                            RETURNING id, email, full_name, company_name, is_admin, is_active,
                                      COALESCE(has_password, TRUE) AS has_password,
                                      TRUE AS google_linked
                            """,
                            (user_dict["id"],),
                        )
                        user_dict = dict(cursor.fetchone())
                        conn.commit()
                else:
                    dummy_hash = bcrypt.hashpw(secrets.token_hex(32).encode(), bcrypt.gensalt(rounds=12)).decode()
                    is_admin_user = email in ["developer@veilproof.com", "developer@nextcaptcha.com", "hulkb690@gmail.com"]
                    cursor.execute("""
                        INSERT INTO users (email, password_hash, full_name, is_admin, has_password, google_linked)
                        VALUES (%s, %s, %s, %s, FALSE, TRUE)
                        RETURNING id, email, full_name, company_name, is_admin, created_at,
                                  FALSE AS has_password, TRUE AS google_linked
                    """, (email, dummy_hash, name, is_admin_user))
                    new_user = cursor.fetchone()
                    conn.commit()
                    user_dict = dict(new_user)

                if not user_dict.get("is_active", True):
                    raise ValueError("Account is disabled")

                cursor.execute("SELECT id FROM projects WHERE owner_id = %s", (user_dict["id"],))
                project_row = cursor.fetchone()
                if not project_row:
                    cursor.execute("""
                        INSERT INTO projects (owner_id, name, allowed_domains)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (user_dict["id"], "Default Workspace", ["*"]))
                    conn.commit()
                return user_dict
        finally:
            conn.close()

    @staticmethod
    def create_project(user_id: str, name: str, allowed_domains: List[str] = None) -> Dict:
        """
        Create a new project for a user
        
        Args:
            user_id: UUID of the user
            name: Project name
            allowed_domains: List of allowed domains
            
        Returns:
            Dict with project info
        """
        domains = UserManager.normalize_allowed_domains(allowed_domains)
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    INSERT INTO projects (owner_id, name, allowed_domains)
                    VALUES (%s, %s, %s)
                    RETURNING id, name, owner_id, allowed_domains, created_at
                """, (user_id, name, domains))
                
                result = cursor.fetchone()
                conn.commit()
                
                return dict(result)
                
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create project: {e}")
        finally:
            conn.close()

    @staticmethod
    def normalize_allowed_domains(raw) -> Optional[List[str]]:
        """Turn user input into clean hostnames for Origin checks.

        Accepts None, [], or a list of strings that may include URLs.
        Empty / missing → None (treated as open allowlist by predict).
        '*' alone → ['*'].
        """
        if not raw:
            return None
        cleaned = []
        for item in raw:
            if item is None:
                continue
            d = str(item).strip().lower()
            if not d:
                continue
            if d == "*":
                return ["*"]
            # Users often paste https://example.com/path — keep hostname only.
            if "://" in d:
                d = d.split("://", 1)[1]
            d = d.split("/")[0]
            d = d.split("?")[0]
            if d.startswith("*."):
                d = d[2:]
            # Drop port: Origin hostname matching ignores it.
            if ":" in d and not d.startswith("["):
                d = d.rsplit(":", 1)[0]
            if d and d not in cleaned:
                cleaned.append(d)
        return cleaned or None

    @staticmethod
    def update_project_domains(project_id: str, allowed_domains: List[str] = None) -> Optional[Dict]:
        """Update allowed_domains for an existing project."""
        domains = UserManager.normalize_allowed_domains(allowed_domains)
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    UPDATE projects
                    SET allowed_domains = %s
                    WHERE id = %s
                    RETURNING id, name, owner_id, allowed_domains, created_at
                """, (domains, project_id))
                result = cursor.fetchone()
                conn.commit()
                return dict(result) if result else None
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to update project domains: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def get_project(project_id: str) -> Optional[Dict]:
        """Look up a project by ID (for ownership checks)."""
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, name, owner_id, allowed_domains, created_at
                    FROM projects
                    WHERE id = %s
                """, (project_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        finally:
            conn.close()

    @staticmethod
    def list_user_projects(user_id: str) -> List[Dict]:
        """
        List all projects for a user
        
        Args:
            user_id: UUID of the user
            
        Returns:
            List of project info
        """
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, name, allowed_domains, created_at
                    FROM projects
                    WHERE owner_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        finally:
            conn.close()
