"""SQLAlchemy engine, session factory, and schema initialization."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import database_url
from src.models import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def engine() -> Engine:
    """Lazy singleton SQLAlchemy engine with connection health checks (pre-ping)."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            database_url(),
            pool_pre_ping=True,
            echo=os.getenv("SQLALCHEMY_ECHO", "").lower() in ("1", "true", "yes"),
        )
    return _engine


def SessionLocal() -> sessionmaker[Session]:
    """Return the bound session factory (created on first use)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=engine(), autoflush=False, autocommit=False
        )
    return _session_factory


def init_db() -> None:
    """Create database tables for all models registered on ``Base`` if they do not exist.

    This calls ``metadata.create_all()`` and does not migrate or drop existing tables.
    """
    Base.metadata.create_all(bind=engine())


def get_session() -> Session:
    """Open a new ORM ``Session``. Caller is responsible for ``close()`` or context usage."""
    return SessionLocal()()
