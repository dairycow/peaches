"""Event handlers for EventBus."""

from typing import TYPE_CHECKING, Protocol

from app.events.handlers.discord_handler import DiscordHandler
from app.events.handlers.import_handler import ImportHandler
from app.events.handlers.strategy_handler import StrategyHandler

if TYPE_CHECKING:
    pass


class EventHandler(Protocol):
    """Protocol for event handlers."""

    async def initialize(self, event_bus) -> None:
        """Initialize handler with event bus."""
        ...


__all__ = [
    "DiscordHandler",
    "ImportHandler",
    "StrategyHandler",
    "EventHandler",
]
