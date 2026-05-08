# Configuration Reference

All settings are read from environment variables. Copy `.env.example` to `.env` and fill in your values — `.env` is gitignored and must never be committed.

## Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes* | — | Full connection URL. Example: `postgresql://user:pass@localhost:5432/mydb` |
| `POSTGRES_USER` | Yes* | — | Used only when `DATABASE_URL` is unset |
| `POSTGRES_PASSWORD` | Yes* | — | Used only when `DATABASE_URL` is unset |
| `POSTGRES_DB` | Yes* | — | Used only when `DATABASE_URL` is unset |
| `POSTGRES_HOST` | No | `localhost` | Used only when `DATABASE_URL` is unset |
| `POSTGRES_PORT` | No | `5432` | Used only when `DATABASE_URL` is unset |

\* Either `DATABASE_URL` **or** the full set of `POSTGRES_*` variables is required.

## Pipeline behaviour

| Variable | Default | Description |
|----------|---------|-------------|
| `SALES_CSV_PATH` | — | Path to the CSV file to extract. If unset or missing, the pipeline runs with zero rows. |
| `LOAD_MODE` | `bulk` | Loading strategy: `bulk` or `upsert` |
| `LOAD_BATCH_SIZE` | `500` | Rows processed per database batch. Min: 1. |

## Scheduling

| Variable | Default | Description |
|----------|---------|-------------|
| `RUN_SCHEDULED` | — | Set to `true` / `1` / `yes` to run on a repeating schedule instead of once |
| `SCHEDULE_INTERVAL_MINUTES` | `60` | Interval between scheduled runs |

## Retry (tenacity)

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_RETRY_ATTEMPTS` | `10` | Maximum retries on `OperationalError` |
| `DB_RETRY_BASE_DELAY_SECONDS` | `0.5` | Initial backoff delay |
| `DB_RETRY_MAX_DELAY_SECONDS` | `10` | Maximum backoff delay |

## Debugging

| Variable | Default | Description |
|----------|---------|-------------|
| `SQLALCHEMY_ECHO` | — | Set to `true` / `1` / `yes` to print all SQL statements |
| `VALIDATE_FORCE_SQLITE` | — | Forces `scripts/validate_load.py` to use SQLite even when `DATABASE_URL` is set |
