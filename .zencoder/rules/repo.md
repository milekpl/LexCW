# Lexicographic Curation Workbench Information

## Summary
A Flask-based Lexicographic Curation Workbench designed to interact with a BaseX XML database for managing large-scale lexicographic data in the LIFT format. The system provides a responsive web interface for dictionary management with advanced search capabilities, import/export functionality, and comprehensive API endpoints.

## Structure
- **app/**: Core application code with MVC architecture
  - **api/**: RESTful API endpoints
  - **database/**: Database connectors (BaseX, PostgreSQL)
  - **models/**: Data models
  - **services/**: Business logic services
  - **templates/**: Jinja2 HTML templates
  - **static/**: CSS, JavaScript, and other static assets
- **tests/**: Comprehensive test suite with 150+ test files
- **scripts/**: Utility scripts for import/export operations
- **BaseXClient/**: Python client for BaseX XML database
- **schemas/**: XML validation schemas
- **docs/**: Project documentation

## Language & Runtime
**Language**: Python
**Version**: Compatible with Python 3.8+
**Framework**: Flask 2.3.3
**Build System**: pip
**Package Manager**: pip

## Dependencies
**Main Dependencies**:
- Flask 2.3.3 - Web framework
- lxml 4.9.3 - XML processing
- psycopg2-binary 2.9.7 - PostgreSQL database adapter
- flasgger 0.9.7.1 - API documentation
- injector 0.21.0 - Dependency injection
- spacy 3.6.0+ - Natural language processing

**Development Dependencies**:
- pytest 7.4.0 - Testing framework
- black 23.7.0 - Code formatter
- flake8 6.1.0 - Linter
- mypy 1.5.1 - Type checking

## Build & Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with appropriate values

# Run the application
python run.py
```

## Docker
**Configuration**: docker-compose.yml
**Services**:
- flask_app: Main application container
- basex: BaseX XML database (port 1984)
- postgres: PostgreSQL database for analytics (port 5432)
- postgres_test: PostgreSQL for testing (port 5433)
- redis: Redis for caching (port 6379)
- test_runner: Container for running tests

**Run Command**:
```bash
docker-compose up -d
```

## Testing
**Framework**: pytest
**Test Location**: tests/ directory
**Markers**: performance, slow, integration, unit, postgresql, word_sketch
**Configuration**: pytest.ini
**Run Command**:
```bash
pytest
# With coverage
pytest --cov=app tests/
```

## API Endpoints
**Main Endpoints**:
- `/api/entries/`: CRUD operations for dictionary entries
- `/api/search/`: Search functionality
- `/api/ranges/`: Range definitions and values
- `/api/validation/`: Entry validation endpoints

**Documentation**: Available at `/apidocs/` endpoint via Swagger UI

## Database Integration
**Primary Database**: BaseX XML (for LIFT format data)
**Secondary Database**: PostgreSQL (for analytics and corpus processing)
**Cache**: Redis for performance optimization

## Import/Export
**Supported Formats**:
- LIFT XML (import/export)
- Kindle (export)
- SQLite (export for mobile apps)

**Scripts**:
```bash
# Import LIFT file
python -m scripts.import_lift path/to/lift_file.lift

# Export to LIFT
python -m scripts.export_lift path/to/output.lift
```