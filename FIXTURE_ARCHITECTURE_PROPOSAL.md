# Proposed Fixture Architecture Improvements

## Current State Analysis

### Current Issues
1. ✅ **FIXED**: `basex_test_connector` was destroying e2e pristine data
2. ⚠️ **REMAINING**: Module-level code in `tests/conftest.py` runs at import (creates empty DB)
3. ⚠️ **REMAINING**: Some tests fail in full suite but pass individually (minor pollution)
4. ⚠️ **COMPLEXITY**: Fixture dependencies not immediately obvious from code

### Current Architecture

```
tests/
├── conftest.py
│   ├── Module-level: TEST_DB_NAME = create_test_db()  # ❌ Runs at import
│   ├── basex_test_connector (function) - removed from e2e ✅
│   └── flask_test_server (function)
│
├── e2e/
│   └── conftest.py
│       ├── setup_e2e_test_database (session, autouse) ✅ Creates pristine data
│       └── _db_snapshot_restore (function, autouse) ✅ Snapshot/restore
│
└── integration/
    └── conftest.py
        └── (integration fixtures)
```

## Proposed Architecture

### Option 1: Minimal Changes (Recommended)

**Goal**: Fix remaining issues with minimal code changes

#### Step 1: Remove Module-Level Side Effects

```python
# tests/conftest.py - BEFORE
import os
from tests.basex_test_utils import create_test_db, generate_safe_db_name

# ❌ This runs at import time!
TEST_DB_NAME = os.getenv('TEST_DB_NAME')
if not TEST_DB_NAME:
    TEST_DB_NAME = generate_safe_db_name()
    create_test_db(TEST_DB_NAME)

# tests/conftest.py - AFTER
import os
from tests.basex_test_utils import create_test_db, generate_safe_db_name

# Module-level variable, but no side effects
_test_db_name_cache = None

@pytest.fixture(scope="session")
def test_db_name():
    """Get or create test database name."""
    global _test_db_name_cache
    if _test_db_name_cache is None:
        _test_db_name_cache = os.getenv('TEST_DB_NAME')
        if not _test_db_name_cache:
            _test_db_name_cache = generate_safe_db_name()
            create_test_db(_test_db_name_cache)
    return _test_db_name_cache
```

#### Step 2: Make E2E Tests Completely Independent

```python
# tests/e2e/conftest.py
@pytest.fixture(scope="session", autouse=True)
def setup_e2e_test_database():
    """
    Creates pristine e2e test database with 3 test entries.
    
    IMPORTANT: Does NOT use parent conftest's test_db_name!
    E2E tests need their own isolated database.
    """
    # ALWAYS generate fresh e2e-specific database name
    test_db = generate_safe_db_name('e2e')
    
    # Set environment so flask_test_server uses correct DB
    os.environ['TEST_DB_NAME'] = test_db
    os.environ['REDIS_ENABLED'] = 'false'
    
    # Create database with pristine test data
    connector = BaseXConnector(test_db)
    add_pristine_entries(connector)
    
    yield test_db
    
    # Cleanup
    connector.drop_database(test_db)
```

#### Step 3: Add Fixture for Unit Tests (Optional)

```python
# tests/unit/conftest.py (new file)
import pytest

@pytest.fixture
def empty_database(test_db_name):
    """
    Provides empty database for unit tests.
    Uses shared test_db_name from parent conftest.
    """
    # Unit tests can share empty database
    return test_db_name
```

**Benefits**:
- ✅ Minimal code changes
- ✅ E2E completely isolated
- ✅ No import-time side effects
- ✅ Clear fixture hierarchy

**Drawbacks**:
- ⚠️ Still some shared code between test types

### Option 2: Complete Separation (More Work)

**Goal**: Complete isolation between test types

```
tests/
├── conftest.py (minimal common fixtures only)
│   └── common_config (session)
│
├── unit/
│   ├── conftest.py
│   │   ├── unit_db_name (session) - empty database
│   │   └── unit_connector (function) - reset between tests
│   └── test_*.py
│
├── integration/
│   ├── conftest.py
│   │   ├── integration_db_name (session) - minimal test data
│   │   └── integration_connector (function)
│   └── test_*.py
│
└── e2e/
    ├── conftest.py
    │   ├── e2e_db_name (session) - pristine test data
    │   ├── db_snapshot_restore (function, autouse)
    │   └── flask_test_server (function)
    └── test_*.py
```

**Implementation**:

```python
# tests/conftest.py - MINIMAL
"""Common fixtures for all test types."""
import pytest

@pytest.fixture(scope="session")
def common_config():
    """Configuration shared by all test types."""
    return {
        'basex_host': 'localhost',
        'basex_port': 1984,
        # ... other common config
    }

# tests/unit/conftest.py
"""Fixtures specific to unit tests."""
import pytest
from tests.basex_test_utils import create_test_db, generate_safe_db_name

@pytest.fixture(scope="session")
def unit_db_name():
    """Empty database for unit tests."""
    db_name = generate_safe_db_name('unit')
    create_test_db(db_name)
    yield db_name
    # cleanup

@pytest.fixture
def unit_connector(unit_db_name):
    """Database connector for unit tests (empty database)."""
    connector = BaseXConnector(unit_db_name)
    yield connector
    # Reset to empty state
    connector.truncate_all()

# tests/integration/conftest.py
"""Fixtures specific to integration tests."""
import pytest

@pytest.fixture(scope="session")
def integration_db_name():
    """Database with minimal test data for integration tests."""
    db_name = generate_safe_db_name('integration')
    connector = create_test_db(db_name)
    add_minimal_test_data(connector)
    yield db_name
    # cleanup

@pytest.fixture
def integration_connector(integration_db_name):
    """Database connector for integration tests."""
    return BaseXConnector(integration_db_name)

# tests/e2e/conftest.py - NO CHANGES NEEDED
# Already well isolated!
```

**Benefits**:
- ✅ Complete isolation between test types
- ✅ Clear separation of concerns
- ✅ Easy to understand which fixtures are used where
- ✅ Can run test types in parallel (different databases)

**Drawbacks**:
- ❌ More code to maintain
- ❌ Need to migrate existing tests
- ❌ Some duplication between conftest files

### Option 3: Fixture Plugin (Advanced)

**Goal**: Reusable fixture patterns across projects

Create a pytest plugin with common patterns:

```python
# tests/plugins/database_fixtures.py
import pytest
from typing import Callable, Any

def database_fixture_factory(
    scope: str,
    create_fn: Callable[[], Any],
    populate_fn: Callable[[Any], None] = None,
    cleanup_fn: Callable[[Any], None] = None
):
    """Factory for creating database fixtures with consistent patterns."""
    
    @pytest.fixture(scope=scope)
    def _database_fixture():
        db = create_fn()
        if populate_fn:
            populate_fn(db)
        yield db
        if cleanup_fn:
            cleanup_fn(db)
    
    return _database_fixture

# Usage in conftest.py
from tests.plugins.database_fixtures import database_fixture_factory

unit_database = database_fixture_factory(
    scope="function",
    create_fn=lambda: create_empty_db(),
    cleanup_fn=lambda db: db.drop()
)

e2e_database = database_fixture_factory(
    scope="session",
    create_fn=lambda: create_db_with_name('e2e'),
    populate_fn=lambda db: add_pristine_entries(db),
    cleanup_fn=lambda db: db.drop()
)
```

**Benefits**:
- ✅ DRY (Don't Repeat Yourself)
- ✅ Consistent patterns
- ✅ Reusable across projects
- ✅ Well-tested patterns

**Drawbacks**:
- ❌ More complex
- ❌ Harder to debug
- ❌ Overkill for single project

## Recommended Implementation Plan

### Phase 1: Quick Fix (Completed ✅)
- Remove `basex_test_connector` from e2e tests
- Ensure session fixture creates pristine data
- Add debug instrumentation

### Phase 2: Stabilization (Recommended Next)
- Move module-level code in `tests/conftest.py` to fixtures
- Ensure e2e tests never inherit parent database fixtures
- Document fixture dependencies in docstrings

### Phase 3: Future Enhancement (Optional)
- Create separate unit/integration/e2e conftest hierarchy (Option 2)
- Add meta-tests to verify fixture behavior
- Create fixture documentation generator

## Implementation Steps for Phase 2

### Step 1: Refactor tests/conftest.py

```python
# tests/conftest.py - BEFORE (Current)
TEST_DB_NAME = os.getenv('TEST_DB_NAME')
if not TEST_DB_NAME:
    TEST_DB_NAME = generate_safe_db_name()
    create_test_db(TEST_DB_NAME)

# tests/conftest.py - AFTER (Proposed)
@pytest.fixture(scope="session")
def base_test_db_name():
    """
    Base test database name for unit/integration tests.
    
    NOTE: E2E tests should NOT use this - they create their own database.
    """
    db_name = os.getenv('TEST_DB_NAME')
    if not db_name:
        db_name = generate_safe_db_name('base')
        create_test_db(db_name)
    yield db_name
    # Optional: cleanup
```

### Step 2: Update E2E Conftest

```python
# tests/e2e/conftest.py
@pytest.fixture(scope="session", autouse=True)
def setup_e2e_test_database(request):
    """
    Creates pristine e2e test database with 3 test entries.
    
    Scope: session
    Autouse: Yes
    Dependencies: NONE (intentionally isolated from parent fixtures)
    
    IMPORTANT: This fixture does NOT depend on base_test_db_name!
    E2E tests need complete isolation from unit/integration tests.
    """
    # Generate unique e2e database name
    test_db = generate_safe_db_name('e2e')
    
    _log_db_state("SESSION FIXTURE ENTERED", test_db)
    
    # Set environment for test server
    os.environ['TEST_DB_NAME'] = test_db
    os.environ['REDIS_ENABLED'] = 'false'
    
    # Create and populate database
    connector = BaseXConnector(test_db)
    connector.create_database()
    add_pristine_entries(connector)  # Adds test_entry_1, test_entry_2, test_entry_3
    
    _log_db_state("SESSION-SETUP-COMPLETE", test_db)
    
    yield test_db
    
    # Cleanup
    connector.drop_database(test_db)
```

### Step 3: Add Fixture Documentation

Create `tests/FIXTURES_README.md`:

```markdown
# Test Fixtures Guide

## Fixture Hierarchy

```
tests/conftest.py
├── base_test_db_name (session) - For unit/integration tests
└── flask_test_server (function) - Flask test server

tests/e2e/conftest.py
├── setup_e2e_test_database (session, autouse) - Pristine e2e database
├── _db_snapshot_restore (function, autouse) - Database isolation
└── page (function) - Playwright page [from plugin]
```

## Which Fixture Should I Use?

| Test Type | Database Fixture | Server Fixture | Notes |
|-----------|-----------------|----------------|-------|
| Unit | `base_test_db_name` | None | Direct function calls |
| Integration | `base_test_db_name` | `flask_test_server` | API calls via requests |
| E2E | (automatic) | `flask_test_server` | Browser automation |

## E2E Test Guidelines

❌ **DO NOT** request these fixtures in e2e tests:
- `basex_test_connector` - Will destroy pristine data!
- `base_test_db_name` - Wrong database!

✅ **DO** rely on autouse fixtures:
- `setup_e2e_test_database` - Creates pristine data automatically
- `_db_snapshot_restore` - Provides isolation automatically

✅ **DO** request these fixtures when needed:
- `flask_test_server` - Provides server URL
- `page` - Playwright page object
```

### Step 4: Add Meta-Tests

```python
# tests/e2e/test_fixture_sanity.py
"""Meta-tests to verify fixture behavior."""
import pytest
from app.database.basex_connector import BaseXConnector

def test_pristine_database_has_correct_entries(setup_e2e_test_database):
    """Verify e2e database starts with exactly 3 test entries."""
    db_name = setup_e2e_test_database
    connector = BaseXConnector(db_name)
    
    query = f"count(collection('{db_name}')//entry)"
    result = connector.execute_query(query)
    count = int(result.strip())
    
    assert count == 3, f"Expected 3 entries, got {count}"

def test_database_isolation_between_tests(setup_e2e_test_database):
    """Verify database state is restored between tests."""
    # This test intentionally doesn't modify anything
    # If isolation works, the next test should also see 3 entries
    pass

def test_database_still_has_three_entries(setup_e2e_test_database):
    """Verify previous test didn't pollute this test's database state."""
    db_name = setup_e2e_test_database
    connector = BaseXConnector(db_name)
    
    query = f"count(collection('{db_name}')//entry)"
    result = connector.execute_query(query)
    count = int(result.strip())
    
    assert count == 3, f"Expected 3 entries (isolation failed), got {count}"
```

## Testing the Changes

### Verification Checklist

After implementing Phase 2 changes:

```bash
# 1. Unit tests should still work
pytest tests/unit/ -v

# 2. Integration tests should still work
pytest tests/integration/ -v

# 3. E2E tests should pass individually
pytest tests/e2e/test_ranges_ui_playwright.py -v

# 4. E2E tests should pass as a group
pytest tests/e2e/ -v

# 5. Full suite should have high success rate
pytest tests/ -v --tb=short

# 6. Meta-tests should pass
pytest tests/e2e/test_fixture_sanity.py -v
```

### Expected Results

- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ E2E tests pass individually AND together
- ✅ No "database destroyed" debug messages
- ✅ Meta-tests confirm proper isolation

## Migration Checklist

- [ ] Create backup branch
- [ ] Implement fixture refactoring (Step 1-2)
- [ ] Add fixture documentation (Step 3)
- [ ] Add meta-tests (Step 4)
- [ ] Run full test suite
- [ ] Fix any newly revealed issues
- [ ] Update project documentation
- [ ] Create PR with detailed explanation

## Long-Term Maintenance

### Regular Checks

Run these periodically to catch fixture issues early:

```bash
# Check for import-time side effects
python -c "import tests.conftest; print('No import errors')"

# Run meta-tests
pytest tests/e2e/test_fixture_sanity.py -v

# Check fixture execution order
pytest tests/e2e/ --setup-show | less

# Debug database state
E2E_DEBUG_STATE=true pytest tests/e2e/test_ranges_ui_playwright.py -v
```

### Code Review Guidelines

When reviewing fixture changes:
- ✅ No side effects at module level
- ✅ Clear fixture scope (session/module/function)
- ✅ Explicit dependencies declared
- ✅ Docstring explains purpose and scope
- ✅ Cleanup code in teardown
- ✅ Meta-test added if changing isolation strategy

---

*Document created: 2026-01-10*  
*Proposed improvements based on fixture isolation fix*
