# Entry Form Refactoring - Breaking Changes Summary

**Date**: 2025-11-25  
**Status**: Ready for Implementation

## Overview

We've successfully moved `usage_type` and `domain_type` (semantic domain) fields to the **Sense model** (sense-level) to align with LIFT 0.13 XML schema. The backend changes are complete, but the **entry form UI** still has these fields at the **entry level**, which is incorrect.

## What's Been Completed ✅

1. **Sense Model Updated** (`app/models/sense.py`)
   - Added `usage_type: list[str]` field
   - Added `domain_type: list[str]` field (for semantic domain)

2. **LIFT Parser Updated** (`app/parsers/lift_parser.py`)
   - Now parses `<trait name="usage-type">` from sense elements
   - Now parses `<trait name="domain-type">` from sense elements

3. **Form Processing Fixed** (`app/utils/multilingual_form_processor.py`)
   - Fixed to output flattened format `{lang: {text: value}}` consistently
   - Handles sense-level data correctly

4. **Unit Tests Fixed**
   - 228 unit tests passing (up from 209)
   - Only 3 pre-existing validation failures remain

5. **Integration Tests - Playwright Hanging Fixed**
   - Updated `playwright_page` fixture in `tests/integration/conftest.py`
   - Now runs in headless mode (`headless=True`)
   - Proper cleanup with try/finally blocks
   - Browser, context, and page always closed even on test failures

## What Needs Refactoring ⚠️

### 1. Entry Form Template (`app/templates/entry_form.html`)

**Current Issue**: Lines 127-147 have semantic domain and usage type at entry level:

```html
<!-- LIFT Ranges: Semantic Domain -->
<div class="mb-3">
    <label for="semantic-domain-list" class="form-label">Semantic Domain</label>
    <select class="form-select dynamic-lift-range" id="semantic-domain-ddp4" name="semantic_domain" 
            data-range-id="semantic-domain-ddp4" 
            data-hierarchical="true" 
            data-searchable="true">
        <option value="">Select semantic domain</option>
    </select>
</div>

<!-- LIFT Ranges: Usage Type -->
<div class="mb-3">
    <label for="usage-type" class="form-label">Usage Type</label>
    <select class="form-select dynamic-lift-range" id="usage-type" name="usage_type" 
            data-range-id="usage-type"
            data-hierarchical="true"
            data-searchable="true">
        <option value="">Select usage type</option>
    </select>
</div>
```

**Required Change**: Move these fields INSIDE the sense card template (starting around line 886), alongside definition and gloss fields.

**Updated Field Names** (sense-level):
- `name="senses[{{ loop.index0 }}].usage_type"`
- `name="senses[{{ loop.index0 }}].semantic_domain"` (or `domain_type`)

### 2. JavaScript (`app/static/js/entry-form.js`)

**Required Changes**:
- Update field selectors for usage_type and semantic_domain
- Update serialization logic in `serializeFormData()` to handle these at sense level
- Update `addSenseRow()` to include usage_type and semantic_domain fields
- Update `removeSense()` to handle these fields
- Ensure LIFT range loading works for sense-level fields

### 3. Form Processor (`app/utils/multilingual_form_processor.py`)

**Verification Needed**:
- Ensure `process_senses_form_data()` handles `usage_type` and `domain_type` as **lists**
- These should be extracted from sense data, not entry data
- Values should be stored as `list[str]` to support multiple selections

### 4. Integration Tests

**Files to Update**:
- `tests/integration/test_validation_playwright.py` - Update field selectors
- `tests/integration/test_ui_ranges_phase4.py` - Update semantic domain tests to check sense-level
- `tests/integration/test_workset_api.py` - Update semantic domain filtering (if applicable)

**Example Update**:
```python
# OLD (entry-level)
page.fill('select[name="semantic_domain"]', 'value')

# NEW (sense-level)
page.fill('select[name="senses[0].semantic_domain"]', 'value')
```

### 5. API/Routes (If Applicable)

**Check**:
- Any routes that filter by semantic_domain or usage_type
- Any API endpoints that expect these at entry level
- Update to look at sense-level data instead

## Migration Strategy

1. **Template First**: Move fields in `entry_form.html` to sense section
2. **JavaScript Second**: Update `entry-form.js` to handle sense-level fields
3. **Test Integration**: Update integration tests for new field locations
4. **Verify Form Processing**: Ensure backend correctly processes sense-level data
5. **Manual Testing**: Create/edit entries, verify data persists to BaseX
6. **Update Documentation**: Update API docs if affected

## Backward Compatibility

**Breaking Changes**:
- Any existing entries with entry-level `semantic_domain` or `usage_type` will need migration
- Form submissions with old field names will fail validation
- External API clients may need updates

**Migration Script Needed?**:
- Check if any production data has entry-level semantic_domain/usage_type
- If yes, create migration script to move data to first sense

## Testing Checklist

- [ ] Template renders correctly with fields at sense level
- [ ] JavaScript serializes sense-level fields correctly
- [ ] Form submission saves data to correct sense
- [ ] Data persists to BaseX XML correctly
- [ ] LIFT parser reads back data correctly
- [ ] Integration tests pass
- [ ] Manual end-to-end test: create entry → save → edit → verify data

## Questions for User

1. Should we support **multiple selections** for semantic_domain and usage_type? (Currently implemented as lists in model)

Yes, allow users to select multiple values. This matches LIFT 0.13 XML schema where both can contain multiple values separated by semicolons.

2. Should we create a **migration script** for existing data?

The existing data already is in LIFT format, our codebase is incompatible with it, so no. We'll just update the form to work with sense-level data only.

3. Are there any **API endpoints** that rely on entry-level semantic_domain/usage_type?

I do not know. Check.

4. Should semantic_domain be renamed to `domain_type` everywhere for consistency with LIFT schema?

Yes. But note that there are academic domains as well, and these are different and not yet implemented (much much more important for my purposes.)

---

**Next Action**: Begin template refactoring (task #7 in todo list)
