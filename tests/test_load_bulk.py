"""Bulk insert tests for the Load stage."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from py_etl_pipeline.load import load, load_bulk_insert
from py_etl_pipeline.models import LogEntry, Sale


def test_load_bulk_insert_empty_list(session: Session) -> None:
    result = load_bulk_insert(session, [])
    assert result == {"inserted": 0, "skipped": 0, "failed": 0}


def test_load_bulk_insert_single_row(session: Session) -> None:
    sale = Sale(
        external_id="ext-001",
        product_name="Widget",
        quantity=5,
        unit_price=Decimal("10.50"),
    )
    result = load_bulk_insert(session, [sale])

    assert result == {"inserted": 1, "skipped": 0, "failed": 0}
    queried = session.query(Sale).filter_by(external_id="ext-001").first()
    assert queried is not None
    assert queried.product_name == "Widget"


def test_load_bulk_insert_multiple_rows(session: Session) -> None:
    sales = [
        Sale(
            external_id=f"ext-{i:03d}",
            product_name=f"Product {i}",
            quantity=i,
            unit_price=Decimal(f"{i * 10}.00"),
        )
        for i in range(1, 6)
    ]
    result = load_bulk_insert(session, sales)

    assert result == {"inserted": 5, "skipped": 0, "failed": 0}
    assert session.query(Sale).count() == 5


def test_load_bulk_mode_dispatch(session: Session) -> None:
    sale = Sale(
        external_id="ext-bulk-001",
        product_name="BulkProduct",
        quantity=3,
        unit_price=Decimal("7.50"),
    )
    result = load(session, [sale], mode="bulk")
    assert result == {"inserted": 1, "skipped": 0, "failed": 0}


def test_load_creates_log_entries_on_success(session: Session) -> None:
    sale = Sale(
        external_id="ext-log-001",
        product_name="LogProduct",
        quantity=1,
        unit_price=Decimal("1.00"),
    )
    load_bulk_insert(session, [sale])
    session.flush()

    entry = session.query(LogEntry).filter(
        LogEntry.message.contains("Bulk insert completed")
    ).first()
    assert entry is not None
    assert entry.level == "INFO"
    assert "1 rows inserted" in entry.message


def test_load_large_batch(session: Session) -> None:
    sales = [
        Sale(
            external_id=f"ext-batch-{i:05d}",
            product_name=f"Product {i}",
            quantity=i % 100 + 1,
            unit_price=Decimal(f"{(i % 10) * 10 + 1}.99"),
        )
        for i in range(1000)
    ]
    result = load_bulk_insert(session, sales)

    assert result["inserted"] == 1000
    assert result["skipped"] == 0
    assert result["failed"] == 0
    assert session.query(Sale).count() == 1000


def test_load_bulk_insert_batches_rows(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOAD_BATCH_SIZE", "2")

    import importlib

    import py_etl_pipeline.config as config
    import py_etl_pipeline.load as load_mod

    importlib.reload(config)
    importlib.reload(load_mod)

    sales = [
        Sale(
            external_id=f"b-{i}",
            product_name=f"P{i}",
            quantity=1,
            unit_price=Decimal("1.00"),
        )
        for i in range(5)
    ]
    result = load_mod.load_bulk_insert(session, sales)
    assert result == {"inserted": 5, "skipped": 0, "failed": 0}
    assert session.query(Sale).count() == 5

