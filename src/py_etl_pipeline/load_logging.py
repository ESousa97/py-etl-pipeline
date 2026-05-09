"""DB-backed logging utilities for the Load stage."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .models import LogEntry


def log_pipeline_event(
    session: Session,
    level: str,
    message: str,
    source: str = "pipeline.load",
) -> None:
    session.add(LogEntry(level=level, message=message, source=source))
