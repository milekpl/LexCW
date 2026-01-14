# Pytest Fixture Best Practices for E2E Tests

## Lessons Learned from Database Isolation Issues

### Problem Pattern: Fixture Scope Conflicts

**Anti-Pattern**: Using fixtures with conflicting scopes and side effects
```python
# tests/conftest.py (parent)
@pytest.fixture(scope="function")
def basex_test_connector():
    # Creates a NEW database (drops existing!)
    connector = create_database()
    yield connector
    # cleanup

# tests/e2e/conftest.py (child)
@pytest.fixture(scope="session", autouse=True)
def setup_e2e_test_database():
    # Creates pristine database with test data
    db = create_database_with_data()
    yield
    # cleanup

# tests/e2e/test_something.py
def test_ranges(basex_test_connector):  # ❌ WRONG!
    # This destroys the session database!
    pass
```

**Result**: Function-scoped fixture destroys session-scoped pristine data on EVERY test.

### Solution Pattern: Fixture Inheritance Hierarchy

**Best Practice**: Use explicit fixture dependencies and avoid side effects
```python
# tests/e2e/conftest.py
@pytest.fixture(scope="session", autouse=True)
def setup_e2e_test_database():
    """Creates pristine test database once per session."""
    db_name = generate_safe_db_name('e2e')
    connector = BaseXConnector(db_name)
    # Add pristine test data
    add_test_entries(connector, ['entry_1', 'entry_2', 'entry_3'])
    yield db_name
    # cleanup

@pytest.fixture(scope="function", autouse=True)
def _db_snapshot_restore(setup_e2e_test_database):
    """Saves/restores database state around each test."""
    db_name = setup_e2e_test_database
    snapshot = create_snapshot(db_name)
    yield
    restore_snapshot(db_name, snapshot)

# tests/e2e/test_something.py
def test_ranges():  # ✅ CORRECT!
    # Uses session database via autouse fixtures
    # No need to explicitly request connector
    pass
```

**Benefits**:
1. Session data created once and reused
2. Each test gets clean slate via snapshot/restore
3. No fixture parameter needed in test signatures
4. Impossible to accidentally destroy pristine data

## Fixture Scope Guidelines

### When to Use Each Scope

| Scope | Use Case | Example |
|-------|----------|---------|
| `session` | Expensive setup needed once | Database with test data, test server |
| `module` | Setup per test file | Module-specific configuration |
| `class` | Setup per test class | Class-level shared state |
| `function` | Setup per test | Most common, default scope |

### Scope Interaction Rules

1. **Parent scope fixtures cannot depend on child scope fixtures**
   - Session fixtures cannot use function fixtures
   - Function fixtures CAN use session fixtures

2. **Autouse fixtures run before explicit fixtures**
   - `@pytest.fixture(autouse=True)` runs automatically
   - Useful for setup/teardown without parameter passing

3. **Fixture execution order**:
   ```
   session setup (autouse)
   ├── session setup (explicit)
   │   ├── function setup (autouse)
   │   │   ├── function setup (explicit)
   │   │   │   └── TEST EXECUTION
   │   │   └── function teardown (explicit)
   │   └── function teardown (autouse)
   └── session teardown (explicit)
   session teardown (autouse)
   ```

## Database Testing Patterns

### Pattern 1: Session Pristine + Function Snapshot (Recommended)

**Use when**: Fast snapshot/restore available (BaseX, SQLite)

```python
@pytest.fixture(scope="session", autouse=True)
def pristine_database():
    """Create pristine database once."""
    db = create_database()
    populate_test_data(db)
    yield db
    drop_database(db)

@pytest.fixture(scope="function", autouse=True)
def isolated_test(pristine_database):
    """Snapshot before, restore after each test."""
    snapshot = pristine_database.snapshot()
    yield
    pristine_database.restore(snapshot)
```

**Pros**:
- ✅ Fast (pristine data created once)
- ✅ Perfect isolation (each test starts fresh)
- ✅ No test pollution possible

**Cons**:
- ⚠️ Requires snapshot/restore capability
- ⚠️ Snapshot overhead per test

### Pattern 2: Function-Level Database (Slower but Simple)

**Use when**: No snapshot capability OR tests need different starting states

```python
@pytest.fixture(scope="function")
def fresh_database():
    """Create new database for each test."""
    db = create_database()
    populate_test_data(db)
    yield db
    drop_database(db)
```

**Pros**:
- ✅ Perfect isolation
- ✅ Simple implementation
- ✅ No snapshot needed

**Cons**:
- ❌ Slow (database created per test)
- ❌ High overhead for large test suites

### Pattern 3: Transaction Rollback (Database-Specific)

**Use when**: Using SQL databases with transaction support

```python
@pytest.fixture(scope="function", autouse=True)
def transaction_rollback(db_session):
    """Rollback transaction after each test."""
    transaction = db_session.begin_nested()
    yield
    transaction.rollback()
```

**Pros**:
- ✅ Very fast (no database recreation)
- ✅ Built-in database feature

**Cons**:
- ⚠️ Doesn't work for all databases (BaseX has no transactions)
- ⚠️ May not catch all side effects

## Debugging Fixture Issues

### Symptom Checklist

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| Tests pass individually, fail together | Fixture scope conflict or test pollution | Check fixture scopes, add isolation |
| Tests fail randomly | Race conditions or shared state | Use autouse fixtures for cleanup |
| Database empty during test | Fixture destroying pristine data | Remove destructive fixtures from child conftest |
| Session fixture not running | Import errors or wrong scope | Check pytest collection, add debug logging |

### Debug Techniques

**1. Add Debug Logging**
```python
def _log_state(label: str) -> None:
    if os.getenv('DEBUG_FIXTURES', 'false') == 'true':
        state = inspect_current_state()
        print(f"[FIXTURE-DEBUG] {label} | state={state}")
```

**2. Check Fixture Execution Order**
```bash
pytest tests/e2e/ --setup-show
```

**3. Run with Verbosity**
```bash
pytest tests/e2e/ -vv --tb=short
```

**4. Bisect Test Order**
```bash
# Find which test causes pollution
pytest tests/e2e/test_a.py tests/e2e/test_b.py -v
pytest tests/e2e/test_b.py tests/e2e/test_c.py -v
# ... narrow down the culprit
```

## Common Anti-Patterns

### ❌ Anti-Pattern 1: Mixing Test Type Fixtures

```python
# tests/conftest.py - used by ALL tests (unit, integration, e2e)
@pytest.fixture
def database():
    return create_empty_database()  # Wrong for e2e!

# tests/e2e/test_something.py
def test_something(database):  # Gets EMPTY database!
    # Expected 3 entries, got 0
    pass
```

**Fix**: Use separate conftest.py files for different test types
```python
# tests/conftest.py - unit/integration tests
@pytest.fixture
def database():
    return create_empty_database()

# tests/e2e/conftest.py - e2e tests only
@pytest.fixture
def database():
    return create_database_with_pristine_data()
```

### ❌ Anti-Pattern 2: Module-Level Side Effects

```python
# tests/conftest.py
import pytest

# ❌ BAD: Runs at import time, BEFORE session fixtures!
TEST_DB_NAME = os.getenv('TEST_DB_NAME') or create_test_db()

@pytest.fixture(scope="session")
def pristine_database():
    # Uses TEST_DB_NAME which was created EMPTY at import time!
    pass
```

**Fix**: Move side effects into fixtures
```python
# tests/conftest.py
import pytest

@pytest.fixture(scope="session")
def test_db_name():
    # Create at fixture time, not import time
    return os.getenv('TEST_DB_NAME') or create_test_db()

@pytest.fixture(scope="session")
def pristine_database(test_db_name):
    populate_test_data(test_db_name)
    yield test_db_name
```

### ❌ Anti-Pattern 3: Implicit Dependencies

```python
# tests/e2e/conftest.py
@pytest.fixture(scope="session")
def setup_database():
    # Assumes some other fixture already ran
    db_name = get_current_db()  # ❌ What if it doesn't exist?
    populate_test_data(db_name)
```

**Fix**: Explicit dependencies
```python
@pytest.fixture(scope="session")
def setup_database(base_database):  # ✅ Explicit dependency
    populate_test_data(base_database)
    yield base_database
```

## Recommendations for This Project

### Immediate Actions

1. **✅ DONE**: Remove `basex_test_connector` from e2e test files
2. **✅ DONE**: Ensure session fixture creates pristine database
3. **✅ DONE**: Add debug instrumentation for troubleshooting

### Future Improvements

1. **Separate conftest hierarchy**:
   ```
   tests/
   ├── conftest.py              # Common fixtures (minimal)
   ├── unit/
   │   └── conftest.py          # Unit test fixtures (mocks, empty DB)
   ├── integration/
   │   └── conftest.py          # Integration fixtures (real DB, no data)
   └── e2e/
       └── conftest.py          # E2e fixtures (real DB, pristine data)
   ```

2. **Explicit fixture naming**:
   - `empty_database` - for unit tests
   - `real_database` - for integration tests  
   - `pristine_database` - for e2e tests
   - Prevents confusion about which database fixture to use

3. **Fixture documentation**:
   ```python
   @pytest.fixture(scope="session", autouse=True)
   def setup_e2e_test_database():
       """
       Creates pristine e2e test database with 3 test entries.
       
       Scope: session (created once)
       Autouse: Yes (runs automatically)
       Dependencies: None
       Side effects: Creates database, sets environment variables
       Cleanup: Drops database at session end
       
       ❌ DO NOT request basex_test_connector in e2e tests!
       Use this fixture implicitly via autouse.
       """
   ```

4. **Fixture testing**:
   ```python
   # tests/e2e/test_fixtures.py
   def test_pristine_database_has_correct_entries(setup_e2e_test_database):
       """Meta-test: Verify fixture provides expected starting state."""
       db_name = setup_e2e_test_database
       entries = get_entries(db_name)
       assert len(entries) == 3
       assert 'test_entry_1' in entries
   ```

## Summary

### Key Principles

1. **Scope matches lifecycle**: Use session scope for expensive setup, function scope for isolation
2. **Explicit dependencies**: Always declare fixture dependencies explicitly
3. **No side effects at import**: Move all setup into fixtures
4. **Autouse for safety**: Use autouse for setup/teardown that should ALWAYS run
5. **Separate test types**: Different conftest files for unit/integration/e2e tests

### Testing the Fixtures

When adding/modifying fixtures, verify:
- ✅ Tests pass individually
- ✅ Tests pass when run together  
- ✅ Tests pass in full suite
- ✅ Database state is correct at each test start
- ✅ No leftover state after test suite

### Golden Rule

**"If your tests pass individually but fail together, you have a fixture isolation problem."**

The fix is usually one of:
1. Wrong fixture scope (use session for shared setup)
2. Missing cleanup (use autouse teardown fixtures)
3. Conflicting fixtures (remove or rename conflicting fixtures)
4. Side effects at import (move to fixtures)

---

*Document created: 2026-01-10*  
*Based on fixing database isolation issues in e2e test suite*
