"""Lightweight in-process EventBus for decoupled domain event dispatch."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Protocol

from app.core.events.idempotency import get_idempotency_store
from app.core.events.schemas import DomainEvent, EventType
from app.core.logging import get_logger

logger = get_logger(__name__)

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None: ...


class AsyncEventBus:
    """Async event bus dispatching domain events to registered handlers."""

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._idempotency = get_idempotency_store()

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)
        logger.debug("event handler subscribed", extra={"event_type": str(event_type), "handler": handler.__name__})

    async def publish(self, event: DomainEvent) -> None:
        # Idempotency check on event_id
        if not self._idempotency.check_and_set(f"event:{event.event_id}"):
            logger.warning("duplicate event ignored", extra={"event_id": event.event_id, "type": str(event.event_type)})
            return

        handlers = self._handlers.get(event.event_type, [])
        logger.info(
            "publishing event",
            extra={
                "event_id": event.event_id,
                "event_type": str(event.event_type),
                "complaint_id": event.complaint_id,
                "handlers_count": len(handlers),
            },
        )

        for handler in handlers:
            try:
                # Dispatch handler safely
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(self._safe_execute(handler, event))
                else:
                    handler(event)
            except Exception as exc:
                logger.error(
                    "failed to schedule event handler",
                    extra={"event_id": event.event_id, "error": str(exc)},
                )

    async def _safe_execute(self, handler: EventHandler, event: DomainEvent) -> None:
        try:
            await handler(event)
        except Exception as exc:
            logger.error(
                "event handler execution failed",
                extra={
                    "event_id": event.event_id,
                    "event_type": str(event.event_type),
                    "handler": getattr(handler, "__name__", str(handler)),
                    "error": str(exc),
                },
            )


# Global event bus singleton
_default_bus = AsyncEventBus()


def get_event_bus() -> AsyncEventBus:
    return _default_bus
