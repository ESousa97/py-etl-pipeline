"""Transformation stage: normalize types and build ORM objects."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from .models import Sale


def _to_int(value: Any, *, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        ts = pd.to_datetime(value, utc=True, errors="coerce")
    except Exception:
        return None
    if pd.isna(ts):
        return None
    return ts.to_pydatetime()


def transform_sales(rows: list[dict[str, Any]]) -> list[Sale]:
    out: list[Sale] = []

    for r in rows:
        product_name = (r.get("product_name") or r.get("product") or "").strip()
        if not product_name:
            continue

        qty = _to_int(r.get("quantity"), default=1)
        if qty is None:
            qty = 1

        unit_price = _to_decimal(r.get("unit_price") or r.get("price"))
        if unit_price is None:
            continue

        sold_at = _to_datetime(r.get("sold_at") or r.get("soldat") or r.get("date"))

        sale = Sale(
            external_id=(r.get("external_id") or r.get("id") or None),
            product_name=product_name,
            quantity=qty,
            unit_price=unit_price,
        )
        if sold_at is not None:
            sale.sold_at = sold_at

        sale.total_value = unit_price * Decimal(qty)  # type: ignore[attr-defined]

        out.append(sale)

    return out
