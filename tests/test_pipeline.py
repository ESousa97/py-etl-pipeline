"""Tests for the ETL stages and orchestrator in `src.pipeline`."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest
from sqlalchemy.orm import Session

import src.pipeline as pipeline


def test_run_pipeline_stub_returns_zero_counts(session: Session) -> None:
    assert pipeline.run_pipeline(session) == {"extracted": 0, "loaded": 0}


def test_run_pipeline_wires_extract_transform_load(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = [{"a": 1}, {"a": 2}, {"a": 3}]
    transformed = [{"a": r["a"] * 10} for r in raw]
    calls: dict[str, Any] = {}

    def fake_extract(s: Session) -> Iterable[dict[str, Any]]:
        calls["extract_session_is_test_session"] = s is session
        return iter(raw)

    def fake_transform(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        calls["transform_input"] = list(rows)
        return transformed

    def fake_load(s: Session, rows: list[dict[str, Any]]) -> int:
        calls["load_session_is_test_session"] = s is session
        calls["load_input"] = rows
        return len(rows)

    monkeypatch.setattr(pipeline, "extract", fake_extract)
    monkeypatch.setattr(pipeline, "transform", fake_transform)
    monkeypatch.setattr(pipeline, "load", fake_load)

    result = pipeline.run_pipeline(session)

    assert calls["extract_session_is_test_session"] is True
    assert calls["transform_input"] == raw
    assert calls["load_session_is_test_session"] is True
    assert calls["load_input"] == transformed
    assert result == {"extracted": 3, "loaded": 3}
