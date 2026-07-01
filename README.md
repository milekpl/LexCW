# ![LexCW Logo](LexCW_logo_v3_consistent.png) Lexicographic Curation Workbench

A professional tool for creating and managing comprehensive dictionaries using the LIFT (Lexicon Interchange FormaT) standard. This Flask-based application provides full support for LIFT 0.13+ with extensive features designed for lexicographers, linguists, and language documentation specialists.

## 🌟 Key Features

### Core Lexicographic Features
- **Multilingual Support**: Every text field supports multiple writing systems simultaneously
- **Senses & Subsenses**: Organize word meanings hierarchically to capture polysemy and semantic relationships
- **Examples & Usage**: Rich contextual information with source language examples and translations
- **Pronunciation Management**: Comprehensive phonetic documentation with IPA transcription, audio files, and TTS integration
- **Etymology Tracking**: Document word origins and historical development
- **Variants & Allomorphs**: Document different forms of the same lexeme following SIL Fieldworks approach
- **Lexical Relations**: Create semantic networks connecting related entries (synonyms, antonyms, hypernyms, etc.)
- **Reversals**: Essential for bilingual dictionaries — create L2→L1 lookup capability
- **Annotations & Messages**: Editorial workflow and quality control with per-entry discussion threads

### Editing & Curation
- **Entry Form**: Rich multilingual editing with POS inheritance, variant relations, component relations, and subentries
- **Worksets**: Query-based dynamic collections of entries with curation metadata (status, favorites, notes)
- **Bulk Operations**: Batch update traits, POS tags, and other fields across multiple entries with preview mode
- **Merge & Split**: Merge multiple entries into one or split an entry into multiple, with full undo/redo history
- **Auto-Save**: Automatic form state persistence with undo/redo for entry edits
- **Keyboard Shortcuts**: Full keyboard navigation and editing workflow

### Import & Export
- **LIFT Import/Export**: Full bidirectional LIFT 0.13+ support with merge/replace modes
- **SFM/Shoebox Import**: Two-step import with marker auto-detection and interactive mapping UI
- **FieldWorks list.xml Import**: Abbreviation import from FieldWorks
- **HTML Export**: Generate browsable static HTML dictionaries with alphabetical navigation
- **Markdown Export**: Export entries in Markdown format

### Quality Assurance
- **Validation Engine**: Multiple validation backends — Schematron (XSLT), Hunspell spelling, LanguageTool grammar, IPA pronunciation, real-time field validation
- **Validation Rules**: Project-specific validation rules with admin UI
- **AI Proofreading**: LLM-powered proofreading and drafting of entries (BYOK — bring your own API key)
- **Data Quality Dashboard**: Overview of dictionary health and completeness

### Customization & Workflow
- **Custom Fields**: Extend LIFT to meet specific project needs with FieldWorks-compatible custom fields
- **Ranges Editor**: Full CRUD for controlled vocabularies (grammatical categories, semantic domains, lexical relations)
- **Display Profiles**: CSS-based entry rendering system with multiple profiles and custom styling
- **Project Settings**: Per-project configuration for AI, SMTP, external services, and field visibility defaults
- **Project Setup Wizard**: Bootstrap new projects with recommended ranges and configurations

### Technical Features
- **RESTful API**: Comprehensive JSON API for all dictionary operations
- **Advanced Search**: XQuery-powered full-text search across all fields with filters and facets
- **Corpus Management**: Lucene-based parallel corpus search (concordance) with management UI
- **Word Sketch**: External ConceptSketch integration for collocation and grammar pattern analysis
- **Backup & Restore**: Manual and scheduled backups of the BaseX XML database with undo/redo history
- **User Management**: Role-based access control (ADMIN, MEMBER, VIEWER) with API key authentication
- **Swagger API Docs**: Interactive API documentation via Flasgger at `/apidocs/`
- **Docker Support**: Full docker-compose setup for all services including the Flask app

## 🛠️ Requirements

### System Requirements
- **Python 3.8+**
- **BaseX XML Database** (version 9.0+, port 1984)
- **PostgreSQL** (version 15+, port 5432)
- **Redis** (for caching, port 6379)
- **Java Runtime Environment** (for BaseX and Saxon)
- **Docker & Docker Compose** (recommended for easy setup)

### Optional External Services
- **[ConceptSketch](https://github.com/cognitive-metascience/concept-sketch)** (port 8080) — word sketch / collocation analysis service. Clone and run separately to enable the **Word Sketch** feature.
- **[corpus-lucene-service](https://github.com/milekpl/corpus-lucene-service)** (port 8082) — parallel corpus concordance search. Clone and run separately to enable **Corpus Management**.
- **[LanguageTool](https://github.com/languagetool-org/languagetool)** (port 8081) — grammar and style checking (for validation engine)
- **Saxon XSLT Processor** (included at `tools/saxon/`, auto-installed via `install_saxon.sh`) — Schematron XSLT2 validation

### Services Setup
Use Docker Compose to start all required services:

```bash
docker compose up -d
```

This starts: Flask app (port 5000), BaseX (ports 1984 TCP, 8984 HTTP), PostgreSQL (port 5432), Redis (port 6379), and a test PostgreSQL instance (port 5433).

To start services individually with the provided scripts:

```bash
# Start BaseX
./start-basex.sh

# Or start all services (BaseX + Redis)
./start-services.sh
```

Ensure PostgreSQL is running separately (e.g. `systemctl start postgresql` or via your OS package manager).

## 📦 Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd flask-app
```

### 2. Set up Python virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3.1 Node (for e2e tests)
If you intend to run the Playwright end-to-end tests, install Node dependencies and download the Playwright browsers. Note that the `node_modules/` directory is ignored by Git (run `npm ci` after cloning to populate it).

```bash
# Install Node dependencies (deterministic install)
npm ci

# Install Playwright browsers (Chromium, Firefox, WebKit)
# Use --with-deps on Linux to ensure system packages are installed
npx playwright install --with-deps chromium firefox webkit
```

### 4. Configure environment variables
Copy the example environment file and update the settings:
```bash
cp .env.example .env
```

Edit `.env` file with your configuration — see `.env.example` for all available variables. Key settings:
```bash
# BaseX
BASEX_HOST=localhost
BASEX_PORT=1984
BASEX_USERNAME=admin
BASEX_PASSWORD=admin
BASEX_DATABASE=dictionary

# PostgreSQL (worksets, users, settings)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dictionary_analytics
POSTGRES_USER=dict_user
POSTGRES_PASSWORD=dict_pass

# Redis (caching)
REDIS_HOST=localhost
REDIS_PORT=6379

# Flask
SECRET_KEY=your-secret-key-here
```

### 5. Start required services

**Option A — Docker Compose (recommended):**
```bash
docker compose up -d
```

**Option B — Start manually:**
```bash
# Start BaseX
./start-basex.sh

# Ensure PostgreSQL is running and create the database
createdb dictionary_analytics

# Redis (if installed locally)
redis-server
```

### 6. Run the application
```bash
python run.py
```

The application will be available at `http://localhost:5000`

## 🚀 Getting Started

### Import Your Dictionary Data
1. Go to **Import/Export → Import LIFT**
2. Upload your LIFT file to begin working with your dictionary data
3. The application supports LIFT 0.13 format with 91% element coverage

### Browse and Edit Entries
1. Click on **Entries** to view your lexicon
2. Click on any entry to open the full editor
3. Use the comprehensive editing interface to modify or add new entries

### Use the Ranges Editor
Access the **Tools → Ranges Editor** to manage controlled vocabularies:
- View and edit grammatical information categories
- Manage semantic domains and lexical relations
- Create custom classification systems

### Export Your Work
Export your dictionary in multiple formats through **Import/Export → Export**:
- **LIFT Export**: Full LIFT 0.13+ XML export (single file or dual file + ranges ZIP)
- **HTML Export**: Generate browsable static HTML pages with CSS-driven entry rendering
- **Markdown Export**: Export entries in Markdown format for documentation or publishing

## 📊 LIFT 0.13 Compliance

The application provides comprehensive LIFT 0.13+ support across all major element categories:

### Element Coverage:
- **Entry Elements**: All essential entry components (lexeme, citation, variants, alternate forms, notes, fields)
- **Sense Elements**: Complete sense management with glosses, definitions, semantic domains, and subsenses
- **Example Elements**: Full example support with translations and source language
- **Pronunciation**: Complete phonetic documentation with IPA, audio files, and TTS integration
- **Etymology**: Full etymology tracking with source, form, and gloss
- **Custom Fields**: Extensive custom field support compatible with FieldWorks/FLEx

## 🔄 Import/Export Capabilities

### Import
| Format | Status | Details |
|---|---|---|
| **LIFT (.lift)** | Full | Merge or replace modes, with optional `.lift-ranges` and `list.xml` |
| **SFM/Shoebox** | Full | Marker auto-detection with interactive mapping interface |
| **FieldWorks list.xml** | Full | Abbreviation import |

```bash
# Import a LIFT file with optional ranges
python -m scripts.import_lift path/to/lift_file.lift [path/to/lift_ranges.lift-ranges]
```

### Export
| Format | Status | Details |
|---|---|---|
| **LIFT (.lift)** | Full | Single file or dual file + ranges ZIP |
| **HTML** | Full | Browsable static HTML with CSS rendering and alphabetical navigation |
| **Markdown** | Full | Markdown format for documentation |
| **Kindle (MOBI/AZW3)** | Available | Script at `tools/scripts/kindle_generator.py` — generates Kindle-compatible dictionaries via the REST API |

```bash
# Export to a LIFT file
python -m scripts.export_lift path/to/output.lift

# Generate a Kindle dictionary (requires Calibre or KindleGen)
python tools/scripts/kindle_generator.py --format mobi --output my_dict.mobi
```

### Extension Scripts
The `scripts/` and `tools/scripts/` directories contain utility scripts for extending and maintaining the application:

| Script | Purpose |
|---|---|
| `tools/scripts/kindle_generator.py` | Generate Kindle MOBI/AZW3 dictionaries from the API |
| `tools/scripts/api_client.py` | Programmatic REST API client for batch operations |
| `tools/scripts/ai_quality_control.py` | AI-powered quality checks on dictionary data |
| `scripts/import_lift.py` | CLI LIFT import (alternative to web UI) |
| `scripts/export_lift.py` | CLI LIFT export (alternative to web UI) |
| `scripts/validate_xml_compatibility.py` | Validate LIFT XML compatibility |

## 🌐 API Endpoints

Full interactive API documentation is available at `/apidocs/` (Swagger/OpenAPI via Flasgger). Key endpoint groups:

### Entry Management (`/api/entries/`)
- `GET /` — List entries with pagination and search
- `GET /{id}` — Get a specific entry
- `POST /` — Create a new entry
- `PUT /{id}` — Update an existing entry
- `DELETE /{id}` — Delete an entry

### Search (`/api/search/`)
- `GET /` — Full-text search across all fields
- `GET /ranges` — Get range definitions and controlled vocabularies
- `GET /ranges/{id}` — Get values for a specific range

### Export (`/api/export/`)
- `GET /lift` — Export dictionary to LIFT XML
- `GET /html` — Export dictionary to HTML
- `GET /download/{file}` — Download a generated export file

### AI Assistance (`/api/ai/`)
- `POST /proofread` — AI proofreading of an entry
- `POST /draft` — AI drafting of a new entry from description
- `POST /batch-proofread` — Batch proofread multiple entries

### Validation (`/api/validation/`)
- `GET /entry/{id}` — Validate a specific entry
- `GET /dictionary` — Validate the entire dictionary
- `POST /check` — Run validation checks

### Worksets (`/api/worksets`)
- `GET /` — List worksets
- `POST /` — Create a workset
- `POST /{id}/entries` — Manage workset entries

### Other Endpoints
- `GET /api/stats` — Dictionary statistics and entry counts
- `POST /api/backup/create` — Create database backup
- `POST /api/merge-split/merge` — Merge entries
- `POST /api/merge-split/split` — Split an entry
- `GET/POST /api/corpus/search` — Lucene-based parallel corpus search
- `GET /api/profiles` — Display profile management
- `GET /api/query-builder/fields` — Available search fields
- `GET/POST /api/bulk/query` — Query and bulk-operate on entries
- `POST /api/auth/login` — User authentication
- `GET /api/projects/{id}/validation-rules` — Validation rules
- `GET /api/lift/elements` — LIFT element registry

## 🔧 Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run JavaScript tests
npm test

# Run end-to-end tests (requires Playwright browsers)
npm run test:e2e


```

### Development Commands
```bash
# Format Python code with black
black .

# Lint Python code
flake8

# Type checking
mypy .

# Format JavaScript code
npm run format:js

# Lint JavaScript code
npm run lint:js
```

## ⚠️ Status

This application is in **active development**. All core features are operational: full LIFT import/export, entry editing, search, validation, AI assistance, user management, backup/restore, and multiple export formats.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For technical questions about LIFT format:
- [LIFT Standard Documentation](https://code.google.com/archive/p/lift-standard/)
- [SIL FieldWorks](https://software.sil.org/fieldworks/)

For lexicographic resources and guidance:
- [Introduction to Lexicography](https://downloads.languagetechnology.org/fieldworks/Documentation/Intro%20to%20Lexicography/Introduction%20to%20Lexicography.htm) by Ron Moe

For application-specific support, contact your system administrator or open an issue in the repository.
