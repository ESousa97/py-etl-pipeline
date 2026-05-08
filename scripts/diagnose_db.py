from __future__ import annotations

import os
from urllib.parse import urlparse

from dotenv import load_dotenv


def _mask(s: str | None) -> str:
    if not s:
        return "∅"
    if len(s) <= 2:
        return "*" * len(s)
    return s[0] + ("*" * (len(s) - 2)) + s[-1]


def main() -> int:
    load_dotenv()

    db_url = os.getenv("DATABASE_URL")
    print("DATABASE_URL:", db_url or "∅")
    print("POSTGRES_USER:", os.getenv("POSTGRES_USER") or "∅")
    print("POSTGRES_PASSWORD:", _mask(os.getenv("POSTGRES_PASSWORD")))
    print("POSTGRES_HOST:", os.getenv("POSTGRES_HOST") or "∅")
    print("POSTGRES_PORT:", os.getenv("POSTGRES_PORT") or "∅")
    print("POSTGRES_DB:", os.getenv("POSTGRES_DB") or "∅")

    if not db_url:
        print("\nSet DATABASE_URL in .env to run connection tests.")
        return 2

    p = urlparse(db_url)
    dbname = (p.path or "").lstrip("/") or "postgres"
    user = p.username or "postgres"
    password = p.password or ""
    port = p.port or 5432

    try:
        import psycopg2  # type: ignore
    except Exception as e:
        print("\npsycopg2 import failed:", repr(e))
        return 3

    def try_connect(host: str) -> None:
        print(f"\nTrying host={host!r} port={port} user={user!r} dbname={dbname!r}")
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=dbname,
                connect_timeout=3,
            )
            conn.close()
            print("OK")
        except Exception as e:
            print("FAILED:", type(e).__name__, str(e).strip())

    try_connect(p.hostname or "localhost")
    try_connect("127.0.0.1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

