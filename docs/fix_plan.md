# Revision Plan: Race Conditions, Data Loss & Anti-Patterns

Based on audit in `docs/audit_report.md`.  
**Order:** by severity, then by dependency (fix foundations first).

---

## Phase 1 — CRITICAL (3 issues)

### 1.1 PostgreSQLConnector: Replace Single Connection with Thread-Safe Pool

**Files:** `app/database/postgresql_connector.py`  
**Problem (1.1, 1.2):** Single `psycopg2.connect()` shared across all threads with `autocommit=True`, making transactions unsafe. Pool config (`pool_size`, `max_overflow`) is dead code.

**Fix:**
- Replace `self._connection` with `psycopg2.pool.ThreadedConnectionPool(minconn=2, maxconn=10, ...)`
- `get_cursor()` → `pool.getconn()`, `pool.putconn()` instead of single cursor
- Remove `autocommit=True`; let `execute_transaction()` manage commits
- Add `_ensure_pool()` lazy init
- Add thread-safety docstring and remove legacy locale env manipulation (lines 89-96)

### 1.2 Merge/Split: Add Compensation Logic for Partial Failures

**Files:** `app/services/merge_split_service.py` (lines 86-88, 204-210)  
**Problem (2.1):** Multi-step (create then update, or update then delete) without rollback. A failure mid-way permanently corrupts entries.

**Fix:**
- In `split_entry()`: wrap `create_entry` + `update_entry` in a try/except that calls `delete_entry(new_entry.id)` on failure to undo the partial create.
- In `merge_entries()`: save original data, wrap in try/except that re-inserts original data on failure.
- In `XMLEntryService.update_entry()` (delete-then-insert): same pattern.
- Store pre-modification snapshots in memory for compensation.

### 1.3 SQLAlchemy Unhandled Commit Failures

**Files:** All 31+ files under `app/` that call `db.session.commit()` without try/except/rollback.  
**Problem (2.3):** If a commit fails, the session is poisoned — subsequent operations fail with "This session is in 'failed' state".

**Fix:**
- Create a helper: `app/utils/db_utils.py` with `safe_commit()` that wraps `db.session.commit()` with rollback and re-raise.
- Replace all bare `db.session.commit()` calls with `safe_commit()`.
- Pattern:
  ```python
  def safe_commit(session=None):
      s = session or db.session
      try:
          s.commit()
      except Exception:
          s.rollback()
          raise
  ```

---

## Phase 2 — HIGH (8 issues)

### 2.1 BaseX Pool `_created` Counter Drift

**File:** `app/database/basex_connector.py:119-142`  
**Problem (1.3):** `_acquire()` and `_discard()` acquire `_pool_lock` separately, creating a window where count drifts.

**Fix:**
- Merge the two lock acquisitions: hold `_pool_lock` across both the `_created` increment in `_acquire()` AND the `_created` decrement in `_discard()`.
- Better: make `_created` an `atomic` counter or use `queue.Queue(maxsize=_max_pool)`'s built-in `qsize()`.

### 2.2 Singleton Races (CacheService, ValidationCacheService)

**Files:** `app/services/cache_service.py:24-25`, `app/services/validation_cache_service.py:39-41`  
**Problem (1.4):** `__new__` without lock — two threads can both create instances.

**Fix:**
- Add `_singleton_lock = threading.Lock()` class variable.
- In `__new__`, acquire lock before checking `_instance`.
- Use double-checked locking:
  ```python
  def __new__(cls):
      if cls._instance is None:
          with cls._singleton_lock:
              if cls._instance is None:
                  cls._instance = super().__new__(cls)
      return cls._instance
  ```

### 2.3 OperationHistoryService File TOCTOU

**File:** `app/services/operation_history_service.py:55-84`  
**Problem (1.5):** Read-modify-write on shared JSON file races between concurrent requests.

**Fix:**
- Add `_file_lock = threading.Lock()` instance variable.
- In `_read_history()` + `_write_history()`, acquire file lock.
- Use atomic write pattern: write to temp file, `os.rename()` to replace.
- OR: switch to `sqlite3` or SQLAlchemy for history storage (but that's a larger refactor — the lock + atomic write is the minimal fix).

### 2.4 EventBus Thread Safety

**File:** `app/services/event_bus.py:34-40`  
**Problem (1.6):** `emit()` iterates subscriber list while `on()`/`off()` modifies it without lock.

**Fix:**
- Add `_lock = threading.Lock()`.
- Wrap `on()`, `off()`, `emit()` with the lock.
- In `emit()`, capture the callback list under lock, then iterate outside.

### 2.5 SQLAlchemy Bulk Delete Orphans

**Files:** `app/models/validation_cache_models.py:291`, `app/models/validation_models.py:221`, `app/services/dictionary_service.py:632`  
**Problem (2.2):** `query.delete()` bypasses cascade and ORM events.

**Fix:**
- Replace bulk deletes with ORM-safe iteration + `session.delete()` for models with cascade dependencies.
- OR at minimum: add explicit `cascade="all, delete-orphan"` to relationship definitions and use the ORM path.
- Add explicit ordering: delete children first, then parents.

### 2.6 XQuery Injection via Unescaped Entry IDs

**Files:** `app/models/entry.py:762-768`, `app/models/sense.py:338-343`, `app/services/dictionary_service.py:1044-1048`  
**Problem (2.4):** Entry IDs interpolated directly into XQuery.

**Fix:**
- Create `xquery_escape(value: str) -> str` in `app/utils/xquery_builder.py` that escapes both single and double quotes, backslashes, and closing braces.
- Apply to all inline XQuery constructions.
- For the `dictionary_service.py` bidirectional relations path: use parameterized queries or `escape_xquery_string()` which already exists but isn't used everywhere.

### 2.7 BackupService Daemon Thread Safety

**File:** `app/services/backup_service.py:166-194`  
**Problem (1.7, 2.8):** Daemon thread can be killed mid-operation. No lock on `backup_ops` dict.

**Fix:**
- Use `threading.Lock` for `current_app.backup_ops`.
- Add a `_backup_ops_lock` when reading/writing the ops dict.
- Document that daemon thread termination means partial backup state is an expected risk.
- Optionally: switch to non-daemon threads with explicit timeout shutdown.

### 2.8 BackupScheduler `_dirty` + `_scheduled_backup_jobs` Race

**File:** `app/services/backup_scheduler.py:45-48, 159-213`  
**Problem (1.8, §10 in exploration):** Plain `bool` for `_dirty`, unprotected dict for jobs.

**Fix:**
- Replace `_dirty` with `threading.Event()` — `.set()` and `.clear()` are atomic.
- Add `_jobs_lock = threading.Lock()` for `_scheduled_backup_jobs`.
- Guard all reads/writes to `_scheduled_backup_jobs` with the lock.

---

## Phase 3 — MEDIUM (5 key issues)

### 3.1 Hardcoded `dictionary` Database Name

**Files:** `app/models/entry.py:763`, `app/models/sense.py:339`  
**Problem (2.5):** `collection('dictionary')` hardcoded in inline queries.

**Fix:**
- Pass the configured database name (from `dict_service.db_connector.database`) into these methods.
- Make `get_subentries()` and `enrich_relations_with_display_text()` accept an optional `db_name` parameter.

### 3.2 Autosave Version Tracking

**File:** `app/api/entry_autosave_working.py:35, 86`, `app/services/dictionary_service.py:912-978`  
**Problem (2.6):** Autosave ignores client `version` field. No conflict detection.

**Fix:**
- Add optimistic locking: store a `date_modified` or version counter on each entry.
- Before autosave, check that the entry's stored version matches the client's version.
- If mismatch, return `409 Conflict` — client must reload.

### 3.3 Global Injector Duplication

**File:** `app/__init__.py:22, 833`  
**Problem (3.2):** Two injectors — one global, one in `create_app()`.

**Fix:**
- Remove the global `injector = Injector()` at line 22.
- Change all references from `app.injector` (already correct) — remove the global import.
- Ensure all injection goes through `current_app.injector`.

### 3.4 Mock Connector Interface Mismatch

**File:** `app/database/mock_connector.py`  
**Problem (3.7):** `execute_update` returns `bool` vs `None`.

**Fix:**
- Make `MockDatabaseConnector.execute_update()` match `BaseXConnector.execute_update()` return signature (returns `None`, raises on error).
- Or: add a common abstract base class / protocol.

### 3.5 Module-Level `create_app()` in Tests

**Files:** `tests/conftest.py:21-34`, `tests/integration/conftest.py:51-65`  
**Problem (3.8):** `create_app('testing')` at import time before env vars are set.

**Fix:**
- Defer `create_app()` to fixture time, not module import time.
- Use `pytest.fixture(scope='session', autouse=True)` for the initial app creation.
- Remove the module-level `create_app()` call from conftest.py.

---

## Phase 4 — LOW (fix if time permits)

### 4.1 Inconsistent Datetime Handling
- Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` across all models and services.
- Standardize on timezone-aware UTC everywhere.

### 4.2 Zombie Health-Check Threads
- Add explicit timeout + connection cleanup in the health-check thread wrappers in test infrastructure.
- Close BaseX sessions on timeout.

### 4.3 APScheduler in Factory
- Move `BackupScheduler.start()` out of `create_app()` into a separate startup hook or CLI command.

---

## Verification

After each phase, run the relevant tests:

```bash
# Unit tests (fastest, covers services/models)
python -m pytest tests/unit/ -x --timeout=60 -v

# Integration tests (covers database access)
python -m pytest tests/integration/ -x --timeout=120 -v

# E2E tests (covers full stack, requires all services)
python -m pytest tests/e2e/ -x --timeout=300 -v

# All tests
python -m pytest tests/ -x --timeout=300 -v
```

**Key test files to verify each fix:**
- PostgreSQL pool: `tests/integration/test_workset_api.py`
- Merge/split compensation: `tests/unit/test_merge_split_service.py`
- XQuery escaping: `tests/unit/test_xquery_builder.py`
- History concurrency: existing history service tests
- EventBus thread safety: event bus tests
- Singleton: cache service tests
