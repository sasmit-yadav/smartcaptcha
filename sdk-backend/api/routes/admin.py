"""
VeilProof API — Customer account routes.
User registration/login (email + Google OAuth), project management, and
API key lifecycle. Used by the website dashboard.

Auth model:
  - register / login / google-login issue a short-lived access JWT + rotating refresh token
  - /admin/refresh rotates refresh; /admin/logout revokes it
  - authenticated /admin/* routes require Bearer access token (core/auth.py)
"""

import os
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api_key_manager import APIKeyManager, UserManager
from core.auth import (
    CurrentUser,
    get_current_user,
    issue_session_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)
from core.rate_limit import rate_limit

router = APIRouter()


class UserRegistration(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=12, max_length=72)
    full_name: Optional[str] = Field(None, max_length=120)
    company_name: Optional[str] = Field(None, max_length=120)


class UserLogin(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=72)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., max_length=4096)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, max_length=512)


class ProjectCreate(BaseModel):
    name: str
    allowed_domains: Optional[List[str]] = None


class ProjectDomainsUpdate(BaseModel):
    allowed_domains: Optional[List[str]] = None


class APIKeyCreate(BaseModel):
    project_id: str
    key_type: str = 'live'  # 'live', 'test', 'admin'


class APIKeyRotate(BaseModel):
    grace_hours: float = 0


class ProjectIdOnly(BaseModel):
    project_id: str


def _client_meta(request: Request):
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    # Prefer first X-Forwarded-For hop when behind Cloudflare/Heroku.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        ip = xff.split(",")[0].strip()
    return ua, ip


def _public_user(user: dict) -> dict:
    return {
        "id": str(user["id"]),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "company_name": user.get("company_name"),
        "is_admin": bool(user.get("is_admin", False)),
    }


def _require_project_owner(project_id: str, user: CurrentUser) -> dict:
    """Fetch a project and raise 403/404 unless the current user owns it."""
    project = UserManager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if str(project["owner_id"]) != str(user.user_id):
        raise HTTPException(status_code=403, detail="You do not have access to this project")
    return project


@router.post("/admin/register", dependencies=[Depends(rate_limit("admin_register", limit=5, window_seconds=60))])
async def register_user(user_data: UserRegistration, request: Request):
    """Register with email/password and issue access + refresh tokens."""
    try:
        user = UserManager.create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            company_name=user_data.company_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to create account. Please try again.")

    ua, ip = _client_meta(request)
    tokens = issue_session_tokens(
        str(user["id"]),
        user["email"],
        bool(user.get("is_admin", False)),
        user_agent=ua,
        ip=ip,
    )
    return {"success": True, "user": _public_user(user), **tokens}


@router.post("/admin/login", dependencies=[Depends(rate_limit("admin_login", limit=10, window_seconds=60))])
async def login_user(login_data: UserLogin, request: Request):
    """Email/password login → access + refresh tokens."""
    user = UserManager.verify_user(login_data.email, login_data.password)
    if not user:
        # Generic message — do not reveal whether email exists.
        raise HTTPException(status_code=401, detail="Invalid email or password")

    ua, ip = _client_meta(request)
    tokens = issue_session_tokens(
        str(user["id"]),
        user["email"],
        bool(user.get("is_admin", False)),
        user_agent=ua,
        ip=ip,
    )
    return {"success": True, "user": _public_user(user), **tokens}


@router.post("/admin/refresh", dependencies=[Depends(rate_limit("admin_refresh", limit=30, window_seconds=60))])
async def refresh_session(body: RefreshRequest, request: Request):
    """Rotate refresh token and mint a new access token."""
    ua, ip = _client_meta(request)
    user, access, new_refresh = rotate_refresh_token(body.refresh_token, user_agent=ua, ip=ip)
    return {
        "success": True,
        "user": {"id": user["id"], "email": user["email"], "is_admin": user["is_admin"]},
        "access_token": access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.post("/admin/logout", dependencies=[Depends(rate_limit("admin_logout", limit=30, window_seconds=60))])
async def logout_session(body: LogoutRequest):
    """Revoke the presented refresh token (access JWT expires naturally)."""
    if body.refresh_token:
        revoke_refresh_token(body.refresh_token)
    return {"success": True}


@router.post("/admin/google-login", dependencies=[Depends(rate_limit("admin_google_login", limit=20, window_seconds=60))])
async def google_login(login_req: GoogleLoginRequest, request: Request):
    """Verify Google ID token, get or create user, issue session tokens."""
    import urllib.request
    import json

    id_token = login_req.id_token
    tokeninfo_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"

    try:
        req = urllib.request.Request(tokeninfo_url)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                raise HTTPException(status_code=401, detail="Google sign-in failed")

            payload = json.loads(response.read().decode())

            client_id = os.getenv("GOOGLE_CLIENT_ID")
            if client_id and payload.get("aud") != client_id:
                raise HTTPException(status_code=401, detail="Google sign-in failed")

            email = payload.get("email")
            if not email or payload.get("email_verified") in ("false", False):
                raise HTTPException(status_code=400, detail="Google account email is not verified")

            name = payload.get("name", "")
            user = UserManager.get_or_create_google_user(email=email, name=name)
            ua, ip = _client_meta(request)
            tokens = issue_session_tokens(
                str(user["id"]),
                user["email"],
                bool(user.get("is_admin", False)),
                user_agent=ua,
                ip=ip,
            )
            return {"success": True, "user": _public_user(user), **tokens}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=401, detail="Google sign-in failed")


@router.post("/admin/projects")
async def create_project(project_data: ProjectCreate, user: CurrentUser = Depends(get_current_user)):
    """Create a new project for the authenticated user."""
    try:
        project = UserManager.create_project(
            user_id=user.user_id,
            name=project_data.name,
            allowed_domains=project_data.allowed_domains
        )
        return {"success": True, "project": project}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/projects")
async def list_projects(user: CurrentUser = Depends(get_current_user)):
    """List all projects owned by the authenticated user."""
    projects = UserManager.list_user_projects(user.user_id)
    return {"success": True, "projects": projects}


@router.patch("/admin/projects/{project_id}")
async def update_project_domains(
    project_id: str,
    body: ProjectDomainsUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update allowed domains for a project the authenticated user owns."""
    _require_project_owner(project_id, user)
    try:
        project = UserManager.update_project_domains(project_id, body.allowed_domains)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True, "project": project}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/api-keys")
async def create_api_key(key_data: APIKeyCreate, user: CurrentUser = Depends(get_current_user)):
    """Create a new API key for a project the authenticated user owns."""
    _require_project_owner(key_data.project_id, user)
    try:
        api_key_info = APIKeyManager.create_api_key(
            project_id=key_data.project_id,
            key_type=key_data.key_type
        )
        return {"success": True, "api_key": api_key_info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/api-keys/pair")
async def create_api_key_pair(key_data: ProjectIdOnly, user: CurrentUser = Depends(get_current_user)):
    """
    Create a site key + secret key pair for a project (the recommended flow
    for new integrations). Both plaintexts are only ever returned here, once.
    """
    _require_project_owner(key_data.project_id, user)
    try:
        pair = APIKeyManager.create_key_pair(key_data.project_id)
        return {"success": True, **pair}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/api-keys/{key_id}/rotate")
async def rotate_api_key(key_id: str, rotate_data: APIKeyRotate, user: CurrentUser = Depends(get_current_user)):
    """
    Rotate an API key belonging to a project the authenticated user owns.
    The old key keeps working for `grace_hours` (0 = deactivated immediately).
    """
    project_id = APIKeyManager.get_key_project_id(key_id)
    if not project_id:
        raise HTTPException(status_code=404, detail="API key not found")
    _require_project_owner(project_id, user)

    try:
        result = APIKeyManager.rotate_api_key(key_id, project_id, grace_hours=rotate_data.grace_hours)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/api-keys/{project_id}")
async def list_api_keys(project_id: str, user: CurrentUser = Depends(get_current_user)):
    """List all API keys for a project the authenticated user owns."""
    _require_project_owner(project_id, user)
    api_keys = APIKeyManager.list_api_keys(project_id)
    return {"success": True, "api_keys": api_keys}


@router.delete("/admin/api-keys/{key_id}")
async def revoke_api_key(key_id: str, user: CurrentUser = Depends(get_current_user)):
    """Revoke an API key belonging to a project the authenticated user owns."""
    project_id = APIKeyManager.get_key_project_id(key_id)
    if not project_id:
        raise HTTPException(status_code=404, detail="API key not found")
    _require_project_owner(project_id, user)

    success = APIKeyManager.revoke_api_key(key_id, project_id=project_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"success": True, "message": "API key revoked"}
