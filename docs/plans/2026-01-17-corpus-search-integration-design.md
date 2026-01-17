# Lucene Corpus Search Integration Design

**Date:** 2026-01-17
**Status:** Approved for Implementation

## Overview

Integrate Lucene corpus search capability into the Lexicographic Curation Workbench entry form, enabling lexicographers to quickly search for usage examples when adding examples or writing definitions.

## Goals

- Provide corpus search from within the entry form
- Pre-populate search with the current entry's headword
- Allow inserting corpus examples as templates for editing
- Support both example and definition contexts

## User Stories

1. As a lexicographer, I want to search for example sentences containing a headword so I can find authentic usage patterns
2. As a lexicographer, I want to insert corpus examples directly into the entry form so I can use them as templates
3. As a lexicographer, I want to search corpus when writing definitions to find context-aware usage

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│ Entry Form (entry_form.html)                                    │
│  ├── "Search Corpus" button in Examples section                 │
│  └── "Search Corpus" button in Definition area                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Corpus Search Modal (corpus_search_modal.html)                  │
│  ├── Search input with headword pre-filled                      │
│  ├── Results list (scrollable, unlimited)                       │
│  └── Insert/Copy actions per result                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Corpus Search API (/api/corpus/search)                          │
│  └── Proxies requests to Lucene corpus service (port 8082)      │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. User clicks "Search Corpus" button
2. Modal opens with headword pre-filled
3. GET /api/corpus/search?q={headword}&limit=500&context=8
4. Lucene service returns KWIC results
5. Results displayed in scrollable modal
6. User selects "Insert" on a result
7. Selected text populates example/definition field
8. User edits and saves entry

## API Endpoint

### GET /api/corpus/search

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| q | string | Yes | - | Search query |
| limit | integer | No | 500 | Max results (max 2000) |
| context | integer | No | 8 | Words before/after match (max 15) |

**Response (200 OK):**
```json
{
  "success": true,
  "query": "run",
  "total": 47,
  "results": [
    {
      "left": "...she went for her morning",
      "match": "run",
      "right": "...around the park",
      "sentence_id": "doc123"
    }
  ]
}
```

**Response (400 Bad Request):**
```json
{
  "success": false,
  "error": "Missing required parameter: q"
}
```

**Response (500 Error):**
```json
{
  "success": false,
  "error": "Corpus service unavailable"
}
```

## User Interface

### Modal Layout

```
+------------------------------------------------------------------+
| Search Corpus Examples                                           |
| [_________________] [Search]                      [Cancel]      |
|                                                                  |
| Found 47 examples for "run" (8 words context)                   |
| +--------------------------------------------------------------+ |
| | ...she went for her morning | **run** | around the park     | |
| |                                          [Insert as Example] | |
| +--------------------------------------------------------------+ |
| +--------------------------------------------------------------+ |
| | ...the marathon, he decided to | **run** | anyway despite    | |
| |                            [Insert as Example]               | |
| +--------------------------------------------------------------+ |
| +--------------------------------------------------------------+ |
| | ...don't just stand there, | **run** | and get help now!   | |
| |                              [Insert as Example]             | |
| +--------------------------------------------------------------+ |
| ... (unlimited scrollable results)                              |
+------------------------------------------------------------------+
```

### Trigger Buttons

**In Examples Section:**
```html
<button type="button" class="btn btn-outline-primary search-corpus-btn"
        data-sense-index="0">
    <i class="fas fa-search"></i> Search Corpus
</button>
```

**In Definition Area:**
```html
<button type="button" class="btn btn-sm btn-outline-secondary search-corpus-btn"
        data-sense-index="0" data-field="definition">
    <i class="fas fa-search"></i> Search Corpus
</button>
```

## Implementation Plan

### Phase 1: Backend API
1. Create `/api/corpus/search` endpoint in `app/api/corpus_search.py`
2. Use existing `LuceneCorpusClient` for service communication
3. Register endpoint in `corpus_routes.py`

### Phase 2: Frontend JavaScript
1. Create `corpus-search.js` module
2. Handle modal open/close
3. Manage search API calls
4. Handle insert/copy actions

### Phase 3: Frontend CSS
1. Create `corpus-search.css` styles
2. Scrollable results container
3. Result card styling

### Phase 4: Modal Template
1. Create `corpus_search_modal.html`
2. Search input and results display
3. Insert dropdown per result

### Phase 5: Integration
1. Add "Search Corpus" buttons to `entry_form.html`
2. Include modal in base template
3. Load JavaScript module

## File Changes

| File | Action |
|------|--------|
| `app/api/corpus_search.py` | Create |
| `app/routes/corpus_routes.py` | Modify |
| `app/static/js/corpus-search.js` | Create |
| `app/static/css/corpus-search.css` | Create |
| `app/templates/corpus_search_modal.html` | Create |
| `app/templates/entry_form.html` | Modify |

## Error Handling

| Scenario | Handling |
|----------|----------|
| Lucene service down | Show "Corpus search unavailable" in modal |
| Empty query | Inline validation message |
| No results | Friendly "No examples found" message |
| Timeout (30s) | "Search timed out" with retry button |
| Network error | Graceful degradation with retry |

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| 8-word context | Large context for rich usage patterns |
| Unlimited scroll | Users need to browse many examples |
| Fuzzy query | Allow wildcards, OR, etc. for flexibility |
| Two trigger points | Examples and definitions |
| Insert as template | Pre-fill field, user edits |
| Modal auto-populates headword | Reduce manual entry |

## Testing Considerations

1. API returns correct format
2. Modal opens with headword pre-filled
3. Results display correctly
4. Insert action populates correct field
5. Error states display properly
6. Accessibility (keyboard navigation, ARIA)
