"""ETL stages: extract from sources, transform records, load into the database."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any, Literal

from sqlalchemy.orm import Session

from .extract import extract_sales
from .load import load as load_records
from .models import Sale
from .transform import transform_sales

logger = logging.getLogger(__name__)


def extract(session: Session) -> Iterable[dict[str, Any]]:
    return extract_sales(session)


def transform(rows: Iterable[dict[str, Any]]) -> list[Sale]:
    return transform_sales(list(rows))


def load(
    session: Session,
    rows: list[Sale],
    mode: Literal["bulk", "upsert"] = "bulk",
) -> dict[str, int]:
    return load_records(session, rows, mode=mode)


def run_pipeline(
    session: Session, load_mode: Literal["bulk", "upsert"] = "bulk"
) -> dict[str, int]:
    raw_list = list(extract(session))
    prepared = transform(raw_list)
    load_summary = load(session, prepared, mode=load_mode)
    session.commit()

    return {
        "extracted": len(raw_list),
        "transformed": len(prepared),
        **load_summary,
    }
