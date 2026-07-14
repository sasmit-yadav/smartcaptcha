import os

import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Depends, HTTPException
from core.database import DATABASE_URL
from core.auth import create_access_token, get_current_super_admin, CurrentUser
from typing import Dict, List

router = APIRouter(prefix="/admin", tags=["Super Admin"])

from pydantic import BaseModel

class AdminLoginRequest(BaseModel):
    username: str
    password: str

# Super-admin login for the internal admin-dashboard. Configured via env vars
# — never hardcoded. SUPER_ADMIN_PASSWORD_HASH is a bcrypt hash, generated
# once with: python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
SUPER_ADMIN_USERNAME = os.getenv("SUPER_ADMIN_USERNAME")
SUPER_ADMIN_PASSWORD_HASH = os.getenv("SUPER_ADMIN_PASSWORD_HASH")


@router.post("/verify-credentials")
async def verify_credentials(login_req: AdminLoginRequest):
    """Verify super-admin credentials (env-configured) and issue a session token."""
    if not SUPER_ADMIN_USERNAME or not SUPER_ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=503,
            detail="Super-admin login is not configured (SUPER_ADMIN_USERNAME / SUPER_ADMIN_PASSWORD_HASH unset)"
        )

    valid = (
        login_req.username == SUPER_ADMIN_USERNAME
        and bcrypt.checkpw(login_req.password.encode(), SUPER_ADMIN_PASSWORD_HASH.encode())
    )
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id::text, email, full_name, is_admin FROM users WHERE is_admin = TRUE LIMIT 1")
            admin_user = cursor.fetchone()
    finally:
        conn.close()

    if not admin_user:
        raise HTTPException(status_code=500, detail="No admin user record found in database")

    token = create_access_token(user_id=admin_user["id"], email=admin_user["email"], is_admin=True)
    return {"success": True, "user": dict(admin_user), "access_token": token}


@router.get("/global-analytics")
async def get_global_analytics(admin: CurrentUser = Depends(get_current_super_admin)):
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # 1. Total sessions, active users, active projects
            cursor.execute("SELECT COUNT(s.id)::int as total_sessions FROM sessions s JOIN projects p ON s.project_id = p.id")
            total_sessions = cursor.fetchone()['total_sessions']
            
            cursor.execute("SELECT COUNT(*)::int as total_users FROM users")
            total_users = cursor.fetchone()['total_users']
            
            cursor.execute("SELECT COUNT(*)::int as total_projects FROM projects")
            total_projects = cursor.fetchone()['total_projects']
            
            # 2. Mitigated (bot) vs Accepted (human) count
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN label IN ('bot', 'block', 'reject') THEN 1 END)::int as bot_count,
                    COUNT(CASE WHEN label IN ('human', 'allow', 'accept') THEN 1 END)::int as human_count,
                    COUNT(CASE WHEN label = 'challenge' THEN 1 END)::int as challenge_count
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
            """)
            counts = cursor.fetchone()
            
            # 3. Daily activity stats (last 30 days)
            cursor.execute("""
                SELECT 
                    s.created_at::date::text as day,
                    COUNT(CASE WHEN label IN ('bot', 'block', 'reject') THEN 1 END)::int as bots,
                    COUNT(CASE WHEN label IN ('human', 'allow', 'accept') THEN 1 END)::int as humans
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                WHERE s.created_at >= NOW() - INTERVAL '30 days'
                GROUP BY s.created_at::date
                ORDER BY s.created_at::date ASC
            """)
            daily_stats = cursor.fetchall()
            
            # 4. Top 5 active projects by request volume
            cursor.execute("""
                SELECT 
                    p.id::text as project_id,
                    p.name as project_name,
                    u.email as owner_email,
                    COUNT(s.id)::int as request_count
                FROM projects p
                LEFT JOIN sessions s ON p.id = s.project_id
                JOIN users u ON p.owner_id = u.id
                GROUP BY p.id, p.name, u.email
                ORDER BY request_count DESC
                LIMIT 5
            """)
            top_projects = cursor.fetchall()
            
            return {
                "success": True,
                "stats": {
                    "total_sessions": total_sessions,
                    "total_users": total_users,
                    "total_projects": total_projects,
                    "bot_count": counts['bot_count'],
                    "human_count": counts['human_count'],
                    "challenge_count": counts['challenge_count']
                },
                "daily_stats": daily_stats,
                "top_projects": top_projects
            }
    finally:
        conn.close()

@router.get("/global-users")
async def get_global_users(admin: CurrentUser = Depends(get_current_super_admin)):
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    u.id::text,
                    u.email,
                    u.full_name,
                    u.company_name,
                    u.is_admin,
                    u.is_active,
                    u.created_at::text,
                    COUNT(p.id)::int as project_count,
                    COUNT(s.id)::int as total_requests
                FROM users u
                LEFT JOIN projects p ON u.id = p.owner_id
                LEFT JOIN sessions s ON p.id = s.project_id
                GROUP BY u.id, u.email, u.full_name, u.company_name, u.is_admin, u.is_active, u.created_at
                ORDER BY u.created_at DESC
            """)
            users = cursor.fetchall()
            return {"success": True, "users": users}
    finally:
        conn.close()

@router.get("/global-sessions")
async def get_global_sessions(admin: CurrentUser = Depends(get_current_super_admin)):
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    s.id,
                    p.name as project_name,
                    s.device_type,
                    s.user_agent,
                    s.risk_score,
                    s.webdriver_flag,
                    s.label as verdict,
                    s.created_at::text
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                ORDER BY s.created_at DESC
                LIMIT 100
            """)
            sessions = cursor.fetchall()
            return {"success": True, "sessions": sessions}
    finally:
        conn.close()

@router.post("/users/toggle-status")
async def toggle_user_status(payload: Dict, admin: CurrentUser = Depends(get_current_super_admin)):
    target_user_id = payload.get("target_user_id")
    is_active = payload.get("is_active")
    
    if not target_user_id:
        raise HTTPException(status_code=400, detail="Missing target_user_id in payload")
        
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET is_active = %s WHERE id = %s
            """, (is_active, target_user_id))
            conn.commit()
            return {"success": True, "message": f"User status updated to {'active' if is_active else 'suspended'}"}
    finally:
        conn.close()
