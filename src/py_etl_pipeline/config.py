"""Load environment variables and build the PostgreSQL connection URL."""

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Avoid letting a developer's local `.env` file interfere with unit tests.
# In production/CLI usage we still want `.env` to be loaded automatically.
if not os.getenv("PYTEST_CURRENT_TEST"):
    load_dotenv()


def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    user = os.getenv("POSTGRES_USER", "")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    db = os.getenv("POSTGRES_DB", "")

    if not all([user, password, db]):
        raise ValueError("Set DATABASE_URL or POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB.")

    safe_user = quote_plus(user)
    safe_password = quote_plus(password)
    return f"postgresql://{safe_user}:{safe_password}@{host}:{port}/{db}"


def load_batch_size() -> int:
    raw = os.getenv("LOAD_BATCH_SIZE", "500").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 500
    return max(1, n)
