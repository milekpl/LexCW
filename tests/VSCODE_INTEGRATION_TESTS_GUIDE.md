# VS Code Integration Tests Guide

## ✅ Problem Solved!

Integration tests are now properly configured and can be run from VS Code.

## What Was Fixed

1. **Removed automatic skipping**: Integration tests were being automatically skipped unless specific command line flags were used
2. **Updated conftest.py logic**: Now only skips integration tests when explicitly excluded (e.g., `-m "not integration"`)
3. **Added VS Code configurations**: Tasks, launch configurations, and proper settings

## Running Integration Tests in VS Code

### Method 1: Test Explorer (Recommended)

1. **Open Test Explorer**: Click the test tube icon in the sidebar
2. **Refresh Tests**: `Ctrl+Shift+P` → "Python: Refresh Tests"
3. **Run Integration Tests**: 
   - Expand `tests/integration/` folder in Test Explorer
   - Click the play button next to any integration test or test class
   - Right-click and select "Run Test" or "Debug Test"

### Method 2: Command Palette

1. **Open Command Palette**: `Ctrl+Shift+P`
2. **Run Tests**: Type "Python: Run Tests in Current File" (if viewing an integration test file)
3. **Debug Tests**: Type "Python: Debug Tests in Current File"

### Method 3: VS Code Tasks

1. **Open Command Palette**: `Ctrl+Shift+P`
2. **Run Task**: Type "Tasks: Run Task"
3. **Select Task**:
   - "Run Integration Tests Only"
   - "Run Unit Tests Only" 
   - "Run All Tests"

### Method 4: Debug Configurations

1. **Open Debug Panel**: `Ctrl+Shift+D`
2. **Select Configuration**:
   - "Debug Integration Tests" - Runs all integration tests with debugging
   - "Debug Unit Tests" - Runs all unit tests with debugging
   - "Debug All Tests" - Runs all tests with debugging
   - "Debug Current Test File" - Runs tests in currently open file
3. **Start Debugging**: Press F5 or click the green play button

### Method 5: Terminal in VS Code

```bash
# Integration tests only
python -m pytest tests/integration/ -v

# Specific integration test
python -m pytest tests/integration/test_basic.py::TestEntry::test_entry_creation -v

# Integration tests with debugging output
python -m pytest tests/integration/ -v -s
```

## Test Categories

### Unit Tests (Fast, Mocked)
- **Location**: `tests/test_*.py`
- **Dependencies**: All mocked
- **Run Command**: `pytest tests/ -m "not integration"`
- **VS Code**: Automatically discovered and runnable

### Integration Tests (Real Database)
- **Location**: `tests/integration/test_*.py`
- **Dependencies**: Real BaseX database with sample LIFT files
- **Run Command**: `pytest tests/integration/`
- **VS Code**: Now properly discovered and runnable

## Environment Setup for Integration Tests

### BaseX Server Requirements
Integration tests require a running BaseX server:

1. **Default Connection**:
   - Host: localhost
   - Port: 1984
   - Username: admin
   - Password: admin

2. **Custom Configuration** (optional):
   Set environment variables:
   ```bash
   BASEX_HOST=your-host
   BASEX_PORT=your-port
   BASEX_USERNAME=your-username
   BASEX_PASSWORD=your-password
   ```

3. **Sample Files**:
   Integration tests automatically load:
   - `sample-lift-file/sample-lift-file.lift`
   - `sample-lift-file/sample-lift-file.lift-ranges`

## VS Code Configuration Files

### `.vscode/settings.json`
```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests",
        "--tb=short",
        "--strict-markers",
        "-v",
        "--disable-warnings"
    ]
}
```

### `.vscode/tasks.json`
Provides tasks for:
- Run Unit Tests Only
- Run Integration Tests Only  
- Run All Tests

### `.vscode/launch.json`
Provides debug configurations for:
- Debug Unit Tests
- Debug Integration Tests
- Debug All Tests
- Debug Current Test File

## Test Statistics

- **Total Tests**: 1,043
- **Unit Tests**: 213 (fast, mocked)
- **Integration Tests**: 830 (real database)

## Troubleshooting

### Integration Tests Not Running

1. **Check BaseX Server**: Ensure BaseX is running on localhost:1984
2. **Refresh Test Discovery**: `Ctrl+Shift+P` → "Python: Refresh Tests"
3. **Check Sample Files**: Verify `sample-lift-file/` directory exists
4. **Check Python Interpreter**: `Ctrl+Shift+P` → "Python: Select Interpreter"

### Tests Showing as Skipped

1. **Unit Tests**: Should run normally (all mocked)
2. **Integration Tests**: Only skip if BaseX server unavailable or explicitly excluded

### Performance Issues

- **Unit Tests**: Very fast (< 1 second each)
- **Integration Tests**: Slower (real database operations)
- **Recommendation**: Use unit tests for development, integration tests for validation

## Best Practices

### Development Workflow
1. **Write Code**: Make changes to your code
2. **Run Unit Tests**: Quick feedback on business logic
3. **Run Integration Tests**: Comprehensive validation before commit
4. **Debug Issues**: Use VS Code debugger with breakpoints

### Test Selection
- **Unit Tests**: Test individual components, business logic, edge cases
- **Integration Tests**: Test component interactions, API endpoints, database operations

### VS Code Features
- **Test Explorer**: Visual test management
- **Debugging**: Set breakpoints in test code
- **Terminal Integration**: Run tests with full output
- **Problem Panel**: View test failures and errors

## Example: Running a Specific Integration Test

1. **Open Test File**: `tests/integration/test_basic.py`
2. **Set Breakpoint**: Click in the gutter next to a line in the test
3. **Debug Test**: Right-click on test in Test Explorer → "Debug Test"
4. **Inspect Variables**: Use VS Code's debug panel to inspect test state

The integration tests are now fully functional in VS Code! 🎉