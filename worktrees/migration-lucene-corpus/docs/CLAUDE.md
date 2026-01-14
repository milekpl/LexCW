# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Lexicographic Curation Workbench - A Flask-based dictionary management system for handling large-scale lexicographic data in LIFT format, with BaseX XML database backend.

## Architecture Overview

### Core Components

**Database Layer:**
- `app/database/basex_connector.py` - BaseX XML database connector (primary data store)
- `app/database/workset_db.py` - PostgreSQL integration for workset management
- Connection pooling handled via dependency injection pattern

**Service Layer:**
- `app/services/dictionary_service.py` - Core service for entry CRUD operations
- `app/services/merge_split_service.py` - Entry merge/split operations
- `app/services/ranges_service.py` - LIFT ranges management
- `app/services/lift_import_service.py` / `lift_export_service.py` - LIFT file operations
- `app/services/validation_engine.py` - Centralized validation system

**Parser Layer:**
- `app/parsers/lift_parser.py` - Main LIFT format parser
- `app/parsers/enhanced_lift_parser.py` - Enhanced parsing with validation
- `app/parsers/undefined_ranges_parser.py` - Handles undefined range values

**API Layer:**
- `app/api/entries.py` - Entry management endpoints
- `app/api/search.py` - Search functionality
- `app/api/export.py` - Export operations
- `app/api/display_profiles.py` - Display configuration
- `app/api/merge_split.py` - Merge/split operations

**Models:**
- `app/models/entry.py` - Entry model
- `app/models/sense.py` - Sense model
- `app/models/example.py` - Example model
- `app/models/pronunciation.py` - Pronunciation model
- `app/models/workset.py` - Workset management
- `app/models/display_profile.py` - Display configuration
- `app/models/project_settings.py` - Project-wide settings

**Frontend Views:**
- `app/views.py` - Main Flask routes and views
- `app/templates/` - Jinja2 templates

### Data Flow Architecture

1. **LIFT Import:** `lift_import_service.py` → `lift_parser.py` → `dictionary_service.py` → `basex_connector.py`
2. **Search:** `search.py` API → `dictionary_service.py` → `basex_connector.py` (XQuery)
3. **Export:** `dictionary_service.py` → `lift_export_service.py` → File output
4. **Validation:** `validation_engine.py` (centralized) used throughout

### Key Design Patterns

- **Dependency Injection:** Using `injector` for service management
- **Singleton Services:** Services configured as singletons in `app/__init__.py`
- **Blueprint Architecture:** Modular API and view routing
- **Context Managers:** Database connections use `@contextmanager`
- **Centralized Validation:** Single validation engine used across all entry operations

## Common Development Commands

### Running the Application
```bash
# Start the Flask application
python run.py

# Set specific configuration
FLASK_ENV=development python run.py
```

### Testing
```bash
# Run all tests
pytest

# Run specific test markers
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m e2e              # End-to-end tests (Playwright)
pytest -m selenium         # Selenium tests

# Run specific test files
pytest tests/unit/test_dictionary_service_search.py
pytest tests/integration/test_entry_update.py

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term tests/

# Run single test function
pytest tests/unit/test_file.py::test_function_name -v

# Run tests with specific Python module syntax
python -m pytest tests/unit/ -v --tb=short
```

### Code Quality & Linting
```bash
# Code formatting
black app tests/
black --check app tests/     # Check only

# Import sorting
isort app tests/
isort --check-only app tests/

# Linting
flake8 app tests/
flake8 app tests --count --select=E9,F63,F7,F82 --show-source --statistics

# Security checks
bandit -r app
safety check
```

### Database Management
```bash
# With Docker Compose (recommended for development)
docker-compose up -d postgres basex redis

# View logs
docker-compose logs -f flask_app

# Run tests in Docker
docker-compose --profile testing run test_runner pytest

# Stop all services
docker-compose down
```

### BaseX Setup (for local development without Docker)
```bash
# BaseX typically runs on ports 1984 (database) and 8080/8984 (HTTP)
# Configuration in .env or environment variables:
BASEX_HOST=localhost
BASEX_PORT=1984
BASEX_USERNAME=admin
BASEX_PASSWORD=admin
BASEX_DATABASE=dictionary
```

### Import/Export Operations
```bash
# Import LIFT file
python -m scripts.import_lift path/to/file.lift path/to/ranges.lift-ranges

# Export to LIFT
python -m scripts.export_lift path/to/output.lift

# Use custom scripts in /scripts/ directory
```

## Test Configuration

### pytest.ini Markers
- `@pytest.mark.unit` - Unit tests with mocking
- `@pytest.mark.integration` - Integration tests with real services
- `@pytest.mark.e2e` - End-to-end tests with Playwright
- `@pytest.mark.selenium` - Selenium WebDriver tests
- `@pytest.mark.postgresql` - Tests requiring PostgreSQL
- `@pytest.mark.word_sketch` - Word sketch functionality tests
- `@pytest.mark.parser_integration` - Parser integration tests
- `@pytest.mark.search_integration` - Search integration tests

### Test Structure
```
tests/
├── unit/                    # Fast unit tests
├── integration/            # Service integration tests
├── e2e/                    # End-to-end browser tests
├── conftest.py             # Shared fixtures
└── basex_test_utils.py     # BaseX test helpers
```

## Environment Variables Required

### For Development
```bash
# BaseX Connection
BASEX_HOST=localhost
BASEX_PORT=1984
BASEX_USERNAME=admin
BASEX_PASSWORD=admin
BASEX_DATABASE=dictionary

# PostgreSQL (for worksets and analytics)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dictionary_analytics
POSTGRES_USER=dict_user
POSTGRES_PASSWORD=dict_pass

# Redis (caching)
REDIS_HOST=localhost
REDIS_PORT=6379

# Flask
FLASK_ENV=development
SECRET_KEY=dev-key-change-in-production
```

### For Testing
```bash
TESTING=true
FLASK_ENV=testing
# Same DB credentials but test databases
```

## Key Files for Reference

- `README.md` - Project overview and basic setup
- `requirements.txt` - Python dependencies
- `pytest.ini` - Test configuration and markers
- `.github/workflows/ci-cd.yml` - CI/CD pipeline
- `docker-compose.yml` - Multi-service development environment
- `validation_rules.json` - Centralized validation rules
- `endpoint_definitions.json` - API endpoint documentation

## Important Notes

### Database Context
- Primary data stored in BaseX XML database
- PostgreSQL used for worksets, analytics, and backup management
- Redis for caching and session management

### LIFT Format
- Standard lexicographic interchange format
- Uses `lift` and `lift-ranges` files
- Supports complex structures: entries, senses, examples, pronunciations, relations

### Performance Considerations
- Use cached services for repeated operations
- Connection pooling handled via dependency injection
- XQuery optimized for BaseX performance
- Background processing for bulk operations

### Security
- Centralized validation prevents data corruption
- Input sanitization in validation engine
- File upload validation and size limits

## Common Development Patterns

### Adding New API Endpoints
1. Add route to appropriate API file in `app/api/`
2. Create service method in corresponding service
3. Update validation rules if needed
4. Add unit tests in `tests/unit/`
5. Add integration tests in `tests/integration/`

### Adding New Models
1. Create model in `app/models/`
2. Add to `app/models/__init__.py`
3. Update database schema if needed
4. Add service methods for CRUD operations
5. Create corresponding API endpoints

### Running Specific Test Scenarios
```bash
# Test all entry operations
pytest tests/unit/test_dictionary_service_search.py tests/integration/test_entry_update.py

# Test LIFT parsing specifically
pytest -m parser_integration

# Test search functionality
pytest -m search_integration

# Test performance
pytest -m performance

# Test specific functionality with verbose output
pytest tests/unit/test_specific.py::test_function -v -s
```

### Debugging Test Failures
```bash
# Run with verbose output
pytest -v -s

# Run specific failing test
pytest path/to/test.py::test_name --tb=short

# Debug mode (show print outputs)
pytest -s

# Use debug_test.py helper
python debug_test.py tests/path/to/test.py::test_name
```