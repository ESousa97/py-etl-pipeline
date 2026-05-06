"""Application entrypoint: bootstrap schema and execute the ETL pipeline."""

from src.database import get_session, init_db
from src.pipeline import run_pipeline


def main() -> None:
    """Create missing tables, open a session, run the pipeline, then close."""
    init_db()
    session = get_session()
    try:
        stats = run_pipeline(session)
        print(stats)
    finally:
        session.close()


if __name__ == "__main__":
    main()
