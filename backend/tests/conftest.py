from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.clock import SystemClock, set_clock
from app.core.config import AppEnvironment, Settings
from app.database import Database
from app.main import create_app


class FixedClock:
    """Deterministic clock for tests."""

    def __init__(self, start: datetime | None = None) -> None:
        self.current = start or datetime(2026, 1, 1, 9, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current += timedelta(**kwargs)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,  # never read a developer's real .env in tests
        app_env=AppEnvironment.TEST,
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        log_level="WARNING",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings), raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def database(settings: Settings) -> Iterator[Database]:
    db = Database(settings.database_url)
    db.init_schema()
    yield db
    db.dispose()


@pytest.fixture
def clock() -> Iterator[FixedClock]:
    fixed = FixedClock()
    set_clock(fixed)
    yield fixed
    set_clock(SystemClock())
