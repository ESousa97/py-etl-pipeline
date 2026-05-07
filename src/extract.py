"""Extraction stage: load raw rows from a CSV file via pandas."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from typing import Any

import pandas as pd


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_column_name(name: str) -> str:
    """Normalize column names to snake_case-ish ASCII.

    Examples:
        "Product Name" -> "product_name"
        " soldAt " -> "soldat"
        "UNIT-PRICE" -> "unit_price"
    """
    s = str(name).strip().lower()
    s = _NON_ALNUM.sub("_", s)
    s = s.strip("_")
    return s


def extract_csv(path: str) -> Iterable[dict[str, Any]]:
    """Read a CSV from `path` and yield raw dictionaries with normalized columns."""
    df = pd.read_csv(path)
    df = df.rename(columns={c: normalize_column_name(c) for c in df.columns})
    # NaN -> None for downstream normalization/validation
    df = df.where(pd.notna(df), None)
    return df.to_dict(orient="records")


def extract_sales(session: Any) -> Iterable[dict[str, Any]]:
    """Default extractor used by the pipeline.

    Reads `SALES_CSV_PATH` from the environment. If unset or the file does not
    exist, returns an empty iterable (keeping the skeleton runnable by default).
    """
    _ = session
    path = os.getenv("SALES_CSV_PATH", "").strip()
    if not path:
        return []
    if not os.path.exists(path):
        return []
    return extract_csv(path)

