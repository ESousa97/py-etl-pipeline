"""GraphQL schema smoke tests (no HTTP server)."""

from __future__ import annotations

import pytest

pytest.importorskip("strawberry")

from py_etl_pipeline.graphql_server import schema


def test_graphql_health() -> None:
    result = schema.execute_sync("{ health }")
    assert result.errors is None
    assert result.data is not None
    assert result.data["health"] == "ok"


def test_graphql_etl_shape() -> None:
    result = schema.execute_sync("{ etl { loadBatchSize defaultLoadMode scheduledDefault } }")
    assert result.errors is None
    assert result.data is not None
    etl = result.data["etl"]
    assert etl["loadBatchSize"] >= 1
    assert etl["defaultLoadMode"] in ("bulk", "upsert")
    assert isinstance(etl["scheduledDefault"], bool)
