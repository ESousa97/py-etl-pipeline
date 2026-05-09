"""Extraction stage: load raw rows from a CSV file via pandas."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from typing import Any

import pandas as pd

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_column_name(name: str) -> str:
    s = str(name).strip().lower()
    s = _NON_ALNUM.sub("_", s)
    s = s.strip("_")
    return s


def extract_csv(path: str) -> Iterable[dict[str, Any]]:
    df = pd.read_csv(path)
    df = df.rename(columns={c: normalize_column_name(c) for c in df.columns})
    df = df.where(pd.notna(df), None)
    return df.to_dict(orient="records")


def extract_sales(session: Any) -> Iterable[dict[str, Any]]:
    _ = session
    path = os.getenv("SALES_CSV_PATH", "").strip()
    if not path:
        return []
    if not os.path.exists(path):
        return []
    return extract_csv(path)
