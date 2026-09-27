"""EventBus abstraction for decoupled event-driven workflows."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Protocol

from app.core.events.schema import DomainEvent
from app.core.logging import get_logger

logger = get_logger(__name__)

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBusProtocol(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: str, handler: EventHandler) -> None: ...


class LocalAsyncEventBus:
    """Lightweight in-memory asynchronous event bus with decoupled subscriber execution."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[DomainEvent] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed handler to event", extra={"event_type": event_type})

    async def publish(self, event: DomainEvent) -> None:
        self._history.append(event)
        logger.info(
            "Event published",
            extra={
                "event_type": event.event_type,
                "event_id": event.event_id,
                "complaint_id": event.complaint_id,
            },
        )

        handlers = list(self._subscribers.get(event.event_type, []))
        # Support wildcard '*' and prefix wildcard like 'complaint.*'
        for pattern, subs in self._subscribers.items():
            if pattern == "*":
                handlers.extend(subs)
            elif pattern.endswith(".*") and event.event_type.startswith(pattern[:-2] + "."):
                handlers.extend(subs)

        for handler in handlers:
            # Run subscriber without blocking other subscribers or caller
            asyncio.create_task(self._safe_execute(handler, event))

    async def _safe_execute(self, handler: EventHandler, event: DomainEvent) -> None:
        try:
            await handler(event)
        except Exception as exc:
            logger.error(
                "Error executing event handler",
                extra={
                    "event_type": event.event_type,
                    "event_id": event.event_id,
                    "error": str(exc),
                },
            )

    def get_history(self, complaint_id: str | None = None) -> list[DomainEvent]:
        if complaint_id:
            return [e for e in self._history if e.complaint_id == complaint_id]
        return list(self._history)


# Global default instance
event_bus = LocalAsyncEventBus()
