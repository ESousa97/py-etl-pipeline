#!/usr/bin/env python
"""
Demo script: Load module showcase with practical examples.

This script demonstrates:
1. Bulk insert operations
2. Upsert (insert-or-update) operations
3. Log querying
4. Performance with large batches
"""

import logging
from datetime import datetime
from decimal import Decimal

import os
import sys

# Allow running from repository root without installing the package
ROOT = os.path.abspath(os.path.dirname(__file__))
SRC_PATH = os.path.join(ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from py_etl_pipeline.database import get_session, init_db
from py_etl_pipeline.load import load, log_pipeline_event
from py_etl_pipeline.models import LogEntry, Sale

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def demo_bulk_insert(session):
    """Demonstrate bulk insert performance."""
    print("\n" + "=" * 70)
    print("DEMO 1: Bulk Insert (1000 records)")
    print("=" * 70)

    sales = [
        Sale(
            external_id=f"bulk-{i:05d}",
            product_name=f"Product {i % 50}",
            quantity=(i % 20) + 1,
            unit_price=Decimal(f"{(i % 100) + 1}.99"),
        )
        for i in range(1000)
    ]

    result = load(session, sales, mode="bulk")
    session.commit()

    print(f"\nBulk Insert Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    # Verify
    count = session.query(Sale).count()
    print(f"\nTotal rows in database: {count}")


def demo_upsert_insert(session):
    """Demonstrate upsert with new records."""
    print("\n" + "=" * 70)
    print("DEMO 2: Upsert with New Records (500 records)")
    print("=" * 70)

    sales = [
        Sale(
            external_id=f"upsert-new-{i:05d}",
            product_name=f"New Product {i}",
            quantity=(i % 15) + 1,
            unit_price=Decimal(f"{(i % 50) * 2}.50"),
        )
        for i in range(500)
    ]

    result = load(session, sales, mode="upsert")
    session.commit()

    print(f"\nUpsert Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    count = session.query(Sale).count()
    print(f"\nTotal rows in database: {count}")


def demo_upsert_update(session):
    """Demonstrate upsert with existing records (updates)."""
    print("\n" + "=" * 70)
    print("DEMO 3: Upsert with Updates (50 records, 50 new)")
    print("=" * 70)

    # Mix of existing external_ids (from DEMO 2) and new ones
    sales = []

    # Update 50 existing records
    for i in range(50):
        sales.append(
            Sale(
                external_id=f"upsert-new-{i:05d}",
                product_name=f"UPDATED Product {i}",  # Changed
                quantity=99,  # Changed
                unit_price=Decimal("999.99"),  # Changed
            )
        )

    # Insert 50 new records
    for i in range(50, 100):
        sales.append(
            Sale(
                external_id=f"upsert-new-{i:05d}",
                product_name=f"New Product {i}",
                quantity=i % 10,
                unit_price=Decimal(f"{i}.00"),
            )
        )

    result = load(session, sales, mode="upsert")
    session.commit()

    print(f"\nUpsert Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    count = session.query(Sale).count()
    print(f"\nTotal rows in database: {count}")

    # Verify updates
    updated_product = session.query(Sale).filter_by(
        external_id="upsert-new-00000"
    ).first()
    if updated_product:
        print(f"\nVerify update - Product name: {updated_product.product_name}")


def demo_logging(session):
    """Demonstrate log querying."""
    print("\n" + "=" * 70)
    print("DEMO 4: Log Analysis")
    print("=" * 70)

    # Query logs
    logs = session.query(LogEntry).filter_by(source="pipeline.load").all()

    print(f"\nTotal load operations logged: {len(logs)}")
    print("\nRecent logs:")
    for log in logs[-5:]:
        print(f"  [{log.level}] {log.created_at.strftime('%H:%M:%S')}: {log.message}")

    # Count by level
    info_count = session.query(LogEntry).filter_by(level="INFO").count()
    error_count = session.query(LogEntry).filter_by(level="ERROR").count()
    print(f"\nLog Summary:")
    print(f"  INFO: {info_count}")
    print(f"  ERROR: {error_count}")


def demo_skip_no_key(session):
    """Demonstrate that records without external_id are skipped in upsert."""
    print("\n" + "=" * 70)
    print("DEMO 5: Upsert with Skipped Records (no external_id)")
    print("=" * 70)

    sales = []

    # Valid records with external_id
    for i in range(25):
        sales.append(
            Sale(
                external_id=f"skip-demo-{i:05d}",
                product_name=f"Valid Product {i}",
                quantity=1,
                unit_price=Decimal("10.00"),
            )
        )

    # Invalid records without external_id (will be skipped)
    for i in range(25):
        sales.append(
            Sale(
                external_id=None,  # No key - will be skipped
                product_name=f"Skipped Product {i}",
                quantity=1,
                unit_price=Decimal("5.00"),
            )
        )

    result = load(session, sales, mode="upsert")
    session.commit()

    print(f"\nUpsert Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    # Note: skipped records are NOT inserted
    count_with_key = session.query(Sale).filter(
        Sale.external_id.like("skip-demo-%")
    ).count()
    print(f"\nRecords with skip-demo-* pattern: {count_with_key}")


def demo_manual_logging(session):
    """Demonstrate manual logging."""
    print("\n" + "=" * 70)
    print("DEMO 6: Manual Logging")
    print("=" * 70)

    log_pipeline_event(
        session,
        "INFO",
        "Demo: Processed vendor ABC's monthly sales export (5000 records)",
        source="vendor_sync.abc",
    )

    log_pipeline_event(
        session,
        "WARNING",
        "Demo: 23 records skipped due to missing external_id",
        source="vendor_sync.abc",
    )

    session.flush()

    logs = session.query(LogEntry).filter_by(source="vendor_sync.abc").all()
    print(f"\nManual logs created: {len(logs)}")
    for log in logs:
        print(f"  [{log.level}] {log.message}")


def main():
    """Run all demos."""
    init_db()
    session = get_session()

    try:
        demo_bulk_insert(session)
        demo_upsert_insert(session)
        demo_upsert_update(session)
        demo_skip_no_key(session)
        demo_manual_logging(session)
        demo_logging(session)

        print("\n" + "=" * 70)
        print("FINAL SUMMARY")
        print("=" * 70)
        total_sales = session.query(Sale).count()
        total_logs = session.query(LogEntry).count()
        print(f"\nTotal Sales in DB: {total_sales}")
        print(f"Total Log Entries: {total_logs}")
        print("\nDemo completed successfully!")
        print("=" * 70 + "\n")

    finally:
        session.close()


if __name__ == "__main__":
    main()
