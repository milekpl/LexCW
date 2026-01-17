# Corpus Management API Design

## Overview

Design for corpus management operations in the Lexicographic Curation Workbench, integrating with the Lucene corpus service.

## Current State

- Lucene corpus service running at port 8082
- ~74.7M documents in parallel corpus (en-pl)
- Existing Flask app with corpus management UI
- PostgreSQL `parallel_corpus` table deprecated

## API Endpoints

### GET /api/corpus/stats

Retrieve corpus statistics.

**Response:**
```json
{
  "success": true,
  "total_records": 74740856,
  "last_updated": "2024-01-15 10:30:00",
  "source": "lucene"
}
```

### POST /api/corpus/upload

Upload and import corpus data (TMX, CSV, SQLite).

**Content-Type:** `multipart/form-data`

**Fields:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| file | File | Yes | TMX, CSV, or SQLite file |
| source_lang | string | Yes | Source language code (en, de, fr, etc.) |
| target_lang | string | Yes | Target language code (pl, en, de, etc.) |
| table_name | string | No* | Table name for SQLite imports |
| drop_existing | boolean | No | Replace existing data (default: false) |

*Required for SQLite files.

**Response:**
```json
{
  "success": true,
  "records_processed": 15000,
  "stats": {
    "total_records": 74755856,
    "source": "lucene"
  }
}
```

### POST /api/corpus/clear-cache

Clear corpus statistics cache.

### POST /api/corpus/deduplicate

Remove duplicate entries from corpus.

### POST /api/corpus/cleanup

Clear all corpus data.

### POST /api/corpus/convert/tmx-to-csv

Convert TMX file to CSV format.

## File Format Specifications

### TMX
- Standard Translation Memory Exchange XML format
- Extract `<seg>` elements from `<tuv lang="xx">` pairs
- Skip header/metadata segments

### CSV
- Header required: `source_text,target_text` (or detected)
- UTF-8 encoding
- Comma delimiter

### SQLite
- JDBC-compatible SQLite database
- Required columns: `source_text`, `target_text`
- Table name specified in `table_name` parameter

## UI Changes

### Removed
- Avg Source Length stat card
- Avg Target Length stat card

### Retained
- Total Records stat
- Last Updated timestamp
- File upload section
- TMX to CSV converter
- Deduplicate/Cleanup tools

## Lucene Service Integration

The Lucene corpus service supports custom SQL queries via `--query` parameter. For SQLite imports:

1. Flask app receives file + table name
2. Flask app passes to Lucene service:
   ```
   java -jar corpus-service.jar build \
     --jdbc "jdbc:sqlite:/path/to/uploaded.db" \
     --query "SELECT source_text, target_text FROM {table_name}" \
     --index /path/to/index
   ```

## Future Enhancements (Out of Scope)

- Frequency analysis field in LIFT format
- Concordance search modal on entry form
- Translation pattern analysis
- Multi-language pair support (separate indices or language tagging)
- Incremental index updates (currently full rebuild)

## Files Modified

- `app/api/corpus.py` - Updated stats endpoint, new upload endpoint
- `app/templates/corpus_management.html` - Removed avg length cards, simplified stats display
- `app/services/lucene_corpus_client.py` - Added upload/import methods if needed
