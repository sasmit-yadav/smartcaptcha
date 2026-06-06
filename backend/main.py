"""
EcoHub Backend - Main FastAPI application.
"""

import sys
import os
from pathlib import Path

# Add backend root to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.telemetry import router as telemetry_router
from api.routes.session import router as session_router
from core.database import init_db, get_session_stats

print("DATABASE URL:")
print(os.getenv("DATABASE_URL"))

app = FastAPI(title="EcoHub API", version="0.1.0")

# CORS - use ALLOWED_ORIGINS from env or allow all for development
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins != "*":
    allowed_origins = [origin.strip() for origin in allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins != "*" else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(telemetry_router)
app.include_router(session_router)


@app.on_event("startup")
async def startup():
    init_db()
    port = os.getenv("PORT", "8000")
    print(f"[EcoHub API] Started on port {port} (PostgreSQL)")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ecohub-api"}


@app.get("/api/stats")
async def stats():
    """Quick stats for monitoring."""
    return get_session_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
