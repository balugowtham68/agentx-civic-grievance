"""Database engine, sessions and initialisation.

One `Database` object per application instance (stored on `app.state.db`), so
tests can run against an isolated temporary database.

Schema creation uses `create_all` for the hackathon MVP; there are no migrations.
Changing a column means deleting `backend/data/agentx.db` locally.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.logging import get_logger
from app.database.base import Base

logger = get_logger(__name__)


def _prepare_sqlite(url: str) -> None:
    database = make_url(url).database
    if database and database != ":memory:":
        Path(database).parent.mkdir(parents=True, exist_ok=True)


def _sqlite_pragmas(dbapi_connection: object, _: object) -> None:
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")  # watchdog + API write concurrently later
    cursor.close()


class Database:
    def __init__(self, url: str) -> None:
        self.url = url
        is_sqlite = url.startswith("sqlite")
        if is_sqlite:
            _prepare_sqlite(url)
        self.engine: Engine = create_engine(
            url,
            connect_args={"check_same_thread": False} if is_sqlite else {},
            future=True,
        )
        if is_sqlite:
            event.listen(self.engine, "connect", _sqlite_pragmas)
        self._session_factory = sessionmaker(
            bind=self.engine, autoflush=False, expire_on_commit=False
        )

    def init_schema(self) -> None:
        # Import models so they register on Base.metadata.
        import app.models  # noqa: F401

        Base.metadata.create_all(self.engine)
        logger.info("database schema ready", extra={"tables": sorted(Base.metadata.tables)})

    def is_reachable(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001 - health check must never raise
            logger.exception("database health check failed")
            return False

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Unit of work: commits on success, rolls back on error."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        self.engine.dispose()
