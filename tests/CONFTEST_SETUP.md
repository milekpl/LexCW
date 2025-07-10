# Test Configuration Setup

This document explains the conftest.py setup for unit and integration tests.

## Overview

The test suite now has separate configurations for unit and integration tests:

- **Unit tests** (`tests/conftest.py`) - Use mocking, no real database connections
- **Integration tests** (`tests/integration/conftest.py`) - Set up real BaseX database with sample LIFT files

## Unit Tests Configuration (`tests/conftest.py`)

### Purpose
- Fast execution with no external dependencies
- Uses mocking for all database and external service calls
- Suitable for testing individual components in isolation

### Key Features
- **Mock BaseX Connector**: All database operations are mocked
- **Mock Dictionary Service**: Returns predictable test data
- **Mock Flask App**: Configured with mocked dependencies
- **Automatic Mocking**: External dependencies (BaseX, Redis, XML parsing) are automatically mocked
- **Sample Data**: Provides sample Entry, Sense, Example objects for testing

### Usage
```bash
# Run unit tests only
pytest tests/ -m 'not integration'

# Run specific unit test
pytest tests/test_entry_model_comprehensive.py
```

### Fixtures Available
- `mock_basex_connector` - Mocked BaseX connector
- `mock_dict_service` - Mocked dictionary service with predictable responses
- `app` - Flask app with mocked dependencies
- `client` - Test client for mocked Flask app
- `sample_entry` - Sample Entry object
- `sample_entries` - List of sample Entry objects

## Integration Tests Configuration (`tests/integration/conftest.py`)

### Purpose
- Tests real interactions between components
- Uses actual BaseX database loaded with sample LIFT files
- Tests end-to-end workflows and API endpoints

### Key Features
- **Real BaseX Database**: Creates isolated test database for each test
- **Sample LIFT Data**: Loads `sample-lift-file.lift` and `sample-lift-file.lift-ranges`
- **Real Dictionary Service**: Connected to test database with real data
- **Automatic Cleanup**: Test databases are automatically created and destroyed
- **Skip Logic**: Tests are skipped if BaseX server is not available

### Sample Data Loading
The integration tests automatically load:
- `sample-lift-file/sample-lift-file.lift` - Complete LIFT dictionary data
- `sample-lift-file/sample-lift-file.lift-ranges` - All LIFT range definitions

### Usage
```bash
# Run integration tests only
pytest tests/integration/ -m integration

# Run specific integration test
pytest tests/integration/test_api_integration.py

# Run all tests (unit + integration)
pytest tests/
```

### Fixtures Available
- `basex_test_connector` - Real BaseX connector with test database
- `dict_service_with_db` - Real dictionary service with sample data
- `app` - Flask app with real database connections
- `client` - Test client for real Flask app
- `sample_lift_files` - Paths to sample LIFT files
- `sample_entry` - Sample Entry object

## Environment Requirements

### Unit Tests
- No external dependencies required
- All services are mocked

### Integration Tests
- **BaseX Server**: Must be running on localhost:1984 (or configured via environment variables)
- **Sample Files**: Must exist in `sample-lift-file/` directory
- **Environment Variables** (optional):
  - `BASEX_HOST` (default: localhost)
  - `BASEX_PORT` (default: 1984)
  - `BASEX_USERNAME` (default: admin)
  - `BASEX_PASSWORD` (default: admin)

## Test Database Management

### Integration Tests
- Each test gets a unique database: `test_{random_id}`
- Database is populated with sample LIFT files
- Automatic cleanup after test completion
- No interference between tests

### Unit Tests
- No real databases used
- All database operations return mocked responses

## Migration from Old Setup

### What Changed
1. **Separated Concerns**: Unit tests now use pure mocking, integration tests use real databases
2. **Sample Data**: Integration tests load real sample LIFT files instead of minimal test data
3. **Automatic Mocking**: Unit tests automatically mock external dependencies
4. **Better Isolation**: Each integration test gets its own database

### Backward Compatibility
- Existing test fixtures are maintained for compatibility
- Tests should work without modification
- Legacy fixture names are aliased to new implementations

## Best Practices

### Unit Tests
- Test individual components in isolation
- Use mocked dependencies
- Focus on business logic and edge cases
- Fast execution (< 1 second per test)

### Integration Tests
- Test component interactions
- Use real database with sample data
- Test API endpoints end-to-end
- Verify data persistence and retrieval
- Test with realistic data volumes

### When to Use Which
- **Unit Tests**: Model validation, utility functions, business logic
- **Integration Tests**: API endpoints, database operations, UI workflows, multi-component features

## Troubleshooting

### Integration Tests Failing
1. Check BaseX server is running: `http://localhost:8984`
2. Verify sample files exist: `sample-lift-file/sample-lift-file.lift`
3. Check database permissions
4. Review test logs for connection errors

### Unit Tests Failing
1. Check for unmocked external dependencies
2. Verify mock configurations in conftest.py
3. Ensure tests don't require real database connections

### Performance Issues
- Unit tests should be very fast (mocked)
- Integration tests may be slower (real database operations)
- Consider running unit tests during development, integration tests in CI/CD