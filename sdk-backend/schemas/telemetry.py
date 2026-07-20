"""
VeilProof API — Pydantic schemas for telemetry request validation.
Shared contract with the browser SDK (sdk/src/core/transport.ts) and the
demo site's inline collectors.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal


class SessionMeta(BaseModel):
    sessionId: str
    startTime: Optional[int] = None
    userAgent: Optional[str] = None
    platform: Optional[str] = None
    language: Optional[str] = None
    screenWidth: Optional[int] = None
    screenHeight: Optional[int] = None
    colorDepth: Optional[int] = None
    timezone: Optional[str] = None
    deviceType: Optional[str] = None
    hasTouch: Optional[bool] = None
    pageUrl: Optional[str] = None
    pageTitle: Optional[str] = None
    referrer: Optional[str] = None
    # 'volunteer' (2026-07-20): demo-site visits reached via a ?src=volunteer
    # link — auto-labeled 'human' server-side (api/routes/session.py). Never
    # set by any bot script (those hit demo-site's bare URL directly), so
    # this can't collide with bot-labeling regardless of whether a bot
    # script's own label_session('bot') call succeeds.
    source: Optional[Literal['demo', 'client', 'script-tag', 'volunteer']] = None
    # Found 2026-07-18: this field never existed, so Pydantic silently
    # dropped it from every /api/session/start and /api/telemetry payload
    # regardless of sender — meaning sessions.webdriver_flag (and therefore
    # session_features.webdriver_flag, one of the 52 training features) was
    # hardcoded false for the entire training dataset, independent of
    # whether the session was actually automated. The live /api/predict path
    # was unaffected (it reads a separate top-level `webdriver_flag` field,
    # not this schema). See docs/MODEL_IMPROVEMENT_STRATEGY.md.
    webdriverFlag: Optional[bool] = None
    # Honeypot (strategy step 7): a hidden form field invisible to humans but
    # filled by naive bots. When true, this session is a near-certain bot and
    # can be auto-labeled for training — a free, continuous label source.
    honeypotTriggered: Optional[bool] = None


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Literal['mm', 'cl', 'kd', 'ku', 'sc', 'fv', 'tc']
    t: int  # Unix timestamp ms
    # Coordinates may be integers or floats depending on browser/device; accept float
    x: Optional[float] = None
    y: Optional[float] = None
    k: Optional[str] = None
    # Mouse extras
    dist: Optional[float] = None
    ang: Optional[float] = None
    vel: Optional[float] = None  # px/sec (mouse or scroll)
    totalDist: Optional[float] = None  # cumulative mouse distance
    # Click extras
    target: Optional[str] = None
    interval: Optional[int] = None
    is_double: Optional[bool] = Field(None, alias='double')
    tw: Optional[int] = None  # target element width
    th: Optional[int] = None  # target element height
    # Keyboard extras
    iki: Optional[int] = None  # inter-key interval ms
    hold: Optional[int] = None  # key hold duration ms
    # Scroll extras
    scroll_rev: Optional[bool] = Field(None, alias='rev')
    scroll_pause: Optional[bool] = Field(None, alias='pause')
    # Focus extras
    state: Optional[str] = None
    # Touch extras
    action: Optional[str] = None
    force: Optional[float] = None
    duration: Optional[int] = None
    gesture: Optional[str] = None
    swipeDist: Optional[float] = None  # swipe distance px
    swipeVel: Optional[float] = None  # swipe velocity px/sec


class TelemetryPayload(BaseModel):
    sessionId: str = Field(..., min_length=1, max_length=100)
    meta: SessionMeta
    events: List[TelemetryEvent]
    # Top-level payload timestamp in ms (SDK sends Date.now())
    timestamp: Optional[int] = None


class SessionStartPayload(BaseModel):
    sessionId: str
    meta: SessionMeta


class SessionEndPayload(BaseModel):
    sessionId: str
    duration: Optional[int] = None
