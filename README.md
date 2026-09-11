# postgres-lite

A minimal in-process relational database implementation in Python with B+ tree indexing, MVCC transactions, and SQL-like query execution.

## Features

- **B+ Tree Indexing**: Efficient data structure for fast lookups and range queries with O(log n) time complexity
- **MVCC Transactions**: Multi-Version Concurrency Control for concurrent reads without locking, supporting multiple isolation levels
- **Table Operations**: Full insert, update, delete, and select with optional WHERE clause filtering
- **Row Versioning**: Track row changes via version numbers and timestamp tracking for MVCC
- **Persistence**: Serialize and deserialize tables to/from disk using pickle
- **Flexible Schema**: Define tables with typed columns (INT, TEXT, REAL, BOOL), nullable constraints, and default values
- **Transaction Support**: Explicit transaction demarcation with begin/commit/rollback
- **Isolation Levels**: Support for READ_UNCOMMITTED, READ_COMMITTED, REPEATABLE_READ, and SERIALIZABLE

## Architecture

### Core Components

**BPlusTree & BPlusTreeNode**: Implement a B+ tree with configurable order. Interior nodes route to children; leaf nodes store key-value pairs. Supports insertion, search, and range queries.

**Table**: Manages rows for a single table. Stores rows in a list with metadata (version, deletion marker, timestamp). Supports creating indexes on columns for accelerated lookups.

**Row**: Wraps data values plus version/deletion/timestamp metadata for MVCC.

**Database**: Central coordinator. Manages multiple tables, transactions, and isolation semantics.

### Transaction Model

- Transactions are identified by integer IDs and marked with isolation level
- begin_transaction() returns a tx_id; commit() and rollback() change status
- Each row is versioned; readers check isolation level to determine which versions are visible
- Lock manager placeholder for future work

### Persistence

- persist(filepath): Serializes all tables and counter state to disk as pickle
- load(filepath): Restores database from disk

## Usage

```python
from postgres import Database, Column, IsolationLevel

db = Database()
db.create_table("users", [
    Column("id", "INT", primary_key=True),
    Column("name", "TEXT", nullable=False),
    Column("age", "INT", nullable=True, default=0),
])

db.insert("users", {"id": 1, "name": "Alice", "age": 30})
db.insert("users", {"id": 2, "name": "Bob", "age": 25})

users = db.select("users")
alice = db.select("users", where={"name": "Alice"})
db.update("users", {"age": 31}, {"name": "Alice"})
db.delete("users", {"name": "Bob"})

tx = db.begin_transaction()
db.insert("users", {"id": 3, "name": "Charlie", "age": 35})
db.commit(tx)

db.persist("users.db")
db2 = Database()
db2.load("users.db")
```

## Running Tests

```bash
python -m pytest tests.py -v
```

Test coverage includes:
- B+ tree insertion, search, and range queries
- Table operations (insert, update, delete, scan)
- WHERE clause filtering
- Index creation
- Multi-table queries
- Transaction primitives
- Isolation level configurations

## Design Decisions

1. **B+ Tree Over Hash Table**: B+ trees provide efficient range queries and naturally support iteration in sorted order, critical for databases. Hash tables are faster for point lookups but lack range support.

2. **MVCC Over Locks**: Multi-version concurrency control allows readers to see consistent snapshots without blocking writers. Simpler for concurrent workloads where reads outnumber writes.

3. **Pickle for Persistence**: For this prototype, pickle provides simple serialization. Production systems use custom binary formats (page-based, with compression and checksums).

4. **Version Markers vs. Undo Logs**: Each row stores its version number. Cleaner than maintaining a separate undo log, though less space-efficient at scale.

5. **Simple WHERE Clauses**: Current implementation supports only equality predicates. Full query planning and optimizer would be needed for production.

6. **Lock Manager Placeholder**: Foundation is laid for row-level locking (lock_manager dict). Actual implementation would queue lock requests and check for conflicts.

## Future Enhancements

- Query Planning: Parse SQL strings and build execution plans with join ordering
- Buffer Pool: Cache pages in memory with LRU eviction for better I/O efficiency
- Query Optimizer: Cost-based plan selection (index usage, join order)
- Constraint Enforcement: Foreign keys, unique constraints, check constraints
- Write-Ahead Logging (WAL): Ensure durability and recovery from crashes
- Bloom Filters: Reduce false index lookups
- Compression: Dictionary and delta encoding for column values
- Async I/O: Non-blocking disk operations for higher throughput

## Performance Notes

- Inserts are O(log n) due to B+ tree indexing
- Full table scans are O(n)
- Range queries are O(log n + k) where k is result size
- MVCC has memory overhead (multiple row versions)
- No query plan optimization; full table scans used unless index available

## License

MIT
