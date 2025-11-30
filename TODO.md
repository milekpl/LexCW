# Outstanding project issues and bugs

## 🚧 REVOLUTIONARY CHANGE IN PLANNING

### XML Direct Manipulation Architecture

**Status**: ✅ APPROVED - Ready to implement  
**Impact**: 🔴 BREAKING CHANGE - Major architectural revolution  
**Plan**: [`docs/XML_DIRECT_MANIPULATION_PLAN.md`](docs/XML_DIRECT_MANIPULATION_PLAN.md)  
**Kickoff**: [`IMPLEMENTATION_KICKOFF.md`](IMPLEMENTATION_KICKOFF.md)

**Summary**: Transition from WTForms-based entry editing to **direct XML manipulation** in BaseX. This simplifies the architecture by removing intermediate Python object conversion.

**Key Changes**:
- Form operations will directly create/modify LIFT XML elements
- JavaScript-based XML serialization replacing WTForms
- XQuery-based CRUD operations instead of Python object → XQuery
- Simplify Entry/Sense models to XML wrapper classes
- Keep PostgreSQL only for: worksets, corpus analytics, validation results (no change)

**Clarification**: PostgreSQL was **never** used for entry storage - entries are already in BaseX XML. This change just makes the form → BaseX flow more direct.

**Timeline**: 4-week implementation plan  
**Status**: Ready to start - see [`IMPLEMENTATION_KICKOFF.md`](IMPLEMENTATION_KICKOFF.md) for day-by-day tasks

---

## Critical Issues

### 1. Ranges Data Not Loading from Database

**Status**: ✅ FIXED (API), ⚠️ UI TESTS PENDING
**Error**: LIFT ranges were not loading in dropdowns due to:
1. Wrong BaseX query (hardcoded filename)  
2. Missing API route mappings (`academic-domain` → `domain-type`)
3. Incorrect API response format (missing `success` field)
4. JavaScript only initialized `.dynamic-grammatical-info`, not all `.dynamic-lift-range` elements
5. **Missing mapping in app/api/ranges.py** - was editing wrong file initially

**Fix Applied**:
1. Changed BaseX query from `doc('{db}/sample-lift-file.lift-ranges')` to `collection('{db}')//lift-ranges`
2. Added mappings in **app/api/ranges.py** (THE ACTUAL API FILE IN USE):
   - `'academic-domain': 'domain-type'`
   - `'academic-domains': 'domain-type'`
3. Fixed API response format to include `success: true` and `data:` keys  
4. Extended `initializeDynamicSelects()` to populate ALL `.dynamic-lift-range` elements
5. Fixed JavaScript syntax error: "const grammatic selects" → "const dynamicSelects"
6. Updated test data in conftest.py to use `domain-type` instead of `academic-domain`

**Files Modified**:
- `app/services/dictionary_service.py` (lines 1294-1365) - BaseX query fix
- `app/api/ranges.py` (lines 174-184) - **PRIMARY FIX** - Added academic-domain mapping
- `app/routes/api_routes.py` (lines 90-170) - API response format (not used in tests)
- `app/static/js/entry-form.js` (lines 48-88) - Initialize all dynamic-lift-range, fixed syntax
- `tests/conftest.py` (lines 310-370) - Updated test data to use domain-type

**Tests Created**:
- `tests/integration/test_all_ranges_dropdowns_playwright.py` - Comprehensive Playwright tests

**Verification Status**:
- ✅ API Endpoints Working (test_all_ranges_api_accessible PASSED):
  - `GET /api/ranges/grammatical-info` → 200 OK
  - `GET /api/ranges/academic-domain` → 200 OK (mapped to domain-type)
  - `GET /api/ranges/semantic-domain` → 200 OK (mapped to semantic-domain-ddp4)
  - `GET /api/ranges/usage-type` → 200 OK
- ⚠️ UI Form Tests: Failing because `/entries/new` redirects (needs real entry ID)
- ℹ️ Next: Manual verification in browser or fix UI tests to use existing entry

## Non-Critical Issues

### 2. Source Language Definition Requirements

The source language should not require a definition if there is none. Currently, it does, which makes NO sense for me (validation does not require this!). Also, if there is an empty definition, I should be able to remove it, especially if it is an empty definition / gloss for the source language.

### 3. Remaining Issues in Validation (failures)

- Note Structure Validation: Missing validation rule implementation (failing unit test)
- IPA Character Validation: Missing validation rule  implementation (failing unit test)
- POS Consistency Rules: Missing validation rule implementation

### 4. Make validation rules editable per project

Is this in JSON?

## Recently Fixed

### ✅ Sense Deletion Bug (FIXED)

**Issue**: Deleted senses reappeared after save  
**Root Cause**: Orphaned multilingual form fields (definition.pl, gloss.pl) remained in DOM outside deleted `.sense-item` containers  
**Fix**: FormSerializer now disables orphaned sense fields before serialization by validating field indices against actual visible sense items  
**Test Coverage**: `tests/integration/test_sense_deletion_fixed.py::test_sense_deletion_persists_after_save` ✅ PASSING  
**Files Modified**:

- `app/static/js/form-serializer.js` (lines 35-65) - orphaned field detection
- `app/templates/entry_form.html` (line 1149) - marked default template
- `app/static/js/entry-form.js` - console logging for debugging

### ✅ Validation Blocking Entry Loads/Saves (FIXED)

**Fix**: Made validation non-blocking with `skip_validation` parameter throughout save chain, added UI checkbox
