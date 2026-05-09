"""Upsert strategy (insert-or-update)."""

from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .config import load_batch_size
from .load_logging import log_pipeline_event
from .load_utils import chunks, dedupe_last_wins, is_missing_key, row_to_dict
from .models import Sale

logger = logging.getLogger(__name__)


def load_upsert(
    session: Session,
    rows: list[Sale],
    key: Literal["external_id", "id"] = "external_id",
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
                    logger.warning("Failed to upsert row: %s", e)
                    failed_count += 1

        total_processed = inserted_count + updated_count + skipped_count + failed_count
        logger.info(
            "Upsert completed: %s rows processed (%s inserted, %s updated, %s skipped, %s failed)",
            total_processed,
            inserted_count,
            updated_count,
            skipped_count,
            failed_count,
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
        logger.error("Upsert operation failed: %s", e)
        log_pipeline_event(session, "ERROR", f"Upsert operation failed: {str(e)}")
        raise


def _upsert_postgresql(
    session: Session,
    rows: list[Sale],
    key: str,
    batch_size: int,
) -> tuple[int, int, int]:
    key_column = getattr(Sale, key)
    skipped_count = sum(1 for r in rows if is_missing_key(getattr(r, key)))
    keyed_rows = [r for r in rows if not is_missing_key(getattr(r, key))]

    inserted_total = 0
    updated_total = 0

    batches = (len(keyed_rows) + batch_size - 1) // batch_size if keyed_rows else 0

    for batch_idx, batch in enumerate(chunks(keyed_rows, batch_size), start=1):
        batch_unique = dedupe_last_wins(batch, key)
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

        stmt = pg_insert(Sale).values([row_to_dict(r) for r in batch_unique])
        stmt = stmt.on_conflict_do_update(
            index_elements=[key_column],
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


def _upsert_single_row(
    session: Session, row: Sale, key: str
) -> Literal["inserted", "updated", "skipped"]:
    key_value = getattr(row, key)
    if is_missing_key(key_value):
        logger.debug("Skipping row: %s is missing", key)
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
