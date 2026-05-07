# Load Module Documentation

## Overview

The `src/load.py` module implements the **Load (L)** stage of the ETL pipeline. It efficiently persists transformed records into the database with support for:

- **Bulk Inserts**: High-performance insertion of multiple records at once
- **Upsert Operations**: Insert-or-update logic based on primary keys (external_id)
- **Detailed Logging**: Comprehensive logging of operation counts and results
- **Database Compatibility**: Optimized for PostgreSQL with fallback support for other databases

## Key Features

### 1. Bulk Insert Mode

The `load_bulk_insert()` function is optimized for scenarios where you need to insert many new records without handling duplicates:

```python
from src.load import load_bulk_insert
from src.models import Sale
from decimal import Decimal

sales = [
    Sale(
        external_id="ext-001",
        product_name="Widget",
        quantity=5,
        unit_price=Decimal("10.50"),
    ),
    Sale(
        external_id="ext-002",
        product_name="Gadget",
        quantity=3,
        unit_price=Decimal("25.99"),
    ),
]

result = load_bulk_insert(session, sales)
# result: {"inserted": 2, "skipped": 0, "failed": 0}
```

**Performance Characteristics:**
- O(n) time complexity for n records
- Uses SQLAlchemy's `add_all()` for efficient bulk operations
- No conflict detection or merge logic
- Best for initial data loads or when duplicates are guaranteed not to occur

### 2. Upsert Mode

The `load_upsert()` function implements "insert or update" logic. If a record with the same `external_id` already exists, it updates the existing record instead of trying to insert a duplicate.

```python
from src.load import load_upsert

# New records (some may match existing external_ids)
sales = [
    Sale(external_id="ext-001", product_name="Updated Widget", ...),
    Sale(external_id="ext-new", product_name="New Product", ...),
]

result = load_upsert(session, sales)
# result: {"inserted": 1, "updated": 1, "skipped": 0, "failed": 0}
```

**Features:**
- **PostgreSQL Optimization**: Uses native `ON CONFLICT DO UPDATE` clause for atomic, efficient operations
- **Fallback for Other Databases**: Individual row processing with query-first approach
- **Skip Handling**: Rows with None `external_id` are skipped (upsert key required)
- **Error Handling**: Failed rows are counted separately and logged

### 3. Logging Integration

All load operations automatically log detailed information:

```python
# Logged to the database 'logs' table
# Example log entry:
# {
#   "level": "INFO",
#   "message": "Bulk insert completed: 1000 rows inserted",
#   "source": "pipeline.load",
#   "created_at": "2026-05-07T12:00:00Z"
# }
```

You can query logs later:

```python
from src.models import LogEntry

entries = session.query(LogEntry).filter_by(source="pipeline.load").all()
for entry in entries:
    print(f"[{entry.level}] {entry.message}")
```

## API Reference

### `load_bulk_insert(session, rows) -> dict[str, int]`

Inserts multiple rows using bulk operations.

**Parameters:**
- `session` (Session): Active SQLAlchemy session
- `rows` (list[Sale]): List of Sale ORM objects to insert

**Returns:**
```python
{
    "inserted": int,  # Number of successfully inserted rows
    "skipped": int,   # Always 0 for bulk insert
    "failed": int,    # Always 0 for bulk insert (raises on error)
}
```

**Raises:**
- `Exception`: On database errors (e.g., constraint violations)

### `load_upsert(session, rows, key="external_id") -> dict[str, int]`

Inserts or updates rows based on conflict detection.

**Parameters:**
- `session` (Session): Active SQLAlchemy session
- `rows` (list[Sale]): List of Sale ORM objects
- `key` (str): Column name for conflict detection (default: "external_id")

**Returns:**
```python
{
    "inserted": int,   # New rows inserted
    "updated": int,    # Existing rows updated
    "skipped": int,    # Rows skipped (e.g., None key)
    "failed": int,     # Rows that failed to process
}
```

**Raises:**
- `Exception`: On database errors

### `load(session, rows, mode="bulk", upsert_key="external_id") -> dict[str, int]`

Unified interface for loading with configurable strategy.

**Parameters:**
- `session` (Session): Active SQLAlchemy session
- `rows` (list[Sale]): List of Sale ORM objects
- `mode` (str): "bulk" or "upsert"
- `upsert_key` (str): Key for upsert mode (default: "external_id")

**Returns:**
- Same as `load_bulk_insert()` or `load_upsert()` depending on mode

**Example:**
```python
from src.load import load
import os

load_mode = os.getenv("LOAD_MODE", "bulk")
result = load(session, sales, mode=load_mode)
```

### `log_pipeline_event(session, level, message, source="pipeline.load") -> None`

Manually create a log entry in the database.

**Parameters:**
- `session` (Session): Active SQLAlchemy session
- `level` (str): Log level ("INFO", "WARNING", "ERROR", etc.)
- `message` (str): Log message content
- `source` (str): Origin identifier (default: "pipeline.load")

**Example:**
```python
from src.load import log_pipeline_event

log_pipeline_event(
    session,
    "INFO",
    f"Processed batch of 500 records from vendor XYZ",
    source="vendor_sync"
)
```

## Integration with Pipeline

The load module integrates seamlessly with the ETL pipeline:

```python
from src.pipeline import run_pipeline
from src.database import get_session

session = get_session()
try:
    # Run with bulk insert (default)
    stats = run_pipeline(session, load_mode="bulk")
    
    # Or run with upsert
    stats = run_pipeline(session, load_mode="upsert")
finally:
    session.close()
```

**Pipeline Statistics:**
```python
{
    "extracted": 1000,    # Raw records from source
    "transformed": 950,   # Valid records after transformation
    "inserted": 900,      # New records inserted
    "updated": 50,        # Existing records updated (upsert only)
    "skipped": 0,         # Records skipped due to missing keys
    "failed": 0,          # Records that failed
}
```

## Performance Considerations

### Bulk Insert Performance

- **Best for**: Initial loads, no duplicate handling needed
- **Throughput**: ~10,000-100,000 rows/sec (varies by row size and DB)
- **Memory**: O(n) - all rows kept in memory before flush
- **Recommendation**: Use for datasets < 1M rows; consider streaming/pagination for larger batches

### Upsert Performance

- **PostgreSQL**: Native `ON CONFLICT DO UPDATE` is atomic and highly efficient
- **Other Databases**: Falls back to row-by-row processing (slower)
- **Key Lookup**: Creates temporary index on `external_id` for conflict detection
- **Recommendation**: 
  - PostgreSQL: Suitable for 10K-100K rows per batch
  - Other DBs: Keep batches < 10K for reasonable performance

### Optimization Strategies

1. **Batch Size Tuning**:
   ```python
   # Process in chunks for large datasets
   BATCH_SIZE = 5000
   for i in range(0, len(all_rows), BATCH_SIZE):
       batch = all_rows[i:i + BATCH_SIZE]
       result = load(session, batch, mode="upsert")
       session.commit()  # Commit between batches
   ```

2. **Use Bulk Insert When Possible**:
   - Bulk insert is faster than upsert
   - Use it for initial loads when duplicates aren't a concern

3. **Enable Logging Only When Needed**:
   ```python
   import logging
   logging.getLogger("src.load").setLevel(logging.WARNING)  # Reduce I/O
   ```

## Error Handling

The load module provides robust error handling:

### Constraint Violations

```python
from sqlalchemy.exc import IntegrityError

try:
    result = load_bulk_insert(session, sales)
except IntegrityError as e:
    print(f"Constraint violation: {e}")
    session.rollback()
```

### Upsert Partial Failures

In upsert mode, individual row failures don't stop the entire batch:

```python
result = load_upsert(session, mixed_rows)
print(f"Inserted: {result['inserted']}")
print(f"Failed: {result['failed']}")

if result['failed'] > 0:
    # Query logs to see why they failed
    from src.models import LogEntry
    errors = session.query(LogEntry).filter_by(level="ERROR").all()
    for error in errors:
        print(error.message)
```

## Testing

The module includes comprehensive tests:

```bash
# Run all load tests
pytest tests/test_load.py -v

# Run specific test
pytest tests/test_load.py::test_load_upsert_update_existing_row -v

# Run with PostgreSQL integration tests
pytest tests/test_load.py -v --run-pg
```

## Environment Configuration

Control load behavior via environment variables:

```bash
# Choose load mode (default: bulk)
export LOAD_MODE=upsert

# Enable SQL logging
export SQLALCHEMY_ECHO=1

# Run the pipeline
python main.py
```

## Database Support

| Database | Bulk Insert | Upsert | Native Optimization |
|----------|-------------|--------|---------------------|
| PostgreSQL | ✓ | ✓ | ON CONFLICT DO UPDATE |
| SQLite | ✓ | ✓ (fallback) | Individual queries |
| MySQL | ✓ | ✓ (fallback) | Individual queries |
| Oracle | ✓ | ✓ (fallback) | Individual queries |

## Examples

### Example 1: Simple Bulk Load

```python
from src.database import get_session, init_db
from src.load import load_bulk_insert
from src.models import Sale
from decimal import Decimal

init_db()
session = get_session()

try:
    sales = [
        Sale(external_id=f"id-{i}", product_name=f"Product {i}", 
             quantity=i, unit_price=Decimal("10.00"))
        for i in range(1000)
    ]
    
    result = load_bulk_insert(session, sales)
    session.commit()
    print(f"Loaded {result['inserted']} rows")
finally:
    session.close()
```

### Example 2: Incremental Load with Upsert

```python
from src.pipeline import run_pipeline

# Load new data, updating duplicates
stats = run_pipeline(session, load_mode="upsert")

print(f"Extracted: {stats['extracted']}")
print(f"Inserted: {stats['inserted']}")
print(f"Updated: {stats['updated']}")
print(f"Failed: {stats['failed']}")
```

### Example 3: Query Logs

```python
from src.models import LogEntry
from datetime import datetime, timedelta

# Get last hour's load operations
cutoff = datetime.now() - timedelta(hours=1)
recent_logs = session.query(LogEntry).filter(
    LogEntry.created_at >= cutoff,
    LogEntry.source == "pipeline.load",
).all()

for log in recent_logs:
    print(f"[{log.level}] {log.created_at}: {log.message}")
```

## Troubleshooting

### Issue: "NOT NULL constraint failed: sales.sold_at"

**Cause**: Upsert tries to update `sold_at` with None value

**Solution**: Only update `sold_at` if the new row has a valid value
```python
# This is already handled in _upsert_single_row
if row.sold_at is not None:
    existing.sold_at = row.sold_at
```

### Issue: Slow upsert on non-PostgreSQL databases

**Cause**: Fallback mode does row-by-row queries

**Solution**: 
- Migrate to PostgreSQL for better performance
- Reduce batch size
- Use bulk insert when possible

### Issue: Logs table grows too large

**Cause**: Too many log entries

**Solution**: Archive old logs periodically
```python
from datetime import datetime, timedelta
from src.models import LogEntry

# Delete logs older than 30 days
cutoff = datetime.now() - timedelta(days=30)
session.query(LogEntry).filter(LogEntry.created_at < cutoff).delete()
session.commit()
```
