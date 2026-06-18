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

### Additional Services (not listed above)
- `app/services/auth_service.py` — User authentication, registration, password reset
- `app/services/backup_scheduler.py` — Scheduled BaseX database backups
- `app/services/basex_backup_manager.py` — Backup creation, restore, validation
- `app/services/bulk_action_service.py` — Bulk edit action parsing/validation
- `app/services/bulk_operations_service.py` — Bulk entry operations (trait conversion, POS updates)
- `app/services/bulk_query_service.py` — XQuery-building for bulk queries
- `app/services/cache_service.py` — Redis-backed caching with fallback
- `app/services/css_mapping_service.py` — Display profile CSS mapping
- `app/services/display_profile_service.py` — Display profile CRUD
- `app/services/event_bus.py` — Internal pub/sub for service coordination
- `app/services/field_language_detector.py` — Language detection for multilingual fields
- `app/services/lift_element_registry.py` — LIFT element metadata and default profiles
- `app/services/lucene_corpus_client.py` — HTTP client for Lucene corpus service (port 8082)
- `app/services/message_service.py` — User messaging/notifications
- `app/services/operation_history_service.py` — Audit trail for entry operations
- `app/services/query_builder_service.py` / `query_builder.py` — Query abstraction (SQL, XQuery)
- `app/services/user_preferences_service.py` — Per-user preferences
- `app/services/user_service.py` — User CRUD
- `app/services/validation_cache_service.py` — Caching for validation results
- `app/services/validation_rules_service.py` — Project-specific validation rules
- `app/services/word_sketch_service.py` + `word_sketch/` subpackage — Word sketch/collocation analysis
- `app/services/workset_service.py` — Workset management (PostgreSQL-backed)
- `app/services/xml_entry_service.py` — Direct XML CRUD on BaseX

### Additional APIs (not listed above)
- `app/api/auth_api.py` — Login, logout, registration endpoints
- `app/api/backup_api.py` — Backup download, restore, validation endpoints
- `app/api/bulk_operations.py` — Bulk trait conversion, POS updates
- `app/api/corpus_search.py` / `corpus.py` — Corpus search and management
- `app/api/dashboard.py` — Dashboard statistics endpoint
- `app/api/dictionary_api.py` — Dictionary-level management
- `app/api/display.py` — Display rendering endpoints
- `app/api/entry_autosave_working.py` — Auto-save endpoint
- `app/api/illustration.py` — Illustration/media upload
- `app/api/lift_registry.py` — LIFT element registry API
- `app/api/messages_api.py` — User messaging endpoints
- `app/api/project_members_api.py` — Project membership management
- `app/api/pronunciation.py` — Pronunciation management
- `app/api/query_builder.py` — Query builder API
- `app/api/ranges_editor.py` / `ranges.py` — Ranges CRUD and editor
- `app/api/setup.py` — Initial setup wizard
- `app/api/user_preferences_api.py` — User preferences
- `app/api/users_api.py` — User management
- `app/api/validation_endpoints.py` — Real-time validation API
- `app/api/validation_rules_api.py` — Validation rules CRUD
- `app/api/validation_service.py` — Validation service API (includes XML validation)
- `app/api/validation.py` — Validation blueprint
- `app/api/word_sketch_api.py` — Word sketch API
- `app/api/worksets.py` — Workset management
- `app/api/xml_entries.py` — XML-based entry CRUD

### Web Routes (`app/routes/`)
- `api_routes.py` — Additional API route registration
- `auth_routes.py` — Login, register, password reset pages
- `backup_routes.py` — Backup management UI routes
- `corpus_routes.py` — Corpus management UI
- `field_visibility_routes.py` — Field visibility settings
- `settings_routes.py` / `settings_routes_clean.py` — Project settings pages
- `word_sketch_routes.py` — Word sketch browser page

### Validators (`app/validators/`)
- `base.py` — Base validator class
- `hunspell_validator.py` — Hunspell spell-check integration
- `languagetool_validator.py` — LanguageTool grammar check
- `layered_hunspell_validator.py` — Multi-dictionary Hunspell validation

### Exporters (`app/exporters/`)
- `base_exporter.py` — Abstract base exporter
- `html_exporter.py` — HTML export
- `kindle_exporter.py` — Kindle/MOBI export
- `sqlite_exporter.py` — SQLite export (for Flutter mobile apps)

### Forms (`app/forms/`)
- `entry_form.py` — Main entry editing form
- `settings_form.py` — Project settings form
- `enhanced_language_field.py` — Language-aware form fields
- `searchable_language_field.py` — Searchable language picker

### XQuery Scripts (`app/xquery/`)
- `entry_operations.xq` — Entry CRUD XQuery functions
- `sense_operations.xq` — Sense-level XQuery functions
- `validation_queries.xq` — Validation XQuery checks

### Additional Models (`app/models/`)
- `backup_models.py` — Backup, ScheduledBackup models
- `user_models.py` — ActivityLog, UserRole, Permission models
- `validation_models.py` / `validation_cache_models.py` — Validation rule and cache models
- `word_sketch.py` — Word sketch data model
- `workset_models.py` — Workset, WorksetEntry, Pipeline models
- `search_query.py` — Search query model
- `merge_split_operations.py` — Merge/split operation tracking
- `custom_ranges.py` — Custom range definitions
- `dictionary_models.py` — Dictionary-level models

### Static Data (`app/data/`)
- `languages.yaml` — Language metadata (codes, names, writing systems)
- `lift_elements.json` — LIFT element definitions
- `validation_templates/` — Pre-built validation rule templates (5 JSON files)

### All pytest Markers
`unit`, `integration`, `e2e`, `selenium`, `postgresql`, `word_sketch`, `parser_integration`, `search_integration`, `performance`, `coverage_focused`, `playwright`, `safe_db`, `unsafe_db`, `javascript`, `js_lint`, `asyncio`, `destructive`

## Startup

### Starting Services (WSL with Windows-hosted PostgreSQL)
```bash
# BaseX (REQUIRED — must use this script, not raw basexserver)
bash start-basex.sh restart

# PostgreSQL runs on Windows host, accessible via localhost from WSL
# Ensure .env has: POSTGRES_HOST=localhost

# Redis and Lucene corpus are optional — the app degrades gracefully without them
```

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