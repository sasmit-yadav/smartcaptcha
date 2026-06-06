"""
SmartCaptcha Backend — Pydantic schemas for request validation.
"""

from pydantic import BaseModel, Field
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


class TelemetryEvent(BaseModel):
    type: Literal['mm', 'cl', 'kd', 'ku', 'sc', 'fv', 'tc']
    t: int  # Unix timestamp ms
    x: Optional[int] = None
    y: Optional[int] = None
    k: Optional[str] = None
    # Mouse extras
    dist: Optional[float] = None
    ang: Optional[float] = None
    vel: Optional[float] = None  # px/sec (mouse or scroll)
    totalDist: Optional[float] = None  # cumulative mouse distance
    # Click extras
    target: Optional[str] = None
    interval: Optional[int] = None
    double: Optional[bool] = None
    tw: Optional[int] = None  # target element width
    th: Optional[int] = None  # target element height
    # Keyboard extras
    iki: Optional[int] = None  # inter-key interval ms
    hold: Optional[int] = None  # key hold duration ms
    # Scroll extras
    rev: Optional[bool] = None
    pause: Optional[bool] = None
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
    events: List[TelemetryEvent] = Field(..., min_length=1, max_length=200)
    timestamp: int


class SessionStartPayload(BaseModel):
    sessionId: str
    meta: SessionMeta


class SessionEndPayload(BaseModel):
    sessionId: str
    duration: Optional[int] = None
