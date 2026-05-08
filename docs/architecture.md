# Architecture

## Overview

The pipeline follows a classic **Extract → Transform → Load** pattern, with each stage in its own module. A thin orchestration layer (`pipeline.py`) wires the three stages and returns aggregated stats.

## Component Map

```
main.py                 ← CLI entrypoint (one-shot or scheduled)
└── pipeline.run_pipeline
    ├── extract.extract_sales    ← reads CSV via pandas
    ├── transform.transform_sales ← converts dicts to Sale ORM objects
    └── load.load                ← dispatches to bulk or upsert strategy
        ├── load_bulk.load_bulk_insert   ← SQLAlchemy bulk_save_objects
        └── load_upsert.load_upsert     ← ON CONFLICT (PG) or row-by-row fallback

Supporting modules:
  config.py       ← env-var parsing (DATABASE_URL, batch size, …)
  database.py     ← engine + session factory + schema bootstrap
  models.py       ← SQLAlchemy ORM: Sale, LogEntry
  load_logging.py ← writes LogEntry records to DB
  load_utils.py   ← shared helpers: chunking, dedup, key checks
  retry.py        ← tenacity exponential-backoff decorator
```

## Data Flow

```
CSV file
  │  pandas.read_csv + column normalisation
  ▼
list[dict]
  │  transform_sales: type coercion, defaults, skip invalid rows
  ▼
list[Sale]           (transient attribute: total_value = qty × price)
  │  load(): bulk_save_objects OR ON CONFLICT DO UPDATE
  ▼
PostgreSQL / SQLite   + LogEntry audit records
```

## Load Strategies

| Strategy | When to use | How it works |
|----------|-------------|--------------|
| `bulk`   | Initial loads, no duplicates | `bulk_save_objects` in batches — fastest |
| `upsert` | Incremental / idempotent runs | PG: `ON CONFLICT DO UPDATE`; others: query then insert/update |

The active strategy is selected at runtime via the `LOAD_MODE` env variable (or the `mode` argument to `load()`).

## Resilience

- **Retry**: `@retry_db` (tenacity) wraps the pipeline run and retries on `OperationalError` with exponential backoff.
- **Batch size**: Both strategies process rows in configurable batches (`LOAD_BATCH_SIZE`) to bound memory use.
- **Audit log**: Every load operation writes a `LogEntry` row (`level`, `message`, `source`, `created_at`).

## Database Schema

```
sales
  id           SERIAL PK
  external_id  VARCHAR(255) UNIQUE NULLABLE   ← upsert key
  product_name VARCHAR(255) NOT NULL
  quantity     INTEGER DEFAULT 1
  unit_price   NUMERIC(12,2) NOT NULL
  sold_at      TIMESTAMPTZ DEFAULT NOW()

logs
  id         SERIAL PK
  level      VARCHAR(16) INDEXED              ← INFO / WARNING / ERROR
  message    TEXT
  source     VARCHAR(128) NULLABLE
  created_at TIMESTAMPTZ DEFAULT NOW()
```

## Migrations

Schema is managed by **Alembic** with autogenerate. See [development.md](development.md#migrations).
