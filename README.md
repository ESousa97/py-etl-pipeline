# Python ETL Pipeline (PostgreSQL + SQLAlchemy)

Minimal ETL skeleton: declarative models, PostgreSQL via SQLAlchemy `create_engine`, automatic table creation, and credentials from environment variables (`python-dotenv`).

## Features

- **Extract**: Read from CSV files with automatic column normalization
- **Transform**: Convert, validate, and enrich raw data into ORM objects
- **Load**: Efficiently persist data with bulk inserts and upsert (insert-or-update) operations
- **Logging**: Comprehensive logging to database for audit trails
- **PostgreSQL Optimized**: Native `ON CONFLICT DO UPDATE` support for efficient upserts
- **Fallback Support**: Works with SQLite, MySQL, Oracle, and other SQLAlchemy-supported databases

## Requirements

- Python 3.10+
- PostgreSQL server reachable from this machine (or SQLite for testing)

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
| `LOAD_MODE` | Loading strategy: `bulk` (default) or `upsert` |
| `SQLALCHEMY_ECHO` | Set to `true` / `1` / `yes` to log SQL statements |
| `SALES_CSV_PATH` | Path to CSV file for extraction (optional) |

Credentials must stay in `.env` or your secret manager; `.env` is gitignored.

## Run

From the project root:

```bash
# Default: bulk insert mode
python main.py

# Or with upsert (insert-or-update) mode
LOAD_MODE=upsert python main.py
```

This ensures tables exist (`CREATE TABLE` only for missing objects) and runs the pipeline.

## Load Module

The **Load** stage implements high-performance data persistence with two strategies:

### Bulk Insert (Default)

Fast insertion of new records without duplicate handling:

```bash
LOAD_MODE=bulk python main.py
```

- Optimized for initial data loads
- ~10,000-100,000 rows/sec throughput
- Raises on constraint violations (duplicates)

### Upsert (Insert-or-Update)

Insert new records or update existing ones based on primary key:

```bash
LOAD_MODE=upsert python main.py
```

- **PostgreSQL**: Uses native `ON CONFLICT DO UPDATE` for atomic operations
- **Other DBs**: Falls back to row-by-row processing
- Skips records with missing keys (null / empty / NaN)
- Logs operation counts (inserted, updated, skipped, failed)

See [LOAD_MODULE.md](LOAD_MODULE.md) for complete documentation.

## Validate Bulk + Upsert (One Command)

To help users validate the load strategies, this repo includes a small, repeatable validation script.

### Quick validation (no PostgreSQL required)

Runs on a fresh local SQLite database and prints inserted/updated/skipped counts:

```bash
python scripts/validate_load.py
```

### Validate against PostgreSQL

If you want to validate against a real PostgreSQL, pass an explicit URL (recommended to use a throwaway database):

```powershell
.\scripts\validate_load.ps1 -DatabaseUrl "postgresql://user:pass@127.0.0.1:5432/data_py_validate"
```

### Why bulk may fail on the 2nd run

Bulk insert is **insert-only**. If you run the validator against the same database more than once, the first bulk step may fail with a unique-constraint error because the validation data uses fixed keys (e.g. `ext-1`).

Options:

- Use a fresh/throwaway database for validation (recommended)
- Or truncate the `sales` table before re-running:

```sql
TRUNCATE TABLE sales RESTART IDENTITY;
```

## CSV Input (Extract + Transform)

The default pipeline `extract()` reads a CSV file configured by the environment variable `SALES_CSV_PATH`.

- If `SALES_CSV_PATH` is **unset** or points to a missing file, the pipeline extracts **zero** rows (keeps the skeleton runnable by default).
- The extractor uses **pandas** to read the CSV and normalizes column names to lower-case, underscore-separated tokens (e.g. `Unit Price` → `unit_price`).

### Expected Columns (After Normalization)

`transform()` builds `Sale` ORM objects from the normalized rows. Supported inputs:

- `product_name` (required)
- `quantity` (optional, defaults to 1)
- `unit_price` (required)
- `sold_at` (optional; parsed to UTC datetime when present)
- `external_id` (optional; used as upsert key)

**Business rule**: `total_value = quantity * unit_price` is computed as a **transient attribute** on the `Sale` object (not persisted, since the table model does not include a column for it).

### Example CSV

```csv
Product Name,Quantity,Unit Price,Sold At,External ID
Laptop,2,1299.99,2026-05-01T10:30:00Z,ext-laptop-001
Mouse,5,29.99,2026-05-01T11:00:00Z,ext-mouse-001
Keyboard,3,89.99,2026-05-01T11:30:00Z,ext-keyboard-001
```

To use the demo data:

```bash
$env:SALES_CSV_PATH = "data/sales_demo.csv"
python main.py
```

## Demo Script

Run the interactive demo to see all load module features:

```bash
$env:DATABASE_URL = "sqlite:///demo.db"
python demo_load.py
```

This demonstrates:
- Bulk insert (1000 records)
- Upsert with new records
- Upsert with updates
- Log querying and analysis
- Skip handling for records without keys

## Project Layout

```
├── main.py              # CLI entrypoint
├── demo_load.py         # Interactive load module demonstration
├── requirements.txt
├── requirements-dev.txt # Adds pytest on top of runtime deps
├── pytest.ini           # Test discovery + `pg` marker registration
├── .env.example         # Template (no secrets)
├── LOAD_MODULE.md       # Load module documentation
├── data/
│   ├── sales_demo.csv   # Demo CSV data
│   └── sales_test.csv   # Test CSV data
├── src/
│   ├── config.py        # Environment → database URL
│   ├── database.py      # Engine, session factory, schema bootstrap
│   ├── models.py        # SQLAlchemy ORM models
│   ├── extract.py       # CSV extraction stage
│   ├── transform.py     # Data transformation and validation
│   ├── load.py          # Bulk insert and upsert operations
│   └── pipeline.py      # ETL orchestration
└── tests/
    ├── conftest.py             # Fixtures + `--run-pg` opt-in flag
    ├── test_config.py          # database_url() behavior
    ├── test_models.py          # ORM models against in-memory SQLite
    ├── test_load.py            # Load module (bulk insert and upsert)
    ├── test_pipeline.py        # ETL orchestration
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

Run only load module tests:

```bash
pytest tests/test_load.py -v
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

## Usage Examples

### Example 1: Simple Pipeline Run with Bulk Insert

```python
from py_etl_pipeline.database import get_session, init_db
from py_etl_pipeline.pipeline import run_pipeline

init_db()
session = get_session()
try:
    stats = run_pipeline(session, load_mode="bulk")
    print(f"Loaded {stats['inserted']} rows")
finally:
    session.close()
```

### Example 2: Upsert Mode with CSV

```bash
export DATABASE_URL="postgresql://user:pass@localhost/mydb"
export SALES_CSV_PATH="data/sales.csv"
export LOAD_MODE="upsert"
python main.py
```

### Example 3: Query Logs

```python
from py_etl_pipeline.models import LogEntry
from py_etl_pipeline.database import get_session

session = get_session()
logs = session.query(LogEntry).filter_by(source="pipeline.load").all()
for log in logs:
    print(f"[{log.level}] {log.message}")
```

## Performance

### Bulk Insert

- **Throughput**: ~10,000-100,000 rows/sec (varies by row size)
- **Best for**: Initial loads, no duplicate handling
- **Memory**: O(n) - all rows kept before flush

### Upsert

- **PostgreSQL**: Highly efficient with native `ON CONFLICT DO UPDATE`
- **Other DBs**: Falls back to row-by-row (slower)
- **Recommended batch size**: 5,000-10,000 rows per commit

For large datasets, process in batches and commit between batches for better performance and memory usage.

## Conventions

- Docstrings and user-facing env docs are **English** (common open-source convention).
- Types follow **PEP 484** / **PEP 526**; SQLAlchemy 2 declarative style with `Mapped[]`.
- Database identifiers use **snake_case** table names (`sales`, `logs`).

## License

Specify your license here.
