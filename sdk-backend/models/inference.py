"""Inference module for bot detection predictions with Risk Engine integration."""
import json
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd

from features.feature_columns import LEGACY_FEATURE_COLUMNS, V2_FEATURE_COLUMNS, V3_FEATURE_COLUMNS, V4_FEATURE_COLUMNS, V5_FEATURE_COLUMNS
from models.risk_engine import create_risk_engine, RiskEngine

ROOT = Path(__file__).resolve().parents[1]


class BotDetector:
    """Bot detection model for inference with Risk Engine integration."""

    def __init__(self, model_path=None, scaler_path=None, metadata_path=None):
        # Prefer the newest artifact version that has actually been trained
        # (a model_comparison_*.json present). Falls back down the chain so a
        # deploy without v5 artifacts keeps serving v4/v3.
        artifacts_root = ROOT / "models" / "artifacts"
        artifacts_dir = artifacts_root / "v3"
        for version in ("v4", "v5"):
            candidate = artifacts_root / version
            if any(candidate.glob("model_comparison_*.json")):
                artifacts_dir = candidate
        if model_path is None:
            selected = self._selected_artifacts_from_latest_comparison(artifacts_dir)
            if selected:
                model_path = selected.get("model_path")
                scaler_path = scaler_path or selected.get("scaler_path")
                metadata_path = metadata_path or selected.get("metadata_path")
                print(f"Using selected model from latest comparison: {model_path}")
            else:
                model_files = list(artifacts_dir.glob("*random_forest*.pkl")) + list(
                    artifacts_dir.glob("*xgboost*.pkl")
                )
                if not model_files:
                    raise FileNotFoundError("No trained model found. Please train a model first.")
                model_path = max(model_files, key=lambda x: x.stat().st_mtime)
                print(f"Using latest model: {model_path}")

        if scaler_path is None:
            scaler_files = list(artifacts_dir.glob("scaler_*.pkl"))
            if not scaler_files:
                raise FileNotFoundError("No scaler found. Please train a model first.")
            scaler_path = max(scaler_files, key=lambda x: x.stat().st_mtime)
            print(f"Using latest scaler: {scaler_path}")

        self.model_path = Path(model_path)
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.metadata = self._load_metadata(metadata_path)
        
        self.feature_columns = self._resolve_feature_columns()
        print(f"Loaded {len(self.feature_columns)} feature columns")
        
        # Filter incoming features to only use what the model expects
        print(f"[DEBUG] Will filter incoming features to match model's {len(self.feature_columns)} expected features")

        self.risk_engine = create_risk_engine()

        # Calibrated decision threshold from training (strategy doc Finding 2:
        # serving must consume this, not a hard-coded 0.50). Falls back to
        # 0.50 for older v3 artifacts that never recorded a calibrated value.
        self.decision_threshold = float(self.metadata.get("decision_threshold", 0.5))

        # Optional orthogonal anomaly-detection axis (human-only IsolationForest,
        # strategy doc §B.1/§B.7). Loaded if this model's metadata references one;
        # silently absent (anomaly axis contributes 0) for older artifacts.
        self.anomaly_forest = None
        self.anomaly_score_zero = None
        self.anomaly_score_block = None
        anomaly_meta = self.metadata.get("anomaly") or {}
        anomaly_model_path = anomaly_meta.get("model_path")
        if anomaly_model_path:
            # metadata records the ml-train absolute path; on a real deploy only
            # sdk-backend's copy exists. Prefer the local artifacts-dir copy by
            # filename, fall back to the recorded path (same-machine dev).
            local_anomaly = self.model_path.parent / Path(anomaly_model_path).name
            resolved = local_anomaly if local_anomaly.exists() else Path(anomaly_model_path)
            if resolved.exists():
                try:
                    self.anomaly_forest = joblib.load(resolved)
                    self.anomaly_score_zero = anomaly_meta.get("score_zero")
                    self.anomaly_score_block = anomaly_meta.get("score_block")
                    print(f"Loaded anomaly detector: {resolved}")
                except Exception as e:
                    print(f"Could not load anomaly detector {resolved}: {e}")

        print(f"BotDetector initialized with model: {model_path}")
        print(f"Feature count: {len(self.feature_columns)}")
        print(f"Decision threshold: {self.decision_threshold}")

    def _selected_artifacts_from_latest_comparison(self, artifacts_dir):
        comparison_files = list(artifacts_dir.glob("model_comparison_*.json"))
        if not comparison_files:
            return None
        comparison_path = max(comparison_files, key=lambda x: x.stat().st_mtime)
        try:
            with open(comparison_path) as f:
                comparison = json.load(f)
            best_model = comparison.get("best_model")
            if not best_model or best_model not in comparison:
                return None
            artifacts = comparison[best_model].get("artifacts")
            
            # Convert absolute or Windows-style paths to local paths in artifacts_dir if they exist there
            if artifacts:
                for key in ['model_path', 'scaler_path', 'metadata_path']:
                    if key in artifacts and artifacts[key]:
                        orig_path_str = artifacts[key]
                        # Extract the base filename cleanly handling both Windows and Unix slashes
                        filename = orig_path_str.replace('\\', '/').split('/')[-1]
                        local_file = artifacts_dir / filename
                        if local_file.exists():
                            artifacts[key] = str(local_file)
                        else:
                            # Fallback check if the original path exists on the host
                            try:
                                if not Path(orig_path_str).exists():
                                    return None
                            except Exception:
                                return None
            return artifacts
        except Exception as exc:
            print(f"Could not read comparison artifact {comparison_path}: {exc}")
            return None

    def _load_metadata(self, metadata_path):
        if metadata_path:
            path = Path(metadata_path)
            if path.exists():
                try:
                    with open(path, encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Error loading metadata from {metadata_path}: {e}")
            else:
                print(f"Metadata path does not exist: {metadata_path}")
            return {}

        stem_parts = self.model_path.stem.split("_")
        if len(stem_parts) >= 3:
            model_name = "_".join(stem_parts[:-2])
            timestamp = "_".join(stem_parts[-2:])
            candidate = self.model_path.with_name(f"{model_name}_metadata_{timestamp}.json")
            if candidate.exists():
                try:
                    with open(candidate, encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Error loading candidate metadata: {e}")
        return {}

    def _resolve_feature_columns(self):
        if "feature_columns" in self.metadata:
            return list(self.metadata["feature_columns"])

        expected_features = getattr(self.model, "n_features_in_", None) or getattr(self.scaler, "n_features_in_", None)
        if expected_features == len(V5_FEATURE_COLUMNS):
            return V5_FEATURE_COLUMNS
        if expected_features == len(V4_FEATURE_COLUMNS):
            return V4_FEATURE_COLUMNS
        if expected_features == len(V3_FEATURE_COLUMNS):
            return V3_FEATURE_COLUMNS
        if expected_features == len(V2_FEATURE_COLUMNS):
            return V2_FEATURE_COLUMNS
        if expected_features == len(LEGACY_FEATURE_COLUMNS):
            return LEGACY_FEATURE_COLUMNS

        if hasattr(self.scaler, "feature_names_in_"):
            return list(self.scaler.feature_names_in_)
        if hasattr(self.model, "feature_names_in_"):
            return list(self.model.feature_names_in_)

        return V2_FEATURE_COLUMNS

    def _validate_features(self, features: Dict[str, Any], fingerprint_data: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        merged_features = features.copy()
        if fingerprint_data:
            for field in ["webdriver_flag"]:
                if field in fingerprint_data:
                    merged_features[field] = fingerprint_data[field]
        prepared = {column: merged_features.get(column, 0) for column in self.feature_columns}
        return pd.DataFrame([prepared], columns=self.feature_columns).fillna(0)

    def _rule_risk_boost(self, features: Dict[str, Any]) -> float:
        """Small deterministic guardrail for obvious automation signatures."""
        boost = 0.0
        event_count = float(features.get("event_count", 0) or 0)
        duration = float(features.get("session_duration", 0) or 0)
        key_count = float(features.get("key_count", 0) or 0)
        click_count = float(features.get("click_count", 0) or 0)
        mouse_ratio = float(features.get("mouse_event_ratio", 0) or 0)
        path_efficiency = float(features.get("mouse_path_efficiency", 0) or 0)
        std_iki = float(features.get("std_iki", 0) or 0)
        click_std = float(features.get("click_interval_std", 0) or 0)

        if duration and event_count / duration > 35:
            boost += 0.10
        if event_count < 8 and click_count > 0:
            boost += 0.15
        if key_count >= 8 and std_iki < 8:
            boost += 0.12
        if click_count >= 3 and click_std < 15:
            boost += 0.10
        if click_count > 0 and mouse_ratio < 0.15:
            boost += 0.10
        if path_efficiency > 0.98 and event_count >= 10:
            boost += 0.08
        return min(boost, 0.35)

    def predict_session(self, features: Dict[str, Any],
                       fingerprint_data: Optional[Dict[str, Any]] = None,
                       network_score: float = 0.0,
                       project_id: Optional[str] = None,
                       session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Predict bot risk for a session, combining the ML model's behavioral
        prediction with rule-based fingerprint signals (see RiskEngine).

        Args:
            features: Behavioral features dictionary
            fingerprint_data: Optional fingerprint data (webdriver_flag, user_agent, has_touch, platform)
            network_score: Optional 0-100 network-layer risk (IP/ASN + JA4),
                computed by the route from request headers via
                core/network_signals.evaluate_network. Defaults to 0 so
                callers without request context (offline/batch, tests) and
                deployments with no edge behave identically to before.
            project_id: Optional, scopes replay-detection (core/replay_detection)
                comparisons to sessions on the same project. Omitted -> no
                replay check is made (duplicate_score stays 0).
            session_id: Optional, excludes self-matches when the same session
                is scored more than once (e.g. repeated predict calls as more
                events accumulate).

        Returns:
            Dictionary with the risk_score, action, and component scores.
        """
        feature_df = self._validate_features(features, fingerprint_data)
        features_scaled = self.scaler.transform(feature_df)
        model_probability = float(self.model.predict_proba(features_scaled)[0, 1])
        rule_boost = self._rule_risk_boost(features)
        bot_probability = min(1.0, model_probability + rule_boost)

        raw_anomaly_score = None
        if self.anomaly_forest is not None:
            raw_anomaly_score = float(self.anomaly_forest.decision_function(features_scaled)[0])

        # Replay-trace detection (strategy doc Part D.2): compare this
        # session's scaled feature vector against recent sessions on the same
        # project. A near-duplicate from a *different* session is the one
        # signal available against a faithfully-replayed real human
        # recording, since the recording reproduces identical features every
        # time — see core/replay_detection module docstring.
        from core.replay_detection import record_and_score as replay_record_and_score
        replay_result = replay_record_and_score(
            project_id, session_id, features_scaled[0].tolist()
        )

        fingerprint_data = fingerprint_data or {}
        risk_result = self.risk_engine.evaluate_session(
            ml_probability=bot_probability,
            webdriver_flag=fingerprint_data.get('webdriver_flag', False),
            user_agent=fingerprint_data.get('user_agent', ''),
            has_touch=fingerprint_data.get('has_touch', False),
            platform=fingerprint_data.get('platform', ''),
            decision_threshold=self.decision_threshold,
            raw_anomaly_score=raw_anomaly_score,
            anomaly_score_zero=self.anomaly_score_zero,
            anomaly_score_block=self.anomaly_score_block,
            network_score=network_score,
            duplicate_score=replay_result.duplicate_score,
        )

        overall_risk = risk_result['overall_risk']
        # Distance from the 50-point decision boundary — how far this
        # session sits from the allow/block cutoff, not a statistical
        # confidence interval.
        confidence = round(min(1.0, abs(overall_risk - 50) / 50), 4)

        return {
            "action": risk_result['decision'],
            "risk_score": int(round(overall_risk)),
            "behavior_score": round(risk_result['behavior_score'], 2),
            "fingerprint_score": round(risk_result['fingerprint_score'], 2),
            "confidence": confidence,
        }

    def predict_batch(self, features_list):
        return [self.predict_session(features) for features in features_list]


def predict_session(features: Dict[str, Any], model_path=None, scaler_path=None) -> Dict[str, Any]:
    detector = BotDetector(model_path, scaler_path)
    return detector.predict_session(features)


if __name__ == "__main__":
    bot_features = {
        "avg_mouse_vel": 250.0,
        "std_mouse_vel": 5.0,
        "max_mouse_vel": 260.0,
        "total_distance": 500.0,
        "avg_angle_change": 0.0,
        "click_count": 5,
        "avg_click_interval": 500,
        "avg_iki": 100,
        "std_iki": 0.0,
        "avg_hold": 50,
        "scroll_count": 0,
        "avg_scroll_vel": 0.0,
        "session_duration": 10.0,
        "event_count": 20,
    }
    print(predict_session(bot_features))
