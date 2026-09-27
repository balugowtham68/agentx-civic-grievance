"""Idempotency management to prevent duplicate job or event execution."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from app.core.logging import get_logger

logger = get_logger(__name__)


class DuplicateEventError(Exception):
    """Raised when an event or task with an already-processed idempotency key is submitted."""
    pass


class IdempotencyManager:
    """Tracks executed operation keys to guarantee at-most-once execution per key."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._processed_keys: set[str] = set()

    def is_processed(self, key: str) -> bool:
        with self._lock:
            return key in self._processed_keys

    def mark_processed(self, key: str) -> None:
        with self._lock:
            self._processed_keys.add(key)

    @contextmanager
    def execute_idempotent(self, key: str) -> Iterator[bool]:
        """Yields True if this execution should proceed, False if already executed."""
        with self._lock:
            if key in self._processed_keys:
                logger.info("Skipping duplicate execution for key", extra={"idempotency_key": key})
                yield False
                return
            self._processed_keys.add(key)
        yield True

    def clear(self) -> None:
        with self._lock:
            self._processed_keys.clear()


# Global default instance
idempotency_manager = IdempotencyManager()
