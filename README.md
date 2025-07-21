# Lexicographic Curation Workbench 

A Flask-based Lexicographic Curation Workbench designed to interact with a BaseX XML database for managing large-scale lexicographic data in the LIFT format.

## Features

- Responsive web interface for dictionary management
- BaseX XML database connection for LIFT file operations
- Advanced search and filtering capabilities
- Import/export functionality (LIFT, Kindle, Flutter/SQLite)
- Pronunciation management (IPA, TTS)
- Example and sense management with LLM integration
- Semantic relation management

## Installation

1. Clone the repository
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure BaseX connection in .env file (or environment variables):

   ```bash
   BASEX_HOST=localhost
   BASEX_PORT=1984
   BASEX_USERNAME=admin
   BASEX_PASSWORD=admin
   BASEX_DATABASE=dictionary
   ```

4. Run the application:

   ```bash
   python run.py
   ```

## API Endpoints

The system provides a RESTful API for interacting with the dictionary:

- **GET /api/entries/** - List entries with pagination
- **GET /api/entries/{id}** - Get a specific entry
- **POST /api/entries/** - Create a new entry
- **PUT /api/entries/{id}** - Update an existing entry
- **DELETE /api/entries/{id}** - Delete an entry
- **GET /api/entries/{id}/related** - Get related entries

- **GET /api/search/** - Search entries by text
- **GET /api/search/grammatical** - Search entries by grammatical information
- **GET /api/search/ranges** - Get range definitions
- **GET /api/search/ranges/{id}** - Get values for a specific range

## Import/Export

Use the scripts to import and export LIFT files:

```bash
# Import a LIFT file
python -m scripts.import_lift path/to/lift_file.lift [path/to/lift_ranges.lift-ranges]

# Export to a LIFT file
python -m scripts.export_lift path/to/output.lift
```

## Development

- Run tests: `pytest`
- Generate coverage report: `pytest --cov=app tests/`

## License

[MIT License](LICENSE)
