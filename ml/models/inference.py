"""
Inference module for bot detection predictions.
Provides predict_session function with decision thresholds.
"""
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[2]

# Decision thresholds (binary: accept or reject)
THRESHOLD = 0.50  # < 0.50 → accept (human), >= 0.50 → reject (bot)


class BotDetector:
    """Bot detection model for inference."""
    
    def __init__(self, model_path=None, scaler_path=None):
        """
        Initialize bot detector with trained model and scaler.
        
        Args:
            model_path: Path to trained model pickle file
            scaler_path: Path to fitted scaler pickle file
        """
        if model_path is None:
            # Use latest model by default
            artifacts_dir = ROOT / "ml" / "models" / "artifacts"
            model_files = list(artifacts_dir.glob("*random_forest*.pkl")) + list(artifacts_dir.glob("*xgboost*.pkl"))
            if model_files:
                model_path = max(model_files, key=lambda x: x.stat().st_mtime)
                print(f"Using latest model: {model_path}")
            else:
                raise FileNotFoundError("No trained model found. Please train a model first.")
        
        if scaler_path is None:
            # Use latest scaler by default
            artifacts_dir = ROOT / "ml" / "models" / "artifacts"
            scaler_files = list(artifacts_dir.glob("scaler_*.pkl"))
            if scaler_files:
                scaler_path = max(scaler_files, key=lambda x: x.stat().st_mtime)
                print(f"Using latest scaler: {scaler_path}")
            else:
                raise FileNotFoundError("No scaler found. Please train a model first.")
        
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        
        # Feature columns (must match training)
        self.feature_columns = [
            'avg_mouse_vel',
            'std_mouse_vel',
            'max_mouse_vel',
            'total_distance',
            'avg_angle_change',
            'click_count',
            'avg_click_interval',
            'avg_iki',
            'std_iki',
            'avg_hold',
            'scroll_count',
            'avg_scroll_vel',
            'session_duration',
            'event_count'
        ]
        
        print(f"BotDetector initialized with model: {model_path}")
    
    def _validate_features(self, features: Dict[str, Any]) -> pd.DataFrame:
        """
        Validate and prepare features for prediction.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            DataFrame with features in correct order
        """
        # Check for missing features
        missing = set(self.feature_columns) - set(features.keys())
        if missing:
            raise ValueError(f"Missing required features: {missing}")
        
        # Create DataFrame with correct column order
        feature_df = pd.DataFrame([features], columns=self.feature_columns)
        
        # Handle NaN values
        feature_df = feature_df.fillna(0)
        
        return feature_df
    
    def predict_session(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict if a session is bot or human.
        
        Args:
            features: Dictionary of feature values (14 features required)
            
        Returns:
            Dictionary with:
                - bot_probability: Probability of being bot (0-1)
                - risk_score: Risk score (0-100)
                - action: 'allow', 'challenge', or 'block'
                - confidence: Confidence in prediction
        """
        try:
            # Validate and prepare features
            feature_df = self._validate_features(features)
            
            # Scale features
            features_scaled = self.scaler.transform(feature_df)
            
            # Get prediction probability
            bot_probability = float(self.model.predict_proba(features_scaled)[0, 1])
            
            # Calculate risk score (0-100)
            risk_score = int(bot_probability * 100)
            
            # Determine action based on binary threshold
            if bot_probability < THRESHOLD:
                action = 'accept'  # Human
            else:
                action = 'reject'  # Bot
            
            # Calculate confidence (distance from threshold)
            if action == 'accept':
                confidence = 1 - (bot_probability / THRESHOLD)
            else:  # reject
                confidence = (bot_probability - THRESHOLD) / (1 - THRESHOLD)
            
            confidence = max(0, min(1, confidence))  # Clamp to [0, 1]
            
            return {
                'bot_probability': round(bot_probability, 4),
                'risk_score': risk_score,
                'action': action,
                'confidence': round(confidence, 4)
            }
            
        except Exception as e:
            print(f"Error during prediction: {e}")
            raise
    
    def predict_batch(self, features_list: list) -> list:
        """
        Predict multiple sessions at once.
        
        Args:
            features_list: List of feature dictionaries
            
        Returns:
            List of prediction dictionaries
        """
        results = []
        for features in features_list:
            result = self.predict_session(features)
            results.append(result)
        return results


def predict_session(features: Dict[str, Any], model_path=None, scaler_path=None) -> Dict[str, Any]:
    """
    Convenience function for single session prediction.
    
    Args:
        features: Dictionary of feature values
        model_path: Path to model (optional, uses latest if not provided)
        scaler_path: Path to scaler (optional, uses latest if not provided)
        
    Returns:
        Prediction dictionary with bot_probability, risk_score, action, confidence
    """
    detector = BotDetector(model_path, scaler_path)
    return detector.predict_session(features)


# Example usage
if __name__ == "__main__":
    # Example features (typical bot session)
    bot_features = {
        'avg_mouse_vel': 250.0,
        'std_mouse_vel': 5.0,  # Very low variance (linear bot)
        'max_mouse_vel': 260.0,
        'total_distance': 500.0,
        'avg_angle_change': 0.0,  # Perfectly straight lines
        'click_count': 5,
        'avg_click_interval': 500,  # Exact 500ms intervals
        'avg_iki': 100,  # Exact 100ms inter-key intervals
        'std_iki': 0.0,  # No variance
        'avg_hold': 50,
        'scroll_count': 0,
        'avg_scroll_vel': 0.0,
        'session_duration': 10.0,
        'event_count': 20
    }
    
    # Example features (typical human session)
    human_features = {
        'avg_mouse_vel': 180.0,
        'std_mouse_vel': 85.0,  # High variance
        'max_mouse_vel': 350.0,
        'total_distance': 1200.0,
        'avg_angle_change': 45.0,  # Curved movements
        'click_count': 15,
        'avg_click_interval': 850,  # Variable timing
        'avg_iki': 150,  # Variable inter-key intervals
        'std_iki': 80.0,  # High variance
        'avg_hold': 120,
        'scroll_count': 10,
        'avg_scroll_vel': 450.0,
        'session_duration': 45.0,
        'event_count': 150
    }
    
    print("Example predictions (run after training):")
    print("\nBot-like session:")
    print(predict_session(bot_features))
    
    print("\nHuman-like session:")
    print(predict_session(human_features))
