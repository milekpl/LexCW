# Plan: FieldWorks list.xml Integration for Real Abbreviations

## Problem
- `list.xml` (118K lines, 36 lists) contains the real FieldWorks abbreviations for Parts of Speech, Variant Types, Complex Form Types, Lexical Relations, etc.
- The app currently auto-generates fake abbreviations (`v[:3].lower()`) or shows empty
- The Range Editor shows no abbreviations, and variant types are flat (not hierarchical)
- The `list.xml` format (`<lists><list><letitem>...`) is completely different from LIFT ranges XML (`<lift-ranges><range><range-element>...`)

## Phase 1: Create `FieldWorksListParser`
**New file:** `app/parsers/fieldworks_list_parser.py`

Parse all 36 list types from list.xml into a unified dict format compatible with the existing ranges system. Each list produces `{range_id: {id, values: [{id, label, labels, abbrev, abbrevs, description, children, ...}]}}`.

Out-of-scope for Phase 1 but tracked for later:
- Semantic Domains (`<sditem>`) — huge, nested, very complex
- Anthropology Categories (`<aitem>`)

Item types to handle:
- `<letitem>` — lexical entry types (Complex Form Types, Variant Types)
- `<positem>` — Parts of Speech
- `<item>` — generic (Publications, Sense Types, Usages, etc.)
- `<lrtitem>` — Lexical Relations
- `<mtitem>` — Morpheme Types
- `<locitem>` — Locations
- `<peritem>` — People

Field extraction from each item:
- `id` → from `<name><str ws="Eng">` or `<name><str ws="Pol">`
- `guid` → from `<guidi>`
- `parent` → from nested `<subitems>` hierarchy
- `label` / `labels` → from `<name><str ws="LANG">`
- `abbrev` / `abbrevs` → from `<abbr><str ws="LANG">`
- `description` → from `<descr>`

## Phase 2: Map list.xml Lists to App Range IDs

```python
LIST_TO_RANGE_MAP = {
    "Complex Form Types": "complex-form-type",
    "Variant Types": "variant-type",
    "Parts Of Speech": "grammatical-info",
    "Lexical Relations": "lexical-relation",
    "Semantic Domains": "semantic-domain-ddp4",
    "Morpheme Types": "morph-type",
    "Locations": "location",
    "Anthropology Categories": "anthro-code",
    "Publications": "Publications",
    "Status": "status",
    "People": "users",
    "Usages": "usage-type",
    "Academic Domains": "domain-type",
    "Sense Types": "sense-type",
    "Dialect Labels": "dialect",
    "Restrictions": "restrictions",
    "Translation Types": "translation-type",
    "Education Levels": None  # not in STANDARD_RANGE_METADATA
}
```

## Phase 3: Integration Paths (choose one or combine)

### Option A: API endpoint + CLI command (RECOMMENDED)
- Add `POST /api/ranges/import-list-xml` endpoint that accepts a list.xml file
- Parses it with `FieldWorksListParser`
- For each list that maps to an app range ID, upserts the values into BaseX (`<lift-ranges>/<range id="...">`)
- Existing `<range-element>` values are updated with real abbrevs; new ones are added
- The range editor reads from BaseX → real abbreviations show
- The CSS preview reads from BaseX → real abbreviations show
- Also add a CLI command (`flask import-list-xml path/to/list.xml`)

### Option B: Auto-import on LIFT file import
- Add to `LIFTImportService.import_lift()`: scan for a `list.xml` in the same directory
- Parse it and store in BaseX after the main import
- Less explicit, more magical

### Option C: Config file pre-population
- Parse list.xml offline, extract abbreviations into `custom_ranges.json`
- Ship the config with the app
- Only covers the 4 values already in custom_ranges.json; doesn't solve the dynamic extraction

**Recommendation: Option A** — explicit, testable, reusable.

## Phase 4: Hierarchy Support in Range Editor

Currently the Range Editor shows variant types as a flat list. The items in list.xml have a hierarchical structure (e.g., "Irregularly Inflected Form" → "Gerundium", "Past", "Past Participle").

The `renderElement()` function in `ranges-editor.js:507-558` already handles nested children via recursive calls. The hierarchy data is in the `children` key of each element dict. Problem: SQL `custom_range_values` stores values flat (no parent-child). BaseX stores hierarchies via the `parent` attribute.

To fix:
1. Ensure list.xml import preserves the `<subitems>` hierarchy as `children` nested dicts in BaseX
2. The BaseX `<range-element parent="...">` attributes already encode parent-child relationships
3. The parser already handles this via `_parse_range_element` which reads the `parent` attribute

No frontend changes needed — the recursive rendering already works when data has `children`.

## Phase 5: Verification

1. **Parser tests**: Unit tests for `FieldWorksListParser` with a small sample `lists.xml`
2. **Import test**: Test `POST /api/ranges/import-list-xml` with the sample file
3. **Range Editor test**: Open the range editor, verify variant types show real abbreviations (e.g., "irreg. infl." for Irregularly Inflected Form, "cont." for Gerundium)
4. **CSS preview test**: Verify variant relations in the entry editor show real abbreviations
5. **Existing tests**: All 1962 unit tests must pass

## Critical Files to Modify

| File | What to Change |
|------|---------------|
| `app/parsers/fieldworks_list_parser.py` | **New file** — parse list.xml format |
| `app/api/ranges.py` | Add `POST /import-list-xml` endpoint |
| `app/services/ranges_service.py` | Add method to upsert range values from list.xml data |
| `app/services/lift_import_service.py` | Optionally integrate list.xml auto-import |
| `app/services/dictionary_service.py` | No change needed — already reads from ranges |
| `app/services/css_mapping_service.py` | Already has computed fallback; will use real abbrevs from ranges |
| `app/static/js/ranges-editor.js` | Already reads `abbrev` + `effective_abbrev` |
| `app/config/custom_ranges.json` | May be partially replaced by list.xml data |
