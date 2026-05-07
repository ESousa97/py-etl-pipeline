"""SQLAlchemy engine, session factory, and schema initialization."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import database_url
from .models import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            database_url(),
            pool_pre_ping=True,
            echo=os.getenv("SQLALCHEMY_ECHO", "").lower() in ("1", "true", "yes"),
        )
    return _engine


def SessionLocal() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=engine(), autoflush=False, autocommit=False)
    return _session_factory


def init_db() -> None:
    Base.metadata.create_all(bind=engine())


def get_session() -> Session:
    return SessionLocal()()
