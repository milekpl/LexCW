# ![LexCW Logo](LexCW_logo_v3_consistent.png) Lexicographic Curation Workbench

> NOTE: PostgreSQL-based corpus migration utilities (e.g. `CorpusMigrator`) have been removed; corpus management now uses Lucene services. CI workflows have been switched to manual-only dispatch while CI is reconfigured.

A professional tool for creating and managing comprehensive dictionaries using the LIFT (Lexicon Interchange FormaT) standard. This Flask-based application provides full support for LIFT 0.13 with extensive features designed for lexicographers, linguists, and language documentation specialists.

## 🌟 Key Features

### Core Lexicographic Features
- **Multilingual Support**: Every text field supports multiple writing systems simultaneously
- **Senses & Subsenses**: Organize word meanings hierarchically to capture polysemy and semantic relationships
- **Examples & Usage**: Rich contextual information with source language examples and translations
- **Pronunciation Management**: Comprehensive phonetic documentation with IPA transcription, audio files, and TTS integration
- **Etymology Tracking**: Document word origins and historical development

### Advanced Features
- **Variants & Allomorphs**: Document different forms of the same lexeme following SIL Fieldworks approach
- **Lexical Relations**: Create semantic networks connecting related entries (synonyms, antonyms, hypernyms, etc.)
- **Reversals**: Essential for bilingual dictionaries - create L2→L1 lookup capability
- **Annotations**: Editorial workflow and quality control features with review comments and status tracking

### Customization & Workflow
- **Custom Fields**: Extend LIFT to meet specific project needs with FieldWorks-compatible custom fields
- **Ranges Editor**: Manage controlled vocabularies for grammatical categories, semantic domains, and lexical relations
- **Project Setup Wizard**: Bootstrap new projects with recommended ranges and configurations
- **91% LIFT 0.13 Compliance**: Implements 51 out of 56 LIFT elements, covering all essential features

### Technical Features
- **Responsive Web Interface**: Works seamlessly on desktop and mobile devices
- **Advanced Search & Filtering**: Powerful search capabilities across all dictionary data
- **Import/Export Functionality**: Full support for LIFT, Kindle, and Flutter/SQLite formats
- **FieldWorks Compatibility**: Seamless import/export with FieldWorks/FLEx preserving 91% of elements
- **LLM Integration**: Example and sense management with AI assistance

## 🛠️ Requirements

### System Requirements
- **Python 3.8+**
- **BaseX XML Database** (version 9.0+)
- **Redis** (for caching and performance optimization)
- **Java Runtime Environment** (for BaseX)

### Services Setup
The application requires BaseX and Redis services to run properly. Use the provided scripts to start all required services:

```bash
# Start BaseX and Redis services
./start-services.sh

# The script will:
# - Start BaseX server (runs on port 1984)
# - Start Redis (runs on port 6379, optional but recommended)
# - Initialize admin user if needed
# - Check database connectivity
```

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

### 4. Configure environment variables
Copy the example environment file and update the settings:
```bash
cp .env.example .env
```

Edit `.env` file with your configuration:
```bash
BASEX_HOST=localhost
BASEX_PORT=1984
BASEX_USERNAME=admin
BASEX_PASSWORD=admin
BASEX_DATABASE=dictionary
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
```

### 5. Start required services
```bash
# Start BaseX and Redis
./start-services.sh
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
Export functionality is currently under development. Import is fully operational through **Import/Export → Import LIFT**.

## 📊 LIFT 0.13 Compliance

The application implements **51 out of 56 LIFT 0.13 elements** (91% compliance), covering all essential and professional features needed for lexicography:

### Element Coverage:
- **Entry Elements**: 11/12 (92%) - All essential entry components
- **Sense Elements**: 12/14 (86%) - Complete sense management
- **Example Elements**: 7/7 (100%) - Full example support
- **Pronunciation**: 3/3 (100%) - Complete phonetic documentation
- **Etymology**: 5/5 (100%) - Full etymology tracking
- **Custom Fields**: 6/7 (86%) - Extensive custom field support

## 🔄 Import/Export Capabilities

### Import LIFT Files
```bash
# Import a LIFT file with optional ranges
python -m scripts.import_lift path/to/lift_file.lift [path/to/lift_ranges.lift-ranges]
```

### Export LIFT Files
```bash
# Export to a LIFT file (currently in development)
python -m scripts.export_lift path/to/output.lift
```

### Supported Formats
- **LIFT** (primary format) - Full LIFT 0.13 support for import, limited export
- **Kindle** - Dictionary format for Kindle devices (development in progress)
- **SQLite** - Database format (development in progress)

**Note**: Export functionality is currently limited and under active development. Import functionality is fully operational.

## 🌐 API Endpoints

The system provides a comprehensive RESTful API for programmatic access:

### Entry Management
- **GET /api/entries/** - List entries with pagination and search
- **GET /api/entries/{id}** - Get a specific entry
- **POST /api/entries/** - Create a new entry
- **PUT /api/entries/{id}** - Update an existing entry
- **DELETE /api/entries/{id}** - Delete an entry
- **GET /api/entries/{id}/related** - Get related entries

### Search Functionality
- **GET /api/search/** - Search entries by text across all fields
- **GET /api/search/grammatical** - Search entries by grammatical information
- **GET /api/search/ranges** - Get range definitions and controlled vocabularies
- **GET /api/search/ranges/{id}** - Get values for a specific range

### Additional API Features
- **GET /api/stats** - Get dictionary statistics and entry counts
- **GET /api/projects** - Manage multiple dictionary projects
- **GET /api/reports** - Generate various dictionary reports

## 🔧 Development

### Running Tests
```bash
# Run all tests
pytest

# Generate coverage report
pytest --cov=app tests/
```

### Development Commands
```bash
# Format code with black
black .

# Lint code
flake8

# Type checking
mypy .
```

## ⚠️ Status

This application is currently in **pre-alpha** stage. While the core functionality is operational, some features are still under active development and may not work as expected. The export functionality is currently limited and undergoing improvements.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For technical questions about LIFT format:
- [LIFT Standard Documentation](https://code.google.com/archive/p/lift-standard/)
- [SIL FieldWorks](https://software.sil.org/fieldworks/)

For lexicographic resources and guidance:
- [Introduction to Lexicography](https://downloads.languagetechnology.org/fieldworks/Documentation/Intro%20to%20Lexicography/Introduction%20to%20Lexicography.htm) by Ron Moe

For application-specific support, contact your system administrator or open an issue in the repository.
