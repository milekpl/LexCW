# Lexicographic Curation Workbench - Tools Directory

This directory contains external tools and utilities that interact with the 
Lexicographic Curation Workbench via its REST API.

## Directory Structure

```
tools/
├── scripts/           # Executable Python scripts for API operations
│   ├── api_client.py      # General API client for entry CRUD operations
│   └── kindle_generator.py # Generate Kindle-compatible dictionaries
├── examples/          # Example usage scripts and data files
└── README.md          # This file
```

## Scripts

### api_client.py

A command-line interface for interacting with the LCW REST API.

**Prerequisites:**
```bash
pip install requests
```

**Usage:**
```bash
# List all entries
python api_client.py entries list

# Get a specific entry
python api_client.py entries get abc123

# Create entry from JSON file
python api_client.py entries create --file new_entry.json

# Search entries
python api_client.py search --query "word" --grammatical "noun"

# Export to LIFT
python api_client.py export lift --output dict.lift
```

**Environment Variables:**
- `LCW_API_URL` - Base URL of LCW instance (default: http://localhost:5000)
- `LCW_API_KEY` - API key for authentication

### kindle_generator.py

Generates Kindle-compatible dictionary files from an LCW instance.

**Prerequisites:**
```bash
pip install requests

# For MOBI generation (optional):
# - Install Kindle Previewer 3 (includes kindlegen)
# OR
# - Install Calibre (provides ebook-convert)
```

**Usage:**
```bash
# Generate HTML dictionary
python kindle_generator.py --output my_dict.html

# Generate MOBI (requires conversion tool)
python kindle_generator.py --format mobi --output my_dict.mobi

# With custom metadata
python kindle_generator.py \
    --title "My Language Dictionary" \
    --author "My Name" \
    --output dict.html
```

**Features:**
- Fetches all entries via LCW API
- Transforms entries to Kindle dictionary format
- Generates HTML with proper `<idx:entry>` markup
- Optional MOBI conversion via KindleGen or Calibre
- Supports variants for lookup
- Includes pronunciation, POS, definitions, examples

## Future Scripts

Potential additions:
- `bulk_import.py` - Import entries from CSV/Excel
- `corpus_sync.py` - Sync with external corpus tools
- `analysis_report.py` - Generate dictionary statistics
- `backup_manager.py` - Automated backup/restore

## Notes

- All scripts use the public REST API - no direct database access
- Scripts can be run from any machine with network access to LCW
- API authentication is supported via API keys
- Scripts are designed to be composable (pipe output between them)
