"""Smart Home Plugin for Hermes Agent.

Provides integration with Tuya Smart IR Gateway for controlling AC, TV, and automation scenes.
"""

from .client import SmartHomeClient
from .tools import SMART_HOME_TOOLS, execute_smart_home_tool

__all__ = ["SmartHomeClient", "SMART_HOME_TOOLS", "execute_smart_home_tool"]
