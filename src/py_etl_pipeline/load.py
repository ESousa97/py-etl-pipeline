"""Load stage: efficiently persist transformed records with bulk operations and upsert logic."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .config import load_batch_size
from .models import LogEntry, Sale

logger = logging.getLogger(__name__)


def log_pipeline_event(
    session: Session,
    level: str,
    message: str,
    source: str = "pipeline.load",
) -> None:
    entry = LogEntry(level=level, message=message, source=source)
    session.add(entry)


def _chunks(items: list[Sale], size: int) -> Iterator[list[Sale]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _dedupe_last_wins(rows: list[Sale], key: str) -> list[Sale]:
    by_key: dict[Any, Sale] = {}
    for r in rows:
        by_key[getattr(r, key)] = r
    return list(by_key.values())


def load_bulk_insert(session: Session, rows: list[Sale]) -> dict[str, int]:
    if not rows:
        logger.info("No rows to load (bulk insert)")
        log_pipeline_event(session, "INFO", "Bulk insert: 0 rows processed")
        return {"inserted": 0, "skipped": 0, "failed": 0}

    batch_size = load_batch_size()
    inserted_total = 0

    try:
        for batch in _chunks(rows, batch_size):
            session.bulk_save_objects(batch)
            session.flush()
            inserted_total += len(batch)

        logger.info(
            f"Bulk insert: {inserted_total} rows inserted in "
            f"{(len(rows) + batch_size - 1) // batch_size} batch(es) "
            f"(batch_size={batch_size})"
        )
        log_pipeline_event(
            session,
            "INFO",
            f"Bulk insert completed: {inserted_total} rows inserted",
        )
        return {"inserted": inserted_total, "skipped": 0, "failed": 0}

    except Exception as e:
        logger.error(f"Bulk insert failed: {e}")
        log_pipeline_event(session, "ERROR", f"Bulk insert failed: {str(e)}")
        raise


def load_upsert(
    session: Session,
    rows: list[Sale],
    key: Literal["external_id"] = "external_id",
) -> dict[str, int]:
    if not rows:
        logger.info("No rows to load (upsert)")
        log_pipeline_event(session, "INFO", "Upsert: 0 rows processed")
        return {"inserted": 0, "updated": 0, "skipped": 0, "failed": 0}

    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    failed_count = 0

    try:
        dialect = session.get_bind().dialect.name
        use_pg_upsert = dialect == "postgresql"
        batch_size = load_batch_size()

        if use_pg_upsert:
            inserted_count, updated_count, skipped_count = _upsert_postgresql(
                session, rows, key, batch_size
            )
        else:
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
    session: Session,
    rows: list[Sale],
    key: str,
    batch_size: int,
) -> tuple[int, int, int]:
    key_column = getattr(Sale, key)
    skipped_count = sum(1 for r in rows if getattr(r, key) is None)
    keyed_rows = [r for r in rows if getattr(r, key) is not None]

    inserted_total = 0
    updated_total = 0

    batches = (len(keyed_rows) + batch_size - 1) // batch_size if keyed_rows else 0

    for batch_idx, batch in enumerate(_chunks(keyed_rows, batch_size), start=1):
        batch_unique = _dedupe_last_wins(batch, key)
        keys = [getattr(r, key) for r in batch_unique]

        existing = session.scalars(select(key_column).where(key_column.in_(keys))).all()
        existing_set = set(existing)

        batch_inserted = 0
        batch_updated = 0
        for r in batch_unique:
            k = getattr(r, key)
            if k in existing_set:
                batch_updated += 1
            else:
                batch_inserted += 1

        inserted_total += batch_inserted
        updated_total += batch_updated

        stmt = pg_insert(Sale).values([_row_to_dict(r) for r in batch_unique])
        stmt = stmt.on_conflict_do_update(
            index_elements=[key],
            set_={
                "product_name": stmt.excluded.product_name,
                "quantity": stmt.excluded.quantity,
                "unit_price": stmt.excluded.unit_price,
                "sold_at": stmt.excluded.sold_at,
            },
        )
        session.execute(stmt)
        session.flush()

        logger.debug(
            "Upsert batch %s/%s: keys=%s inserted=%s updated=%s",
            batch_idx,
            batches or 1,
            len(batch_unique),
            batch_inserted,
            batch_updated,
        )

    return inserted_total, updated_total, skipped_count


def _upsert_single_row(session: Session, row: Sale, key: str) -> Literal["inserted", "updated", "skipped"]:
    key_value = getattr(row, key)
    if key_value is None:
        logger.debug("Skipping row: %s is None", key)
        return "skipped"

    existing = session.query(Sale).filter(getattr(Sale, key) == key_value).first()

    if existing:
        existing.product_name = row.product_name
        existing.quantity = row.quantity
        existing.unit_price = row.unit_price
        if row.sold_at is not None:
            existing.sold_at = row.sold_at
        session.flush()
        return "updated"

    session.add(row)
    session.flush()
    return "inserted"


def _row_to_dict(row: Sale) -> dict[str, Any]:
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
    if mode == "bulk":
        return load_bulk_insert(session, rows)
    elif mode == "upsert":
        return load_upsert(session, rows, upsert_key)
    else:
        raise ValueError(f"Unknown load mode: {mode}")
