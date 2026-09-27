"""Cache abstraction supporting in-process memory and future distributed stores."""

from __future__ import annotations

import time
from typing import Any, Protocol


class CacheService(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...


class InMemoryCacheService:
    """Thread-safe in-memory cache with time-to-live expiration."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        val, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return None
        return val

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        self._store[key] = (value, time.time() + ttl_seconds)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


# Default cache service singleton
_default_cache = InMemoryCacheService()


def get_cache_service() -> InMemoryCacheService:
    return _default_cache
