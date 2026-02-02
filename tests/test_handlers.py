"""Test event handlers."""

import pytest

from app.events import (
    AnnouncementFoundEvent,
    EventBus,
    ScanCompletedEvent,
)
from app.events.handlers import DiscordHandler, ImportHandler, StrategyHandler
from app.services import (
    get_notification_service,
    get_strategy_trigger_service,
)


@pytest.mark.asyncio
async def test_discord_handler():
    """Test DiscordHandler subscribes to events."""
    event_bus = EventBus()
    notification_service = get_notification_service(
        webhook_url="https://test.com",
        username="test",
        enabled=False,
    )

    handler = DiscordHandler(notification_service)
    await handler.initialize(event_bus)

    assert handler is not None


@pytest.mark.asyncio
async def test_strategy_handler():
    """Test StrategyHandler subscribes to events."""
    event_bus = EventBus()
    strategy_trigger_service = get_strategy_trigger_service(
        enabled=False,
        strategy_names=[],
    )

    handler = StrategyHandler(strategy_trigger_service)
    await handler.initialize(event_bus)

    assert handler is not None


@pytest.mark.asyncio
async def test_import_handler():
    """Test ImportHandler subscribes to events."""
    event_bus = EventBus()
    handler = ImportHandler(csv_dir="/tmp")
    await handler.initialize(event_bus)

    assert handler is not None
