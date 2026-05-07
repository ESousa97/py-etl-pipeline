"""Tests for `src.config.database_url`."""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip DB-related env vars so each test starts from a known baseline."""
    for var in (
        "DATABASE_URL",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "LOAD_BATCH_SIZE",
    ):
        monkeypatch.delenv(var, raising=False)


def _reload_config():
    import py_etl_pipeline.config as config

    return importlib.reload(config)


def test_uses_database_url_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host:5432/db")
    assert _reload_config().database_url() == "postgresql://u:p@host:5432/db"


def test_builds_from_postgres_vars_with_url_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTGRES_USER", "u@1")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p ss")
    monkeypatch.setenv("POSTGRES_HOST", "h")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    monkeypatch.setenv("POSTGRES_DB", "db")
    assert _reload_config().database_url() == "postgresql://u%401:p+ss@h:6543/db"


def test_uses_defaults_for_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    monkeypatch.setenv("POSTGRES_DB", "db")
    assert _reload_config().database_url() == "postgresql://u:p@localhost:5432/db"


def test_raises_when_required_vars_missing() -> None:
    with pytest.raises(ValueError):
        _reload_config().database_url()


def test_load_batch_size_defaults_to_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOAD_BATCH_SIZE", raising=False)
    assert _reload_config().load_batch_size() == 500


def test_load_batch_size_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOAD_BATCH_SIZE", "100")
    assert _reload_config().load_batch_size() == 100


def test_load_batch_size_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOAD_BATCH_SIZE", "not-a-number")
    assert _reload_config().load_batch_size() == 500


def test_load_batch_size_minimum_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOAD_BATCH_SIZE", "0")
    assert _reload_config().load_batch_size() == 1
