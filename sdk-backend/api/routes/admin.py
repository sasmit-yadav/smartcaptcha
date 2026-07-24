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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api_key_manager import APIKeyManager, UserManager
from core.auth import (
    CurrentUser,
    get_current_user,
    issue_session_tokens,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)
from core.email import (
    send_api_key_created_email,
    send_api_key_revoked_email,
    send_api_key_rotated_email,
    send_domains_updated_email,
    send_new_signin_email,
    send_password_changed_email,
    send_project_created_email,
    send_welcome_email,
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
    """Safe user payload for the dashboard (never include password_hash)."""
    # Explicit False only → Google-only. Missing/None must default to True so
    # email accounts and legacy refresh stubs never look like "set password".
    if "has_password" not in user or user.get("has_password") is None:
        has_password = True
    else:
        has_password = bool(user.get("has_password"))

    if "google_linked" not in user or user.get("google_linked") is None:
        google_linked = False
    else:
        google_linked = bool(user.get("google_linked"))

    # Legacy Google-only rows may predate google_linked.
    if not has_password:
        google_linked = True

    methods = []
    if has_password:
        methods.append("password")
    if google_linked:
        methods.append("google")
    if not methods:
        methods.append("password")
    return {
        "id": str(user["id"]),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "company_name": user.get("company_name"),
        "is_admin": bool(user.get("is_admin", False)),
        "has_password": has_password,
        "google_linked": google_linked,
        "auth_methods": methods,
    }


class ChangePasswordRequest(BaseModel):
    current_password: Optional[str] = Field(None, max_length=72)
    new_password: str = Field(..., min_length=12, max_length=72)


def _require_project_owner(project_id: str, user: CurrentUser) -> dict:
    """Fetch a project and raise 403/404 unless the current user owns it."""
    project = UserManager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if str(project["owner_id"]) != str(user.user_id):
        raise HTTPException(status_code=403, detail="You do not have access to this project")
    return project


@router.post("/admin/register", dependencies=[Depends(rate_limit("admin_register", limit=5, window_seconds=60))])
async def register_user(
    user_data: UserRegistration,
    request: Request,
    background_tasks: BackgroundTasks,
):
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
    background_tasks.add_task(
        send_welcome_email,
        user["email"],
        full_name=user.get("full_name"),
        signup_method="email",
    )
    return {"success": True, "user": _public_user(user), **tokens}


@router.post("/admin/login", dependencies=[Depends(rate_limit("admin_login", limit=10, window_seconds=60))])
async def login_user(
    login_data: UserLogin,
    request: Request,
    background_tasks: BackgroundTasks,
):
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
    background_tasks.add_task(
        send_new_signin_email,
        user["email"],
        full_name=user.get("full_name"),
        ip=ip,
        user_agent=ua,
        method="password",
    )
    return {"success": True, "user": _public_user(user), **tokens}


@router.post("/admin/refresh", dependencies=[Depends(rate_limit("admin_refresh", limit=30, window_seconds=60))])
async def refresh_session(body: RefreshRequest, request: Request):
    """Rotate refresh token and mint a new access token."""
    ua, ip = _client_meta(request)
    user_stub, access, new_refresh = rotate_refresh_token(body.refresh_token, user_agent=ua, ip=ip)
    profile = UserManager.get_user_by_id(user_stub["id"]) or user_stub
    return {
        "success": True,
        "user": _public_user(profile),
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


@router.get("/admin/me")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    """Return the authenticated account profile for the dashboard account menu."""
    profile = UserManager.get_user_by_id(user.user_id)
    if not profile:
        raise HTTPException(status_code=401, detail="Account not found")
    return {"success": True, "user": _public_user(profile)}


@router.post(
    "/admin/change-password",
    dependencies=[Depends(rate_limit("admin_change_password", limit=5, window_seconds=60))],
)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Change password (email accounts) or set a first password (Google-only accounts).
    Revokes other sessions, then re-issues tokens for this browser.
    """
    before = UserManager.get_user_by_id(user.user_id) or {}
    was_set = not bool(before.get("has_password"))
    try:
        updated = UserManager.change_password(
            user.user_id,
            body.new_password,
            current_password=body.current_password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to update password")

    revoke_all_refresh_tokens(user.user_id)
    ua, ip = _client_meta(request)
    tokens = issue_session_tokens(
        str(updated["id"]),
        updated["email"],
        bool(updated.get("is_admin", False)),
        user_agent=ua,
        ip=ip,
    )
    background_tasks.add_task(
        send_password_changed_email,
        updated["email"],
        full_name=updated.get("full_name"),
        ip=ip,
        user_agent=ua,
        was_set=was_set,
    )
    return {
        "success": True,
        "user": _public_user(updated),
        "message": "Password updated. Other devices must sign in again.",
        **tokens,
    }


@router.post("/admin/google-login", dependencies=[Depends(rate_limit("admin_google_login", limit=20, window_seconds=60))])
async def google_login(
    login_req: GoogleLoginRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
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
            created_now = bool(user.pop("created_now", False))
            ua, ip = _client_meta(request)
            tokens = issue_session_tokens(
                str(user["id"]),
                user["email"],
                bool(user.get("is_admin", False)),
                user_agent=ua,
                ip=ip,
            )
            if created_now:
                background_tasks.add_task(
                    send_welcome_email,
                    user["email"],
                    full_name=user.get("full_name"),
                    signup_method="google",
                )
            else:
                background_tasks.add_task(
                    send_new_signin_email,
                    user["email"],
                    full_name=user.get("full_name"),
                    ip=ip,
                    user_agent=ua,
                    method="google",
                )
            return {"success": True, "user": _public_user(user), **tokens}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=401, detail="Google sign-in failed")


@router.post("/admin/projects")
async def create_project(
    project_data: ProjectCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new project for the authenticated user."""
    try:
        project = UserManager.create_project(
            user_id=user.user_id,
            name=project_data.name,
            allowed_domains=project_data.allowed_domains
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    ua, ip = _client_meta(request)
    profile = UserManager.get_user_by_id(user.user_id) or {}
    background_tasks.add_task(
        send_project_created_email,
        user.email,
        full_name=profile.get("full_name"),
        project_name=project.get("name"),
        ip=ip,
        user_agent=ua,
    )
    return {"success": True, "project": project}


@router.get("/admin/projects")
async def list_projects(user: CurrentUser = Depends(get_current_user)):
    """List all projects owned by the authenticated user."""
    projects = UserManager.list_user_projects(user.user_id)
    return {"success": True, "projects": projects}


@router.patch("/admin/projects/{project_id}")
async def update_project_domains(
    project_id: str,
    body: ProjectDomainsUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    """Update allowed domains for a project the authenticated user owns."""
    project = _require_project_owner(project_id, user)
    try:
        updated = UserManager.update_project_domains(project_id, body.allowed_domains)
        if not updated:
            raise HTTPException(status_code=404, detail="Project not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    ua, ip = _client_meta(request)
    profile = UserManager.get_user_by_id(user.user_id) or {}
    background_tasks.add_task(
        send_domains_updated_email,
        user.email,
        full_name=profile.get("full_name"),
        project_name=updated.get("name") or project.get("name"),
        domains=updated.get("allowed_domains") or body.allowed_domains or [],
        ip=ip,
        user_agent=ua,
    )
    return {"success": True, "project": updated}


@router.post("/admin/api-keys")
async def create_api_key(
    key_data: APIKeyCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new API key for a project the authenticated user owns."""
    project = _require_project_owner(key_data.project_id, user)
    try:
        api_key_info = APIKeyManager.create_api_key(
            project_id=key_data.project_id,
            key_type=key_data.key_type
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    ua, ip = _client_meta(request)
    profile = UserManager.get_user_by_id(user.user_id) or {}
    background_tasks.add_task(
        send_api_key_created_email,
        user.email,
        full_name=profile.get("full_name"),
        project_name=project.get("name"),
        ip=ip,
        user_agent=ua,
        key_kind="single",
    )
    return {"success": True, "api_key": api_key_info}


@router.post("/admin/api-keys/pair")
async def create_api_key_pair(
    key_data: ProjectIdOnly,
    request: Request,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Create a site key + secret key pair for a project (the recommended flow
    for new integrations). Both plaintexts are only ever returned here, once.
    """
    project = _require_project_owner(key_data.project_id, user)
    try:
        pair = APIKeyManager.create_key_pair(key_data.project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    ua, ip = _client_meta(request)
    profile = UserManager.get_user_by_id(user.user_id) or {}
    background_tasks.add_task(
        send_api_key_created_email,
        user.email,
        full_name=profile.get("full_name"),
        project_name=project.get("name"),
        ip=ip,
        user_agent=ua,
    )
    return {"success": True, **pair}


@router.post("/admin/api-keys/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    rotate_data: APIKeyRotate,
    request: Request,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Rotate an API key belonging to a project the authenticated user owns.
    The old key keeps working for `grace_hours` (0 = deactivated immediately).
    """
    project_id = APIKeyManager.get_key_project_id(key_id)
    if not project_id:
        raise HTTPException(status_code=404, detail="API key not found")
    project = _require_project_owner(project_id, user)

    try:
        result = APIKeyManager.rotate_api_key(key_id, project_id, grace_hours=rotate_data.grace_hours)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    ua, ip = _client_meta(request)
    profile = UserManager.get_user_by_id(user.user_id) or {}
    background_tasks.add_task(
        send_api_key_rotated_email,
        user.email,
        full_name=profile.get("full_name"),
        project_name=project.get("name"),
        ip=ip,
        user_agent=ua,
        grace_hours=rotate_data.grace_hours,
    )
    return {"success": True, **result}


@router.get("/admin/api-keys/{project_id}")
async def list_api_keys(project_id: str, user: CurrentUser = Depends(get_current_user)):
    """List all API keys for a project the authenticated user owns."""
    _require_project_owner(project_id, user)
    api_keys = APIKeyManager.list_api_keys(project_id)
    return {"success": True, "api_keys": api_keys}


@router.delete("/admin/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    """Revoke an API key belonging to a project the authenticated user owns."""
    project_id = APIKeyManager.get_key_project_id(key_id)
    if not project_id:
        raise HTTPException(status_code=404, detail="API key not found")
    project = _require_project_owner(project_id, user)

    success = APIKeyManager.revoke_api_key(key_id, project_id=project_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    ua, ip = _client_meta(request)
    profile = UserManager.get_user_by_id(user.user_id) or {}
    background_tasks.add_task(
        send_api_key_revoked_email,
        user.email,
        full_name=profile.get("full_name"),
        project_name=project.get("name"),
        ip=ip,
        user_agent=ua,
    )
    return {"success": True, "message": "API key revoked"}
