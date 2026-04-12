"""Event handlers for EventBus."""

from typing import TYPE_CHECKING, Protocol

from app.events.handlers.announcement_gap_handler import AnnouncementGapHandler
from app.events.handlers.discord_handler import DiscordHandler
from app.events.handlers.ibkr_scanner_handler import IBKRScannerHandler
from app.events.handlers.import_handler import ImportHandler

if TYPE_CHECKING:
    pass


class EventHandler(Protocol):
    """Protocol for event handlers."""

    async def initialize(self, event_bus) -> None:
        """Initialize handler with event bus."""
        ...


__all__ = [
    "AnnouncementGapHandler",
    "DiscordHandler",
    "IBKRScannerHandler",
    "ImportHandler",
    "EventHandler",
]
