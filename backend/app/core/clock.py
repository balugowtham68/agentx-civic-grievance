"""Clock abstraction.

Every component that needs "now" (SLA, watchdog, audit) must ask a `Clock`,
never call `datetime.now()` directly. Phase 7 adds a simulated, accelerated clock
behind this same interface so the SLA lifecycle can be demonstrated in minutes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time, timezone-aware (UTC)."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


_clock: Clock = SystemClock()


def get_clock() -> Clock:
    return _clock


def set_clock(clock: Clock) -> None:
    """Swap the process clock (used by tests now, by the simulated clock in Phase 7)."""
    global _clock
    _clock = clock
