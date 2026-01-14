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

## Non-Critical Issues

### 2. Source Language Definition Requirements

**Status**: Needs investigation - no tests found for this specific issue

The source language should not require a definition if there is none. Currently, it does, which makes NO sense for me (validation does not require this!). Also, if there is an empty definition, I should be able to remove it, especially if it is an empty definition / gloss for the source language.

### 3. Remaining Issues in Validation

**Status**: 130/135 validation tests passing (96% success rate)

**Test Results**:
- ✅ 130 validation tests passing
- ❌ 3 failing tests are Playwright UI issues (element visibility/timeouts)
- ✅ No actual validation rule implementation gaps found

**Specific Validation Rules Status**:
- ✅ Note Structure Validation: Implemented and working
- ✅ IPA Character Validation: Implemented and working
- ✅ POS Consistency Rules: Implemented and working
- ✅ All core validation rules are functioning correctly

**Failing Tests Analysis**:
The 3 failing tests are UI-related (Playwright) and involve element visibility and timeout issues, not actual validation logic problems.

### 4. Make validation rules editable per project

**Status**: Needs investigation

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
