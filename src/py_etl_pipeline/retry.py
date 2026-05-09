"""Retry helpers for transient DB failures."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy.exc import OperationalError as SAOperationalError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

F = TypeVar("F", bound=Callable[..., Any])


def _attempts() -> int:
    raw = os.getenv("DB_RETRY_ATTEMPTS", "10").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 10
    return max(1, n)


def _base_delay() -> float:
    raw = os.getenv("DB_RETRY_BASE_DELAY_SECONDS", "0.5").strip()
    try:
        x = float(raw)
    except ValueError:
        x = 0.5
    return max(0.0, x)


def _max_delay() -> float:
    raw = os.getenv("DB_RETRY_MAX_DELAY_SECONDS", "10").strip()
    try:
        x = float(raw)
    except ValueError:
        x = 10.0
    return max(0.0, x)


def retry_db(fn: F) -> F:
    """Retry a function on transient DB connectivity failures.

    Retries on SQLAlchemy OperationalError (covers psycopg2 OperationalError).
    """

    return retry(
        reraise=True,
        retry=retry_if_exception_type(SAOperationalError),
        stop=stop_after_attempt(_attempts()),
        wait=wait_exponential(multiplier=_base_delay(), min=_base_delay(), max=_max_delay()),
    )(fn)  # type: ignore[return-value]
