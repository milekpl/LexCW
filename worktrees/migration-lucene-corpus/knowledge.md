# Lexicographic Curation Workbench

## Overview
A Flask-based web application for managing lexicographic data in LIFT (Lexicon Interchange FormaT) format, using BaseX XML database as the primary storage.

## Tech Stack
- **Backend**: Flask 2.3.3 with Flask-SQLAlchemy, Flask-WTF, Flasgger (Swagger docs)
- **Database**: BaseX XML database (primary), PostgreSQL (analytics), Redis (caching)
- **Frontend**: Jinja2 templates with Bootstrap
- **Testing**: pytest, Selenium, Playwright

## Key Directories
- `app/` - Main Flask application
  - `api/` - REST API endpoints
  - `routes/` - HTML page routes
  - `services/` - Business logic services
  - `templates/` - Jinja2 templates
  - `static/js/` - JavaScript modules
- `tests/` - Test suites (unit, integration)
- `scripts/` - CLI utilities for import/export
- `schemas/` - JSON/Schematron validation schemas

## Running the Application
```bash
# Start Docker services (BaseX, PostgreSQL, Redis)
docker-compose up -d

# Run Flask app
python run.py
```

## Testing
```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run with coverage
pytest --cov=app tests/
```

## Key Patterns
- Dependency injection via `injector` library
- ConfigManager for project settings
- DictionaryService as main service layer
- XQuery for BaseX database operations
