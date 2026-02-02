"""In-memory async event bus."""

import asyncio
import contextlib
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from loguru import logger

if TYPE_CHECKING:
    pass

E = TypeVar("E", bound="Event")


@dataclass
class Event:
    """Base class for all application events."""

    def __post_init__(self) -> None:
        """Initialize event timestamp."""
        object.__setattr__(self, "timestamp", asyncio.get_event_loop().time())


class EventBus:
    """In-memory async event bus using asyncio.Queue.

    Features:
    - Non-blocking event publishing
    - Concurrent subscriber processing
    - Graceful shutdown support
    - Error isolation per subscriber
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        """Initialize event bus."""
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max_queue_size)
        self._subscribers: dict[type[Event], list[Callable[[Any], Coroutine[Any, Any, None]]]] = {}
        self._running: bool = False
        self._worker_task: asyncio.Task[None] | None = None
        self._lock: asyncio.Lock = asyncio.Lock()

    async def subscribe(
        self, event_type: type[E], handler: Callable[[E], Coroutine[Any, Any, None]]
    ) -> None:
        """Subscribe to an event type."""
        await self._subscribe(event_type, handler)

    async def _subscribe(
        self, event_type: type[E], handler: Callable[[E], Coroutine[Any, Any, None]]
    ) -> None:
        """Thread-safe subscribe implementation."""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
            logger.debug(
                f"Subscribed handler {handler.__name__} to {event_type.__name__} "
                f"(total: {len(self._subscribers[event_type])})"
            )

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        await self._queue.put(event)
        logger.debug(f"Published event {event.__class__.__name__}")

    async def start(self) -> None:
        """Start event bus processing."""
        if self._running:
            logger.warning("Event bus already running")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop event bus and drain queue."""
        if not self._running:
            return

        logger.info("Stopping event bus...")
        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

        logger.info("Event bus stopped")

    async def _process_events(self) -> None:
        """Process events from queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._dispatch_event(event)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def _dispatch_event(self, event: Event) -> None:
        """Dispatch event to all subscribers concurrently."""
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            logger.debug(f"No subscribers for {event_type.__name__}")
            return

        tasks = [self._call_handler(handler, event) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _call_handler(
        self, handler: Callable[[Event], Coroutine[Any, Any, None]], event: Event
    ) -> None:
        """Call a single handler with error isolation."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Handler {handler.__name__} failed for {event.__class__.__name__}: {e}",
                exc_info=True,
            )


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create EventBus singleton.

    Returns:
        EventBus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def reset_event_bus() -> None:
    """Reset EventBus singleton for test isolation."""
    global _event_bus
    if _event_bus is not None and _event_bus._running:
        await _event_bus.stop()
    _event_bus = None
