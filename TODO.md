# Outstanding project issues and bugs

## Critical Issues

### 1. Ranges Data Not Loading from Database

**Status**: Identified, needs fix  
**Error**: `DictionaryService.get_ranges()` fails to load LIFT ranges from database, returns empty dict  
**Impact**: Dropdown menus (grammatical info, relation types, etc.) are empty  
**Fix Applied**: Changed fallback from calling missing `_get_default_ranges()` method to returning empty dict (prevents 500 error, now returns 404)  
**Next Steps**:

- Investigate why ranges document is not found in database queries
- Check if ranges are imported correctly during LIFT file import
- May need to add default ranges or fix database queries in `DictionaryService.get_ranges()` (lines 1294-1363)

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
