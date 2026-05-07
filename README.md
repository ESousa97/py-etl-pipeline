# Python ETL Pipeline (PostgreSQL + SQLAlchemy)

Minimal ETL skeleton: declarative models, PostgreSQL via SQLAlchemy `create_engine`, automatic table creation, and credentials from environment variables (`python-dotenv`).

## Requirements

- Python 3.10+
- PostgreSQL server reachable from this machine

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
# Copy template → .env, then edit secrets (never commit .env)
# Windows PowerShell: Copy-Item .env.example .env
# Unix shell:        cp .env.example .env
```

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Full PostgreSQL URL (preferred). Example: `postgresql://user:pass@host:5432/dbname` |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Used only if `DATABASE_URL` is unset |
| `POSTGRES_HOST` | Default: `localhost` |
| `POSTGRES_PORT` | Default: `5432` |
| `SQLALCHEMY_ECHO` | Set to `true` / `1` / `yes` to log SQL statements |

Credentials must stay in `.env` or your secret manager; `.env` is gitignored.

## Run

From the project root:

```bash
python main.py
```

This ensures tables exist (`CREATE TABLE` only for missing objects) and runs the pipeline stub.

## CSV input (extract + transform)

The default pipeline `extract()` reads a CSV file configured by the environment variable `SALES_CSV_PATH`.

- If `SALES_CSV_PATH` is **unset** or points to a missing file, the pipeline extracts **zero** rows (keeps the skeleton runnable by default).
- The extractor uses **pandas** to read the CSV and normalizes column names to lower-case, underscore-separated tokens (e.g. `Unit Price` → `unit_price`).

### Expected columns (after normalization)

`transform()` builds `Sale` ORM objects from the normalized rows. Supported inputs:

- `product_name` (required)
- `quantity` (optional, defaults to 1)
- `unit_price` (required)
- `sold_at` (optional; parsed to UTC datetime when present)
- `external_id` (optional)

Business rule: `total_value = quantity * unit_price` is computed as a **transient attribute** on the `Sale` object (not persisted, since the table model does not include a column for it).

## Project layout

```
├── main.py              # CLI entrypoint
├── requirements.txt
├── requirements-dev.txt # Adds pytest on top of runtime deps
├── pytest.ini           # Test discovery + `pg` marker registration
├── .env.example         # Template (no secrets)
├── src/
│   ├── config.py        # Environment → database URL
│   ├── database.py      # Engine, session factory, schema bootstrap
│   ├── models.py        # SQLAlchemy ORM models
│   └── pipeline.py      # extract / transform / load stubs
└── tests/
    ├── conftest.py             # Fixtures + `--run-pg` opt-in flag
    ├── test_config.py          # database_url() behavior
    ├── test_models.py          # ORM models against in-memory SQLite
    ├── test_pipeline.py        # Stub + extract/transform/load wiring
    └── test_pg_integration.py  # Real PostgreSQL (run with `--run-pg`)
```

## Tests

Install the dev dependencies once:

```bash
pip install -r requirements-dev.txt
```

Default suite (in-memory SQLite, no external services):

```bash
pytest
```

Integration suite against a real PostgreSQL — set `DATABASE_URL` first, then opt in with `--run-pg`:

```bash
# Example: throwaway Postgres in Docker
docker run --name etl-pg -e POSTGRES_USER=etl -e POSTGRES_PASSWORD=etl -e POSTGRES_DB=etl_db -p 5432:5432 -d postgres:16

# Windows PowerShell
$env:DATABASE_URL = "postgresql://etl:etl@localhost:5432/etl_db"
pytest --run-pg

# Unix shell
DATABASE_URL=postgresql://etl:etl@localhost:5432/etl_db pytest --run-pg
```

`@pytest.mark.pg` tests are skipped without `--run-pg` and use a transaction-rollback fixture, so committed rows are discarded on teardown.

## Conventions

- Docstrings and user-facing env docs are **English** (common open-source convention).
- Types follow **PEP 484** / **PEP 526**; SQLAlchemy 2 declarative style with `Mapped[]`.
- Database identifiers use **snake_case** table names (`sales`, `logs`).

## License

Specify your license here.
