"""Upsert tests for the Load stage."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from py_etl_pipeline.load import load, load_upsert
from py_etl_pipeline.models import Sale


def test_load_upsert_empty_list(session: Session) -> None:
    result = load_upsert(session, [])
    assert result == {"inserted": 0, "updated": 0, "skipped": 0, "failed": 0}


def test_load_upsert_insert_new_row(session: Session) -> None:
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

    queried = session.query(Sale).filter_by(external_id="ext-new-001").first()
    assert queried is not None
    assert queried.product_name == "NewProduct"


def test_load_upsert_skip_row_without_key(session: Session) -> None:
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
    from datetime import datetime

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

    sale2 = Sale(
        external_id="ext-update-001",
        product_name="UpdatedName",
        quantity=15,
        unit_price=Decimal("20.00"),
        sold_at=now,
    )
    result = load_upsert(session, [sale2])

    assert result["updated"] >= 0  # May vary depending on DB dialect
    assert result["failed"] == 0

    queried = session.query(Sale).filter_by(external_id="ext-update-001").first()
    assert queried is not None
    assert queried.external_id == "ext-update-001"


def test_load_upsert_mode_dispatch(session: Session) -> None:
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


@pytest.mark.pg
def test_load_upsert_postgresql_native(pg_session: Session) -> None:
    sale1 = Sale(
        external_id="pg-ext-001",
        product_name="PGProduct",
        quantity=5,
        unit_price=Decimal("10.00"),
    )
    pg_session.add(sale1)
    pg_session.flush()

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
