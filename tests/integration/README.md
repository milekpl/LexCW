# Integration Tests

This directory contains integration tests that test multiple components working together, including:

## What are Integration Tests?

Integration tests verify that different parts of the application work correctly when combined. They typically:

- Use real database connections (BaseX, PostgreSQL)
- Make HTTP requests using Flask test client
- Test API endpoints end-to-end
- Test UI components with real backend services
- Test file I/O operations
- Test complete workflows and user scenarios

## Organization

All integration tests are marked with `@pytest.mark.integration` and are located in this directory.

## Running Integration Tests

### Run all integration tests:
```bash
pytest tests/integration/ -m integration
```

### Run only unit tests (excluding integration tests):
```bash
pytest tests/ -m 'not integration'
```

### Run specific integration test categories:
```bash
# API integration tests
pytest tests/integration/ -k "api"

# Database integration tests  
pytest tests/integration/ -k "basex or postgresql"

# UI integration tests
pytest tests/integration/ -k "ui"
```

## Test Categories

### API Integration Tests
- `test_api_integration.py` - Core API endpoint testing
- `test_api_comprehensive.py` - Comprehensive API testing
- `test_entries_api_*.py` - Entry-specific API tests
- `test_search_*.py` - Search API tests

### Database Integration Tests
- `test_basex_connector.py` - BaseX database integration
- `test_postgresql_*.py` - PostgreSQL integration
- `test_real_integration.py` - Real database operations

### UI Integration Tests
- `test_*_ui.py` - UI component integration tests
- `test_entry_form_*.py` - Entry form integration
- `test_dashboard_*.py` - Dashboard integration

### Workflow Integration Tests
- `test_phase_*.py` - Multi-phase workflow tests
- `test_complete_*.py` - End-to-end workflow tests
- `test_*_lifecycle.py` - Complete lifecycle tests

## Test Statistics

- **Total Integration Tests**: 781
- **Total Unit Tests**: 33 (in main tests/ directory)
- **Test Files Moved**: 78+ files organized into integration/

## Requirements

Integration tests may require:
- Running BaseX server (localhost:1984)
- PostgreSQL server (for PostgreSQL integration tests)
- Flask application running (for some UI tests)

Some integration tests will skip automatically if required services are not available.

## Markers

All integration tests use the `@pytest.mark.integration` marker. Additional markers may include:
- `@pytest.mark.selenium` - Tests requiring Selenium WebDriver
- `@pytest.mark.postgresql` - Tests requiring PostgreSQL
- `@pytest.mark.performance` - Performance-focused tests

## Contributing

When adding new integration tests:

1. Place them in this `tests/integration/` directory
2. Add the `@pytest.mark.integration` marker to test classes and functions
3. Use descriptive names that indicate what components are being integrated
4. Include proper setup/teardown for any external dependencies
5. Make tests skip gracefully if required services are unavailable

## Migration Notes

This organization was created by automatically analyzing test files for integration patterns such as:
- Flask test client usage
- Database connector usage
- API endpoint testing
- Multi-component workflows
- Real file I/O operations

The migration script identified integration tests based on code patterns and moved them to this directory while adding appropriate pytest markers.