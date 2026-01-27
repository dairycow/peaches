"""Test event bus."""

import asyncio
from dataclasses import dataclass

import pytest

from app.events.bus import EventBus, Event


@dataclass
class TestEvent(Event):
    """Test event type."""

    value: int


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    """Test event bus basic publish/subscribe."""
    bus = EventBus()
    received = []

    async def handler(event: TestEvent) -> None:
        received.append(event.value)

    await bus.start()
    await bus.subscribe(TestEvent, handler)

    await bus.publish(TestEvent(value=42))
    await asyncio.sleep(0.01)

    assert len(received) == 1
    assert received[0] == 42

    await bus.stop()


@pytest.mark.asyncio
async def test_event_bus_error_isolation():
    """Test one subscriber error doesn't affect others."""
    bus = EventBus()
    received = []

    async def failing_handler(event: TestEvent) -> None:
        raise Exception("Handler failed")

    async def working_handler(event: TestEvent) -> None:
        received.append(event.value)

    await bus.start()
    await bus.subscribe(TestEvent, failing_handler)
    await bus.subscribe(TestEvent, working_handler)

    await bus.publish(TestEvent(value=100))
    await asyncio.sleep(0.01)

    assert received == [100]

    await bus.stop()
