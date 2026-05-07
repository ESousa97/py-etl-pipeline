"""ETL stages: extract from sources, transform records, load into the database."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any, Literal

from sqlalchemy.orm import Session

from src.extract import extract_sales
from src.load import load as load_records
from src.models import Sale
from src.transform import transform_sales

logger = logging.getLogger(__name__)


def extract(session: Session) -> Iterable[dict[str, Any]]:
    """Return raw records from the upstream source.

    Implementations may ignore ``session`` when the source is external (files, APIs).
    Subclasses may return a generator instead of a materialized iterable.

    Args:
        session: Active SQLAlchemy session (e.g. for incremental reads).

    Returns:
        An iterable of dicts (one per raw row); shape is defined by :func:`transform`.
    """
    return extract_sales(session)


def transform(rows: Iterable[dict[str, Any]]) -> list[Sale]:
    """Normalize, validate, and enrich records before persistence.

    Args:
        rows: Iterable of raw dictionaries from :func:`extract`.

    Returns:
        A concrete list ready for :func:`load`.
    """
    return transform_sales(list(rows))


def load(
    session: Session,
    rows: list[Sale],
    mode: Literal["bulk", "upsert"] = "bulk",
) -> dict[str, int]:
    """Persist transformed rows with configurable strategy.

    Args:
        session: Session to flush/commit (commit is handled by :func:`run_pipeline`).
        rows: Output of :func:`transform`.
        mode: Loading strategy ('bulk' for insert-only, 'upsert' for insert-or-update).

    Returns:
        Summary dict with operation counts (inserted, updated, skipped, failed).
    """
    return load_records(session, rows, mode=mode)


def run_pipeline(
    session: Session, load_mode: Literal["bulk", "upsert"] = "bulk"
) -> dict[str, int]:
    """Execute extract → transform → load and commit.

    Args:
        session: Shared session for all stages.
        load_mode: Loading strategy ('bulk' for insert-only, 'upsert' for insert-or-update).

    Returns:
        Summary dict with extracted, inserted, updated, skipped, and failed counts.
    """
    raw_list = list(extract(session))
    prepared = transform(raw_list)
    load_summary = load(session, prepared, mode=load_mode)
    session.commit()

    return {
        "extracted": len(raw_list),
        "transformed": len(prepared),
        **load_summary,
    }
