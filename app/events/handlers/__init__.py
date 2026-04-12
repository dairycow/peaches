"""Event handlers for EventBus."""

from typing import Protocol

from app.events.handlers.announcement_gap_handler import AnnouncementGapHandler
from app.events.handlers.discord_handler import DiscordHandler
from app.events.handlers.import_handler import ImportHandler


class EventHandler(Protocol):
    """Protocol for event handlers."""

    async def initialize(self, event_bus) -> None:
        """Initialize handler with event bus."""
        ...


__all__ = [
    "AnnouncementGapHandler",
    "DiscordHandler",
    "ImportHandler",
    "EventHandler",
]
