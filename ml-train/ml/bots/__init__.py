"""
Bot package for generating synthetic bot telemetry data.
"""
from .base_bot import BaseBot
from .instant_bot import InstantBot
from .linear_bot import LinearBot
from .timed_bot import TimedBot
from .smart_bot import SmartBot
from .aggressive_bot import AggressiveBot
from .test_human_like_bot import StealthBot
from .adversarial_bot import AdversarialBot
from .multi_page_bot import MultiPageBot

__all__ = [
    'BaseBot',
    'InstantBot',
    'LinearBot',
    'TimedBot',
    'SmartBot',
    'AggressiveBot',
    'StealthBot',
    'AdversarialBot',
    'MultiPageBot',
]
