"""
VeilProof API — Prediction route.
POST /api/predict — takes behavioral features + fingerprint from the SDK and
returns a bot-detection decision. Requires a valid customer API key.
"""

import os
import uuid
import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks, Depends

from models.inference import BotDetector
from api_key_manager import APIKeyManager
from core.verification_token import issue_token
from core.rate_limit import rate_limit, enforce

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


def _check_allowed_domain(origin: str, allowed_domains) -> bool:
    """
    Check a request Origin against a project's allowed_domains list.
    A leaked API key should only work from the domains its owner configured
    — without this, allowed_domains was stored but never enforced.
    """
    if not allowed_domains or "*" in allowed_domains:
        return True
    if not origin:
        # No Origin header (server-to-server / non-browser caller) — can't
        # check, so don't block a legitimate backend integration.
        return True

    host = urlparse(origin).hostname or origin
    host = host.lower()
    return any(host == d.lower() or host.endswith(f".{d.lower()}") for d in allowed_domains)

# Demo mode for testing (set DEMO_MODE=1 to use simple keys)
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"
DEMO_API_KEYS = ["demo-key", "sc_live_xxxxxxxxxxxxx"]

_detector = None


def get_detector() -> BotDetector:
    """Lazily create the model singleton (warmed at startup from main.py)."""
    global _detector
    if _detector is None:
        _detector = BotDetector()
    return _detector


def verify_key_or_demo(api_key: str):
    """Verify an API key, honouring DEMO_MODE. Returns key info or None."""
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
    return APIKeyManager.verify_api_key(api_key)


@router.post("/api/predict", dependencies=[Depends(rate_limit("predict_ip", limit=300, window_seconds=60))])
async def predict(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str = Header(None),
    x_api_key: str = Header(None, alias="X-API-Key"),
    origin: str = Header(None, alias="Origin")
):
    """
    Prediction API for SDK customers
    Takes behavioral features and returns bot detection decision
    """
    # Never log full credential headers — key prefix only
    logger.debug("Auth headers present: authorization=%s, x_api_key=%s", bool(authorization), bool(x_api_key))

    # Extract API key from X-API-Key header (SDK sends it this way)
    api_key = x_api_key

    # Fallback to Authorization header
    if not api_key and authorization and authorization.startswith("Bearer "):
        api_key = authorization[7:]

    logger.debug("Extracted API key: %s...", api_key[:12] if api_key else None)

    # Verify API key
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    key_info = verify_key_or_demo(api_key)
    if not key_info:
        logger.debug("API key verification failed for: %s...", api_key[:12])
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")

    # Secret keys are for server-side /api/siteverify calls only — never
    # accepted here, where a leaked-in-the-browser key would be catastrophic.
    if key_info.get('key_type') == 'secret':
        raise HTTPException(status_code=403, detail="Secret keys cannot be used with /api/predict — use your site key")

    enforce("predict_key", key_info['key_id'], limit=120, window_seconds=60)

    logger.debug("API key verified successfully for project: %s", key_info['project_name'])

    if not _check_allowed_domain(origin, key_info.get('allowed_domains')):
        logger.debug("Origin '%s' not in allowed_domains for project %s", origin, key_info['project_name'])
        raise HTTPException(status_code=403, detail="Origin not allowed for this API key")

    try:
        # Parse request body
        body = await request.json()

        logger.debug("Received body keys: %s", list(body.keys()))

        # Honeypot (strategy step 7): a hidden field the customer's form marks
        # filled is a near-certain bot — decisive on its own, independent of
        # behaviour/fingerprint. Kept out of `features` (not a model input).
        honeypot_triggered = bool(body.get('honeypot_triggered', False))

        # Extract features and fingerprint data
        features = {k: v for k, v in body.items() if k not in ['webdriver_flag', 'user_agent', 'has_touch', 'platform', 'sdkVersion', 'sessionId', 'honeypot_triggered']}
        fingerprint = {
            'webdriver_flag': body.get('webdriver_flag', False),
            'user_agent': body.get('user_agent', ''),
            'has_touch': body.get('has_touch', False),
            'platform': body.get('platform', '')
        }

        # Network-layer signals (strategy step 2): IP/ASN reputation +
        # non-browser UA now, JA4 the moment an edge forwards it. Header keys
        # are lower-cased for the evaluator; the direct socket peer is the
        # fallback client IP when no proxy/edge sets X-Forwarded-For.
        from core.network_signals import evaluate_network
        from core.velocity import record_and_score
        lower_headers = {k.lower(): v for k, v in request.headers.items()}
        direct_ip = request.client.host if request.client else None
        net = evaluate_network(lower_headers, direct_ip=direct_ip)

        # Cross-session velocity (strategy step 6 / §B.5): rolling counts keyed
        # by IP, /24, ASN, and a stable client fingerprint hash, plus UA
        # rotation and inter-arrival regularity. Same un-forgeable network axis
        # as the per-request signals above, so fuse by max — any can raise it.
        import hashlib
        fp_basis = "|".join(str(fingerprint.get(k, '')) for k in
                            ('user_agent', 'platform', 'has_touch'))
        fingerprint_hash = hashlib.sha256(fp_basis.encode()).hexdigest()[:16] if fp_basis.strip('|') else None
        vel = record_and_score(
            net.client_ip,
            user_agent=fingerprint.get('user_agent', ''),
            asn=net.asn,
            fingerprint_hash=fingerprint_hash,
        )
        network_score = max(net.network_score, vel.velocity_score)
        # A tripped honeypot is decisive — push the (un-forgeable) network axis
        # to 100 so the session blocks regardless of how human the behaviour and
        # fingerprint look.
        if honeypot_triggered:
            network_score = 100.0

        # Log session telemetry asynchronously
        session_id = body.get('sessionId')
        if not session_id:
            session_id = str(uuid.uuid4())

        # Get prediction from model
        result = get_detector().predict_session(
            features, fingerprint_data=fingerprint, network_score=network_score,
            project_id=key_info['project_id'], session_id=session_id,
        )

        from core.database import insert_session_prediction
        background_tasks.add_task(
            insert_session_prediction,
            session_id=session_id,
            project_id=key_info['project_id'],
            device_type=body.get('deviceType', 'desktop' if not body.get('has_touch') else 'mobile'),
            user_agent=fingerprint.get('user_agent', ''),
            risk_score=float(result.get('risk_score', 0)),
            webdriver_flag=fingerprint.get('webdriver_flag', False),
            label=result.get('action', 'block'),
            api_key_id=key_info['key_id'],
        )
        background_tasks.add_task(APIKeyManager.update_last_used, key_info['key_id'])

        # Issue a signed, single-use verify token so the customer's *server*
        # can confirm this decision happened via /api/siteverify — the
        # browser response alone is not a trust boundary (a bot can ignore
        # or fake it).
        result['verification_token'] = issue_token(
            project_id=key_info['project_id'],
            session_id=session_id,
            risk_score=float(result.get('risk_score', 0)),
            action=result.get('action', 'block'),
            hostname=(urlparse(origin).hostname if origin else None),
            site_key_id=key_info['key_id'],
        )

        logger.debug("Prediction result: %s", result)

        return result

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")
