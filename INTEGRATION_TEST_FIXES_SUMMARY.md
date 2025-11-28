# Integration Test Fixes Summary

## Date: November 25, 2025

## Overview
Fixed failing integration tests by addressing validation engine issues, porting Selenium tests to Playwright, and fixing server-side validation logic.

## Test Results Improvement
- **Before**: 422 passed, 68 failed, 296 skipped, 91 errors (877 total)
- **After**: 430 passed, 60 failed, 300 skipped, 91 errors (881 total)
- **Improvement**: +8 passing tests, -8 failing tests

## Changes Made

### 1. Validation Engine Fixes (app/services/declarative_validation_engine.py)
**Issue**: Array element validation was failing on empty arrays, causing draft mode to reject entries without senses.

**Fixes**:
- Added check for array wildcard paths `[*]` - when no targets found (empty array), skip validation instead of erroring
- Updated validation mode handling to skip `save_only` rules in both `draft` and `delete` modes
- This allows progressive workflow: draft → add senses → save

**Code changes**:
```python
# Before: Created error when targets empty
if not targets:
    errors.append(ValidationError(...))
    
# After: Skip validation for empty arrays
if not targets:
    if '[*]' in path:  # Array element validation
        return errors  # Empty array is OK
    errors.append(ValidationError(...))
```

### 2. Validation Rules (validation_rules_v2.json)
**Issue**: Entry ID pattern allowed spaces, but tests expected rejection.

**Fix**: Updated R1.2.1 pattern from `^[a-zA-Z0-9_\\- ]+$` to `^[a-zA-Z0-9_\\-]+$` (removed space)

### 3. Selenium to Playwright Migration
**Created**: `tests/integration/test_relations_variants_ui_playwright.py`

**Ported 4 tests**:
- `test_variant_container_displays_correctly` - Verifies variant UI hides technical debug info
- `test_relations_container_displays_correctly` - Verifies relations UI is user-friendly
- `test_variant_form_interaction` - Tests adding variants through UI
- `test_relation_form_interaction` - Tests adding relations through UI

**Changes from Selenium**:
- Use Playwright's `page.locator()` instead of Selenium's `find_element()`
- Use Playwright's `expect().to_be_visible()` instead of `is_displayed()`
- Use `page.wait_for_selector()` instead of WebDriverWait
- Use `page.wait_for_function()` for JavaScript initialization
- Removed Flask test server setup (use live_server fixture)
- Better error handling with Playwright's built-in waits

## Validation Test Results

### test_validation_rules.py
**Status**: 21/33 passing (63.6%)

**Passing** (21 tests):
- All validation mode tests (draft, delete, progressive workflow)
- Entry ID required/format validation
- Lexical unit required/format/language validation  
- Sense ID and content validation
- Definition and gloss content validation
- Unique note types
- Relation reference integrity
- Dynamic range validation (LIFT ranges, variant types, language codes)
- Error reporting with field paths

**Failing** (9 tests) - Unimplemented features:
- Example text validation
- Note content validation
- Pronunciation language restriction
- IPA character validation  
- Double stress/length markers
- POS consistency rules
- Relation type validation

**Skipped** (3 tests):
- Dictionary service draft mode (BaseX not available)
- Multilingual note structure
- Bulk validation performance

## Remaining Issues

### 1. BaseX Connection Errors (91 errors)
Most errors are due to BaseX server not running during tests:
```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Affected test categories**:
- Dictionary service tests
- Real integration tests
- Search functionality tests
- Performance benchmarks
- Live search tests
- Selenium UI tests (old)

**Resolution needed**: 
- Start BaseX server for integration tests, OR
- Mock BaseX connections for tests that don't need real database

### 2. Playwright Tests Using live_server
**Status**: Playwright tests are being skipped because BaseX isn't available

**Tests affected**:
- Settings page Playwright tests
- Validation Playwright tests
- POS UI tests
- Newly created relations/variants Playwright tests

### 3. Server-Side Validation Only
Per KISS principle, validation is now server-side only (no client-side duplication).

**Impact on tests**:
- Validation errors appear after form submission, not in real-time
- Tests should check for errors after clicking submit button
- No need to test client-side JavaScript validation

## Recommendations

### Immediate Actions
1. **Start BaseX server** for integration tests or add proper mocking
2. **Review unimplemented validation rules** - decide if they should be implemented or tests removed
3. **Update Playwright test expectations** to match server-side validation approach

### Future Improvements
1. **Complete Playwright migration** - remove all Selenium tests after verifying Playwright equivalents work
2. **Implement missing validation rules** if they're part of the specification
3. **Add CI/CD integration** to run BaseX in test environment
4. **Update test documentation** to reflect server-side validation approach

## Files Modified
1. `app/services/declarative_validation_engine.py` - Fixed array validation and mode handling
2. `validation_rules_v2.json` - Fixed entry ID format pattern
3. `tests/integration/test_relations_variants_ui_playwright.py` - New file (Playwright version)

## Test Execution
To run the improved tests:
```bash
# All integration tests
python3 -m pytest tests/integration/ -m integration -v

# Validation tests only
python3 -m pytest tests/integration/test_validation_rules.py -v

# Playwright tests (requires live_server and BaseX)
python3 -m pytest tests/integration/test_relations_variants_ui_playwright.py -v
```
