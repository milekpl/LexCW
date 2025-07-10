# VS Code Test Runner Configuration

This guide explains how to configure VS Code to properly run your tests.

## Issues Fixed

1. ✅ **Unknown pytest marks**: Registered all custom marks in `pytest.ini`
2. ✅ **Tests in wrong directories**: Moved unit tests from integration directory
3. ✅ **VS Code test discovery**: Configured proper test discovery patterns

## VS Code Configuration

### 1. Test Discovery Settings

The `.vscode/settings.json` file is configured with:

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": [
        "tests",
        "--tb=short",
        "--strict-markers",
        "-v",
        "--disable-warnings"
    ],
    "python.testing.autoTestDiscoverOnSaveEnabled": true,
    "python.testing.cwd": "${workspaceFolder}"
}
```

### 2. Pytest Configuration

The `pytest.ini` file registers all custom marks:

- `integration` - Integration tests (require real database)
- `unit` - Unit tests (use mocking)
- `selenium` - Selenium WebDriver tests
- `performance` - Performance/benchmark tests
- `postgresql` - PostgreSQL-specific tests
- And more...

## Running Tests in VS Code

### 1. Test Explorer

1. Open VS Code
2. Go to **View > Command Palette** (`Ctrl+Shift+P`)
3. Type "Python: Configure Tests"
4. Select "pytest"
5. Select "tests" as the test directory

### 2. Test Discovery

VS Code should now automatically discover:
- **Unit tests** in `tests/` directory (marked as `@pytest.mark.unit`)
- **Integration tests** in `tests/integration/` directory (marked as `@pytest.mark.integration`)

### 3. Running Tests

#### From Test Explorer:
- Click the test icon in the sidebar
- Run individual tests or test classes
- Run all unit tests or all integration tests

#### From Command Palette:
- `Python: Run All Tests` - Runs all tests
- `Python: Run Tests in Current File` - Runs tests in current file

#### From Terminal:
```bash
# Run unit tests only (fast)
pytest tests/ -m 'not integration'

# Run integration tests only (requires BaseX)
pytest tests/integration/ -m integration

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_entry_model_comprehensive.py
```

## Test Categories

### Unit Tests (Fast, Mocked)
- Location: `tests/test_*.py`
- Mark: `@pytest.mark.unit` (automatically applied)
- Dependencies: All mocked
- Execution: Very fast (< 1 second per test)

### Integration Tests (Real Database)
- Location: `tests/integration/test_*.py`
- Mark: `@pytest.mark.integration` (automatically applied)
- Dependencies: Real BaseX database with sample data
- Execution: Slower (real I/O operations)

## Troubleshooting

### Tests Not Discovered

1. **Check Python Interpreter**:
   - `Ctrl+Shift+P` → "Python: Select Interpreter"
   - Choose the correct Python environment

2. **Refresh Test Discovery**:
   - `Ctrl+Shift+P` → "Python: Refresh Tests"

3. **Check Test Configuration**:
   - `Ctrl+Shift+P` → "Python: Configure Tests"
   - Ensure pytest is selected and tests directory is correct

### Unknown Mark Warnings

If you see warnings like "Unknown pytest.mark.unit":
1. Check that `pytest.ini` exists in the project root
2. Verify all marks are registered in the `markers` section
3. Restart VS Code to reload configuration

### Integration Tests Skipped

Integration tests are skipped by default unless:
1. You run with `--integration` flag
2. You run with `-m integration` marker
3. BaseX server is available

To run integration tests in VS Code:
1. Open terminal in VS Code
2. Run: `pytest tests/integration/ -m integration`

### Performance Issues

- **Unit tests** should be very fast (all mocked)
- **Integration tests** may be slower (real database)
- Use unit tests for development, integration tests for CI/CD

## Test File Organization

```
tests/
├── conftest.py                 # Unit test fixtures (mocked)
├── test_*.py                   # Unit tests
├── integration/
│   ├── conftest.py            # Integration test fixtures (real DB)
│   └── test_*.py              # Integration tests
├── unit/                      # Optional: explicit unit tests
└── VSCODE_TEST_SETUP.md       # This guide
```

## Best Practices

1. **Use Test Explorer**: Visual interface for running tests
2. **Run Unit Tests Frequently**: Fast feedback during development
3. **Run Integration Tests Before Commits**: Ensure everything works together
4. **Use Debugging**: Set breakpoints and debug tests in VS Code
5. **Check Test Output**: Use the Test Output panel for detailed results

## Debugging Tests

1. Set breakpoints in your test code
2. Right-click on test in Test Explorer
3. Select "Debug Test"
4. VS Code will stop at breakpoints for inspection

## Environment Variables

For integration tests, you may need to set:
- `BASEX_HOST` (default: localhost)
- `BASEX_PORT` (default: 1984)
- `BASEX_USERNAME` (default: admin)
- `BASEX_PASSWORD` (default: admin)

Set these in VS Code:
1. Create `.env` file in project root
2. Add variables: `BASEX_HOST=localhost`
3. Install Python-dotenv extension