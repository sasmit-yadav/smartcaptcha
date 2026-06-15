"""
Bot package for generating synthetic bot telemetry data.
"""
from .base_bot import BaseBot
from .instant_bot import InstantBot
from .linear_bot import LinearBot
from .timed_bot import TimedBot
from .smart_bot import SmartBot

__all__ = ['BaseBot', 'InstantBot', 'LinearBot', 'TimedBot', 'SmartBot']
