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

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.xroqpyuenhowuaueiiwu:sasyrao%401234@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
)


class APIKeyManager:
    """Production-grade API key management with security best practices"""
    
    KEY_PREFIXES = {
        'live': 'vf_live_',
        'test': 'vf_test_',
        'admin': 'vf_admin_'
    }
    
    @staticmethod
    def generate_api_key(key_type: str = 'live') -> tuple[str, str]:
        """
        Generate a secure API key and its hash
        
        Args:
            key_type: Type of key ('live', 'test', 'admin')
            
        Returns:
            Tuple of (api_key, key_hash)
        """
        prefix = APIKeyManager.KEY_PREFIXES.get(key_type, 'vf_live_')
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
                    AND u.is_active = TRUE
                """, (key_hash, key_prefix))
                
                result = cursor.fetchone()
                return dict(result) if result else None
                
        finally:
            conn.close()
    
    @staticmethod
    def create_api_key(project_id: str, key_type: str = 'live', created_by: str = None) -> Dict:
        """
        Create a new API key for a project
        
        Args:
            project_id: UUID of the project
            key_type: Type of key ('live', 'test', 'admin')
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
                    INSERT INTO api_keys (project_id, key_hash, key_prefix)
                    VALUES (%s, %s, %s)
                    RETURNING id, created_at, is_active
                """, (project_id, key_hash, key_prefix))
                
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
                        last_used_at
                    FROM api_keys
                    WHERE project_id = %s
                    ORDER BY created_at DESC
                """, (project_id,))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        finally:
            conn.close()
    
    @staticmethod
    def revoke_api_key(key_id: str) -> bool:
        """
        Revoke (deactivate) an API key
        
        Args:
            key_id: UUID of the API key
            
        Returns:
            True if successful
        """
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor() as cursor:
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
    
    @staticmethod
    def create_user(email: str, password: str, full_name: str = None, 
                   company_name: str = None, is_admin: bool = False) -> Dict:
        """
        Create a new user
        
        Args:
            email: User email
            password: Plain text password (will be hashed)
            full_name: User's full name
            company_name: Company name
            is_admin: Admin status
            
        Returns:
            Dict with user info
        """
        import bcrypt
        
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    INSERT INTO users (email, password_hash, full_name, company_name, is_admin)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, email, full_name, company_name, is_admin, created_at
                """, (email, password_hash, full_name, company_name, is_admin))
                
                result = cursor.fetchone()
                conn.commit()
                
                return dict(result)
                
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create user: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def verify_user(email: str, password: str) -> Optional[Dict]:
        """
        Verify user credentials
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            Dict with user info if valid, None otherwise
        """
        import bcrypt
        
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, email, password_hash, full_name, company_name, is_admin, is_active
                    FROM users
                    WHERE email = %s AND is_active = TRUE
                """, (email,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                
                if bcrypt.checkpw(password.encode(), result['password_hash'].encode()):
                    user_dict = dict(result)
                    del user_dict['password_hash']  # Don't return hash
                    return user_dict
                
                return None
                
        finally:
            conn.close()
            
    @staticmethod
    def get_or_create_google_user(email: str, name: str = None) -> Dict:
        """
        Get an existing user by email, or create a new user for Google OAuth login
        """
        import bcrypt
        
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # 1. Look up existing user
                cursor.execute("""
                    SELECT id, email, full_name, company_name, is_admin, is_active
                    FROM users
                    WHERE email = %s
                """, (email,))
                
                result = cursor.fetchone()
                if result:
                    user_dict = dict(result)
                else:
                    # 2. User doesn't exist, create a new one with a dummy password hash
                    dummy_hash = bcrypt.hashpw(secrets.token_hex(16).encode(), bcrypt.gensalt()).decode()
                    
                    is_admin_user = email in ["developer@veriflow.com", "developer@nextcaptcha.com", "hulkb690@gmail.com"]
                    cursor.execute("""
                        INSERT INTO users (email, password_hash, full_name, is_admin)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id, email, full_name, company_name, is_admin, created_at
                    """, (email, dummy_hash, name, is_admin_user))
                    
                    new_user = cursor.fetchone()
                    conn.commit()
                    user_dict = dict(new_user)
                
                # 3. Ensure they have a default project
                cursor.execute("SELECT id FROM projects WHERE owner_id = %s", (user_dict['id'],))
                project_row = cursor.fetchone()
                if not project_row:
                    cursor.execute("""
                        INSERT INTO projects (owner_id, name, allowed_domains)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (user_dict['id'], "Default Workspace", ["*"]))
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
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    INSERT INTO projects (owner_id, name, allowed_domains)
                    VALUES (%s, %s, %s)
                    RETURNING id, name, owner_id, allowed_domains, created_at
                """, (user_id, name, allowed_domains))
                
                result = cursor.fetchone()
                conn.commit()
                
                return dict(result)
                
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create project: {e}")
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
