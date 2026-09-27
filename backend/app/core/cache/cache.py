"""Cache abstraction for static and rarely-changing civic knowledge."""

from __future__ import annotations

import threading
import time
from typing import Any, Protocol


class CacheProtocol(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None: ...
    def delete(self, key: str) -> None: ...


class InMemoryTTLCache:
    """Thread-safe in-memory cache with Time-To-Live support."""

    def __init__(self, default_ttl: int = 3600) -> None:
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            val, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return None
            return val

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expiry = time.time() + ttl
        with self._lock:
            self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


# Global default instance
cache_service = InMemoryTTLCache()
