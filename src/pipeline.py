"""ETL stages: extract from sources, transform records, load into the database."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy.orm import Session


def extract(session: Session) -> Iterable[dict[str, Any]]:
    """Return raw records from the upstream source.

    Implementations may ignore ``session`` when the source is external (files, APIs).
    Subclasses may return a generator instead of a materialized iterable.

    Args:
        session: Active SQLAlchemy session (e.g. for incremental reads).

    Returns:
        An iterable of dicts (one per raw row); shape is defined by :func:`transform`.
    """
    _ = session
    return []


def transform(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize, validate, and enrich records before persistence.

    Args:
        rows: Iterable of raw dictionaries from :func:`extract`.

    Returns:
        A concrete list ready for :func:`load`.
    """
    return list(rows)


def load(session: Session, rows: list[dict[str, Any]]) -> int:
    """Persist transformed rows (implement using your ORM models or bulk APIs).

    Args:
        session: Session to flush/commit (commit is handled by :func:`run_pipeline`).
        rows: Output of :func:`transform`.

    Returns:
        Number of rows written or affected (domain-specific).
    """
    _ = session, rows
    return 0


def run_pipeline(session: Session) -> dict[str, int]:
    """Execute extract → transform → load and commit.

    Args:
        session: Shared session for all stages.

    Returns:
        Summary counts ``extracted`` and ``loaded``.
    """
    raw_list = list(extract(session))
    prepared = transform(raw_list)
    inserted = load(session, prepared)
    session.commit()
    return {"extracted": len(raw_list), "loaded": inserted}
