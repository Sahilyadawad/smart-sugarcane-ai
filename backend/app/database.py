"""SQLAlchemy engine, session factory and declarative base.

SQLite is the default so the project runs with no external services. The engine
options below are the only SQLite-specific part - switching ``DATABASE_URL`` to
PostgreSQL works without any other code change.
"""

from __future__ import annotations

import logging
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

#: Populated when the configured DATABASE_URL could not be used, so
#: /api/system/status can report the real reason.
ENGINE_ERROR: str | None = None


def _build_engine(uri: str):
    return create_engine(
        uri,
        # check_same_thread is required because FastAPI serves requests on a threadpool.
        connect_args={"check_same_thread": False} if uri.startswith("sqlite") else {},
        pool_pre_ping=True,
        echo=False,
    )


def _fallback_uri() -> str:
    """A URI that is always creatable, used only when the configured one is not."""
    if settings.is_serverless:
        return "sqlite:////tmp/smart_sugarcane.db"
    return f"sqlite:///{(settings.project_root / 'backend' / 'smart_sugarcane.db').as_posix()}"


try:
    engine = _build_engine(settings.database_uri)
except Exception as exc:  # noqa: BLE001
    # create_engine runs at import time, so an unusable DATABASE_URL - a typo in
    # the scheme, or a driver that is not installed - would otherwise kill the
    # process before FastAPI starts. On a serverless host that surfaces as an
    # opaque FUNCTION_INVOCATION_FAILED on every single route, with no clue as
    # to the cause. Falling back keeps the app alive so it can report the fault.
    ENGINE_ERROR = f"{type(exc).__name__}: {exc}"
    logging.getLogger(__name__).error(
        "Could not create the database engine for %r (%s). Falling back to %s.",
        settings.database_uri,
        ENGINE_ERROR,
        _fallback_uri(),
    )
    engine = _build_engine(_fallback_uri())

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Declarative base for every ORM model."""


def storage_is_ephemeral() -> bool:
    """True when this host throws the database away between requests.

    On Vercel/Lambda each invocation may run in a fresh container with its own
    private filesystem, so a SQLite file written by one request is invisible to
    the next. Accounts appear to be created and then "vanish", and every login
    comes back as "Incorrect email or password". Callers use this to say what is
    actually wrong instead of blaming the user's credentials.
    """
    return settings.is_serverless and engine.dialect.name == "sqlite"


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
