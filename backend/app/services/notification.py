"""Notification service for dispatching citizen timeline and status updates."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, Field
from app.core.logging import get_logger

logger = get_logger(__name__)


class TimelineEntry(BaseModel):
    id: str
    complaint_id: str
    stage: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = Field(default_factory=dict)
    icon: str = "check"


class NotificationService:
    """Dispatches notifications and maintains the citizen progress timeline."""

    def __init__(self) -> None:
        self._timelines: dict[str, list[TimelineEntry]] = defaultdict(list)

    def record_timeline(
        self,
        complaint_id: str,
        stage: str,
        message: str,
        details: dict[str, Any] | None = None,
        icon: str = "check",
    ) -> TimelineEntry:
        import uuid
        entry = TimelineEntry(
            id=str(uuid.uuid4()),
            complaint_id=complaint_id,
            stage=stage,
            message=message,
            details=details or {},
            icon=icon,
        )
        self._timelines[complaint_id].append(entry)
        logger.info(
            "timeline event recorded",
            extra={"complaint_id": complaint_id, "stage": stage, "note": message},
        )
        return entry

    def get_timeline(self, complaint_id: str) -> list[TimelineEntry]:
        return self._timelines.get(complaint_id, [])

    async def notify(
        self, complaint_id: str, event_type: str, message: str, channel: str = "in_app"
    ) -> None:
        logger.info(
            "citizen notification dispatched",
            extra={"complaint_id": complaint_id, "event_type": event_type, "channel": channel, "content": message},
        )


_default_notification = NotificationService()


def get_notification_service() -> NotificationService:
    return _default_notification
