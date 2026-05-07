"""Integration tests against a real PostgreSQL.

Skipped by default. Run with::

    pytest --run-pg

The connection URL comes from ``DATABASE_URL`` (or ``POSTGRES_*`` fallback).
Each test runs inside an outer transaction that is rolled back on teardown,
so the test data does not persist between runs.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.models import LogEntry, Sale

pytestmark = pytest.mark.pg


def test_create_all_creates_expected_tables(pg_engine: Engine) -> None:
    names = set(inspect(pg_engine).get_table_names())
    assert {"sales", "logs"}.issubset(names)


def test_engine_dialect_is_postgresql(pg_engine: Engine) -> None:
    assert pg_engine.dialect.name == "postgresql"


def test_insert_round_trip(pg_session: Session) -> None:
    pg_session.add(
        Sale(
            external_id="IT-1",
            product_name="Widget",
            quantity=2,
            unit_price=Decimal("9.99"),
        )
    )
    pg_session.add(LogEntry(level="INFO", message="integration", source="pytest"))
    pg_session.commit()

    assert pg_session.query(Sale).filter_by(external_id="IT-1").count() == 1
    assert pg_session.query(LogEntry).filter_by(message="integration").count() >= 1
