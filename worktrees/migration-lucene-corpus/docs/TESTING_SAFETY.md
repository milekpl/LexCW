# Testing Safety Guidelines

This document describes the safety mechanisms implemented to prevent tests from overwriting production databases and provides guidelines for safe testing practices.

## Overview

The testing framework has been enhanced with multiple layers of protection to ensure that:

1. **Production databases are never accidentally modified by tests**
2. **Test databases are properly isolated and cleaned up**
3. **Environment variables don't leak between test runs**
4. **Failed cleanups don't leave the system in an inconsistent state**

## Database Isolation Strategy

### Safe Database Naming

All test databases follow a strict naming pattern:

```
test_YYYYMMDD_HHMM_<test_type>_<random_suffix>
```

**Example:** `test_20251225_1430_e2e_abc123`

- `test_` - Required prefix for all test databases
- `YYYYMMDD` - Creation date (year, month, day)
- `HHMM` - Creation time (hour, minute)
- `<test_type>` - Type of test (unit, integration, e2e)
- `<random_suffix>` - 6-character random hex string

### Protected Database Names

The following database names are **protected** and will never be dropped or modified by tests:

- `dictionary`
- `production`
- `backup`
- `main`
- `dev`
- `staging`

Any database name containing these patterns is considered unsafe for testing.

## Safety Features Implemented

### 1. Safe Database Naming Utilities

**Location:** `tests/test_db_safety_utils.py`

**Functions:**

- `is_safe_database_name(db_name: str) -> bool` - Validate database name safety
- `generate_safe_db_name(test_type: str) -> str` - Generate safe, unique names
- `is_protected_database(db_name: str) -> bool` - Check for protected names
- `extract_db_timestamp(db_name: str) -> datetime` - Extract creation timestamp

### 2. Isolated BaseX Connector Fixture

**Location:** `tests/conftest.py`

**Fixture:** `isolated_basex_connector`

**Safety Features:**

- Uses safe database naming with timestamp and test type
- Validates database name safety before creation
- Restores original environment variables after test
- Performs atomic cleanup with verification
- Prevents environment variable leakage between tests

**Usage:**

```python
def test_something(isolated_basex_connector):
    # Use the connector - it's completely isolated
    entries = isolated_basex_connector.execute_query("xquery //lift:entry")
    # Database will be automatically cleaned up after test
```

### 3. Safe E2E Test Fixtures

**Location:** `tests/e2e/conftest.py`

**Fixture:** `setup_e2e_test_database`

**Safety Features:**

- Uses safe database naming for E2E tests
- Stores and restores original environment variables
- Atomic cleanup with database existence verification
- Prevents environment variable leakage

### 4. BaseX Connector Safety Checks

**Location:** `app/database/basex_connector.py`

**Enhanced `connect()` method:**

- Checks if running in test mode (`FLASK_CONFIG=testing` or `TESTING=true`)
- Validates database name safety before connecting
- Refuses to connect to unsafe databases in test mode
- Logs safety violations

### 5. Test Database Cleanup Utility

**Location:** `scripts/clean_test_databases.py`

**Features:**

- Lists all test databases matching the safe naming pattern
- Cleans up orphaned test databases older than specified age
- Dry-run mode to preview cleanup actions
- Atomic cleanup with verification
- Comprehensive logging

**Usage:**

```bash
# Dry run - show what would be cleaned
python scripts/clean_test_databases.py --dry-run

# Actually clean databases older than 7 days
python scripts/clean_test_databases.py --force

# Clean databases older than 14 days
python scripts/clean_test_databases.py --force --max-age 14

# List all databases
python scripts/clean_test_databases.py --list-all
```

## Running Tests Safely

### Recommended Test Commands

```bash
# Run all tests (uses safe fixtures automatically)
pytest

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with verbose logging
pytest -v
```

### Using Safe Fixtures

The safest way to run tests is to use the provided safe fixtures:

**Isolated BaseX Connector:**

```python
@pytest.mark.integration
def test_with_isolation(isolated_basex_connector):
    # This automatically gets a safe, isolated database
    entries = isolated_basex_connector.execute_query("xquery //lift:entry")
    # Database will be automatically cleaned up after test
```

**Safe Database Name:**

```python
@pytest.mark.integration
def test_with_safe_name(safe_test_db_name):
    # Get a safe database name for manual use
    db_name = safe_test_db_name
    assert is_safe_database_name(db_name)
```

**Test Markers (for documentation):**

The `safe_db` and `unsafe_db` markers are available for documentation purposes:

```python
@pytest.mark.safe_db
def test_safe_operation():
    # This test uses safe database isolation
    pass

@pytest.mark.unsafe_db
def test_legacy_operation():
    # This test requires manual review
    pass
```

## Environment Variable Management

### Automatic Environment Isolation

The test fixtures automatically manage environment variables:

1. **Before test:** Store original `TEST_DB_NAME` and `BASEX_DATABASE`
2. **During test:** Set isolated values for the current test
3. **After test:** Restore original values or remove them if they didn't exist

### Manual Environment Setup

If you need to set environment variables manually:

```bash
# Set safe test database name
export TEST_DB_NAME=$(python -c "from tests.test_db_safety_utils import generate_safe_db_name; print(generate_safe_db_name('manual'))")
export BASEX_DATABASE=$TEST_DB_NAME

# Run tests
pytest tests/specific_test.py

# Clean up
unset TEST_DB_NAME
unset BASEX_DATABASE
```

## Emergency Procedures

### If Tests Accidentally Affect Production

1. **Stop all test processes immediately:**
   ```bash
   pkill -f pytest
   ```

2. **Restore from backup if needed:**
   ```bash
   # Use your BaseX backup procedures
   ```

3. **Identify the root cause:**
   - Check test logs for safety violations
   - Review recent test changes
   - Verify environment variable settings

4. **Add additional safety checks:**
   - Enhance the safety utilities
   - Add more validation to the connectors
   - Improve test isolation

### Manual Cleanup of Orphaned Test Databases

```bash
# List all test databases
python scripts/clean_test_databases.py --list-all

# Clean up orphaned databases (dry run first!)
python scripts/clean_test_databases.py --dry-run
python scripts/clean_test_databases.py --force
```

## Best Practices

### Writing Safe Tests

1. **Use the isolated fixtures:**
   ```python
   def test_with_isolation(isolated_basex_connector):
       # This automatically gets a safe, isolated database
   ```

2. **Avoid hardcoding database names:**
   ```python
   # Bad - hardcoded database name
   connector = BaseXConnector(database="dictionary")
   
   # Good - use environment or fixtures
   connector = BaseXConnector(database=os.environ.get('TEST_DB_NAME'))
   ```

3. **Mark tests appropriately:**
   ```python
   @pytest.mark.safe_db
   def test_safe_operation():
       # Uses safe isolation
   
   @pytest.mark.unsafe_db
   def test_legacy_operation():
       # Requires manual review
   ```

### Test Development Workflow

1. **Write tests using isolated fixtures**
2. **Run tests with `--safe-db` flag**
3. **Review test output for safety warnings**
4. **Clean up orphaned databases regularly**
5. **Monitor production databases during testing**

## Troubleshooting

### Common Issues and Solutions

**Issue:** Tests fail with "unsafe database name" error

**Solution:**
- Use the `safe_test_db_name` fixture or `generate_safe_db_name()` function
- Ensure database names follow the pattern: `test_YYYYMMDD_HHMM_<type>_<random>`

**Issue:** Tests hang or fail to clean up databases

**Solution:**
- Check for open database connections
- Use the cleanup script to manually remove orphaned databases
- Review the test cleanup logic

**Issue:** Environment variables leak between test runs

**Solution:**
- Use the isolated fixtures that manage environment variables automatically
- Check for manual environment variable modifications in tests
- Use `pytest --safe-db` to enable automatic cleanup

**Issue:** Production database is accidentally modified

**Solution:**
1. Stop all test processes immediately
2. Restore from backup if needed
3. Review the safety checks in `BaseXConnector.connect()`
4. Add the problematic database name to the protected list

## Technical Details

### Database Name Validation

The `is_safe_database_name()` function performs these checks:

1. **Prefix check:** Must start with `test_`
2. **Protected patterns:** Must not contain protected names
3. **Pattern matching:** Must match `test_\d{8}_\d{4}_[a-z]+_[a-f0-9]{6}`

### Environment Variable Isolation

The fixtures implement this pattern:

```python
# Store original values
original_test_db = os.environ.get('TEST_DB_NAME')
original_basex_db = os.environ.get('BASEX_DATABASE')

try:
    # Set isolated values
    os.environ['TEST_DB_NAME'] = safe_db_name
    os.environ['BASEX_DATABASE'] = safe_db_name
    
    # Run test
    yield connector
    
finally:
    # Restore original values
    if original_test_db:
        os.environ['TEST_DB_NAME'] = original_test_db
    elif 'TEST_DB_NAME' in os.environ:
        del os.environ['TEST_DB_NAME']
    
    # Same for BASEX_DATABASE
```

### Atomic Cleanup

The cleanup process follows these steps:

1. **Verify database exists** before attempting to drop
2. **Execute drop command** only if database is confirmed to exist
3. **Log cleanup actions** for auditing
4. **Handle exceptions gracefully** to prevent partial cleanup

## Monitoring and Maintenance

### Regular Maintenance Tasks

1. **Weekly cleanup of orphaned databases:**
   ```bash
   python scripts/clean_test_databases.py --force --max-age 7
   ```

2. **Monitor test database growth:**
   ```bash
   python scripts/clean_test_databases.py --list-all
   ```

3. **Review test safety logs:**
   - Check for safety violations
   - Monitor cleanup failures
   - Review environment variable warnings

### Continuous Improvement

1. **Add more protected database patterns** as needed
2. **Enhance safety checks** based on incident reviews
3. **Improve cleanup reliability** with better error handling
4. **Add more comprehensive logging** for debugging

## Conclusion

The implemented safety mechanisms provide multiple layers of protection to prevent tests from affecting production databases. By following the guidelines in this document and using the provided safety utilities, you can run tests with confidence that your production data is protected.

**Remember:** Always use the safe testing fixtures and regularly clean up orphaned test databases using the provided utility script.