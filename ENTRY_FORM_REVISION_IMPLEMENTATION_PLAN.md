# Entry Form Revision Implementation Plan

## Overview

This document outlines the implementation plan and progress tracking for enhancing the entry form in the dictionary application.

**Last Updated:** 2026-01-02

---

## Implementation Progress Summary

| Feature/Issue | Status | Effort Saved |
|--------------|--------|--------------|
| Code Quality: JavaScript Namespace (DictionaryApp) | ✅ Completed | - |
| Code Quality: Duplicate field names (domain_type) | ✅ Completed | - |
| Code Quality: CSRF Token Protection | ✅ Completed | - |
| Code Quality: Debug Logs Removal | ❌ Pending | 0.5 day |
| Code Quality: Language Code Consolidation | ❌ Pending | 0.25 day |
| Code Quality: Script Loading Order | ❌ Pending | 0.25 day |
| DELETE Button for Dictionary Artifacts | ❌ Pending | 2-3 days |
| Sense-level Variant Relations | ✅ Completed | - |
| Hierarchical Dropdowns | ❌ Pending | 3-4 days |
| Field Visibility Modal Refactor | ❌ Pending | 2-3 days |
| XQuery Builder Entry Update Fix | ✅ Completed | - |
| JavaScript Architecture Refactor | ❌ Pending | 4-5 days |

---

## Code Quality Issues - Current Status

### ✅ Completed Issues

#### 1. JavaScript Global Variable Pollution - FIXED

**Status:** ✅ Completed

**Implementation:**
- `DictionaryApp` namespace properly implemented in `entry_form.html:1038-1056`
- Global data wrapped in IIFE with error handling
- CSRF token included in `DictionaryApp.config`

**Files Modified:**
- `app/templates/entry_form.html`

```javascript
(function() {
    'use strict';
    try {
        window.DictionaryApp = window.DictionaryApp || {};
        window.DictionaryApp.data = {
            ranges: {{ ranges | tojson | safe }},
            componentRelations: {{ (forward_component_relations | default([])) | tojson | safe }}
        };
        window.DictionaryApp.config = {
            entryId: '{{ entry.id | default("") }}',
            csrfToken: csrfToken
        };
    } catch (e) {
        console.error('Failed to initialize DictionaryApp namespace:', e);
    }
})();
```

#### 2. Duplicate field names (domain_type) - FIXED

**Status:** ✅ Completed

**Issue:** `domain_type` was defined twice with different ranges, causing data overwrite.

#### 3. CSRF Token Protection - FIXED

**Status:** ✅ Completed

**Implementation:**
- CSRF meta tag now always renders (not conditional)
- `getCsrfToken()` helper added to all JavaScript files
- All fetch requests include `X-CSRF-TOKEN` header

**Files Modified:**
- `app/templates/base.html` - Always render CSRF meta tag
- `app/static/js/ranges-editor.js` - Added getCsrfToken() and CSRF headers
- `app/static/js/validation-rules-manager.js` - Added getCsrfToken() and CSRF headers
- `app/templates/validation_tool.html` - Added getCsrfToken() and CSRF header

**E2E Tests Added:**
- `tests/e2e/test_csrf_protection_playwright.py`

### ❌ Pending Issues

#### 4. Debug Code Left in Production - HIGH PRIORITY

**Status:** ❌ NOT DONE

**Files Affected:**
- `app/static/js/form-state-manager.js` - 5 console.log statements
- `app/static/js/lift-xml-serializer.js` - 3 console.log statements
- `app/static/js/entry-form.js` - 22+ console.log statements

**Example of problematic code:**
```javascript
// entry-form.js:693-698
console.log('[SENSE DELETION] Removing sense:', senseId);
console.log('[SENSE DELETION] Sense count before removal:', ...);
console.log('[SENSE DELETION] Sense count after removal:', ...);
```

**Solution:** Create `Logger` utility with debug mode toggle:
```javascript
const Logger = {
    debug: (...args) => { if (DictionaryApp.config.debug) console.log(...args); },
    error: (...args) => console.error(...args),
    warn: (...args) => console.warn(...args)
};
```

**Effort:** 0.5 day

#### 5. Duplicate Language Code Extraction

**Status:** ❌ NOT DONE

**Found instances:**
- `entry_form.html:96` - Defines `source_lang`
- `entry_form.html:440,750` - Duplicates with `{% set default_lang_code = source_lang %}`
- `_basic_info.html:9` - Separate definition with different approach

**Effort:** 0.25 day

#### 6. Script Loading Order

**Status:** ❌ NOT DONE

**Issue:** 20+ scripts loaded without `defer` attribute - potential race conditions

**Current State:**
```html
<script src="{{ url_for('static', filename='js/lift-xml-serializer.js') }}"></script>
<script src="{{ url_for('static', filename='js/form-serializer.js') }}"></script>
<!-- No defer on any script tags -->
```

**Solution:** Add `defer` attribute to script tags where order matters.

**Effort:** 0.25 day

---

## Feature Implementation Details

### ✅ Sense-Level Variant Relations - COMPLETED

**Status:** ✅ COMPLETED

**Backend Changes:**
- `app/models/sense.py`:
  - Added `variant_relations` list attribute
  - Added `add_variant_relation()` method
  - Added `remove_variant_relation()` method
  - Updated `to_dict()` to include `variant_relations`

**Frontend Changes:**
- `app/templates/entry_form_partials/_senses.html`:
  - Added "Variant Relations" section after Examples
- `app/static/js/sense-variant-relations.js`:
  - New `SenseVariantRelationsManager` class
  - Add/remove variant relations with proper indexing
  - Select2 integration for variant type dropdown

### ❌ DELETE Button for Dictionary Artifacts

**Status:** ❌ NOT IMPLEMENTED

**Required Changes:**

**Frontend (`entry_form.html`):**
```html
{% if entry.id %}
<button type="button" class="btn btn-outline-danger me-2" id="delete-entry-btn">
    <i class="fas fa-trash-alt"></i> DELETE ENTRY
</button>
{% endif %}
```

**JavaScript:**
```javascript
document.getElementById('delete-entry-btn')?.addEventListener('click', function() {
    // Two-step confirmation process
});
```

**Backend:**
- Route: `POST /entries/<entry_id>/delete`
- Dependency checking to prevent orphaned references
- CSRF protection
- Audit logging

**Effort:** 2-3 days

### ❌ Hierarchical Dropdowns for Usage Type and Domain Type

**Status:** ❌ NOT IMPLEMENTED

**Required Changes:**
- Update dropdown markup to use `multiple` attribute
- Add hierarchical option rendering
- Initialize Select2 with hierarchical support
- Update form serialization for multiple selections
- Modify backend models to handle arrays

**Effort:** 3-4 days

### ❌ Field Visibility Modal Refactor

**Status:** ❌ NOT IMPLEMENTED

**Required Steps:**
1. Extract modal to `app/templates/macros/field_visibility_modal.html`
2. Create `app/static/js/field-visibility-manager.js`
3. Update `entry_form.html` to use macro
4. Initialize manager in entry_form setup

**Effort:** 2-3 days

### ✅ XQuery Builder Entry Update Fix - COMPLETED

**Status:** ✅ Completed (2026-01-02)

**Issue:** After updating an entry (e.g., adding grammatical info), the entry could not be found.

**Root Cause:** The `build_insert_entry_query` and `build_update_entry_query` methods assumed entries were stored under a `<lift>` root element, but they are stored as separate documents directly in the database collection.

**Fix Applied:**
- `build_insert_entry_query`: Changed from `collection('dictionary')/lift` to `collection('dictionary')`
- `build_update_entry_query`: Changed from `collection('dictionary')/lift/entry[@id="..."]` to `collection('dictionary')//entry[@id="..."]`

**Files Modified:**
- `app/utils/xquery_builder.py`

**Verification:**
- All 910 unit tests pass
- Entry update flow tested successfully:
  - Create entry ✓
  - Retrieve entry ✓
  - Update entry ✓
  - Entry still exists after update ✓
  - Updated content is preserved ✓

---

## Testing Results

### Unit Tests
```
910 passed, 8 skipped
```

### Integration Tests
```
tests/integration/test_dashboard.py: 22 passed
tests/integration/test_settings_route.py: 6 passed
```

### CSRF Protection E2E Tests
```
tests/e2e/test_csrf_protection_playwright.py: Created
```

---

## Remaining Work Items

### Immediate (This Sprint)

| Priority | Item | Effort | Owner |
|----------|------|--------|-------|
| 1 | Remove debug console.log statements | 0.5 day | - |
| 2 | Consolidate language code definitions | 0.25 day | - |
| 3 | Add defer to script tags | 0.25 day | - |

### Short Term (Next 2-3 Sprints)

| Feature | Effort | Dependencies |
|---------|--------|--------------|
| DELETE Button | 2-3 days | CSRF protection ✓ |
| Hierarchical Dropdowns | 3-4 days | - |
| Field Visibility Modal | 2-3 days | - |

### Long Term

| Feature | Effort | Dependencies |
|---------|--------|--------------|
| JavaScript Architecture Refactor | 4-5 days | FormEventBus, FormComponent |
| Per-Project Visibility (Database) | 3-4 days | FieldVisibilityManager ✓ |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| DELETE Button: Accidental data loss | Two-step confirmation, dependency checking, logging |
| Hierarchical Dropdowns: Breaking existing functionality | Backward compatibility, extensive testing |
| Field Visibility Modal: Breaking modal during refactor | Extract without behavior change first |

---

## Documentation

- **Code Review Document:** `CODE_REVIEW_dictionary_service.md`
- **Implementation Plan:** This document
- **Test Reports:** See CI/CD pipeline

---

## Change Log

| Date | Description |
|------|-------------|
| 2026-01-02 | Added XQuery Builder entry update fix; Updated CSRF protection; Added CSRF E2E tests |
| 2024-XX-XX | Initial document creation |
