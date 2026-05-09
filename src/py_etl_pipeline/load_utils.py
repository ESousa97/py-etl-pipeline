"""Shared helper utilities for load strategies."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .models import Sale


def is_missing_key(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    # pandas/numpy may surface missing strings as NaN (float).
    return isinstance(value, float) and value != value  # NaN


def chunks(items: list[Sale], size: int) -> Iterator[list[Sale]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def dedupe_last_wins(rows: list[Sale], key: str) -> list[Sale]:
    by_key: dict[Any, Sale] = {}
    for r in rows:
        k = getattr(r, key)
        if is_missing_key(k):
            continue
        by_key[k] = r
    return list(by_key.values())


def row_to_dict(row: Sale) -> dict[str, Any]:
    out: dict[str, Any] = {
        "external_id": row.external_id,
        "product_name": row.product_name,
        "quantity": row.quantity,
        "unit_price": row.unit_price,
        "sold_at": row.sold_at,
    }
    # Support upsert by primary key when upstream provides it (rare, but useful).
    if getattr(row, "id", None) is not None:
        out["id"] = row.id
    return out
