"""SQLAlchemy engine, session factory and declarative base.

SQLite is the default so the project runs with no external services. The engine
options below are the only SQLite-specific part - switching ``DATABASE_URL`` to
PostgreSQL works without any other code change.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import DateTime, TypeDecorator, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class UTCDateTime(TypeDecorator):
    """A DateTime column that always reads back as timezone-aware UTC.

    SQLite has no native timezone support and silently drops tzinfo, so a value
    written as aware UTC comes back naive. Serialised to JSON without an offset,
    the browser then parses it as *local* time and every timestamp in the UI is
    wrong by the local UTC offset. This decorator normalises on the way in and
    re-attaches UTC on the way out, which fixes both Pydantic responses and any
    direct ``.isoformat()`` call.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

_is_sqlite = settings.database_uri.startswith("sqlite")

engine = create_engine(
    settings.database_uri,
    # check_same_thread is required because FastAPI serves requests on a threadpool.
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Declarative base for every ORM model."""


def get_db() -> Generator:
    """FastAPI dependency that yields a request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Safe to call on every startup."""
    from app import models  # noqa: F401  (import registers the models)

    Base.metadata.create_all(bind=engine)
