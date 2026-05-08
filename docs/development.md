# Development Guide

## Local Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements-dev.txt   # includes pytest and alembic
cp .env.example .env                  # then edit .env with your credentials
```

## Running the Pipeline

```bash
# One-shot, bulk mode (default)
python main.py

# One-shot, upsert mode
$env:LOAD_MODE = "upsert"             # PowerShell
python main.py

# Scheduled (runs immediately, then every 60 minutes)
$env:RUN_SCHEDULED = "true"
python main.py
```

## CSV Input

Set `SALES_CSV_PATH` to point at a CSV file. The extractor normalises column names
(e.g. `Unit Price` → `unit_price`) so header casing doesn't matter.

Supported columns (after normalisation):

| Column | Required | Notes |
|--------|----------|-------|
| `product_name` | Yes | |
| `unit_price` | Yes | |
| `quantity` | No | Defaults to 1 |
| `sold_at` | No | Parsed to UTC datetime |
| `external_id` | No | Used as upsert key |

Example CSV:

```csv
Product Name,Quantity,Unit Price,Sold At,External ID
Laptop,2,1299.99,2026-05-01T10:30:00Z,ext-001
Mouse,5,29.99,2026-05-01T11:00:00Z,ext-002
```

## Tests

```bash
# Default suite — uses in-memory SQLite, no live DB required
pytest

# Verbose with failure summary
pytest -v -ra

# Single module
pytest tests/test_config.py -v
```

### PostgreSQL integration tests

Tests marked `@pytest.mark.pg` require a live Postgres instance. Opt in with `--run-pg`:

```bash
# Start a throwaway Postgres
docker run --name etl-pg \
  -e POSTGRES_USER=etl -e POSTGRES_PASSWORD=etl -e POSTGRES_DB=etl_db \
  -p 5432:5432 -d postgres:16

$env:DATABASE_URL = "postgresql://etl:etl@localhost:5432/etl_db"
pytest --run-pg
```

## Migrations (Alembic)

```bash
# Apply all pending migrations
alembic upgrade head

# Generate a new migration after changing models.py
alembic upgrade head
alembic revision --autogenerate -m "describe change"

# Roll back one migration
alembic downgrade -1

# Point at a specific database for a single command
alembic -x url=postgresql://user:pass@localhost:5432/mydb upgrade head
```

## Docker Compose

Brings up Postgres 16 + the ETL container:

```bash
docker compose up --build
```

- **`db`**: Postgres on host port `5433` → container `5432`. Credentials: `postgres`/`admin`, database `data-py`.
- **`etl`**: Builds from `Dockerfile`, mounts `./data` read-only, runs in scheduled mode (every 60 minutes).
- The ETL container starts only after Postgres passes its `pg_isready` healthcheck.

One-off run against the Compose DB:

```bash
LOAD_MODE=upsert docker compose run --rm -e LOAD_MODE=upsert etl python main.py
```

## Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/validate_load.py` | End-to-end smoke test: bulk + upsert against generated CSVs. Uses SQLite by default. |
| `scripts/validate_load.ps1` | PowerShell wrapper that forwards `-DatabaseUrl` to the Python script. |
| `scripts/diagnose_db.py` | Prints effective DB env (masked password) and tests TCP connectivity. |
| `scripts/demo_load.py` | Interactive demo: bulk insert, upsert, logging. Run with `DATABASE_URL=sqlite:///demo.db`. |

Run from the repo root:

```bash
python scripts/validate_load.py
python scripts/diagnose_db.py
python scripts/demo_load.py
```

## Code Conventions

- Modules stay under **300 lines** — split rather than grow.
- Type annotations follow **PEP 484**; SQLAlchemy 2 `Mapped[]` style.
- Database identifiers use **snake_case** (`sales`, `logs`).
- No comments unless the *why* is non-obvious.
