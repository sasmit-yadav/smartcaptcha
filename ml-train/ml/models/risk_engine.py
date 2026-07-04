"""Risk Engine - Multi-factor risk scoring combining Behavior, Fingerprint, and Challenge scores."""
import json
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RiskScores:
    """Container for individual risk component scores."""
    behavior_score: float  # 0-100 from ML model
    fingerprint_score: float  # 0-100 from browser signals
    challenge_score: float  # 0-100 from interactive challenges
    overall_risk: float  # Weighted combination


class RiskEngine:
    """
    Multi-factor risk scoring engine.
    
    Risk = 0.5 * Behavior + 0.3 * Fingerprint + 0.2 * Challenge
    
    Components:
    - Behavior: ML model prediction on behavioral features
    - Fingerprint: Browser signals (webdriver, plugins, automation artifacts)
    - Challenge: Interactive challenges (only if suspicious)
    """
    
    def __init__(self):
        self.weights = {
            'behavior': 0.4,
            'fingerprint': 0.6,
            'challenge': 0.0
        }
    
    def calculate_behavior_score(self, ml_probability: float) -> float:
        """
        Convert ML model probability to behavior score (0-100).
        
        Args:
            ml_probability: Bot probability from ML model (0-1)
        
        Returns:
            Behavior score (0-100)
        """
        return ml_probability * 100
    
    def calculate_fingerprint_score(self, 
                                     webdriver_flag: bool,
                                     user_agent: str,
                                     has_touch: bool,
                                     platform: str) -> float:
        """
        Calculate fingerprint risk score from browser signals.
        
        Args:
            webdriver_flag: navigator.webdriver flag
            user_agent: Browser user agent string
            has_touch: Touch support detected
            platform: Operating system platform
        
        Returns:
            Fingerprint score (0-100)
        """
        risk_score = 0.0
        
        # WebDriver flag is the strongest indicator - should cause immediate blocking
        if webdriver_flag:
            risk_score += 100.0  # Maximum risk for webdriver flag
        
        # Check for known automation tools in user agent
        suspicious_ua_patterns = [
            'selenium',
            'webdriver',
            'headless',
            'phantom',
            'chromeless',
            'automation'
        ]
        ua_lower = user_agent.lower() if user_agent else ''
        for pattern in suspicious_ua_patterns:
            if pattern in ua_lower:
                risk_score += 30.0
                break
        
        # Missing expected capabilities
        if not has_touch and 'mobile' in ua_lower:
            risk_score += 10.0
        
        # Suspicious platform combinations
        if platform and 'linux' in platform.lower() and 'headless' in ua_lower:
            risk_score += 15.0
        
        return min(risk_score, 100.0)
    
    def calculate_challenge_score(self, 
                                  challenge_completed: bool,
                                  challenge_time_ms: Optional[int] = None,
                                  challenge_accuracy: Optional[float] = None) -> float:
        """
        Calculate challenge score from interactive challenge results.
        
        Args:
            challenge_completed: Whether user completed the challenge
            challenge_time_ms: Time taken to complete challenge (optional)
            challenge_accuracy: Accuracy of challenge response (optional)
        
        Returns:
            Challenge score (0-100)
        """
        if not challenge_completed:
            # If challenge was not completed, assume high risk
            return 80.0
        
        risk_score = 0.0
        
        # Time-based analysis (bots often complete too fast or too consistent)
        if challenge_time_ms:
            if challenge_time_ms < 500:  # Suspiciously fast
                risk_score += 40.0
            elif challenge_time_ms < 1000:  # Very fast
                risk_score += 20.0
            elif challenge_time_ms > 10000:  # Suspiciously slow
                risk_score += 10.0
        
        # Accuracy analysis
        if challenge_accuracy is not None:
            if challenge_accuracy > 0.95:  # Too perfect
                risk_score += 30.0
            elif challenge_accuracy < 0.5:  # Failed
                risk_score += 50.0
        
        return min(risk_score, 100.0)
    
    def calculate_overall_risk(self,
                              behavior_score: float,
                              fingerprint_score: float,
                              challenge_score: float = 0.0) -> RiskScores:
        """
        Calculate overall risk score using weighted combination.
        
        Args:
            behavior_score: Behavior score (0-100)
            fingerprint_score: Fingerprint score (0-100)
            challenge_score: Challenge score (0-100, default 0 if no challenge)
        
        Returns:
            RiskScores object with all component scores and overall risk
        """
        overall_risk = (
            self.weights['behavior'] * behavior_score +
            self.weights['fingerprint'] * fingerprint_score +
            self.weights['challenge'] * challenge_score
        )
        
        return RiskScores(
            behavior_score=behavior_score,
            fingerprint_score=fingerprint_score,
            challenge_score=challenge_score,
            overall_risk=overall_risk
        )
    
    def evaluate_session(self,
                       ml_probability: float,
                       webdriver_flag: bool = False,
                       user_agent: str = '',
                       has_touch: bool = False,
                       platform: str = '',
                       challenge_completed: bool = False,
                       challenge_time_ms: Optional[int] = None,
                       challenge_accuracy: Optional[float] = None) -> Dict:
        """
        Full risk evaluation for a session.
        
        Args:
            ml_probability: Bot probability from ML model (0-1)
            webdriver_flag: navigator.webdriver flag
            user_agent: Browser user agent string
            has_touch: Touch support detected
            platform: Operating system platform
            challenge_completed: Whether user completed challenge
            challenge_time_ms: Time to complete challenge
            challenge_accuracy: Accuracy of challenge response
        
        Returns:
            Dictionary with all risk scores and decision
        """
        # Calculate individual component scores
        behavior_score = self.calculate_behavior_score(ml_probability)
        fingerprint_score = self.calculate_fingerprint_score(
            webdriver_flag, user_agent, has_touch, platform
        )
        challenge_score = self.calculate_challenge_score(
            challenge_completed, challenge_time_ms, challenge_accuracy
        ) if challenge_completed else 0.0
        
        # Calculate overall risk
        risk_scores = self.calculate_overall_risk(
            behavior_score, fingerprint_score, challenge_score
        )
        
        # Make decision based on tiered thresholds
        decision = self._make_decision(risk_scores.overall_risk)
        
        return {
            'behavior_score': behavior_score,
            'fingerprint_score': fingerprint_score,
            'challenge_score': challenge_score,
            'overall_risk': risk_scores.overall_risk,
            'decision': decision,
            'weights': self.weights
        }
    
    def _make_decision(self, overall_risk: float) -> str:
        """
        Make decision based on overall risk score.
        
        Binary classification (no challenges):
        - Score < 50: allow (human)
        - Score >= 50: block (bot)
        
        Args:
            overall_risk: Overall risk score (0-100)
        
        Returns:
            Decision: 'allow' or 'block'
        """
        if overall_risk < 50:
            return 'allow'
        else:
            return 'block'


def create_risk_engine() -> RiskEngine:
    """Factory function to create a RiskEngine instance."""
    return RiskEngine()


# Example usage and testing
if __name__ == "__main__":
    engine = create_risk_engine()
    
    # Test case 1: Clear human
    result1 = engine.evaluate_session(
        ml_probability=0.1,
        webdriver_flag=False,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        has_touch=False,
        platform='Win32'
    )
    print(f"Test 1 (Clear human): {result1}")
    
    # Test case 2: Suspicious bot
    result2 = engine.evaluate_session(
        ml_probability=0.9,
        webdriver_flag=True,
        user_agent='Mozilla/5.0 (windows) selenium webdriver',
        has_touch=False,
        platform='Linux x86_64'
    )
    print(f"Test 2 (Suspicious bot): {result2}")
    
    # Test case 3: Needs challenge
    result3 = engine.evaluate_session(
        ml_probability=0.5,
        webdriver_flag=False,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        has_touch=False,
        platform='Win32'
    )
    print(f"Test 3 (Needs challenge): {result3}")
