"""Risk Engine - combines the ML model's behavioral prediction with rule-based fingerprint signals."""
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class RiskScores:
    """Container for individual risk component scores."""
    behavior_score: float  # 0-100, from the ML model's bot probability
    fingerprint_score: float  # 0-100, from rule-based device/automation signals
    anomaly_score: float  # 0-100, from the human-only IsolationForest (0 if unavailable)
    network_score: float  # 0-100, from IP/ASN + JA4 network signals (0 if unavailable)
    duplicate_score: float  # 0-100, replayed-trace detection (0 if unavailable/no match)
    overall_risk: float  # Combined 0-100 risk score


class RiskEngine:
    """
    Multi-factor risk scoring engine.

    overall_risk = max(behavior_score, fingerprint_score, anomaly_score,
                        average(behavior_score, fingerprint_score, anomaly_score))

    Using max() instead of a fixed weighted average means any signal can
    independently justify a block: a behaviorally-obvious bot is blocked even
    with a clean fingerprint (a fixed 0.4 weight on behavior meant even a
    100%-confident bot call topped out at a risk of 40, permanently below the
    50-point block threshold — the model's own verdict could never win on its
    own). A detected automation fingerprint (e.g. navigator.webdriver) still
    blocks on its own too. The averaged term still raises risk when signals
    are moderately elevated together without any single one crossing 50.

    anomaly_score is optional (0 when no anomaly detector is loaded) — it's
    an orthogonal signal from an IsolationForest trained on human sessions
    only (strategy doc §B.1/§B.7), catching bot styles the supervised model
    was never trained to recognise, at the cost of never blocking on its own
    if the supervised model and fingerprint are both clean and the anomaly
    detector alone doesn't reach the block anchor.

    duplicate_score (strategy doc Part D.2) is a different kind of signal:
    it doesn't ask "does this session look human," it asks "have I already
    seen a behaviorally near-identical session on this project." A replayed
    recording of a real human reproduces the same features every time it's
    replayed — no shape-of-motion feature can catch that, since the motion
    genuinely was human once. Reused/near-duplicate feature vectors across
    different sessions are the only signal available without a challenge
    tier. 0 when no prior session was close enough to compare against.
    """

    def calculate_behavior_score(self, ml_probability: float,
                                  decision_threshold: float = 0.5) -> float:
        """
        ML model's calibrated bot probability (0-1), scaled to 0-100 so that
        `decision_threshold` maps exactly to the 50-point block boundary.

        This is the fix for the train/serve threshold skew (strategy doc
        Finding 2): the model's metadata records the threshold it was
        actually tuned at (e.g. 0.24 on calibrated probabilities), but a
        flat `probability * 100` scale silently reverts to blocking only at
        probability >= 0.50 regardless of what the model was tuned for.
        Piecewise-linear remap:
          - probability in [0, threshold]   -> score in [0, 50]
          - probability in [threshold, 1]   -> score in [50, 100]
        Monotonic, and `probability == decision_threshold` always scores
        exactly 50 (the actual block/allow boundary), whatever the
        threshold is.
        """
        threshold = min(max(decision_threshold, 1e-6), 1 - 1e-6)
        if ml_probability <= threshold:
            return (ml_probability / threshold) * 50.0
        return 50.0 + ((ml_probability - threshold) / (1 - threshold)) * 50.0

    def calculate_fingerprint_score(self,
                                     webdriver_flag: bool,
                                     user_agent: str,
                                     has_touch: bool,
                                     platform: str,
                                     automation_score: float = 0.0,
                                     automation_signals: Optional[list] = None) -> float:
        """
        Rule-based risk score (0-100) from browser/device signals.
        Not model-derived — a fixed set of known automation tells.

        `automation_score` comes from client-side stealth probes (spoofed
        navigator.webdriver getter, Playwright globals, CDP Runtime.enable
        leak). Real Chrome never needs these probes to fire; a stealth kit
        that hides webdriver almost always trips at least one.

        CDP-only signals are inconclusive industry-wide (Chrome 2025+ and
        CDP-minimal drivers often never trip the classic Runtime.enable
        leak). A CDP hit alone is capped below the block threshold; silence
        is never treated as proof of humanity.

        `coherence_*` signals (UA↔engine↔WebGL↔platform) are medium-weight
        anti-detect tells — not capped like CDP.
        """
        risk_score = 0.0
        effective_automation = self._effective_automation_score(
            automation_score, automation_signals
        )

        # WebDriver flag is the strongest indicator - decisive on its own.
        if webdriver_flag:
            risk_score += 100.0

        # Client stealth / coherence probes — treat high *decisive* scores as block-worthy.
        if effective_automation >= 50:
            risk_score = max(risk_score, min(100.0, float(effective_automation)))
        elif effective_automation > 0:
            # Soft / inconclusive contribution (e.g. CDP-only or mild coherence).
            risk_score = max(risk_score, float(effective_automation))

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

        # Server-side UA ↔ platform coherence (forgeable but still useful).
        plat = (platform or '').lower()
        if plat:
            if 'win' in plat and ('mac os x' in ua_lower or 'macintosh' in ua_lower):
                risk_score = max(risk_score, 55.0)
            if 'mac' in plat and 'windows nt' in ua_lower:
                risk_score = max(risk_score, 55.0)

        return min(risk_score, 100.0)

    @staticmethod
    def _effective_automation_score(automation_score: float,
                                    automation_signals: Optional[list]) -> float:
        """Cap inconclusive CDP-only evidence below the block threshold.

        Coherence and classic stealth signals remain uncapped (client score).
        """
        score = float(automation_score or 0)
        if score <= 0:
            return 0.0
        signals = [str(s) for s in (automation_signals or [])]
        if not signals:
            return score
        decisive = [
            s for s in signals
            if not s.startswith('cdp_') and s != 'cdp_runtime_enable'
        ]
        cdp_only = any(s.startswith('cdp_') or s == 'cdp_runtime_enable' for s in signals) and not decisive
        if cdp_only:
            # Industry: CDP leak alone is soft evidence (≤35 < block@50).
            return min(score, 35.0)
        return score

    def calculate_anomaly_score(self, raw_anomaly_score: Optional[float],
                                 score_zero: Optional[float],
                                 score_block: Optional[float]) -> float:
        """
        Map an IsolationForest decision_function() output to 0-100.

        `score_zero` (median human score) -> 0 points.
        `score_block` (the calibration anchor picked at train time, more
        anomalous than every training human) -> 50 points (the block
        boundary). Scores below `score_block` extrapolate linearly past 100
        (clamped). Returns 0.0 if any anchor is missing (no anomaly detector
        loaded) — the axis simply contributes nothing rather than erroring.
        """
        if raw_anomaly_score is None or score_zero is None or score_block is None:
            return 0.0
        span = score_zero - score_block
        if span <= 0:
            return 0.0
        points = (score_zero - raw_anomaly_score) / span * 50.0
        return float(min(max(points, 0.0), 100.0))

    def calculate_overall_risk(self, behavior_score: float, fingerprint_score: float,
                                anomaly_score: float = 0.0, network_score: float = 0.0,
                                duplicate_score: float = 0.0) -> RiskScores:
        # The averaged term uses only the axes that actually carry a signal —
        # averaging in a 0 from an unavailable axis (no anomaly model, no edge
        # for network, no prior session close enough to compare) would
        # artificially depress it and could mask a session where several live
        # axes are moderately elevated together. max() over the individual
        # axes is unaffected: any axis can still block on its own.
        active = [s for s in (behavior_score, fingerprint_score, anomaly_score,
                              network_score, duplicate_score) if s > 0]
        combined_average = sum(active) / len(active) if active else 0.0
        overall_risk = max(behavior_score, fingerprint_score, anomaly_score,
                           network_score, duplicate_score, combined_average)
        return RiskScores(
            behavior_score=behavior_score,
            fingerprint_score=fingerprint_score,
            anomaly_score=anomaly_score,
            network_score=network_score,
            duplicate_score=duplicate_score,
            overall_risk=overall_risk,
        )

    def evaluate_session(self,
                          ml_probability: float,
                          webdriver_flag: bool = False,
                          user_agent: str = '',
                          has_touch: bool = False,
                          platform: str = '',
                          decision_threshold: float = 0.5,
                          raw_anomaly_score: Optional[float] = None,
                          anomaly_score_zero: Optional[float] = None,
                          anomaly_score_block: Optional[float] = None,
                          network_score: float = 0.0,
                          duplicate_score: float = 0.0,
                          automation_score: float = 0.0,
                          automation_signals: Optional[list] = None) -> Dict:
        """Full risk evaluation for a session: component scores + final decision.

        `network_score` (0-100) comes from core/network_signals.evaluate_network
        (IP/ASN reputation, non-browser UA, and JA4 when an edge forwards it).
        It defaults to 0 so every existing caller and any deployment without an
        edge behaves exactly as before — the axis only ever raises risk.

        `duplicate_score` (0-100) comes from core/replay_detection —
        behavioral feature vector reuse across sessions on the same project
        (strategy doc Part D.2). Defaults to 0 so callers without it behave
        exactly as before.

        `automation_score` / `automation_signals` come from client stealth
        probes. CDP-only signal sets are capped below the block threshold.
        """
        behavior_score = self.calculate_behavior_score(ml_probability, decision_threshold)
        fingerprint_score = self.calculate_fingerprint_score(
            webdriver_flag, user_agent, has_touch, platform,
            automation_score, automation_signals,
        )
        anomaly_score = self.calculate_anomaly_score(
            raw_anomaly_score, anomaly_score_zero, anomaly_score_block
        )
        # Stealth gap fix: when fingerprint is clean, amplify the anomaly
        # axis so IsolationForest can still block novel bot styles the
        # supervised model was never trained on (Playwright Bezier bots).
        if fingerprint_score < 10 and anomaly_score > 0:
            anomaly_score = min(100.0, anomaly_score * 1.75)

        risk_scores = self.calculate_overall_risk(
            behavior_score, fingerprint_score, anomaly_score, network_score, duplicate_score
        )
        decision = self._make_decision(risk_scores.overall_risk)

        return {
            'behavior_score': behavior_score,
            'fingerprint_score': fingerprint_score,
            'anomaly_score': anomaly_score,
            'network_score': network_score,
            'duplicate_score': duplicate_score,
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
    print(f"Test 1 (Clear human, default threshold 0.5): {result1}")

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
    print(f"Test 3 (Behavior-only block, clean fingerprint, default threshold): {result3}")

    # The bug this file fixes: with a calibrated decision_threshold of 0.24
    # (typical for this dataset), a probability of 0.34 — the exact score
    # that bypassed detection in the 2026-07-16 adversarial test — must now
    # score above 50 instead of the old flat `0.34*100=34`.
    result4 = engine.evaluate_session(
        ml_probability=0.34,
        webdriver_flag=False,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        has_touch=False,
        platform='Win32',
        decision_threshold=0.24,
    )
    print(f"Test 4 (Stealth bot, P=0.34, calibrated threshold 0.24): {result4}")
    assert result4['decision'] == 'block', "threshold-aware scaling should now block this session"
