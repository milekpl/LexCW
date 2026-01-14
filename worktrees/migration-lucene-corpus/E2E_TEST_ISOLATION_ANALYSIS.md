# E2E Test Isolation Root Cause Analysis

## Problem Summary
E2E tests fail when run together but pass individually. 20 tests failed with timeout errors waiting for entries that should exist.

## TRUE Root Cause (After Instrumentation)

### Issue: E2E Tests Using Wrong Fixture

**Location**: `tests/e2e/test_all_ranges_dropdowns_playwright.py` and `tests/e2e/test_ranges_ui_playwright.py`

**Problem Flow**:
1. **Session Setup**: `setup_e2e_test_database` (session-scoped, autouse) runs first
   - Creates database `test_YYYYMMDD_HHMM_e2e_XXXXXX`
   - Adds pristine data: `test_entry_1`, `test_entry_2`, `test_entry_3`
   - Sets `os.environ['TEST_DB_NAME']` to this database

2. **First Test Runs**: `test_all_ranges_dropdowns_playwright.py::test_grammatical_info_dropdown_populated`
   - Declares `basex_test_connector` as a fixture parameter
   - `basex_test_connector` is **function-scoped** from `tests/conftest.py`
   - It calls `connector.create_database(db_name)` which **DROPS and RECREATES** the database
   - Then adds only 1 entry (`test_entry_1`)
   - **Destroys the pristine 3-entry setup!**

3. **Subsequent Tests Fail**:
   - They expect 3 entries but database now has 0 or 1
   - Timeout waiting for entries that don't exist

**Evidence**:
```bash
$ E2E_DEBUG_STATE=true pytest tests/e2e/ -x
# Session setup runs:
[E2E-DEBUG] SESSION SETUP: Creating database test_20260110_0954_e2e_61aae2
[E2E-DEBUG] SESSION-SETUP-COMPLETE | entry_count=3

# But first test using basex_test_connector destroys it:
[E2E-DEBUG] before-snapshot | entry_count=0  # ← Database now empty!
```

**Why It Works When Run Individually**:
- When running `pytest tests/e2e/test_delete_entry.py` alone, `test_all_ranges_dropdowns_playwright.py` doesn't run
- So `basex_test_connector` never gets invoked
- Database keeps its pristine 3 entries

## Solution

**Remove `basex_test_connector` from all e2e test files.**

E2e tests should **NOT** use `basex_test_connector` - it's designed for unit/integration tests that need isolated databases. E2e tests should:
- Use `flask_test_server` fixture (provides running app)
- Rely on session-scoped `setup_e2e_test_database` for pristine data
- Use `_db_snapshot_restore` for per-test isolation

**Files to Fix**:
1. `tests/e2e/test_all_ranges_dropdowns_playwright.py` - 6 test methods
2. `tests/e2e/test_ranges_ui_playwright.py` - 4 test methods

**Change**: Remove `basex_test_connector` parameter from test method signatures.

## Implementation
