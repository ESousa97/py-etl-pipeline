"""Public API / dispatcher tests for Load stage."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from py_etl_pipeline.load import load, log_pipeline_event
from py_etl_pipeline.models import LogEntry, Sale


def test_load_invalid_mode_raises_error(session: Session) -> None:
    sale = Sale(
        external_id="ext-invalid",
        product_name="InvalidProduct",
        quantity=1,
        unit_price=Decimal("1.00"),
    )
    with pytest.raises(ValueError, match="Unknown load mode"):
        load(session, [sale], mode="invalid")  # type: ignore


def test_log_pipeline_event(session: Session) -> None:
    log_pipeline_event(
        session,
        "INFO",
        "Test log message",
        source="test_source",
    )
    session.flush()

    entry = session.query(LogEntry).filter_by(source="test_source").first()
    assert entry is not None
    assert entry.level == "INFO"
    assert entry.message == "Test log message"
