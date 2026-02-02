"""Integration tests for event-driven flow."""

import asyncio

import pytest

from app.events import (
    AnnouncementFoundEvent,
    EventBus,
    ScanCompletedEvent,
    ScanStartedEvent,
)


@pytest.mark.asyncio
async def test_scan_event_flow():
    """Test complete scan event flow."""
    event_bus = EventBus()
    await event_bus.start()

    events = []

    async def capture(event):
        events.append(event)

    await event_bus.subscribe(ScanStartedEvent, capture)
    await event_bus.subscribe(AnnouncementFoundEvent, capture)
    await event_bus.subscribe(ScanCompletedEvent, capture)

    await event_bus.publish(ScanStartedEvent(source="manual", correlation_id="test"))
    from datetime import datetime

    await event_bus.publish(
        AnnouncementFoundEvent(
            source="manual",
            correlation_id="test",
            ticker="BHP",
            headline="Test announcement",
            date="2024-01-01",
            time="10:00",
            timestamp=datetime.now(),
        )
    )
    await event_bus.publish(
        ScanCompletedEvent(
            source="manual",
            correlation_id="test",
            total_announcements=1,
            processed_count=1,
            success=True,
            error=None,
        )
    )

    await asyncio.sleep(0.1)

    assert len(events) == 3
    assert isinstance(events[0], ScanStartedEvent)
    assert isinstance(events[1], AnnouncementFoundEvent)
    assert isinstance(events[2], ScanCompletedEvent)

    await event_bus.stop()
