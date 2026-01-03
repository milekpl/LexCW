# Template and HTML Validation System

This project includes a comprehensive validation system for Jinja2 templates and HTML syntax that can be integrated into CI/CD pipelines.

## Overview

The template validation system provides:

1. **Jinja2 Syntax Validation** - Validates Jinja2 template syntax without requiring Flask context
2. **HTML Syntax Validation** - Validates HTML structure using BeautifulSoup
3. **Template Rendering Validation** - Tests that templates can be rendered in a Flask context
4. **CI/CD Integration** - Can be run as part of automated testing pipelines
5. **VS Code Integration** - Works with existing test infrastructure

## Components

### 1. `check_jinja.py` - Validation Script

A command-line script that can validate:
- Specific template files
- All templates in the project
- Jinja2 syntax only
- HTML syntax only
- Template rendering capability

### 2. `tests/test_template_validation.py` - Test Suite

A pytest-compatible test suite that:
- Validates individual templates
- Validates all templates in the project
- Tests the validation script functionality
- Integrates with existing test infrastructure

## Usage

### Command Line

```bash
# Validate a specific template for Jinja syntax
python check_jinja.py app/templates/entry_form.html --jinja-only

# Validate a specific template for HTML syntax
python check_jinja.py app/templates/entry_form.html --html-only

# Validate both syntax types for a specific template
python check_jinja.py app/templates/entry_form.html

# Validate all templates in the project
python check_jinja.py --all

# Test template rendering capability
python check_jinja.py app/templates/entry_form.html --render-test
```

### npm Scripts

```bash
# Run template validation tests
npm run test:templates

# Run all tests including templates
npm run test:all-with-templates
```

### pytest Integration

```bash
# Run template validation tests
python -m pytest tests/test_template_validation.py -v

# Run with other tests
pytest --js-tests  # This will also include template validation
```

## Features

### 1. Jinja2 Syntax Validation
- Validates Jinja2 template syntax using the Jinja2 parser
- Detects syntax errors like unmatched tags, invalid expressions
- Works without Flask application context
- Provides detailed error messages with line numbers

### 2. HTML Syntax Validation
- Validates HTML structure using BeautifulSoup
- Detects unclosed tags, malformed HTML
- Works with Jinja2 template syntax mixed in HTML

### 3. Rendering Validation
- Tests that templates can be rendered in a Flask context
- Validates template dependencies and context variables
- Catches runtime errors that syntax validation might miss

### 4. Batch Processing
- Validate all templates in the project at once
- Generate comprehensive reports
- Fail fast on first error or continue to report all errors

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Template Validation
on: [push, pull_request]
jobs:
  template-validation:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run template validation
      run: |
        python check_jinja.py --all
    - name: Run template tests
      run: |
        python -m pytest tests/test_template_validation.py -v
```

### GitLab CI Example

```yaml
template_validation:
  stage: test
  script:
    - python check_jinja.py --all
    - python -m pytest tests/test_template_validation.py -v
  coverage: '/\d+\.\d+\%/'
```

## Integration with Existing Test Suite

The template validation integrates seamlessly with the existing JavaScript and Python test infrastructure:

- Uses the same pytest configuration
- Integrates with VS Code test explorer
- Can be run alongside JavaScript tests using `--js-tests` flag
- Follows the same test discovery patterns

## Benefits

1. **Early Error Detection** - Catches template errors before deployment
2. **Improved Code Quality** - Enforces proper template syntax
3. **CI/CD Integration** - Automated validation in pipelines
4. **Developer Experience** - Clear error messages with line numbers
5. **Comprehensive Coverage** - Validates both syntax and rendering
6. **Performance** - Fast validation without full application startup

## Troubleshooting

### Common Issues

1. **Missing Dependencies**: Ensure `beautifulsoup4` is installed
2. **File Not Found**: Use relative paths from project root
3. **Flask Context Errors**: Rendering tests require Flask application context

### Error Messages

- `Jinja syntax error`: Check for unmatched `{% %}`, `{{ }}`, or `{# #}` tags
- `HTML parsing issues`: Check for unclosed HTML tags
- `Template rendering error`: Check for missing context variables or filters

## Maintenance

The validation system automatically discovers new template files in the `app/templates/` directory and its subdirectories. No configuration changes are needed when adding new templates.

Regular validation helps maintain template quality and prevents syntax errors from reaching production.