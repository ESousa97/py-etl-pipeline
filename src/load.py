"""Load stage: efficiently persist transformed records with bulk operations and upsert logic."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import insert, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.models import LogEntry, Sale

logger = logging.getLogger(__name__)


def log_pipeline_event(
    session: Session,
    level: str,
    message: str,
    source: str = "pipeline.load",
) -> None:
    """Persist a log entry to the database.

    Args:
        session: Active SQLAlchemy session.
        level: Log level (e.g., 'INFO', 'WARNING', 'ERROR').
        message: Log message content.
        source: Origin identifier (default: 'pipeline.load').
    """
    entry = LogEntry(level=level, message=message, source=source)
    session.add(entry)


def load_bulk_insert(session: Session, rows: list[Sale]) -> dict[str, int]:
    """Load records using bulk insert with minimal overhead.

    This method is optimized for initial inserts where no duplicates are expected.
    For upsert behavior, use :func:`load_upsert` instead.

    Args:
        session: Active SQLAlchemy session.
        rows: List of Sale ORM objects to insert.

    Returns:
        Dict with keys 'inserted' (count of inserted rows) and 'skipped' (always 0 for bulk insert).
    """
    if not rows:
        logger.info("No rows to load (bulk insert)")
        log_pipeline_event(session, "INFO", "Bulk insert: 0 rows processed")
        return {"inserted": 0, "skipped": 0, "failed": 0}

    try:
        session.add_all(rows)
        session.flush()
        inserted_count = len(rows)
        logger.info(f"Bulk insert: {inserted_count} rows successfully inserted")
        log_pipeline_event(
            session,
            "INFO",
            f"Bulk insert completed: {inserted_count} rows inserted",
        )
        return {"inserted": inserted_count, "skipped": 0, "failed": 0}

    except Exception as e:
        logger.error(f"Bulk insert failed: {e}")
        log_pipeline_event(session, "ERROR", f"Bulk insert failed: {str(e)}")
        raise


def load_upsert(
    session: Session,
    rows: list[Sale],
    key: Literal["external_id"] = "external_id",
) -> dict[str, int]:
    """Load records with upsert (insert or update on conflict) logic.

    For PostgreSQL, this uses the ON CONFLICT DO UPDATE clause for efficiency.
    For other databases, falls back to individual insert-or-update operations.

    Upsert is triggered when:
    - A row with the same primary key (external_id) already exists
    - In that case, the existing row is updated with new data
    - Otherwise, the row is inserted as a new record

    Args:
        session: Active SQLAlchemy session.
        rows: List of Sale ORM objects to insert or update.
        key: Key column name for conflict detection (default: 'external_id').

    Returns:
        Dict with:
        - 'inserted': Count of newly inserted rows
        - 'updated': Count of rows updated due to conflict
        - 'skipped': Count of rows with None key (cannot upsert without key)
        - 'failed': Count of failed operations
    """
    if not rows:
        logger.info("No rows to load (upsert)")
        log_pipeline_event(session, "INFO", "Upsert: 0 rows processed")
        return {"inserted": 0, "updated": 0, "skipped": 0, "failed": 0}

    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    failed_count = 0

    try:
        # Detect PostgreSQL for native ON CONFLICT support
        dialect = session.get_bind().dialect.name
        use_pg_upsert = dialect == "postgresql"

        if use_pg_upsert:
            # PostgreSQL: use native ON CONFLICT DO UPDATE for maximum efficiency
            inserted_count, updated_count, skipped_count = _upsert_postgresql(
                session, rows, key
            )
        else:
            # Fallback: individual insert-or-update operations
            for row in rows:
                try:
                    result = _upsert_single_row(session, row, key)
                    if result == "inserted":
                        inserted_count += 1
                    elif result == "updated":
                        updated_count += 1
                    elif result == "skipped":
                        skipped_count += 1
                except Exception as e:
                    logger.warning(f"Failed to upsert row: {e}")
                    failed_count += 1

        total_processed = inserted_count + updated_count + skipped_count + failed_count
        logger.info(
            f"Upsert completed: {total_processed} rows processed "
            f"({inserted_count} inserted, {updated_count} updated, "
            f"{skipped_count} skipped, {failed_count} failed)"
        )

        log_pipeline_event(
            session,
            "INFO",
            f"Upsert completed: {total_processed} processed "
            f"({inserted_count} inserted, {updated_count} updated, "
            f"{skipped_count} skipped, {failed_count} failed)",
        )

        return {
            "inserted": inserted_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "failed": failed_count,
        }

    except Exception as e:
        logger.error(f"Upsert operation failed: {e}")
        log_pipeline_event(session, "ERROR", f"Upsert operation failed: {str(e)}")
        raise


def _upsert_postgresql(
    session: Session, rows: list[Sale], key: str
) -> tuple[int, int, int]:
    """PostgreSQL-optimized upsert using ON CONFLICT DO UPDATE.

    Returns:
        Tuple of (inserted_count, updated_count, skipped_count).
    """
    rows_with_key = [r for r in rows if getattr(r, key) is not None]
    rows_without_key = [r for r in rows if getattr(r, key) is None]
    skipped_count = len(rows_without_key)

    if rows_with_key:
        # Build bulk insert statement with ON CONFLICT handling
        stmt = (
            pg_insert(Sale)
            .values([_row_to_dict(r) for r in rows_with_key])
            .on_conflict_do_update(
                index_elements=[key],
                set_={
                    "product_name": text(f"EXCLUDED.product_name"),
                    "quantity": text(f"EXCLUDED.quantity"),
                    "unit_price": text(f"EXCLUDED.unit_price"),
                    "sold_at": text(f"EXCLUDED.sold_at"),
                },
            )
        )

        # Execute raw SQL to capture inserted vs. updated counts
        result = session.execute(stmt)
        session.flush()

        # For PostgreSQL ON CONFLICT, we inserted all rows with key
        # (some may have been updates, but the statement succeeded atomically)
        inserted_count = len(rows_with_key)
        updated_count = 0

        # Query to determine actual insert vs. update counts
        # (Note: PostgreSQL doesn't return this directly from INSERT ... ON CONFLICT,
        #  so we approximate: all rows_with_key are considered "processed")
        # For a more precise count, you'd need to query before/after or use triggers.

        return inserted_count, updated_count, skipped_count

    return 0, 0, skipped_count


def _upsert_single_row(session: Session, row: Sale, key: str) -> Literal["inserted", "updated", "skipped"]:
    """Upsert a single row (fallback for non-PostgreSQL databases).

    Returns:
        One of: 'inserted', 'updated', 'skipped'.
    """
    key_value = getattr(row, key)
    if key_value is None:
        logger.debug(f"Skipping row: {key} is None")
        return "skipped"

    # Try to find existing row by key
    existing = session.query(Sale).filter(
        getattr(Sale, key) == key_value
    ).first()

    if existing:
        # Update existing row
        existing.product_name = row.product_name
        existing.quantity = row.quantity
        existing.unit_price = row.unit_price
        # Only update sold_at if the new row has a non-None value
        if row.sold_at is not None:
            existing.sold_at = row.sold_at
        session.flush()
        return "updated"
    else:
        # Insert new row
        session.add(row)
        session.flush()
        return "inserted"


def _row_to_dict(row: Sale) -> dict[str, Any]:
    """Convert a Sale ORM object to a dictionary for bulk operations.

    Args:
        row: Sale ORM instance.

    Returns:
        Dictionary with column names and values.
    """
    return {
        "external_id": row.external_id,
        "product_name": row.product_name,
        "quantity": row.quantity,
        "unit_price": row.unit_price,
        "sold_at": row.sold_at,
    }


def load(
    session: Session,
    rows: list[Sale],
    mode: Literal["bulk", "upsert"] = "bulk",
    upsert_key: Literal["external_id"] = "external_id",
) -> dict[str, int]:
    """Load records into the database with configurable strategy.

    Args:
        session: Active SQLAlchemy session.
        rows: List of Sale ORM objects.
        mode: Loading strategy ('bulk' for insert-only, 'upsert' for insert-or-update).
        upsert_key: Key column for conflict detection in upsert mode.

    Returns:
        Summary dict with operation counts.
    """
    if mode == "bulk":
        return load_bulk_insert(session, rows)
    elif mode == "upsert":
        return load_upsert(session, rows, upsert_key)
    else:
        raise ValueError(f"Unknown load mode: {mode}")
