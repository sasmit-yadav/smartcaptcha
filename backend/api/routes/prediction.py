"""
Prediction API endpoint for bot detection.
Integrates trained ML model for real-time inference.
"""
import csv
import hashlib
import os
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, List, Optional

# Add ML models to path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ml"))

from models.inference import BotDetector

router = APIRouter(prefix="/api/predict", tags=["prediction"])

detector = None
shadow_detector = None
canary_detector = None
feature_importance = {}


def _truthy(value: Optional[str]) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def _fail_open_enabled() -> bool:
    return _truthy(os.getenv("SMARTCAPTCHA_FAIL_OPEN"))


def _stable_percent(key: str) -> float:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF * 100


def _load_detector_from_env(prefix: str):
    model_path = os.getenv(f"{prefix}_MODEL_PATH")
    if not model_path:
        return None
    return BotDetector(
        model_path=model_path,
        scaler_path=os.getenv(f"{prefix}_SCALER_PATH"),
        metadata_path=os.getenv(f"{prefix}_METADATA_PATH"),
        use_risk_engine=True,
    )


def _load_feature_importance(active_detector) -> Dict[str, float]:
    if active_detector is None:
        return {}
    model_path = Path(active_detector.model_path)
    parts = model_path.stem.split("_")
    if len(parts) < 3:
        return {}
    model_name = "_".join(parts[:-2])
    timestamp = "_".join(parts[-2:])
    candidate = model_path.with_name(f"{model_name}_feature_importance_{timestamp}.csv")
    if not candidate.exists():
        return {}

    weights = {}
    with open(candidate, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            feature = row.get("feature")
            importance = row.get("importance")
            if feature and importance is not None:
                try:
                    weights[feature] = float(importance)
                except ValueError:
                    pass
    return weights


def _explain(features: Dict, result: Dict) -> List[Dict]:
    if not feature_importance:
        return []
    ranked = []
    for feature, importance in feature_importance.items():
        value = features.get(feature, 0)
        try:
            magnitude = abs(float(value))
        except (TypeError, ValueError):
            magnitude = 1.0 if value else 0.0
        ranked.append({
            "feature": feature,
            "value": value,
            "importance": round(importance, 6),
            "direction": "higher_risk" if result.get("bot_probability", 0) >= 0.5 else "lower_risk",
            "score": importance * max(magnitude, 1.0),
        })
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:3]


def _risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _apply_external_fusion(result: Dict, request_data: Dict) -> Dict:
    """Phase 17 fusion: combine behavior model with optional network/TLS scores."""
    behavior_score = float(result.get("risk_score", 0))
    signal_scores = [behavior_score]
    signal_names = ["behavior"]

    for name in ("ip_reputation_score", "tls_score", "fingerprint_stability_score"):
        value = request_data.get(name)
        if value is not None:
            signal_scores.append(float(value))
            signal_names.append(name)

    if len(signal_scores) == 1:
        result["risk_level"] = _risk_level(int(result.get("risk_score", 0)))
        result["fusion_signals"] = signal_names
        return result

    fused = round((0.55 * signal_scores[0]) + (0.45 * (sum(signal_scores[1:]) / len(signal_scores[1:]))))
    result["risk_score"] = int(max(0, min(100, fused)))
    result["overall_risk"] = result["risk_score"]
    result["risk_level"] = _risk_level(result["risk_score"])
    result["fusion_signals"] = signal_names
    if result["risk_score"] >= 80:
        result["action"] = "block"
    elif result["risk_score"] >= 30:
        result["action"] = "challenge"
    else:
        result["action"] = "allow"
    return result


def _autofill_adjust(features: Dict) -> Dict:
    """Phase 16.3: autofill should not look like zero-human-typing bot behavior."""
    if not features.get("autofill_detected"):
        return features
    adjusted = dict(features)
    for key in (
        "avg_iki", "std_iki", "avg_hold", "iki_p10", "iki_p50", "iki_p90",
        "hold_std", "hold_p90", "backspace_count"
    ):
        adjusted[key] = 0
    return adjusted


class PredictionRequest(BaseModel):
    """Request model for bot prediction - V4 with Risk Engine support."""
    session_id: Optional[str] = Field(None, description="Stable session id for canary routing")
    # V1 Base Features
    avg_mouse_vel: float = Field(0, description="Average mouse velocity")
    std_mouse_vel: float = Field(0, description="Standard deviation of mouse velocity")
    max_mouse_vel: float = Field(0, description="Maximum mouse velocity")
    total_distance: float = Field(0, description="Total mouse distance")
    avg_angle_change: float = Field(0, description="Average angle change")
    click_count: int = Field(0, description="Number of clicks")
    avg_click_interval: float = Field(0, description="Average click interval")
    avg_iki: float = Field(0, description="Average inter-key interval")
    std_iki: float = Field(0, description="Standard deviation of IKI")
    avg_hold: float = Field(0, description="Average key hold time")
    scroll_count: int = Field(0, description="Number of scroll events")
    avg_scroll_vel: float = Field(0, description="Average scroll velocity")
    session_duration: float = Field(0, description="Session duration in seconds")
    event_count: int = Field(0, description="Total number of events")
    # V2 Additions
    mouse_vel_p10: float = 0
    mouse_vel_p50: float = 0
    mouse_vel_p90: float = 0
    mouse_accel_mean: float = 0
    mouse_accel_std: float = 0
    mouse_accel_max: float = 0
    mouse_angle_std: float = 0
    mouse_angle_p90: float = 0
    mouse_path_efficiency: float = 0
    mouse_idle_gap_count: int = 0
    mouse_event_ratio: float = 0
    click_interval_std: float = 0
    click_interval_min: float = 0
    click_interval_p90: float = 0
    double_click_count: int = 0
    key_count: int = 0
    iki_p10: float = 0
    iki_p50: float = 0
    iki_p90: float = 0
    hold_std: float = 0
    hold_p90: float = 0
    backspace_count: int = 0
    scroll_vel_std: float = 0
    scroll_rev_count: int = 0
    scroll_pause_count: int = 0
    focus_event_count: int = 0
    touch_event_count: int = 0
    event_rate: float = 0
    pause_count: int = 0
    pause_ratio: float = 0
    # V3 Additions
    mouse_curvature_std: float = 0
    mouse_jerk_std: float = 0
    movement_entropy: float = 0
    # V4 Additions
    avg_hover_duration: float = 0
    hover_duration_std: float = 0
    avg_overshoot_ratio: float = 0
    overshoot_ratio_std: float = 0
    webdriver_flag: bool = False
    user_agent: str = ""
    has_touch: bool = False
    platform: str = ""
    autofill_detected: bool = Field(False, description="True when SDK detects browser autofill")
    ip_reputation_score: Optional[float] = Field(None, ge=0, le=100)
    tls_score: Optional[float] = Field(None, ge=0, le=100)
    fingerprint_stability_score: Optional[float] = Field(None, ge=0, le=100)


class FingerprintData(BaseModel):
    """Fingerprint data for Risk Engine."""
    webdriver_flag: bool = False
    user_agent: str = ""
    has_touch: bool = False
    platform: str = ""


class PredictionResponse(BaseModel):
    """Response model for bot prediction - V4 with Risk Engine."""
    model_config = ConfigDict(protected_namespaces=())

    bot_probability: float = Field(..., description="Probability of being a bot (0-1)")
    model_probability: Optional[float] = Field(None, description="Raw model probability before rule boost")
    rule_boost: Optional[float] = Field(None, description="Deterministic risk boost")
    risk_score: int = Field(..., description="Risk score (0-100)")
    action: str = Field(..., description="Action: 'accept', 'challenge', or 'reject'")
    confidence: float = Field(..., description="Confidence in prediction (0-1)")
    # V4 Risk Engine fields
    behavior_score: Optional[float] = Field(None, description="Behavior score (0-100)")
    fingerprint_score: Optional[float] = Field(None, description="Fingerprint score (0-100)")
    challenge_score: Optional[float] = Field(None, description="Challenge score (0-100)")
    overall_risk: Optional[float] = Field(None, description="Overall risk score (0-100)")
    risk_engine_enabled: bool = Field(False, description="Whether Risk Engine was used")
    risk_level: Optional[str] = None
    fusion_signals: List[str] = Field(default_factory=list)
    explanations: List[Dict] = Field(default_factory=list)
    model_track: str = Field("active", description="active, canary, or fail_open")
    shadow_prediction: Optional[Dict] = None


def load_model():
    """Load the trained V4 model and scaler with Risk Engine."""
    global detector, shadow_detector, canary_detector, feature_importance
    try:
        detector = BotDetector(use_risk_engine=True)
        shadow_detector = _load_detector_from_env("SMARTCAPTCHA_SHADOW")
        canary_detector = _load_detector_from_env("SMARTCAPTCHA_CANARY")
        feature_importance = _load_feature_importance(detector)
        print("[Prediction API] V4 Model with Risk Engine loaded successfully")
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
    Predict if a session is bot or human with V4 Risk Engine.
    
    Accepts V4 behavioral features and fingerprint data in the same request:
    - bot_probability: 0-1 score
    - risk_score: 0-100
    - action: 'accept', 'challenge', or 'reject'
    - confidence: 0-1
    - behavior_score, fingerprint_score, challenge_score (if Risk Engine enabled)
    """
    if detector is None:
        if _fail_open_enabled():
            return PredictionResponse(
                bot_probability=0.0,
                model_probability=0.0,
                rule_boost=0.0,
                risk_score=0,
                action="allow",
                confidence=0.0,
                risk_level="low",
                model_track="fail_open",
            )
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        if _fail_open_enabled():
            return PredictionResponse(
                bot_probability=0.0,
                model_probability=0.0,
                rule_boost=0.0,
                risk_score=0,
                action="allow",
                confidence=0.0,
                risk_level="low",
                model_track="fail_open",
            )

        features = request.model_dump()
        
        fingerprint_data = {
            'webdriver_flag': features.get('webdriver_flag', False),
            'user_agent': features.get('user_agent', ''),
            'has_touch': features.get('has_touch', False),
            'platform': features.get('platform', '')
        }
        
        features_for_prediction = {k: v for k, v in features.items() 
                                   if k not in [
                                       'session_id', 'user_agent', 'has_touch', 'platform',
                                       'ip_reputation_score', 'tls_score', 'fingerprint_stability_score'
                                   ]}
        features_for_prediction = _autofill_adjust(features_for_prediction)

        active_detector = detector
        model_track = "active"
        canary_percent = float(os.getenv("SMARTCAPTCHA_CANARY_PERCENT", "0") or 0)
        canary_key = features.get("session_id") or f"{features.get('event_count', 0)}:{features.get('session_duration', 0)}"
        if canary_detector and canary_percent > 0 and _stable_percent(canary_key) < canary_percent:
            active_detector = canary_detector
            model_track = "canary"
        
        result = active_detector.predict_session(features_for_prediction, fingerprint_data=fingerprint_data)
        result = _apply_external_fusion(result, features)
        result["model_track"] = model_track
        result["explanations"] = _explain(features_for_prediction, result)

        if shadow_detector:
            shadow = shadow_detector.predict_session(features_for_prediction, fingerprint_data=fingerprint_data)
            result["shadow_prediction"] = {
                "bot_probability": shadow.get("bot_probability"),
                "risk_score": shadow.get("risk_score"),
                "action": shadow.get("action"),
            }
        
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
