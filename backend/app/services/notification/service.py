"""Notification service for asynchronous citizen updates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NotificationRecord:
    id: str = field(default_factory=lambda: str(uuid4()))
    complaint_id: str = ""
    event_type: str = ""
    channel: str = "IN_APP"  # IN_APP, SMS, WHATSAPP, EMAIL
    title: str = ""
    message: str = ""
    status: str = "DELIVERED"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class NotificationService:
    """Manages multi-channel notifications and in-app status updates for citizens."""

    def __init__(self) -> None:
        self._notifications: list[NotificationRecord] = []

    def notify(
        self,
        complaint_id: str,
        event_type: str,
        title: str,
        message: str,
        channel: str = "IN_APP",
        metadata: dict[str, Any] | None = None,
    ) -> NotificationRecord:
        record = NotificationRecord(
            complaint_id=complaint_id,
            event_type=event_type,
            channel=channel,
            title=title,
            message=message,
            metadata=metadata or {},
        )
        self._notifications.append(record)
        logger.info(
            "Citizen notification sent",
            extra={
                "complaint_id": complaint_id,
                "event_type": event_type,
                "channel": channel,
                "title": title,
            },
        )
        return record

    def get_for_complaint(self, complaint_id: str) -> list[NotificationRecord]:
        return [n for n in self._notifications if n.complaint_id == complaint_id]


# Global default instance
notification_service = NotificationService()
