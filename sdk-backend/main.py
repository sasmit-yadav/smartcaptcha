"""
NextCaptcha SDK-Only Backend - Production API for customers
Only provides prediction API, no telemetry storage
"""

import sys
import os
from pathlib import Path

# Add project root to path so imports work
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from models.inference import BotDetector
from api_key_manager import APIKeyManager, UserManager
from typing import Optional, List
import logging

app = FastAPI(title="NextCaptcha API", version="1.0.0")

logger = logging.getLogger("uvicorn.error")

# Security
security = HTTPBearer()

# Initialize ML model (shared with demo backend)
detector = None

# API Key Manager
api_key_manager = APIKeyManager()

@app.on_event("startup")
async def startup():
    global detector
    try:
        detector = BotDetector(use_risk_engine=True)
        port = os.getenv("PORT", "8000")
        print(f"[NextCaptcha API] Started on port {port}")
        print(f"[NextCaptcha API] V4 Model with Risk Engine loaded")
        print(f"[NextCaptcha API] Production API key verification enabled")
    except Exception as e:
        print(f"[NextCaptcha API] Failed to load model: {e}")
        raise

# CORS - restrict to customer domains in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to customer domains
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["*"],
)

# Demo mode for testing (set DEMO_MODE=1 to use simple keys)
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"
DEMO_API_KEYS = ["demo-key", "sc_live_xxxxxxxxxxxxx"]

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify API key using production API key manager
    Falls back to demo keys if DEMO_MODE is enabled
    """
    api_key = credentials.credentials
    print(f"[DEBUG] Received API key: {api_key[:20]}...")
    
    # Demo mode fallback
    if DEMO_MODE and api_key in DEMO_API_KEYS:
        return {
            'key_id': 'demo',
            'project_id': 'demo-project',
            'project_name': 'Demo Project',
            'owner_id': 'demo-user',
            'owner_email': 'demo@example.com',
            'company_name': 'Demo Company',
            'is_admin': False,
            'allowed_domains': ['*']
        }
    
    # Production verification
    key_info = api_key_manager.verify_api_key(api_key)
    if not key_info:
        raise HTTPException(
            status_code=403, 
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Update last used timestamp
    api_key_manager.update_last_used(key_info['key_id'])
    
    return key_info

@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok", "service": "nextcaptcha-sdk-api"}

@app.get("/")
async def root():
    return {
        "service": "NextCaptcha API",
        "status": "running",
        "version": "4.0"
    }

@app.post("/api/telemetry")
async def telemetry(request: Request):
    """
    Dummy telemetry endpoint for SDK compatibility
    SDK backend doesn't store telemetry, but SDK may try to send it
    """
    print("[DEBUG] Telemetry endpoint called (not storing in SDK backend)")
    return {"status": "ok", "message": "Telemetry received but not stored"}

@app.post("/api/predict")
async def predict(
    request: Request,
    authorization: str = Header(None),
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """
    Prediction API for SDK customers
    Takes behavioral features and returns bot detection decision
    """
    print(f"[DEBUG] Authorization header: {authorization}")
    print(f"[DEBUG] X-API-Key header: {x_api_key}")
    
    # Extract API key from X-API-Key header (SDK sends it this way)
    api_key = x_api_key
    
    # Fallback to Authorization header
    if not api_key and authorization and authorization.startswith("Bearer "):
        api_key = authorization[7:]
    
    print(f"[DEBUG] Extracted API key: {api_key[:20] if api_key else None}...")
    
    # Verify API key
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    key_info = api_key_manager.verify_api_key(api_key)
    if not key_info:
        print(f"[DEBUG] API key verification failed for: {api_key[:20]}...")
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    
    print(f"[DEBUG] API key verified successfully for project: {key_info['project_name']}")
    
    try:
        # Parse request body
        body = await request.json()
        
        # Debug: Log received features
        print(f"[DEBUG] Received body keys: {list(body.keys())}")
        print(f"[DEBUG] Total keys received: {len(body.keys())}")
        print(f"[DEBUG] V4 features present: avg_hover_duration={body.get('avg_hover_duration')}, avg_overshoot_ratio={body.get('avg_overshoot_ratio')}, mouse_curvature_std={body.get('mouse_curvature_std')}")
        
        # Extract features and fingerprint data
        features = {k: v for k, v in body.items() if k not in ['webdriver_flag', 'user_agent', 'has_touch', 'platform', 'sdkVersion']}
        print(f"[DEBUG] Features extracted: {len(features)} keys")
        print(f"[DEBUG] Feature keys: {list(features.keys())}")
        fingerprint = {
            'webdriver_flag': body.get('webdriver_flag', False),
            'user_agent': body.get('user_agent', ''),
            'has_touch': body.get('has_touch', False),
            'platform': body.get('platform', '')
        }
        
        # Get prediction from model
        result = detector.predict_session(features, fingerprint_data=fingerprint)
        
        # Debug: Log the result being returned
        print(f"[DEBUG] Prediction result: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")

# Admin API endpoints for API key management
class UserRegistration(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class ProjectCreate(BaseModel):
    name: str
    allowed_domains: Optional[List[str]] = None

class APIKeyCreate(BaseModel):
    project_id: str
    key_type: str = 'live'  # 'live', 'test', 'admin'

@app.post("/admin/register")
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

@app.post("/admin/login")
async def login_user(login_data: UserLogin):
    """Login user and return user info"""
    user = UserManager.verify_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"success": True, "user": user}

@app.post("/admin/projects")
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

@app.get("/admin/projects")
async def list_projects(user_id: str = Header(...)):
    """List all projects for a user"""
    projects = UserManager.list_user_projects(user_id)
    return {"success": True, "projects": projects}

@app.post("/admin/api-keys")
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

@app.get("/admin/api-keys/{project_id}")
async def list_api_keys(project_id: str):
    """List all API keys for a project"""
    api_keys = APIKeyManager.list_api_keys(project_id)
    return {"success": True, "api_keys": api_keys}

@app.delete("/admin/api-keys/{key_id}")
async def revoke_api_key(key_id: str):
    """Revoke an API key"""
    success = APIKeyManager.revoke_api_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"success": True, "message": "API key revoked"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
