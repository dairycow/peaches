"""Integration tests for announcement gap handler."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from vnpy.trader.constant import Exchange

from app.events import EventBus
from app.events.events import (
    AnnouncementGapScanCompletedEvent,
    AnnouncementGapScanStartedEvent,
)
from app.events.handlers import AnnouncementGapHandler
from app.scanners.gap.announcement_gap_scanner import AnnouncementGapCandidate
from app.services.notification_service import NotificationService


@pytest.fixture
def mock_notification_service():
    """Create mock notification service."""
    service = MagicMock(spec=NotificationService)
    service.send_discord_webhook = AsyncMock()
    service.enabled = True
    return service


@pytest.fixture
def mock_strategy_service():
    """Create mock strategy service with sample candidates."""
    service = MagicMock()
    service.run_daily_scan = AsyncMock(
        return_value=[
            AnnouncementGapCandidate(
                symbol="BHP",
                gap_pct=3.45,
                six_month_high=48.20,
                current_price=49.75,
                announcement_headline="Quarterly Production Report exceeds guidance with record iron ore shipments",
                announcement_time=datetime(2024, 3, 5, 10, 1, 32),
            ),
            AnnouncementGapCandidate(
                symbol="RIO",
                gap_pct=2.15,
                six_month_high=120.50,
                current_price=123.00,
                announcement_headline="Strong Q4 results announced",
                announcement_time=datetime(2024, 3, 5, 10, 2, 15),
            ),
        ]
    )
    return service


@pytest.mark.asyncio
async def test_announcement_gap_handler_initialization(
    mock_notification_service, mock_strategy_service
):
    """Test AnnouncementGapHandler initializes correctly."""
    event_bus = EventBus()
    await event_bus.start()

    handler = AnnouncementGapHandler(
        notification_service=mock_notification_service,
        strategy_service=mock_strategy_service,
    )
    await handler.initialize(event_bus)

    assert handler is not None
    assert handler.notification_service is mock_notification_service
    assert handler.strategy_service is mock_strategy_service

    await event_bus.stop()


@pytest.mark.asyncio
async def test_announcement_gap_handler_event_flow(
    mock_notification_service, mock_strategy_service
):
    """Test complete event flow from scan started to Discord notifications."""
    event_bus = EventBus()
    await event_bus.start()

    handler = AnnouncementGapHandler(
        notification_service=mock_notification_service,
        strategy_service=mock_strategy_service,
    )
    await handler.initialize(event_bus)

    completion_events = []

    async def capture_completion(event):
        completion_events.append(event)

    await event_bus.subscribe(AnnouncementGapScanCompletedEvent, capture_completion)

    await event_bus.publish(
        AnnouncementGapScanStartedEvent(
            source="scheduled",
            correlation_id="test_cron",
        )
    )

    await asyncio.sleep(0.2)

    assert mock_strategy_service.run_daily_scan.called
    assert mock_notification_service.send_discord_webhook.call_count == 2

    first_call = mock_notification_service.send_discord_webhook.call_args_list[0]
    assert first_call.kwargs["ticker"] == "BHP"
    assert "+3.45% gap" in first_call.kwargs["headline"]
    assert "breaking 6M high ($48.20)" in first_call.kwargs["headline"]
    assert "Price: $49.75" in first_call.kwargs["headline"]

    second_call = mock_notification_service.send_discord_webhook.call_args_list[1]
    assert second_call.kwargs["ticker"] == "RIO"
    assert "+2.15% gap" in second_call.kwargs["headline"]

    assert len(completion_events) == 1
    assert completion_events[0].count == 2
    assert completion_events[0].success is True
    assert completion_events[0].error is None

    await event_bus.stop()


@pytest.mark.asyncio
async def test_announcement_gap_handler_no_candidates(mock_notification_service):
    """Test handler behaviour when no candidates found."""
    mock_strategy_service = MagicMock()
    mock_strategy_service.run_daily_scan = AsyncMock(return_value=[])

    event_bus = EventBus()
    await event_bus.start()

    handler = AnnouncementGapHandler(
        notification_service=mock_notification_service,
        strategy_service=mock_strategy_service,
    )
    await handler.initialize(event_bus)

    completion_events = []

    async def capture_completion(event):
        completion_events.append(event)

    await event_bus.subscribe(AnnouncementGapScanCompletedEvent, capture_completion)

    await event_bus.publish(
        AnnouncementGapScanStartedEvent(
            source="scheduled",
            correlation_id="test_cron",
        )
    )

    await asyncio.sleep(0.2)

    assert mock_strategy_service.run_daily_scan.called
    assert mock_notification_service.send_discord_webhook.call_count == 0

    assert len(completion_events) == 1
    assert completion_events[0].count == 0
    assert completion_events[0].success is True

    await event_bus.stop()


@pytest.mark.asyncio
async def test_announcement_gap_handler_scan_error(mock_notification_service):
    """Test handler behaviour when scan fails."""
    mock_strategy_service = MagicMock()
    mock_strategy_service.run_daily_scan = AsyncMock(
        side_effect=Exception("Database connection failed")
    )

    event_bus = EventBus()
    await event_bus.start()

    handler = AnnouncementGapHandler(
        notification_service=mock_notification_service,
        strategy_service=mock_strategy_service,
    )
    await handler.initialize(event_bus)

    completion_events = []

    async def capture_completion(event):
        completion_events.append(event)

    await event_bus.subscribe(AnnouncementGapScanCompletedEvent, capture_completion)

    await event_bus.publish(
        AnnouncementGapScanStartedEvent(
            source="scheduled",
            correlation_id="test_cron",
        )
    )

    await asyncio.sleep(0.2)

    assert mock_strategy_service.run_daily_scan.called
    assert mock_notification_service.send_discord_webhook.call_count == 0

    assert len(completion_events) == 1
    assert completion_events[0].count == 0
    assert completion_events[0].success is False
    assert "Database connection failed" in completion_events[0].error

    await event_bus.stop()


def test_announcement_gap_handler_truncate_headline():
    """Test headline truncation logic."""
    mock_notification_service = MagicMock(spec=NotificationService)
    mock_strategy_service = MagicMock()

    handler = AnnouncementGapHandler(
        notification_service=mock_notification_service,
        strategy_service=mock_strategy_service,
    )

    short_headline = "Short headline"
    assert handler._truncate_headline(short_headline, 100) == short_headline

    long_headline = "A" * 150
    truncated = handler._truncate_headline(long_headline, 100)
    assert len(truncated) == 100
    assert truncated.endswith("...")
    assert truncated == "A" * 97 + "..."

    exact_headline = "B" * 100
    assert handler._truncate_headline(exact_headline, 100) == exact_headline
