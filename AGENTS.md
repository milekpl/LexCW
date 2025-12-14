# AGENTS.md - Development Guidelines for Agentic Coders

## Build/Lint/Test Commands

### Python Testing
- **Single test**: `python -m pytest tests/unit/test_file.py::test_function -v`
- **Unit tests**: `python -m pytest tests/unit/ -v -m unit`
- **Integration tests**: `python -m pytest tests/integration/ -v -m integration`
- **Coverage**: `python -m pytest --cov=app tests/`

### JavaScript Testing
- **All JS tests**: `npm run test:js`
- **Specific module**: `npm run test:lift-serializer`
- **Coverage**: `npm run test:js:coverage`

### Linting/Formatting
- **JS lint**: `npm run lint:js`
- **Python lint**: `flake8 app/`
- **Python format**: `black app/`

## Code Style Guidelines

### Python
- **Style**: PEP 8 compliance, 4-space indentation
- **Type hints**: Required for all function signatures (use Optional for nullable)
- **Docstrings**: Google-style with Args/Returns/Raises sections
- **Imports**: Standard library → Third-party → Local (blank lines between groups)

### JavaScript
- **Style**: ES6+ patterns, JSDoc comments for functions
- **Modules**: Use ES6 import/export, avoid global variables
- **Naming**: camelCase for variables/functions, PascalCase for classes

## Key Conventions

- **Error handling**: Custom ValidationError class, consistent JSON API responses
- **Testing**: Arrange-Act-Assert pattern, descriptive test names with pytest markers
- **Dependencies**: Use injector library for DI, singleton scope for services
- **Logging**: Contextual logging with appropriate levels (DEBUG/INFO/WARNING/ERROR)