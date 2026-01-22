"""Strategy framework and implementations."""

import importlib

from app.strategies.announcement_gap_strategy import (
    AnnouncementGapBreakoutStrategy,
    check_announcement_today,
    register_announcement,
)
from app.strategies.announcement_gap_strategy import (
    AnnouncementGapBreakoutStrategy as AnnouncementGapStrategy,
)
from app.strategies.example_strategy import (
    DEFAULT_PARAMETERS,
    STRATEGY_NAME,
    VT_SYMBOL,
    ASXMomentumStrategy,
)

__all__ = [
    "ASXMomentumStrategy",
    "AnnouncementGapStrategy",
    "AnnouncementGapBreakoutStrategy",
    "DEFAULT_PARAMETERS",
    "STRATEGY_NAME",
    "VT_SYMBOL",
    "get_strategy",
    "register_announcement",
    "check_announcement_today",
]


def get_strategy(strategy_name: str):
    """Dynamically import and return a strategy module by name.

    Args:
        strategy_name: Name of the strategy (e.g., "asx_momentum")

    Returns:
        Strategy module

    Raises:
        ImportError: If strategy module cannot be found
    """
    try:
        module = importlib.import_module(f"app.strategies.{strategy_name}")
        return module
    except ImportError as e:
        raise ImportError(f"Strategy '{strategy_name}' not found: {e}") from None
