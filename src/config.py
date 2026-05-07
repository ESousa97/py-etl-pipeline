"""Load environment variables and build the PostgreSQL connection URL."""

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def database_url() -> str:
    """Return a SQLAlchemy-compatible PostgreSQL URL from the environment.

    ``DATABASE_URL`` takes precedence. Otherwise ``POSTGRES_*`` variables are
    assembled; user and password segments are URL-encoded.

    Returns:
        Connection URL string, e.g. ``postgresql://user:pass@host:port/db``.

    Raises:
        ValueError: If neither ``DATABASE_URL`` nor the minimum discrete vars are set.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    user = os.getenv("POSTGRES_USER", "")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "")

    if not all([user, password, db]):
        raise ValueError(
            "Set DATABASE_URL or POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB."
        )

    safe_user = quote_plus(user)
    safe_password = quote_plus(password)
    return f"postgresql://{safe_user}:{safe_password}@{host}:{port}/{db}"


def load_batch_size() -> int:
    """Maximum rows per load batch (bulk insert or PostgreSQL upsert).

    ``LOAD_BATCH_SIZE`` defaults to ``500``. Values below ``1`` are treated as
    ``1``. Invalid strings fall back to ``500``.
    """
    raw = os.getenv("LOAD_BATCH_SIZE", "500").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 500
    return max(1, n)
