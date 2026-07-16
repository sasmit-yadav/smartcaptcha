"""Risk Engine - combines the ML model's behavioral prediction with rule-based fingerprint signals."""
from typing import Dict
from dataclasses import dataclass


@dataclass
class RiskScores:
    """Container for individual risk component scores."""
    behavior_score: float  # 0-100, from the ML model's bot probability
    fingerprint_score: float  # 0-100, from rule-based device/automation signals
    overall_risk: float  # Combined 0-100 risk score


class RiskEngine:
    """
    Multi-factor risk scoring engine.

    overall_risk = max(behavior_score, fingerprint_score, average(behavior_score, fingerprint_score))

    Using max() instead of a fixed weighted average means either signal can
    independently justify a block: a behaviorally-obvious bot is blocked even
    with a clean fingerprint (a fixed 0.4 weight on behavior meant even a
    100%-confident bot call topped out at a risk of 40, permanently below the
    50-point block threshold — the model's own verdict could never win on its
    own). A detected automation fingerprint (e.g. navigator.webdriver) still
    blocks on its own too. The averaged term still raises risk when both
    signals are moderately elevated together.
    """

    def calculate_behavior_score(self, ml_probability: float) -> float:
        """ML model's bot probability (0-1), scaled to 0-100."""
        return ml_probability * 100

    def calculate_fingerprint_score(self,
                                     webdriver_flag: bool,
                                     user_agent: str,
                                     has_touch: bool,
                                     platform: str) -> float:
        """
        Rule-based risk score (0-100) from browser/device signals.
        Not model-derived — a fixed set of known automation tells.
        """
        risk_score = 0.0

        # WebDriver flag is the strongest indicator - decisive on its own.
        if webdriver_flag:
            risk_score += 100.0

        # Known automation tools in the user agent.
        suspicious_ua_patterns = ('selenium', 'webdriver', 'headless', 'phantom', 'chromeless', 'automation')
        ua_lower = (user_agent or '').lower()
        if any(pattern in ua_lower for pattern in suspicious_ua_patterns):
            risk_score += 30.0

        # Claims to be mobile but has no touch support.
        if not has_touch and 'mobile' in ua_lower:
            risk_score += 10.0

        # Headless Linux is a common bot-farm signature.
        if platform and 'linux' in platform.lower() and 'headless' in ua_lower:
            risk_score += 15.0

        return min(risk_score, 100.0)

    def calculate_overall_risk(self, behavior_score: float, fingerprint_score: float) -> RiskScores:
        combined_average = (behavior_score + fingerprint_score) / 2
        overall_risk = max(behavior_score, fingerprint_score, combined_average)
        return RiskScores(
            behavior_score=behavior_score,
            fingerprint_score=fingerprint_score,
            overall_risk=overall_risk,
        )

    def evaluate_session(self,
                          ml_probability: float,
                          webdriver_flag: bool = False,
                          user_agent: str = '',
                          has_touch: bool = False,
                          platform: str = '') -> Dict:
        """Full risk evaluation for a session: component scores + final decision."""
        behavior_score = self.calculate_behavior_score(ml_probability)
        fingerprint_score = self.calculate_fingerprint_score(
            webdriver_flag, user_agent, has_touch, platform
        )
        risk_scores = self.calculate_overall_risk(behavior_score, fingerprint_score)
        decision = self._make_decision(risk_scores.overall_risk)

        return {
            'behavior_score': behavior_score,
            'fingerprint_score': fingerprint_score,
            'overall_risk': risk_scores.overall_risk,
            'decision': decision,
        }

    def _make_decision(self, overall_risk: float) -> str:
        """
        Binary decision: overall_risk >= 50 -> block, else allow.
        (No 'challenge' tier — there is no challenge UI/flow implemented
        anywhere in the product, so the API never returns one.)
        """
        return 'block' if overall_risk >= 50 else 'allow'


def create_risk_engine() -> RiskEngine:
    """Factory function to create a RiskEngine instance."""
    return RiskEngine()


# Example usage and testing
if __name__ == "__main__":
    engine = create_risk_engine()

    result1 = engine.evaluate_session(
        ml_probability=0.1,
        webdriver_flag=False,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        has_touch=False,
        platform='Win32'
    )
    print(f"Test 1 (Clear human): {result1}")

    result2 = engine.evaluate_session(
        ml_probability=0.9,
        webdriver_flag=True,
        user_agent='Mozilla/5.0 (windows) selenium webdriver',
        has_touch=False,
        platform='Linux x86_64'
    )
    print(f"Test 2 (Suspicious bot): {result2}")

    result3 = engine.evaluate_session(
        ml_probability=0.55,
        webdriver_flag=False,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        has_touch=False,
        platform='Win32'
    )
    print(f"Test 3 (Behavior-only block, clean fingerprint): {result3}")
