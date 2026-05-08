"""Load stage API (facade).

The implementation is split into small modules to keep each file easy to read:

- `load_bulk.py`: bulk insert strategy
- `load_upsert.py`: upsert strategy (PostgreSQL native + fallback)
- `load_logging.py`: DB-backed log helper
- `load_utils.py`: shared helpers (chunking, key handling, row mapping)
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session

from .load_bulk import load_bulk_insert
from .load_logging import log_pipeline_event
from .load_upsert import load_upsert
from .models import Sale


def load(
    session: Session,
    rows: list[Sale],
    mode: Literal["bulk", "upsert"] = "bulk",
    upsert_key: Literal["external_id", "id"] = "external_id",
) -> dict[str, int]:
    if mode == "bulk":
        return load_bulk_insert(session, rows)
    elif mode == "upsert":
        return load_upsert(session, rows, upsert_key)
    else:
        raise ValueError(f"Unknown load mode: {mode}")


__all__ = [
    "load",
    "load_bulk_insert",
    "load_upsert",
    "log_pipeline_event",
]
