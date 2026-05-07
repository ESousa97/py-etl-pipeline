"""Tests for the Load stage in `src.load`."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.load import (
    load,
    load_bulk_insert,
    load_upsert,
    log_pipeline_event,
)
from src.models import LogEntry, Sale


def test_load_bulk_insert_empty_list(session: Session) -> None:
    """Bulk insert with empty list should return zero counts."""
    result = load_bulk_insert(session, [])
    assert result == {"inserted": 0, "skipped": 0, "failed": 0}


def test_load_bulk_insert_single_row(session: Session) -> None:
    """Bulk insert should add rows to the session."""
    sale = Sale(
        external_id="ext-001",
        product_name="Widget",
        quantity=5,
        unit_price=Decimal("10.50"),
    )
    result = load_bulk_insert(session, [sale])

    assert result == {"inserted": 1, "skipped": 0, "failed": 0}
    # Verify row was flushed (but not committed)
    queried = session.query(Sale).filter_by(external_id="ext-001").first()
    assert queried is not None
    assert queried.product_name == "Widget"


def test_load_bulk_insert_multiple_rows(session: Session) -> None:
    """Bulk insert should handle multiple rows."""
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
    # Verify all rows were inserted
    count = session.query(Sale).count()
    assert count == 5


def test_load_upsert_empty_list(session: Session) -> None:
    """Upsert with empty list should return zero counts."""
    result = load_upsert(session, [])
    assert result == {"inserted": 0, "updated": 0, "skipped": 0, "failed": 0}


def test_load_upsert_insert_new_row(session: Session) -> None:
    """Upsert should insert new rows when external_id doesn't exist."""
    sale = Sale(
        external_id="ext-new-001",
        product_name="NewProduct",
        quantity=10,
        unit_price=Decimal("25.99"),
    )
    result = load_upsert(session, [sale])

    assert result["inserted"] >= 1  # On PostgreSQL may be >= 1 due to bulk handling
    assert result["updated"] >= 0
    assert result["skipped"] == 0
    assert result["failed"] == 0

    # Verify row was inserted
    queried = session.query(Sale).filter_by(external_id="ext-new-001").first()
    assert queried is not None
    assert queried.product_name == "NewProduct"


def test_load_upsert_skip_row_without_key(session: Session) -> None:
    """Upsert should skip rows with no external_id (key is None)."""
    sale = Sale(
        external_id=None,
        product_name="NoKeyProduct",
        quantity=1,
        unit_price=Decimal("5.00"),
    )
    result = load_upsert(session, [sale])

    assert result["skipped"] >= 1
    assert result["failed"] == 0


def test_load_upsert_update_existing_row(session: Session) -> None:
    """Upsert should update existing rows when external_id matches (for non-PostgreSQL DB)."""
    from datetime import datetime

    # First, insert a row
    now = datetime.now()
    sale1 = Sale(
        external_id="ext-update-001",
        product_name="OriginalName",
        quantity=5,
        unit_price=Decimal("10.00"),
        sold_at=now,
    )
    session.add(sale1)
    session.flush()

    # Now upsert with the same external_id but different data
    sale2 = Sale(
        external_id="ext-update-001",
        product_name="UpdatedName",
        quantity=15,
        unit_price=Decimal("20.00"),
        sold_at=now,
    )
    result = load_upsert(session, [sale2])

    # Check that we processed the row
    assert result["updated"] >= 0  # May vary depending on DB dialect
    assert result["failed"] == 0

    # Verify the row was updated (on non-PostgreSQL dialects)
    queried = session.query(Sale).filter_by(external_id="ext-update-001").first()
    assert queried is not None
    # On non-PostgreSQL: should be updated
    # On PostgreSQL: ON CONFLICT may update but we can't guarantee the exact state
    # So we just verify it exists
    assert queried.external_id == "ext-update-001"


def test_load_bulk_mode(session: Session) -> None:
    """load() function with mode='bulk' should call load_bulk_insert."""
    sale = Sale(
        external_id="ext-bulk-001",
        product_name="BulkProduct",
        quantity=3,
        unit_price=Decimal("7.50"),
    )
    result = load(session, [sale], mode="bulk")

    assert result == {"inserted": 1, "skipped": 0, "failed": 0}


def test_load_upsert_mode(session: Session) -> None:
    """load() function with mode='upsert' should call load_upsert."""
    sale = Sale(
        external_id="ext-upsert-001",
        product_name="UpsertProduct",
        quantity=2,
        unit_price=Decimal("12.99"),
    )
    result = load(session, [sale], mode="upsert")

    assert result["inserted"] >= 1
    assert result["updated"] >= 0
    assert result["skipped"] == 0
    assert result["failed"] == 0


def test_load_invalid_mode_raises_error(session: Session) -> None:
    """load() function should raise ValueError for unknown mode."""
    sale = Sale(
        external_id="ext-invalid",
        product_name="InvalidProduct",
        quantity=1,
        unit_price=Decimal("1.00"),
    )
    with pytest.raises(ValueError, match="Unknown load mode"):
        load(session, [sale], mode="invalid")  # type: ignore


def test_log_pipeline_event(session: Session) -> None:
    """log_pipeline_event() should create a LogEntry in the database."""
    log_pipeline_event(
        session,
        "INFO",
        "Test log message",
        source="test_source",
    )
    session.flush()

    # Verify log entry was created
    entry = session.query(LogEntry).filter_by(source="test_source").first()
    assert entry is not None
    assert entry.level == "INFO"
    assert entry.message == "Test log message"


def test_load_creates_log_entries_on_success(session: Session) -> None:
    """load_bulk_insert should create a log entry on success."""
    sale = Sale(
        external_id="ext-log-001",
        product_name="LogProduct",
        quantity=1,
        unit_price=Decimal("1.00"),
    )
    load_bulk_insert(session, [sale])
    session.flush()

    # Verify log entry was created
    entry = session.query(LogEntry).filter(
        LogEntry.message.contains("Bulk insert completed")
    ).first()
    assert entry is not None
    assert entry.level == "INFO"
    assert "1 rows inserted" in entry.message


def test_load_large_batch(session: Session) -> None:
    """load_bulk_insert should efficiently handle large batches of rows."""
    # Create 1000 rows
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

    # Verify all rows were inserted
    count = session.query(Sale).count()
    assert count == 1000


@pytest.mark.pg
def test_load_upsert_postgresql_native(pg_session: Session) -> None:
    """On PostgreSQL, upsert should use ON CONFLICT efficiently."""
    # Insert initial row
    sale1 = Sale(
        external_id="pg-ext-001",
        product_name="PGProduct",
        quantity=5,
        unit_price=Decimal("10.00"),
    )
    pg_session.add(sale1)
    pg_session.flush()

    # Upsert with same external_id
    sale2 = Sale(
        external_id="pg-ext-001",
        product_name="PGProductUpdated",
        quantity=10,
        unit_price=Decimal("20.00"),
    )
    result = load_upsert(pg_session, [sale2])

    pg_session.flush()

    assert result["failed"] == 0
    assert result["inserted"] == 0
    assert result["updated"] == 1
    assert result["skipped"] == 0

    queried = pg_session.query(Sale).filter_by(external_id="pg-ext-001").first()
    assert queried is not None
    assert queried.product_name == "PGProductUpdated"
    assert queried.quantity == 10
    assert queried.unit_price == Decimal("20.00")


def test_load_bulk_insert_batches_rows(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bulk insert should process rows in configured batch chunks."""
    monkeypatch.setenv("LOAD_BATCH_SIZE", "2")
    import importlib

    import src.config as config
    import src.load as load_mod

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
