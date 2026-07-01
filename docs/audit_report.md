# Security, Race Condition & Data Loss Audit

**Project:** Lexicographic Curation Workbench (Flask + BaseX + PostgreSQL)
**Audit Date:** 2026-07-01
**Auditor:** Automated codebase analysis

---

## Table of Contents

1. [Race Conditions](#1-race-conditions)
2. [Bugs That Could Cause Data Loss](#2-bugs-that-could-cause-data-loss)
3. [Anti-Patterns](#3-anti-patterns)
4. [Risk Summary](#4-risk-summary)

---

## 1. Race Conditions

### 1.1 PostgreSQLConnector: Single-Connection Shared Across Threads (CRITICAL)

**File:** `app/database/postgresql_connector.py:63`
**Problem:** `self._connection` is a single `psycopg2.connect()` stored as an instance attribute. `psycopg2` connections are **not thread-safe** — concurrent Flask request threads create separate cursors from the same connection, interleaving query execution. This causes unpredictable results: reads return wrong data, writes corrupt rows.

```python
# Line 63 — one connection for all threads
self._connection: Optional[psycopg2.extensions.connection] = None

# Line 124-128 — each request gets a cursor from the shared connection
def get_cursor(self):
    cursor = self._connection.cursor()  # NOT thread-safe
```

The config declares `pool_size=10, max_overflow=20` (lines 40-41) but these are **dead fields** — never passed to `psycopg2.connect()`.

### 1.2 PostgreSQLConnector: autocommit=True Breaks Transactions (CRITICAL)

**File:** `app/database/postgresql_connector.py:109, 216-243`
**Problem:** `self._connection.autocommit = True` is the default state. `execute_transaction()` temporarily sets it to `False`. If another request thread acquires a cursor during the transaction window, that cursor operates inside the unintended transaction. If the transaction is rolled back (line 239), the interleaved query results are also rolled back.

```
Thread A: set autocommit=False -> cursor.execute(q1) -> [interleaved]
Thread B:                                            -> cursor.execute(q2) -> [sees stale data]
Thread A: commit() -> set autocommit=True
```

### 1.3 BaseX Connection Pool: `_created` Counter Drift (HIGH)

**File:** `app/database/basex_connector.py:119-142`
**Problem:** `_acquire()` and `_discard()` each acquire `_pool_lock` independently. Between the two lock acquisitions, a connection can be leaked — the pool "forgets" it. Over time, the actual connection count drifts below `_max_pool` (new connections created unnecessarily) or above it (connections leak and are never closed).

```python
# _acquire() — lock-protected increment
with self._pool_lock:
    self._created += 1   # (line 130)

# _discard() — SEPARATE lock acquisition
def _discard(self, conn):
    conn.close()
    with self._pool_lock:
        self._created -= 1   # (line 142)
```

Window: after `_discard` decrements, `_acquire` could have already passed its `_created < _max_pool` check and is about to create a new connection, exceeding the intended pool size.

### 1.4 Singleton Pattern Without Locks (HIGH)

**Files:** `app/services/cache_service.py:24-25`, `app/services/validation_cache_service.py:39-41`
**Problem:** Classic double-checked locking without synchronization. Two threads entering `__new__` simultaneously both see `_instance is None` and each creates a new instance. Only one survives; the other opens a Redis connection that is immediately garbage collected.

```python
class CacheService:
    _instance = None
    def __new__(cls):
        if cls._instance is None:          # race: both threads pass this
            cls._instance = super().__new__(cls)  # only one wins
        return cls._instance
```

### 1.5 OperationHistoryService: File-Based TOCTOU (HIGH)

**File:** `app/services/operation_history_service.py:55-84`
**Problem:** `_read_history()` reads the entire JSON file into memory; `_write_history()` writes it back. Between the read and write, concurrent requests (e.g., two simultaneous autosaves) overwrite each other's changes. Complete history loss.

```python
# Thread A: reads file -> appends operation A -> writes file
# Thread B: reads file (BEFORE A's write) -> appends operation B -> writes file
# Result: operation A is SILENTLY LOST
```

Only one JSON file (`instance/operation_history.json`) serves all users and all sessions. The `max_history=100` cap is a mitigation but does not solve the concurrency problem.

### 1.6 EventBus: Synchronous Callbacks in Request Threads (HIGH)

**File:** `app/services/event_bus.py:34-40`
**Problem:** `emit('entry_updated', ...)` runs all callbacks synchronously in the calling thread (the Flask request thread). The subscriber `operation_history_service._on_entry_updated()` writes to the unprotected JSON file. Multiple concurrent autosave requests all race on the same file.

```python
def emit(self, event, data):
    for callback in self._subscribers.get(event, []):
        callback(data)   # synchronous in request thread, TOCTOU race on history file
```

### 1.7 BackupService: Daemon Thread Termination (MEDIUM)

**File:** `app/services/backup_service.py:166-194`
**Problem:** Background backups run in a `threading.Thread(target=..., daemon=True)`. Daemon threads are forcibly killed when the main thread exits (SIGTERM, crash, or deploy). A backup in progress is silently aborted. The backup operation is logged as "pending" forever in `app.backup_ops`.

### 1.8 BackupScheduler: `_dirty` Flag Race (MEDIUM)

**File:** `app/services/backup_scheduler.py:48, 159-213`
**Problem:** `_dirty` is a plain `bool` attribute read/written from both the APScheduler thread and Flask request threads (via EventBus callback). Between the `_dirty` check and the reset, a concurrent entry update sets `_dirty = True` — but the backup has already begun. The change is excluded from the backup.

```python
# scheduler thread                    # request thread
if not self._dirty:                   event_bus.emit('entry_updated')
    return                              -> self._dirty = True  <-- MISSED
self._dirty = False
backup()  # <- missing the update
```

There is no `threading.Event`, no `Lock`, no `memoryview` or `volatile` — just a bare Python attribute.

---

## 2. Bugs That Could Cause Data Loss

### 2.1 Merge/Split: No Transactional Rollback (CRITICAL)

**File:** `app/services/merge_split_service.py:86-88, 204-210`
**Problem:** `create_entry()` and `update_entry()` are two separate BaseX operations. If the second fails (e.g., validation error, connection loss), the first has already been committed to BaseX and **cannot be rolled back**. The entry is permanently corrupted — senses duplicated or half-transferred.

```python
# Split (line 86-88):
self.dictionary_service.create_entry(new_entry)       # COMMITTED
self.dictionary_service.update_entry(modified_source_entry)  # FAILS -> source entry still has senses

# Merge (line 205-210):
self.dictionary_service.update_entry(modified_target_entry)  # COMMITTED
self.dictionary_service.update_entry(modified_source_entry)  # FAILS -> senses now in both entries
```

No `savepoint`, no `try/except/rollback` at the operation boundary. The undo history records metadata, but the actual data is gone.

### 2.2 SQLAlchemy Bulk Delete Orphans Related Data (HIGH)

**Files:** `app/models/validation_cache_models.py:291-295`, `app/models/validation_models.py:221-226`, `app/services/dictionary_service.py:632-633`
**Problem:** `Model.query.filter(...).delete()` bypasses SQLAlchemy's unit-of-work and does **not cascade** to child rows nor fire ORM events. `CustomRangeValue` rows referencing a deleted `CustomRange` become orphaned.

```python
# dictionary_service.py:632 — bulk delete, no cascade
CustomRangeValue.query.delete()
CustomRange.query.delete()
# If second fails, CustomRangeValues are gone but CustomRanges remain -> inconsistency
```

### 2.3 SQLAlchemy Sessions: Commit Without Rollback Handlers (HIGH)

**31+ locations across `app/**/.py`**
**Exemplar:** `app/services/user_service.py:56`, `app/services/auth_service.py:219`, `app/services/message_service.py:53`
**Problem:** `db.session.commit()` is called without `try/except/rollback` in the vast majority of places. If a commit fails (deadlock, constraint violation, serialization failure), the **session is poisoned** — SQLAlchemy requires an explicit `rollback()` before any further operations. The poisoned session propagates to the next request in the pool, causing all subsequent database operations in that session to fail with `"This session is in 'failed' state"`.

```python
# Pattern found at 31+ call sites:
db.session.add(some_object)
db.session.commit()   # <- if this fails, session is dead
# no rollback, no error handling
```

### 2.4 XQuery Injection via Unescaped Entry IDs (HIGH)

**Files:** `app/models/entry.py:762-768`, `app/models/sense.py:338-343`, `app/services/dictionary_service.py:1044-1048`
**Problem:** Entry IDs are interpolated directly into XQuery strings. Some paths escape single quotes; others do not. A malformed entry ID with a closing quote, e.g., `entry' or 1=1 or '`, corrupts the query.

```python
# entry.py:762-768 -- unescaped self.id
query = f"""
  for $entry in collection('dictionary')//entry
  where $entry/relation[@type='_component-lexeme' and @ref='{self.id}']
  return $entry
"""

# sense.py:338-343 -- unescaped ref
query = f"""
  for $entry in collection('dictionary')//entry
  where $entry//sense[@id='{ref}']
  return $entry
"""
```

This can cause corrupted XML to be written into BaseX (data loss) or, in the worst case, unintended XQuery execution against other databases.

### 2.5 Hardcoded Database Name in Inline XQueries (MEDIUM)

**Files:** `app/models/entry.py:763`, `app/models/sense.py:339`
**Problem:** `collection('dictionary')` is hardcoded. In multi-project setups where the database is named differently, these queries return empty results. The caller (UI or API) silently sees "no data" rather than an error, making this a silent data loss.

### 2.6 Autosave: bidirectional relations not skipped, leading to duplicate reverse entries (MEDIUM)

**File:** `app/services/dictionary_service.py:912-978`, `app/api/entry_autosave_working.py:86`
**Problem:** The autosave API calls `update_entry(entry, skip_validation=True)` with `skip_bidirectional=False` (default). If the entry has bidirectional relations, `_handle_bidirectional_relations()` creates reverse relations on target entries. On every autosave tick (which fires frequently), the same reverse relations are added again — no deduplication exists for concurrent autosave calls. Target entries accumulate duplicate relation nodes.

```python
# autosave (entry_autosave_working.py:86):
dictionary_service.update_entry(entry, skip_validation=True)
#     -> calls _handle_bidirectional_relations(entry) by default
#     -> inserts reverse relations WITHOUT checking if they already exist
```

---

## 3. Anti-Patterns

### 3.1 PostgreSQL Pool Configuration Is a Dead Letter (HIGH)

**File:** `app/database/postgresql_connector.py:40-41, 84-121`
`pool_size=10` and `max_overflow=20` are declared in the dataclass and populated from the environment, but `_initialize_connection()` calls `psycopg2.connect()` — which does not accept pool parameters. Every connection is a single TCP socket. The only real pooling exists in `app/__init__.py:325-334` which creates a `SimpleConnectionPool` but on a **different db config** (app.config PG_* vars). There are now **two separate PostgreSQL access paths** — one pooled (SQLAlchemy's connection via the db object), one single-connection (PostgreSQLConnector). The latter is used for workset operations and is the bottleneck.

### 3.2 Global Module-Level Injector (HIGH)

**File:** `app/__init__.py:22, 833`
`injector = Injector()` is defined as a global, then a **second** `injector = Injector()` is created in `create_app()` (line 833). Which one services hold depends on import order. Services imported at module level before `create_app()` runs bind to the global unconfigured injector and get a `BaseXConnector(None, ...)` with no database. This creates hard-to-reproduce NPEs.

### 3.3 Environment Variables as Global Mutable State (MEDIUM)

**Files:** `app/database/basex_connector.py:79-83`, `app/database/postgresql_connector.py:66-70`, `app/__init__.py:75-98`, 33 other locations
`os.environ` is read and **written** at nearly every layer: `TEST_DB_NAME`, `BASEX_DATABASE`, `TESTING`, `REDIS_ENABLED`, `BASEX_PASSWORD`. Writing to the process environment (`os.environ[key] = value`) is process-global mutable state. If a test or handler changes an env var mid-request, all concurrent threads see the change. The `TEST_DB_NAME` sync code in `create_app()` (lines 90-92) writes to `os.environ`:

```python
os.environ["TEST_DB_NAME"] = cfg_db   # visible to ALL threads immediately
```

### 3.4 APScheduler Started During Application Factory (MEDIUM)

**File:** `app/__init__.py:597-613`
`BackupScheduler.start()` is called inside `create_app()`, before the injector is fully configured and before error handlers are registered. If any subsequent initialization step fails (e.g., `scan_and_create_custom_ranges()` at line 751), the scheduler thread continues running in the background with a half-initialized app, potentially scheduling backups of an empty state that overwrite real data on restart.

### 3.5 Inconsistent Datetime Handling (LOW)

Across models: `datetime.utcnow()` (naive) vs `datetime.now(timezone.utc)` (aware). Mixed naive/aware datetimes cause SQLAlchemy comparison errors and serialization mismatches in cache keys. Specifically found in:
- `workset_models.py:19,21` — `default=datetime.utcnow` (function reference, correct)
- `backup_service.py:72,98` — mixed usage
- `operation_history_service.py:173,179,211` — `datetime.utcnow().isoformat()`
- `validation_cache_service.py:422` — `datetime.utcnow().isoformat()`
- `custom_ranges.py:30` — `datetime.now(timezone.utc)` (aware)

### 3.6 Thread-Based Health Checks Without Cleanup (LOW)

**Files:** Tests infrastructure, `dictionary_service.py:184-223`
Several places use `threading.Thread(target=..., daemon=True)` with `threading.Event().wait(timeout=N)` to test BaseX availability. On timeout, the thread is abandoned while still holding a half-open BaseX TCP session. These zombie sockets consume BaseX server connection slots and prevent DROP DB operations.

### 3.7 Mock Connector Interface Mismatch (MEDIUM)

**File:** `app/database/mock_connector.py` vs `app/database/basex_connector.py`
`execute_update()` returns `bool` in MockConnector but `None` in BaseXConnector. Callers expecting a truthy return (e.g., `if self.db_connector.execute_update(...):`) behave differently in test vs production. In tests, a failed update returns `False`; in production, it raises an exception — vastly different error handling paths.

### 3.8 Module-Level `create_app()` Calls in Tests (MEDIUM)

**Files:** `tests/conftest.py:21-34`, `tests/integration/conftest.py:51-65`
`create_app('testing')` is called at module import time before pytest fixtures run. This means `TEST_DB_NAME` might not be set yet. The app is created with the default `test_entries_db` from `TestingConfig`. If a session-scoped fixture later changes `TEST_DB_NAME`, the import-time app was already created with the wrong database. This is a **test-ordering-dependent bug** that causes spurious CI failures.

### 3.9 `onupdate=datetime.utcnow` Is a Function Reference on Mutable Default (LOW)

**File:** `app/models/workset_models.py:21`
While `onupdate=datetime.utcnow` is correct (SQLAlchemy calls the function on update), `default=datetime.utcnow` at line 19 is also correct. However, mixing `datetime.utcnow` (naive) with timezone-aware datetimes elsewhere creates the inconsistency described in §3.5.

### 3.10 No Database Migrations, Schema Enforced at Runtime (MEDIUM)

All models use `__allow_unmapped__ = True` to suppress Mypy typing rather than proper type annotations. `db.create_all()` runs on every startup (line 114), which is a development crutch that masks schema drift. In production, schema changes require manual SQL — there is no `alembic` or `flask-migrate` setup.

---

## 4. Risk Summary

| Risk Level | Count | Key Issues |
|---|---|---|
| **CRITICAL** | 3 | Shared psycopg2 connection, autocommit transaction breakage, non-atomic merge/split |
| **HIGH** | 8 | BaseX pool counter drift, singleton races, file-based history TOCTOU, EventBus sync callbacks, bulk-orphan deletes, unhandled commit failures, XQuery injection, daemon thread backup |
| **MEDIUM** | 12 | Hardcoded DB names, autosave duplicate relations, dead pool config, global injector, env var mutation, APScheduler in factory, mock mismatch, test import ordering |
| **LOW** | 3 | Timezone inconsistency, zombie health-check threads, mutable default mix |
