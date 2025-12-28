# Integrated JavaScript and Python Testing

This project includes an integrated testing system that allows you to run both Python and JavaScript tests from a single command, with full integration in VS Code.

## Overview

The integrated testing system provides:

1. **Unified Test Execution**: Run JavaScript tests from Python using `pytest`
2. **VS Code Integration**: All tests can be run from VS Code's test explorer
3. **JavaScript Linting**: ESLint integration for code quality
4. **Browser Compatibility Testing**: Validation of JavaScript for browser environments
5. **Coverage Reports**: Combined coverage for both Python and JavaScript

## Setup

### Prerequisites

Make sure you have Node.js and npm installed:

```bash
node --version
npm --version
```

### Install Dependencies

```bash
npm install
```

This will install Jest, ESLint, and other JavaScript testing dependencies.

## Running Tests

### Run All Tests (Python + JavaScript)

```bash
# Run all Python tests including JavaScript tests
pytest --js-tests

# Run all tests with linting
pytest --js-tests --js-lint

# Run with coverage
pytest --js-tests --js-lint --cov=app
```

### Run Only JavaScript Tests

```bash
# Run only JavaScript tests through Python
pytest tests/test_js_integration.py -v

# Run JavaScript tests directly with Jest
npm test

# Run specific JavaScript test
npm run test:js -- tests/unit/test_lift_xml_serializer.test.js
```

### Run JavaScript Linting

```bash
# Run ESLint through Python
pytest --js-lint

# Run ESLint directly
npm run lint:js
```

## VS Code Integration

### Test Explorer Configuration

The testing system is fully integrated with VS Code's Python test explorer. To enable it:

1. Open VS Code in the project directory
2. Make sure the Python extension is installed
3. Make sure the project's virtual environment is selected
4. Open the Test Explorer (View → Test Explorer)

### VS Code Settings

The following settings in `.vscode/settings.json` enable proper test discovery:

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": [
        ".",
        "--js-tests",
        "--js-lint"
    ]
}
```

### Running Tests from VS Code

1. Open the Test Explorer
2. You'll see both Python tests and JavaScript tests (when `--js-tests` is enabled)
3. Click on individual tests to run them
4. Use the run/debug buttons to execute test groups

## Test Organization

### JavaScript Tests

JavaScript tests are located in:
- `tests/unit/` - Unit tests for JavaScript modules
- `app/static/js/` - JavaScript source files with inline tests

Currently supported JavaScript test types:
- Jest tests (`.test.js`, `.spec.js` files)
- Node.js script tests (`.js` files that can be run with `node`)

### Python Tests

Python tests remain in:
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests
- `tests/e2e/` - End-to-end tests

## JavaScript Test Runner API

The `tests/js_test_runner.py` module provides a Python API for running JavaScript tests:

```python
from tests.js_test_runner import JSTestRunner

runner = JSTestRunner()
results = runner.run_jest_tests()
lint_results = runner.run_eslint()
```

## Configuration

### Jest Configuration

Located at `jest.config.js`, configured for:
- Node.js testing environment
- Coverage collection from `app/static/js/`
- Test files in `tests/unit/` and `tests/integration/`

### ESLint Configuration

Located in `package.json` under `devDependencies`, configured for:
- Modern JavaScript syntax
- Browser and Node.js compatibility
- Code quality rules

## Continuous Integration

The integrated testing system works with CI/CD pipelines:

```bash
# In CI environment
npm install
pytest --js-tests --js-lint --cov=app
```

## Troubleshooting

### Common Issues

1. **"Jest not available"**: Run `npm install` to install dependencies
2. **"Node.js not found"**: Make sure Node.js is installed and in your PATH
3. **JavaScript syntax errors**: Run `npm run lint:js` to identify issues

### Debugging JavaScript Tests

For debugging JavaScript tests specifically:

```bash
# Run Jest in debug mode
npm test -- --debug

# Run specific test with more verbose output
npm run test:js -- path/to/test.js --verbose
```

## Best Practices

1. **Write tests for both Python and JavaScript**: Ensure comprehensive coverage
2. **Use the same test data**: Share test fixtures between Python and JavaScript when possible
3. **Validate browser compatibility**: Test that JavaScript works in browser environments
4. **Run linting regularly**: Use `npm run lint:js` to maintain code quality
5. **Update tests together**: When changing functionality, update both Python and JavaScript tests

## Adding New JavaScript Tests

To add new JavaScript tests:

1. Create test file in `tests/unit/` with `.test.js` extension for Jest tests
2. Or create Node.js script test in `tests/unit/` with `.js` extension
3. Tests will be automatically discovered when running with `--js-tests`

Example Jest test:
```javascript
// tests/unit/my_feature.test.js
test('should do something', () => {
    expect(result).toBe(expected);
});
```

Example Node.js script test:
```javascript
// tests/unit/my_script_test.js
// Simple test that can be run with: node my_script_test.js
const assert = require('assert');
// Your test code here
```