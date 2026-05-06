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

## Project layout

```
├── main.py              # CLI entrypoint
├── requirements.txt
├── .env.example         # Template (no secrets)
└── src/
    ├── config.py        # Environment → database URL
    ├── database.py      # Engine, session factory, schema bootstrap
    ├── models.py        # SQLAlchemy ORM models
    └── pipeline.py      # extract / transform / load stubs
```

## Conventions

- Docstrings and user-facing env docs are **English** (common open-source convention).
- Types follow **PEP 484** / **PEP 526**; SQLAlchemy 2 declarative style with `Mapped[]`.
- Database identifiers use **snake_case** table names (`sales`, `logs`).

## License

Specify your license here.
