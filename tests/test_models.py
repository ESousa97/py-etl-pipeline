"""Tests for the ORM models declared in `src.models`."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from py_etl_pipeline.models import Base, LogEntry, Sale


def test_metadata_registers_expected_tables() -> None:
    assert set(Base.metadata.tables) == {"sales", "logs"}


def test_sale_columns_match_expected_shape() -> None:
    cols = {c.name for c in Sale.__table__.columns}
    assert cols == {
        "id",
        "external_id",
        "product_name",
        "quantity",
        "unit_price",
        "sold_at",
    }


def test_log_entry_columns_match_expected_shape() -> None:
    cols = {c.name for c in LogEntry.__table__.columns}
    assert cols == {"id", "level", "message", "source", "created_at"}


def test_create_all_creates_tables(sqlite_engine: Engine) -> None:
    assert set(inspect(sqlite_engine).get_table_names()) == {"sales", "logs"}


def test_sale_insert_and_read_back(session: Session) -> None:
    session.add(
        Sale(
            external_id="T-1",
            product_name="Caneta",
            quantity=3,
            unit_price=Decimal("4.50"),
        )
    )
    session.commit()

    row = session.scalars(select(Sale).where(Sale.external_id == "T-1")).one()
    assert row.product_name == "Caneta"
    assert row.quantity == 3
    assert row.unit_price == Decimal("4.50")
    assert isinstance(row.sold_at, datetime)


def test_log_entry_insert_and_read_back(session: Session) -> None:
    session.add(LogEntry(level="INFO", message="ola", source="test"))
    session.commit()

    row = session.scalars(select(LogEntry)).one()
    assert row.level == "INFO"
    assert row.message == "ola"
    assert row.source == "test"
    assert isinstance(row.created_at, datetime)
