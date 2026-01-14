# Hunspell Spell Check Support - Feature Specification

## 1. Overview

### 1.1 Executive Summary
Add Hunspell-based spell checking support to the Lexicographic Curation Workbench, enabling users to validate spelling across all text content in dictionary entries. This includes support for custom user-uploaded dictionaries per language, special handling for IPA/phonetic content, and integration with the existing centralized validation engine.

### 1.2 Goals
- Integrate Hunspell (via `cyhunspell` or pure Python alternative) for spell checking
- Support multiple language dictionaries simultaneously
- Allow users to upload custom dictionaries for specific languages (including IPA/custom phonetic alphabets)
- Apply spell checking to all relevant text fields across Entry, Sense, Example, Pronunciation, and Etymology models
- Integrate seamlessly with existing validation system (both server-side and client-side)
- Provide real-time spell checking feedback in the UI

### 1.3 Non-Goals
- Automatic spelling correction (only detection, not auto-fix)
- Browser-based spell checking (using native browser APIs)
- Built-in dictionaries for all world languages (users provide dictionaries)

---

## 2. Technical Architecture

### 2.1 Components Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Spell Check Architecture                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Client Layer (Browser)                          │    │
│  │  ┌─────────────────────┐  ┌─────────────────────────────────────┐  │    │
│  │  │ Inline Validation   │  │ Spell Check API Client              │  │    │
│  │  │ (inline-validaton.js│  │ (spell-check-client.js)             │  │    │
│  │  └─────────────────────┘  └─────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     API Layer (Flask)                               │    │
│  │  ┌─────────────────────┐  ┌─────────────────────────────────────┐  │    │
│  │  │ /api/spell-check/*  │  │ Validation Engine Integration       │  │    │
│  │  │ (spell_check_api.py)│  │ (validation_engine.py)              │  │    │
│  │  └─────────────────────┘  └─────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                       Service Layer                                     ││
│  │  ┌─────────────────────┐  ┌─────────────────────────────────────────┐  ││
│  │  │ Hunspell Service    │  │ Dictionary Management Service           │  ││
│  │  │ (hunspell_service.py│  │ (dictionary_management_service.py)      │  ││
│  │  └─────────────────────┘  └─────────────────────────────────────────┘  ││
│  │           │                             │                                ││
│  │           ▼                             ▼                                ││
│  │  ┌─────────────────────┐  ┌─────────────────────────────────────────┐  ││
│  │  │ Cached Hunspell     │  │ Dictionary Storage (PostgreSQL/File)    │  ││
│  │  │ Dictionary Instances│  │                                         │  ││
│  │  └─────────────────────┘  └─────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Selection: cyhunspell vs. Alternatives

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **cyhunspell** | Native C extension, fast, full Hunspell support | Requires compilation, platform-dependent, complex installation | **Use with fallback** |
| **hunspell** (pure Python) | Pure Python, cross-platform, easy installation | Slower for large texts | **Primary choice** |
| **python-hunspell** | Wrapper around system hunspell | Requires system Hunspell installation | Fallback option |

**Recommended Approach:** Use `hunspell` (pure Python package) as primary, with `cyhunspell` as optional performance optimization.

```python
# app/services/hunspell_service.py
try:
    import hunspell
    HUNSPELL_AVAILABLE = True
except ImportError:
    HUNSPELL_AVAILABLE = False
```

### 2.3 Dictionary Storage Strategy

#### Option A: PostgreSQL Storage (Recommended)
Store dictionary files and custom user dictionaries in PostgreSQL with workset/analytics database.

**Schema:**
```sql
-- Custom dictionaries table
CREATE TABLE custom_dictionaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    language_code VARCHAR(10) NOT NULL,      -- e.g., 'en-US', 'cs-CZ', 'ipa-custom'
    dictionary_name VARCHAR(255) NOT NULL,
    description TEXT,
    dictionary_type VARCHAR(50) NOT NULL,    -- 'standard', 'custom', 'domain_specific'
    aff_file_content BYTEA NOT NULL,         -- .aff file binary
    dic_file_content BYTEA NOT NULL,         -- .dic file binary
    is_active BOOLEAN DEFAULT TRUE,
    is_default_for_language BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- User personal dictionaries (optional extension)
CREATE TABLE user_personal_dictionaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    dictionary_id UUID REFERENCES custom_dictionaries(id),
    added_words TEXT[],                       -- Array of user-added words
    excluded_words TEXT[],                    -- Words to ignore
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Option B: File System Storage
Store dictionaries in `app/data/hunspell_dictionaries/{language_code}/`

```
app/data/hunspell_dictionaries/
├── en-US/
│   ├── en-US.aff
│   ├── en-US.dic
│   └── custom_en-US.aff
│   └── custom_en-US.dic
├── cs-CZ/
│   ├── cs-CZ.aff
│   ├── cs-CZ.dic
│   └── domain_cs-CZ.aff
│   └── domain_cs-CZ.dic
└── ipa-custom/
    ├── ipa-custom.aff
    └── ipa-custom.dic
```

**Recommendation:** Use PostgreSQL for custom dictionaries, file system for bundled standard dictionaries.

---

## 3. API Design

### 3.1 Spell Check API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/spell-check/check` | POST | Check spelling of text |
| `/api/spell-check/suggest` | POST | Get spelling suggestions |
| `/api/spell-check/dictionaries` | GET | List available dictionaries |
| `/api/spell-check/dictionaries` | POST | Upload custom dictionary |
| `/api/spell-check/dictionaries/<id>` | DELETE | Delete custom dictionary |
| `/api/spell-check/dictionaries/<id>/activate` | POST | Activate dictionary for project |
| `/api/spell-check/batch` | POST | Batch spell check multiple texts |

#### 3.1.1 Check Spelling Endpoint

```http
POST /api/spell-check/check
Content-Type: application/json

{
  "text": "Ths is a tst sentence",
  "language_code": "en-US",
  "options": {
    "check_compound_words": true,
    "ignore_numbers": true,
    "ignore_urls": true,
    "return_suggestions": false
  }
}
```

```json
{
  "valid": false,
  "errors": [
    {
      "word": "Ths",
      "start_pos": 0,
      "end_pos": 3,
      "suggestions": ["This", "Th's", "Ths"],
      "context": "Ths is a tst"
    },
    {
      "word": "tst",
      "start_pos": 11,
      "end_pos": 14,
      "suggestions": ["test", "tst", "tat"],
      "context": "a tst sentence"
    }
  ],
  "word_count": 5,
  "error_count": 2
}
```

#### 3.1.2 Batch Spell Check Endpoint

```http
POST /api/spell-check/batch
Content-Type: application/json

{
  "entries": [
    {
      "id": "entry-1",
      "fields": {
        "lexical_unit.en": "Hellow world",
        "senses[0].definition.en": "A gret example",
        "senses[0].gloss.pl": "Dobrze"
      }
    },
    {
      "id": "entry-2",
      "fields": {
        "senses[0].definition.en": "Anothr test"
      }
    }
  ],
  "language_code": "en-US"
}
```

```json
{
  "results": [
    {
      "id": "entry-1",
      "errors": [
        {
          "field": "lexical_unit.en",
          "word": "Hellow",
          "suggestions": ["Hello", "Hellows"],
          "severity": "error"
        },
        {
          "field": "lexical_unit.en",
          "word": "world",
          "suggestions": ["world", "wold"],
          "severity": "warning"  // Could be valid in context
        },
        {
          "field": "senses[0].definition.en",
          "word": "gret",
          "suggestions": ["great", "get"],
          "severity": "error"
        }
      ],
      "valid": false
    },
    {
      "id": "entry-2",
      "errors": [...],
      "valid": false
    }
  ],
  "summary": {
    "total_entries": 2,
    "entries_with_errors": 2,
    "total_errors": 5
  }
}
```

#### 3.1.3 Dictionary Management Endpoints

```http
# Upload custom dictionary
POST /api/spell-check/dictionaries
Content-Type: multipart/form-data

file: (the .dic and .aff files zipped or as separate files)
language_code: "cs-CZ"
dictionary_name: "Legal Czech Dictionary"
dictionary_type: "domain_specific"
description: "Custom dictionary for legal terminology"
is_default: false

# Response
{
  "id": "dict-uuid-here",
  "language_code": "cs-CZ",
  "dictionary_name": "Legal Czech Dictionary",
  "status": "uploaded",
  "word_count": 15420,
  "message": "Dictionary uploaded successfully"
}
```

### 3.2 Validation Engine Integration

#### 3.2.1 New Validation Rule Type

```json
{
  "R10.1.1": {
    "name": "spell_check_content",
    "category": "spelling",
    "priority": "warning",
    "path": "$.lexical_unit.*",
    "condition": {
      "type": "if_present"
    },
    "validation": {
      "type": "spell_check",
      "dictionary": "${language_code}",
      "options": {
        "ignore_proper_nouns": true,
        "ignore_numbers": true,
        "custom_dictionary_id": null
      }
    },
    "error_message": "Spelling errors found: {misspelled_words}",
    "validation_mode": "all"
  },
  "R10.1.2": {
    "name": "spell_check_sense_definition",
    "category": "spelling",
    "priority": "warning",
    "path": "$.senses[*].definition.*",
    "condition": {
      "type": "if_present"
    },
    "validation": {
      "type": "spell_check",
      "dictionary": "${language_code}"
    },
    "error_message": "Spelling errors: {misspelled_words}",
    "validation_mode": "all"
  }
}
```

#### 3.2.2 Dynamic Language Code Resolution

```python
# Validation engine will resolve language codes from:
# 1. Entry's source_language field
# 2. Field's language prefix (e.g., "definition.en")
# 3. Project's default language
# 4. Rule's explicit dictionary setting
```

---

## 4. Text Fields Requiring Spell Checking

### 4.1 Priority Classification

| Priority | Model | Field | Language Context | Notes |
|----------|-------|-------|------------------|-------|
| **HIGH** | Entry | `lexical_unit` | Per-language | Headwords - primary content |
| **HIGH** | Sense | `glosses` | Per-language | Gloss text |
| **HIGH** | Sense | `definitions` | Per-language | Definitions |
| **HIGH** | Sense | `literal_meaning` | Per-language | Literal meaning |
| **HIGH** | Example | `form` | Per-language | Example sentences |
| **HIGH** | Example | `translations` | Per-language | Example translations |
| **HIGH** | Etymology | `form` | Per-language | Etymon forms |
| **HIGH** | Etymology | `gloss` | Per-language | Etymology gloss |
| **MEDIUM** | Entry | `citations` | Per-language | Citation forms |
| **MEDIUM** | Entry | `notes` | Per-language | Entry notes |
| **MEDIUM** | Sense | `exemplar` | Per-language | Exemplar phrases |
| **MEDIUM** | Sense | `notes` | Per-language | Sense notes |
| **MEDIUM** | Example | `notes` | Per-language | Example notes |
| **MEDIUM** | Pronunciation | `notes` | Per-language | Pronunciation notes |
| **SPECIAL** | Pronunciation | `form` | IPA/Phonetic | IPA transcriptions - requires special dictionary |

### 4.2 Special Handling for IPA/Phonetic Content

For IPA fields (`pronunciations.form` with IPA), standard spell checking should be disabled or use a custom phonetic dictionary:

```json
{
  "R10.2.1": {
    "name": "ipa_character_validation",
    "category": "pronunciation",
    "priority": "informational",
    "path": "$.pronunciations[*].form.ipa",
    "condition": {
      "type": "if_present"
    },
    "validation": {
      "type": "custom",
      "custom_function": "validate_ipa_characters"
    },
    "error_message": "Invalid IPA character: {invalid_chars}",
    "validation_mode": "all"
  }
}
```

Users can upload custom IPA dictionaries for domain-specific phonetic notation.

---

## 5. UI Integration

### 5.1 Inline Spell Checking

#### 5.1.1 Architecture

```
User types text
    │
    ▼
Debounce (300ms)
    │
    ▼
JS Spell Check Client
    │
    ├─► Local cache check (if available)
    │
    └─► API call to /api/spell-check/check
                          │
                          ▼
                  Return misspelled words
                  with suggestions
                          │
                          ▼
Highlight misspelled words
Show suggestion dropdown
```

#### 5.1.2 Integration with Existing Inline Validation

```javascript
// app/static/js/inline-validation.js extension

class SpellCheckValidator {
    constructor(options) {
        this.debounceMs = options.debounceMs || 300;
        this.cache = new LRUMap(100);
        this.apiEndpoint = '/api/spell-check/check';
    }

    async validate(fieldElement, text, languageCode) {
        // Check local cache first
        const cacheKey = `${languageCode}:${text}`;
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }

        // Call API
        const response = await fetch(this.apiEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                language_code: languageCode,
                options: { return_suggestions: true }
            })
        });

        const result = await response.json();
        this.cache.set(cacheKey, result);
        return result;
    }

    highlightMisspellings(container, errors) {
        // Wrap misspelled words in <span class="spell-error">
        // with tooltip showing suggestions
    }
}
```

#### 5.1.3 Visual Design

```
┌─────────────────────────────────────────────────────────────┐
│ Definition (English):                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ This is a exmple of a definitoin with mispeled words.  │ │
│ │          ^^^^^^        ^^^^^^^^^                         │
│ │          │            │                                  │
│ │          └─ tooltip: [example] [exempla]                 │
│ │                      [definition] [definitoin]           │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [x] Enable spell checking for this field                    │
│ Dictionary: English (US) ▼                                 │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Dictionary Management UI

#### 5.2.1 Dictionary Settings Page

```
┌─────────────────────────────────────────────────────────────┐
│ Spell Check Settings                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Default Language Dictionary                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ English (en-US)                        ▼            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Active Custom Dictionaries                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [✓] Medical Dictionary (en-US)         [Configure] │   │
│  │ [✓] Legal Dictionary (en-US)           [Configure] │   │
│  │ [ ] Technical Dictionary (en-US)       [Configure] │   │
│  │ [+ Add Custom Dictionary]                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Language-Specific Settings                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ en │ cs │ pl │ [Add Language]                       │   │
│  │  [x] Enable spell check    [x] Custom dictionary    │   │
│  │      Dictionary: English ▼                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [+ Upload New Dictionary]                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2.2 Upload Dictionary Modal

```
┌─────────────────────────────────────────────────────────────┐
│ Upload Custom Dictionary                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Language: *  [Search or select... ▼]                       │
│                                                             │
│  Dictionary Name: *  [e.g., Legal Czech Dictionary]         │
│                                                             │
│  Type: (*) Standard  ( ) Domain-Specific  ( ) Personal      │
│                                                             │
│  Description: [Optional description of the dictionary]      │
│                                                             │
│  Files: *                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Choose Files... No file chosen                       │   │
│  │ [+] Add another file (.aff and .dic required)        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📁 dictionary.dic  (2.4 MB)  [✕]                    │   │
│  │ 📁 dictionary.aff  (45 KB)    [✕]                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [ Cancel ]  [ Upload Dictionary ]                          │
│                                                             │
│  Note: Files will be validated before upload. Max 10MB.     │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Plan

### Phase 1: Core Infrastructure

#### 6.1.1 Backend Services

| Task | File | Description |
|------|------|-------------|
| Create Hunspell Service | `app/services/hunspell_service.py` | Core spell checking service with caching |
| Create Dictionary Management | `app/services/dictionary_service.py` | Upload/manage custom dictionaries |
| Create Spell Check API | `app/api/spell_check_api.py` | REST API endpoints |
| Extend Validation Engine | `app/services/validation_engine.py` | Add spell_check validation type |
| Database Migration | `migrations/` | Add custom_dictionaries tables |

#### 6.1.2 Frontend Services

| Task | File | Description |
|------|------|-------------|
| Spell Check Client | `app/static/js/spell-check-client.js` | Client-side spell check API wrapper |
| Update Inline Validation | `app/static/js/inline-validation.js` | Integrate spell checking |
| Dictionary Settings UI | `app/templates/admin/dictionaries.html` | Admin UI for dictionary management |
| Upload Component | `app/static/js/dictionary-upload.js` | File upload with validation |

### Phase 2: Validation Integration

| Task | File | Description |
|------|------|-------------|
| Add Spelling Rules | `validation_rules_v2.json` | Add spell_check rules |
| Client-side Rules | `app/static/js/client-validation-engine.js` | Add spell check logic |
| Error Display | Templates | Update error display for spelling |

### Phase 3: UI Polish

| Task | File | Description |
|------|------|-------------|
| Field-level Toggle | Templates | Add "Enable spell check" per field |
| Suggestion Dropdowns | `app/static/js/spell-suggestions.js` | Inline suggestion UI |
| Batch Check UI | `app/templates/tools.html` | Bulk spell check tool |

---

## 7. API Reference

### 7.1 Complete API Specification

```yaml
openapi: 3.0.3
info:
  title: Spell Check API
  version: 1.0.0
  description: API for spell checking and dictionary management

paths:
  /api/spell-check/check:
    post:
      summary: Check spelling of text
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SpellCheckRequest'
      responses:
        '200':
          description: Spell check results
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SpellCheckResponse'

  /api/spell-check/suggest:
    post:
      summary: Get spelling suggestions for a word
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                word:
                  type: string
                language_code:
                  type: string
                limit:
                  type: integer
                  default: 5
      responses:
        '200':
          description: List of suggestions

  /api/spell-check/dictionaries:
    get:
      summary: List available dictionaries
      parameters:
        - in: query
          name: language_code
          schema:
            type: string
        - in: query
          name: active_only
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: List of dictionaries

    post:
      summary: Upload custom dictionary
      requestBody:
        content:
          multipart/form-data:
            schema:
              $ref: '#/components/schemas/DictionaryUpload'

  /api/spell-check/dictionaries/{id}:
    delete:
      summary: Delete custom dictionary
      responses:
        '204':
          description: Dictionary deleted

  /api/spell-check/batch:
    post:
      summary: Batch spell check multiple entries
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BatchSpellCheckRequest'
      responses:
        '200':
          description: Batch results

components:
  schemas:
    SpellCheckRequest:
      type: object
      required:
        - text
        - language_code
      properties:
        text:
          type: string
          description: Text to check
        language_code:
          type: string
          description: Language code (e.g., 'en-US')
        options:
          type: object
          properties:
            check_compound_words:
              type: boolean
              default: true
            ignore_numbers:
              type: boolean
              default: true
            ignore_urls:
              type: boolean
              default: true
            return_suggestions:
              type: boolean
              default: false

    SpellCheckResponse:
      type: object
      properties:
        valid:
          type: boolean
        errors:
          type: array
          items:
            $ref: '#/components/schemas/SpellingError'
        word_count:
          type: integer
        error_count:
          type: integer

    SpellingError:
      type: object
      properties:
        word:
          type: string
        start_pos:
          type: integer
        end_pos:
          type: integer
        suggestions:
          type: array
          items:
            type: string
        context:
          type: string

    DictionaryUpload:
      type: object
      required:
        - language_code
        - dictionary_name
        - aff_file
        - dic_file
      properties:
        language_code:
          type: string
        dictionary_name:
          type: string
        dictionary_type:
          type: string
          enum: [standard, custom, domain_specific]
        description:
          type: string
        is_default:
          type: boolean
        aff_file:
          type: string
          format: binary
        dic_file:
          type: string
          format: binary

    BatchSpellCheckRequest:
      type: object
      required:
        - entries
        - language_code
      properties:
        entries:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              fields:
                type: object
                additionalProperties:
                  type: string
        language_code:
          type: string
```

---

## 8. Security Considerations

### 8.1 Input Validation
- Validate uploaded dictionary files (verify .aff/.dic format)
- Limit file size (max 10MB per dictionary)
- Scan uploaded files for malicious content
- Sanitize dictionary names and descriptions

### 8.2 Access Control
- Require authentication for dictionary upload/delete
- Restrict dictionary deletion (only owner or admin)
- Audit log for dictionary operations

### 8.3 Performance
- Cache loaded dictionaries in memory (with LRU eviction)
- Limit concurrent spell check requests per user
- Add request timeouts for spell check operations
- Consider async processing for batch operations

---

## 9. Testing Strategy

### 9.1 Unit Tests

| Test | Description |
|------|-------------|
| `test_hunspell_service_basic` | Basic spell check functionality |
| `test_hunspell_service_suggestions` | Suggestion generation |
| `test_multi_language` | Multiple language dictionaries |
| `test_custom_dictionary_loading` | Custom dictionary loading |
| `test_dictionary_caching` | Dictionary caching behavior |
| `test_edge_cases` | Empty text, special characters, etc. |

### 9.2 Integration Tests

| Test | Description |
|------|-------------|
| `test_spell_check_api` | API endpoint responses |
| `test_dictionary_upload_flow` | Full upload and validation flow |
| `test_validation_engine_integration` | Integration with validation engine |
| `test_batch_spell_check` | Batch spell check operations |

### 9.3 E2E Tests (Playwright)

| Test | Description |
|------|-------------|
| `test_inline_spell_check` | Real-time spell checking in entry form |
| `test_dictionary_upload_ui` | Complete dictionary upload workflow |
| `test_spell_check_toggle` | Enable/disable spell checking per field |
| `test_suggestion_selection` | Clicking suggestion replaces misspelled word |

---

## 10. Dependencies

### 10.1 Python Dependencies

```txt
# requirements.txt additions
hunspell>=2.0.0  # Pure Python Hunspell implementation
# Optional: cyhunspell>=1.7.0  # Fast C extension (install separately)
```

### 10.2 System Dependencies (Optional)

For `cyhunspell` (performance optimization):
```bash
# Ubuntu/Debian
apt-get install libhunspell-dev

# macOS
brew install hunspell

# Windows
# Download from https://github.com/kwrok44/HunspellForWindows
```

---

## 11. Future Enhancements

### 11.1 Roadmap
1. **v2.0**: Personal user dictionaries (per-user word lists)
2. **v2.1**: Machine learning-based spelling suggestions
3. **v2.2**: Browser extension for spell checking
4. **v2.3**: Grammar checking integration (LanguageTool)

### 11.2 Potential Extensions
- **Domain-specific dictionaries**: Pre-built for legal, medical, technical domains
- **Collaborative dictionaries**: Team-shared custom dictionaries
- **Dictionary versioning**: Track dictionary changes over time
- **Dictionary merging**: Combine multiple dictionaries

---

## 12. Appendix

### 12.1 Hunspell Dictionary Format

Standard Hunspell dictionaries consist of two files:

**.aff file** (Affix file):
```
SET UTF-8
TRY esianrtolcdugmphbyfkvżźśńąęół
REP 2
REP a ä
REP o ö
```

**.dic file** (Dictionary file):
```
3
hello
world
dictionary
```

### 12.2 Language Code Mapping

| Language | Code | Notes |
|----------|------|-------|
| English (US) | en-US | Standard |
| English (GB) | en-GB | British spellings |
| Czech | cs-CZ | Standard |
| Polish | pl-PL | Standard |
| IPA (Custom) | ipa-x-ipa | User-defined phonetic alphabet |
| Custom Domain | {lang}-x-{domain} | Extension format (RFC 5646) |

### 12.3 Example: IPA Validation Rule

```json
{
  "R10.3.1": {
    "name": "ipa_spell_check",
    "category": "pronunciation",
    "priority": "informational",
    "path": "$.pronunciations[*].form.ipa",
    "condition": {
      "type": "if_present"
    },
    "validation": {
      "type": "spell_check",
      "dictionary": "ipa-x-ipa"
    },
    "error_message": "Invalid IPA notation: {misspelled_symbols}",
    "validation_mode": "all",
    "enabled": false
  }
}
```

---

## 13. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-31 | Feature Spec | Initial specification |
