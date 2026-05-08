# py-etl-pipeline

Minimal ETL pipeline: CSV → PostgreSQL via SQLAlchemy, with bulk insert, upsert, audit logging, retry, scheduling, and Docker Compose support.

## Features

- **Extract** — CSV via pandas with automatic column normalisation
- **Transform** — type coercion, defaults, row validation
- **Load** — bulk insert or PostgreSQL-native upsert (`ON CONFLICT DO UPDATE`)
- **Audit log** — every load operation written to a `logs` table
- **Resilience** — transient DB failures retried with tenacity (exponential backoff)
- **Scheduling** — optional recurring runs via the `schedule` library
- **Migrations** — Alembic with autogenerate against SQLAlchemy models
- **Docker** — `docker-compose.yml` with Postgres 16 + ETL container

## Quick Start

```bash
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env                             # then fill in DATABASE_URL
python main.py
```

The pipeline creates missing tables on first run and processes the CSV at `SALES_CSV_PATH`.

## Run Modes

```bash
# One-shot (default)
python main.py

# Upsert mode
$env:LOAD_MODE = "upsert"; python main.py

# Scheduled (runs immediately, then every 60 min)
$env:RUN_SCHEDULED = "true"; python main.py

# Docker Compose (Postgres + ETL)
docker compose up --build
```

## Project Layout

```
src/py_etl_pipeline/
  config.py        env-var parsing
  database.py      engine, session factory, schema bootstrap
  models.py        ORM models: Sale, LogEntry
  extract.py       CSV extraction
  transform.py     data validation and type coercion
  load.py          load strategy dispatcher
  load_bulk.py     bulk insert implementation
  load_upsert.py   upsert implementation (PG native + fallback)
  load_logging.py  audit log helper
  load_utils.py    shared helpers (chunks, dedup, key checks)
  pipeline.py      ETL orchestration
  retry.py         tenacity retry decorator

tests/             unit tests (SQLite) + PG integration (--run-pg)
scripts/           validate_load, diagnose_db, demo_load
migrations/        Alembic environment and versions
data/              sample CSV files
```

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/architecture.md](docs/architecture.md) | Component map, data flow, schema |
| [docs/configuration.md](docs/configuration.md) | All environment variables |
| [docs/development.md](docs/development.md) | Setup, tests, migrations, Docker, scripts |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |

## License

MIT — see [LICENSE](LICENSE).
