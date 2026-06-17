"""
Prediction API endpoint for bot detection.
Integrates trained ML model for real-time inference.
"""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import joblib
import numpy as np

# Add ML models to path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ml"))

from models.inference import BotDetector

router = APIRouter(prefix="/api/predict", tags=["prediction"])

# Global model and detector (loaded on startup)
detector = None


class PredictionRequest(BaseModel):
    """Request model for bot prediction."""
    avg_mouse_vel: float = Field(..., description="Average mouse velocity")
    std_mouse_vel: float = Field(..., description="Standard deviation of mouse velocity")
    max_mouse_vel: float = Field(..., description="Maximum mouse velocity")
    total_distance: float = Field(..., description="Total mouse distance")
    avg_angle_change: float = Field(..., description="Average angle change")
    click_count: int = Field(..., description="Number of clicks")
    avg_click_interval: float = Field(..., description="Average click interval")
    avg_iki: float = Field(..., description="Average inter-key interval")
    std_iki: float = Field(..., description="Standard deviation of IKI")
    avg_hold: float = Field(..., description="Average key hold time")
    scroll_count: int = Field(..., description="Number of scroll events")
    avg_scroll_vel: float = Field(..., description="Average scroll velocity")
    session_duration: float = Field(..., description="Session duration in seconds")
    event_count: int = Field(..., description="Total number of events")


class PredictionResponse(BaseModel):
    """Response model for bot prediction."""
    bot_probability: float = Field(..., description="Probability of being a bot (0-1)")
    risk_score: int = Field(..., description="Risk score (0-100)")
    action: str = Field(..., description="Action: 'accept' or 'reject'")
    confidence: float = Field(..., description="Confidence in prediction (0-1)")


def load_model():
    """Load the trained model and scaler."""
    global detector
    try:
        detector = BotDetector()
        print("[Prediction API] Model loaded successfully")
    except Exception as e:
        print(f"[Prediction API] Error loading model: {e}")
        detector = None


@router.on_event("startup")
async def startup():
    """Load model on startup."""
    load_model()


@router.post("", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Predict if a session is bot or human.
    
    Accepts 14 behavioral features and returns:
    - bot_probability: 0-1 score
    - risk_score: 0-100
    - action: 'accept' or 'reject'
    - confidence: 0-1
    """
    if detector is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Convert request to dict
        features = request.dict()
        
        # Run prediction
        result = detector.predict_session(features)
        
        return PredictionResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.get("/health")
async def health():
    """Check if model is loaded."""
    return {
        "status": "ok" if detector is not None else "error",
        "model_loaded": detector is not None
    }
