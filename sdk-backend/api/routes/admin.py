"""
VeriFlow API — Customer account routes.
User registration/login (email + Google OAuth), project management, and
API key lifecycle. Used by the website dashboard.

NOTE: these endpoints currently trust the client-supplied user-id header;
adding real session tokens is tracked as a follow-up security task.
"""

import os
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from api_key_manager import APIKeyManager, UserManager

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


@router.post("/admin/register")
async def register_user(user_data: UserRegistration):
    """Register a new user"""
    try:
        user = UserManager.create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            company_name=user_data.company_name
        )
        return {"success": True, "user": user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/login")
async def login_user(login_data: UserLogin):
    """Login user and return user info"""
    user = UserManager.verify_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"success": True, "user": user}


@router.post("/admin/google-login")
async def google_login(login_req: GoogleLoginRequest):
    """Verify Google token, get or create user, and return user info"""
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
            return {"success": True, "user": user}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=401, detail=f"Google Authentication failed: {e}")


@router.post("/admin/projects")
async def create_project(project_data: ProjectCreate, user_id: str = Header(...)):
    """Create a new project for a user"""
    try:
        project = UserManager.create_project(
            user_id=user_id,
            name=project_data.name,
            allowed_domains=project_data.allowed_domains
        )
        return {"success": True, "project": project}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/projects")
async def list_projects(user_id: str = Header(...)):
    """List all projects for a user"""
    projects = UserManager.list_user_projects(user_id)
    return {"success": True, "projects": projects}


@router.post("/admin/api-keys")
async def create_api_key(key_data: APIKeyCreate):
    """Create a new API key for a project"""
    try:
        api_key_info = APIKeyManager.create_api_key(
            project_id=key_data.project_id,
            key_type=key_data.key_type
        )
        return {"success": True, "api_key": api_key_info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/api-keys/{project_id}")
async def list_api_keys(project_id: str):
    """List all API keys for a project"""
    api_keys = APIKeyManager.list_api_keys(project_id)
    return {"success": True, "api_keys": api_keys}


@router.delete("/admin/api-keys/{key_id}")
async def revoke_api_key(key_id: str):
    """Revoke an API key"""
    success = APIKeyManager.revoke_api_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"success": True, "message": "API key revoked"}
