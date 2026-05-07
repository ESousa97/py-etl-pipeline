"""Application entrypoint: bootstrap schema and execute the ETL pipeline."""

import logging
import os
from typing import Literal

from src.database import get_session, init_db
from src.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)


def main(load_mode: Literal["bulk", "upsert"] = "bulk") -> None:
    """Create missing tables, open a session, run the pipeline, then close.

    Args:
        load_mode: Loading strategy ('bulk' for insert-only, 'upsert' for insert-or-update).
                  Controlled by environment variable LOAD_MODE (default: 'bulk').
    """
    # Allow environment variable override
    load_mode_env = os.getenv("LOAD_MODE", "").strip().lower()
    if load_mode_env in ("bulk", "upsert"):
        load_mode = load_mode_env  # type: ignore

    init_db()
    session = get_session()
    try:
        print(f"\n{'='*60}")
        print(f"Starting ETL Pipeline (load_mode={load_mode})")
        print(f"{'='*60}\n")
        
        stats = run_pipeline(session, load_mode=load_mode)
        
        print(f"\n{'='*60}")
        print("Pipeline Summary:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print(f"{'='*60}\n")
    finally:
        session.close()


if __name__ == "__main__":
    main()
