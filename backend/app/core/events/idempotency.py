"""Idempotency management for events and background jobs."""

from __future__ import annotations

import time
from typing import Protocol


class IdempotencyStore(Protocol):
    def check_and_set(self, key: str, ttl_seconds: int = 3600) -> bool:
        """Returns True if the key was new and is now locked; False if already processed."""
        ...

    def exists(self, key: str) -> bool: ...


class InMemoryIdempotencyStore:
    """Thread-safe and async-safe in-memory idempotency store."""

    def __init__(self) -> None:
        self._keys: dict[str, float] = {}

    def check_and_set(self, key: str, ttl_seconds: int = 3600) -> bool:
        now = time.time()
        # Clean expired keys
        if key in self._keys:
            if self._keys[key] > now:
                return False  # Already exists and not expired
        self._keys[key] = now + ttl_seconds
        return True

    def exists(self, key: str) -> bool:
        now = time.time()
        if key in self._keys:
            if self._keys[key] > now:
                return True
            del self._keys[key]
        return False

    def clear(self) -> None:
        self._keys.clear()


# Global default store
_default_store = InMemoryIdempotencyStore()


def get_idempotency_store() -> InMemoryIdempotencyStore:
    return _default_store
