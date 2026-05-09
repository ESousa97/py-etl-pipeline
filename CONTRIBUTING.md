# Contributing

Thanks for your interest in contributing!

## Setup

```bash
python -m venv .venv
pip install -r requirements.txt
```

## Running tests

```bash
pytest -q
```

PostgreSQL integration tests (opt-in):

```bash
pytest --run-pg
```

## Code style

- Run `ruff check .` and `ruff format .` before opening a pull request (CI enforces both).
- Keep modules small and focused (prefer < 300 lines where reasonable).
- Keep public APIs stable (avoid breaking imports used by `main.py`, scripts, and tests).
- Prefer readable names and small functions over cleverness.

## Migrations

If you change models in `src/py_etl_pipeline/models.py`:

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

## Pull requests

- Include a clear summary and test plan.
- If behavior changes, add or update tests.

