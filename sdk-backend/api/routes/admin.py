"""
VeriFlow API — Customer account routes.
User registration/login (email + Google OAuth), project management, and
API key lifecycle. Used by the website dashboard.

Auth model: register/login/google-login issue a signed session token
(core/auth.py). Every /admin/projects and /admin/api-keys route requires
that token via Depends(get_current_user), and project/key ownership is
checked against the authenticated user — a caller can only see or modify
their own projects and keys.
"""

import os
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api_key_manager import APIKeyManager, UserManager
from core.auth import create_access_token, get_current_user, CurrentUser

router = APIRouter()


class UserRegistration(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str


class ProjectCreate(BaseModel):
    name: str
    allowed_domains: Optional[List[str]] = None


class APIKeyCreate(BaseModel):
    project_id: str
    key_type: str = 'live'  # 'live', 'test', 'admin'


def _require_project_owner(project_id: str, user: CurrentUser) -> dict:
    """Fetch a project and raise 403/404 unless the current user owns it."""
    project = APIKeyManager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if str(project["owner_id"]) != str(user.user_id):
        raise HTTPException(status_code=403, detail="You do not have access to this project")
    return project


@router.post("/admin/register")
async def register_user(user_data: UserRegistration):
    """Register a new user and issue a session token."""
    try:
        user = UserManager.create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            company_name=user_data.company_name
        )
        token = create_access_token(user_id=user["id"], email=user["email"], is_admin=user.get("is_admin", False))
        return {"success": True, "user": user, "access_token": token}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/login")
async def login_user(login_data: UserLogin):
    """Login user and issue a session token."""
    user = UserManager.verify_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user_id=user["id"], email=user["email"], is_admin=user.get("is_admin", False))
    return {"success": True, "user": user, "access_token": token}


@router.post("/admin/google-login")
async def google_login(login_req: GoogleLoginRequest):
    """Verify Google token, get or create user, and issue a session token."""
    import urllib.request
    import json

    id_token = login_req.id_token
    tokeninfo_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"

    try:
        req = urllib.request.Request(tokeninfo_url)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                raise HTTPException(status_code=401, detail="Google token verification failed")

            payload = json.loads(response.read().decode())

            # Verify client ID audience if configured in environment
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            if client_id and payload.get("aud") != client_id:
                raise HTTPException(status_code=401, detail="Invalid Google Client ID audience")

            email = payload.get("email")
            if not email:
                raise HTTPException(status_code=400, detail="Email not provided by Google")

            name = payload.get("name", "")

            # Fetch or create the user in database
            user = UserManager.get_or_create_google_user(email=email, name=name)
            token = create_access_token(user_id=user["id"], email=user["email"], is_admin=user.get("is_admin", False))
            return {"success": True, "user": user, "access_token": token}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=401, detail=f"Google Authentication failed: {e}")


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
