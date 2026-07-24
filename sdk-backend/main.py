"""
VeilProof API — single production backend.

Serves:
- /api/predict          bot-detection decisions (API key required)
- /api/telemetry        behavioral event ingestion (API key, ingest key, or allowed origin)
- /api/session/*        session lifecycle (same auth as telemetry)
- /admin/*              customer accounts, projects, API keys (website dashboard)
- /api/health, /api/stats

Routes live in api/routes/; DB layer in core/database.py; ML in models/.
"""

import sys
import os
from pathlib import Path

# Add project root to path so imports work
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load .env before importing modules that require DATABASE_URL at import time
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from api.routes.predict import router as predict_router, get_detector
from api.routes.telemetry import router as telemetry_router
from api.routes.session import router as session_router
from api.routes.admin import router as admin_router
from api.routes.siteverify import router as siteverify_router
from core.admin_api import router as super_admin_router

app = FastAPI(title="VeilProof API", version="1.0.0")

logger = logging.getLogger("uvicorn.error")

# CORS stays open on purpose: customers call /api/predict from arbitrary
# domains, so security is enforced by API keys and the ingest origin gate
# (core/ingest_auth.py), not by CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict_router)
app.include_router(telemetry_router)
app.include_router(session_router)
app.include_router(admin_router)
app.include_router(siteverify_router)
app.include_router(super_admin_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log the raw body and validation errors to help debug intermittent 422s
    try:
        body = await request.body()
        body_text = body.decode(errors="replace")
    except Exception:
        body_text = "<unreadable>"
    logger.error("Request validation error on %s %s: %s -- Body: %s",
                 request.method, request.url.path, exc.errors(), body_text)
    return JSONResponse(status_code=422, content={"detail": "Request validation error", "errors": exc.errors()})


@app.on_event("startup")
async def startup():
    try:
        # Run database initialization and auto-migrations
        from core.database import init_db
        init_db()

        # Warm the ML model so the first predict request isn't slow
        get_detector()

        port = os.getenv("PORT", "8001")
        print(f"[VeilProof API] Started on port {port}")
        print(f"[VeilProof API] V4 Model with Risk Engine loaded")
        print(f"[VeilProof API] Production API key verification enabled")
        print(f"[VeilProof API] Telemetry storage enabled")
    except Exception as e:
        print(f"[VeilProof API] Startup failed: {e}")
        raise


@app.api_route("/health", methods=["GET", "HEAD"])
@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok", "service": "veilproof-api"}


@app.get("/")
async def root():
    return {
        "service": "VeilProof API",
        "status": "running",
        "version": "4.0"
    }


@app.get("/api/stats")
async def stats():
    """Quick session/event counts + request-signing ops counters."""
    from core.database import get_session_stats
    from core import request_signing
    payload = get_session_stats()
    if isinstance(payload, dict):
        payload = {**payload, "request_signing": request_signing.get_signing_stats()}
    return payload


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
