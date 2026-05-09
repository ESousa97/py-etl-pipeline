"""Bulk insert strategy."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from .config import load_batch_size
from .load_logging import log_pipeline_event
from .load_utils import chunks
from .models import Sale

logger = logging.getLogger(__name__)


def load_bulk_insert(session: Session, rows: list[Sale]) -> dict[str, int]:
    if not rows:
        logger.info("No rows to load (bulk insert)")
        log_pipeline_event(session, "INFO", "Bulk insert: 0 rows processed")
        return {"inserted": 0, "skipped": 0, "failed": 0}

    batch_size = load_batch_size()
    inserted_total = 0

    try:
        for batch in chunks(rows, batch_size):
            session.bulk_save_objects(batch)
            session.flush()
            inserted_total += len(batch)

        logger.info(
            "Bulk insert: %s rows inserted in %s batch(es) (batch_size=%s)",
            inserted_total,
            (len(rows) + batch_size - 1) // batch_size,
            batch_size,
        )
        log_pipeline_event(
            session,
            "INFO",
            f"Bulk insert completed: {inserted_total} rows inserted",
        )
        return {"inserted": inserted_total, "skipped": 0, "failed": 0}
    except Exception as e:
        logger.error("Bulk insert failed: %s", e)
        log_pipeline_event(session, "ERROR", f"Bulk insert failed: {str(e)}")
        raise
