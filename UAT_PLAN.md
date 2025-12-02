# User Acceptance Testing Plan - XML Direct Manipulation

**Version**: 1.0  
**Date**: December 1, 2025  
**Phase**: Week 3 - Day 19-21  
**Status**: Ready for Testing

---

## Executive Summary

This document outlines the User Acceptance Testing (UAT) plan for the XML Direct Manipulation implementation. UAT validates that all features work correctly from an end-user perspective and that the system is ready for production deployment.

**Testing Period**: Days 19-21 (3 days)  
**Test Environment**: Staging/Development  
**Database**: `dictionary` (397 entries)  
**Testers**: Development team + stakeholders

---

## Objectives

### Primary Objectives
1. Validate all XML Direct Manipulation features work correctly
2. Ensure UX is equivalent to previous implementation
3. Verify data integrity and accuracy
4. Confirm performance meets user expectations
5. Identify any critical bugs before production

### Success Criteria
- ✅ All critical features functional
- ✅ No data loss or corruption
- ✅ Performance acceptable (<1 second per operation)
- ✅ No critical bugs (P0/P1)
- ✅ User feedback positive

---

## Test Scenarios

### Scenario 1: Entry Creation

**Feature**: Create new dictionary entry via XML serialization

**Test Steps**:
1. Navigate to entry creation form (`/entries/new`)
2. Fill in required fields:
   - Lexical unit: "test entry"
   - Part of speech: "Noun"
   - Gloss (Polish): "wpis testowy"
3. Add optional fields:
   - Definition
   - Example sentence
   - Translation
4. Click "Save Entry"

**Expected Results**:
- ✅ Entry saves successfully
- ✅ Success message displayed
- ✅ Redirected to entry detail page
- ✅ Entry appears in search results
- ✅ XML stored correctly in BaseX
- ✅ All fields preserved accurately

**Test Data**:
```
Lexical Unit: acceptance testing
POS: Noun
Gloss (PL): testowanie akceptacyjne
Definition: Validation performed to determine if requirements are met
Example: Acceptance testing ensures the system meets user needs.
Translation: Testowanie akceptacyjne zapewnia, że system spełnia potrzeby użytkowników.
```

---

### Scenario 2: Entry Editing

**Feature**: Edit existing entry via XML update

**Test Steps**:
1. Search for existing entry
2. Click "Edit" button
3. Modify fields:
   - Update gloss
   - Add new sense
   - Modify example
4. Click "Save Changes"

**Expected Results**:
- ✅ Changes saved successfully
- ✅ Original data preserved
- ✅ New data appears correctly
- ✅ Version history maintained
- ✅ dateModified updated
- ✅ No data loss

**Test Data**:
- Entry: "test" (existing entry)
- Action: Add second sense
- New POS: Verb
- New Gloss: "testować"

---

### Scenario 3: Multi-Sense Entry

**Feature**: Create entry with multiple senses

**Test Steps**:
1. Create new entry with lexical unit "run"
2. Add first sense:
   - POS: Verb
   - Gloss: "biec"
   - Definition: "to move rapidly on foot"
3. Click "Add Sense"
4. Add second sense:
   - POS: Noun
   - Gloss: "bieg"
   - Definition: "an act of running"
5. Save entry

**Expected Results**:
- ✅ Both senses saved
- ✅ Sense order preserved (order="0", order="1")
- ✅ Each sense has unique ID
- ✅ Both senses appear in UI
- ✅ XML structure correct

---

### Scenario 4: Complex Entry with Relations

**Feature**: Create entry with etymological relations

**Test Steps**:
1. Create entry "etymology"
2. Add sense with definition
3. Add etymological note
4. Add related entry (relation type: "etymology")
5. Save entry

**Expected Results**:
- ✅ Relation saved correctly
- ✅ Relation type preserved
- ✅ Target entry linked
- ✅ Bidirectional relation (if applicable)
- ✅ XML structure validates

---

### Scenario 5: Entry Search

**Feature**: Search entries using various patterns

**Test Steps**:
1. Search for "test" (exact match)
2. Search for "test*" (wildcard)
3. Search for "contest" (substring)
4. Search with filters (POS, language)

**Expected Results**:
- ✅ Relevant results returned
- ✅ Results sorted correctly
- ✅ Performance <150ms (per benchmark)
- ✅ Pagination works
- ✅ Filters apply correctly

---

### Scenario 6: Entry Deletion

**Feature**: Delete entry from database

**Test Steps**:
1. Navigate to entry detail page
2. Click "Delete Entry"
3. Confirm deletion in modal
4. Verify entry removed

**Expected Results**:
- ✅ Entry deleted from BaseX
- ✅ Entry not in search results
- ✅ Related entries unaffected
- ✅ Confirmation message shown
- ✅ Redirected to entry list

---

### Scenario 7: XML Validation

**Feature**: Validate entry against LIFT schema

**Test Steps**:
1. Create entry with missing required field
2. Attempt to save
3. Observe validation errors

**Expected Results**:
- ✅ Validation prevents save
- ✅ Error messages clear
- ✅ Field highlighted in UI
- ✅ No corrupt data saved
- ✅ User can correct and retry

**Test Data**:
- Missing lexical unit
- Empty sense ID
- Invalid POS value
- Malformed XML

---

### Scenario 8: Unicode and Special Characters

**Feature**: Handle international characters correctly

**Test Steps**:
1. Create entry with Unicode:
   - Lexical unit: "café"
   - Polish: "kawiarnia"
   - Example: "Pójdźmy do kawiarni"
2. Save and retrieve entry

**Expected Results**:
- ✅ Unicode preserved
- ✅ Special characters display correctly
- ✅ Search works with Unicode
- ✅ No encoding issues
- ✅ XML encoding correct

---

### Scenario 9: Large Entry Performance

**Feature**: Handle complex entries efficiently

**Test Steps**:
1. Create entry with:
   - 5 senses
   - 10 examples
   - Multiple relations
   - Lengthy definitions
2. Save entry
3. Measure save time

**Expected Results**:
- ✅ Save completes in <250ms
- ✅ All data preserved
- ✅ No timeout errors
- ✅ UI responsive
- ✅ Entry retrievable quickly

---

### Scenario 10: Concurrent Editing

**Feature**: Handle simultaneous edits gracefully

**Test Steps**:
1. Open same entry in two browser tabs
2. Edit in tab 1, save
3. Edit in tab 2, save

**Expected Results**:
- ✅ Last save wins (or conflict detection)
- ✅ No data corruption
- ✅ dateModified reflects last edit
- ✅ No crashes or errors

---

## UAT Checklist

### Pre-Testing Setup

- [ ] BaseX server running and accessible
- [ ] Test database initialized with 397 entries
- [ ] All automated tests passing (116+ tests)
- [ ] Development environment clean
- [ ] Test data prepared
- [ ] Backup created

### Core Functionality

#### Entry Management
- [ ] Create new entry
- [ ] Edit existing entry
- [ ] Delete entry
- [ ] View entry details
- [ ] List all entries

#### Senses
- [ ] Add sense to entry
- [ ] Edit sense
- [ ] Delete sense
- [ ] Reorder senses
- [ ] Multi-sense entries

#### Search
- [ ] Basic search
- [ ] Wildcard search
- [ ] Filter by POS
- [ ] Filter by language
- [ ] Pagination

#### Data Quality
- [ ] Validation on save
- [ ] Required field checks
- [ ] Format validation
- [ ] Unicode support
- [ ] Special characters

### XML Features

#### XML Serialization
- [ ] Form generates valid LIFT XML
- [ ] All fields serialized
- [ ] Namespaces correct
- [ ] Structure validates against schema

#### XML Storage
- [ ] Entries stored in BaseX
- [ ] XML retrieved correctly
- [ ] Updates preserve structure
- [ ] Deletes remove files

#### XML Validation
- [ ] POST /api/validation/xml works
- [ ] Validation rules enforced
- [ ] Error messages clear
- [ ] Invalid XML rejected

### Performance

- [ ] Entry load <200ms
- [ ] Entry save <250ms
- [ ] Search <150ms
- [ ] UI responsive
- [ ] No timeout errors

### Data Integrity

- [ ] No data loss
- [ ] No corruption
- [ ] Dates preserved
- [ ] GUIDs preserved
- [ ] Relations intact

### User Experience

- [ ] Form intuitive
- [ ] Error messages helpful
- [ ] Success feedback clear
- [ ] Navigation smooth
- [ ] No confusing behavior

### Edge Cases

- [ ] Empty fields handled
- [ ] Very long text
- [ ] Special characters
- [ ] Duplicate IDs prevented
- [ ] Network errors handled

---

## Test Environment

### Configuration

**Server**:
- BaseX: localhost:1984
- Flask app: localhost:5000
- Database: `dictionary`
- Entries: 397

**Browser Support**:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

**Test Accounts**:
- Admin: admin/admin
- Editor: (if applicable)

---

## Bug Reporting

### Bug Report Template

```markdown
**Bug ID**: UAT-XXX
**Severity**: P0 (Critical) / P1 (High) / P2 (Medium) / P3 (Low)
**Status**: Open / In Progress / Fixed / Won't Fix

**Summary**: Brief description

**Steps to Reproduce**:
1. Step 1
2. Step 2
3. Step 3

**Expected Result**: What should happen

**Actual Result**: What actually happens

**Screenshots**: [Attach if applicable]

**Environment**:
- Browser: Chrome 120
- OS: Windows 11
- Date: 2025-12-01

**Priority**: How urgent is the fix?
**Workaround**: Any temporary solution?
```

### Severity Definitions

**P0 - Critical**:
- System unusable
- Data loss/corruption
- Security vulnerability
- **Action**: Fix immediately

**P1 - High**:
- Major feature broken
- Workaround exists
- Significant UX impact
- **Action**: Fix before production

**P2 - Medium**:
- Minor feature issue
- Cosmetic problem
- Low frequency
- **Action**: Fix in next sprint

**P3 - Low**:
- Nice-to-have
- Documentation
- Future enhancement
- **Action**: Backlog

---

## Test Results Documentation

### Test Execution Log

| Test ID | Scenario | Tester | Date | Result | Notes |
|---------|----------|--------|------|--------|-------|
| UAT-001 | Entry Creation | | | ⏳ Pending | |
| UAT-002 | Entry Editing | | | ⏳ Pending | |
| UAT-003 | Multi-Sense | | | ⏳ Pending | |
| UAT-004 | Relations | | | ⏳ Pending | |
| UAT-005 | Search | | | ⏳ Pending | |
| UAT-006 | Deletion | | | ⏳ Pending | |
| UAT-007 | Validation | | | ⏳ Pending | |
| UAT-008 | Unicode | | | ⏳ Pending | |
| UAT-009 | Performance | | | ⏳ Pending | |
| UAT-010 | Concurrent | | | ⏳ Pending | |

### Bug Summary

| Severity | Open | In Progress | Fixed | Total |
|----------|------|-------------|-------|-------|
| P0 (Critical) | 0 | 0 | 0 | 0 |
| P1 (High) | 0 | 0 | 0 | 0 |
| P2 (Medium) | 0 | 0 | 0 | 0 |
| P3 (Low) | 0 | 0 | 0 | 0 |

---

## Acceptance Criteria

### Go/No-Go Criteria

**GO Criteria** (Must meet ALL):
- ✅ All P0 bugs fixed
- ✅ All P1 bugs fixed or have workarounds
- ✅ No data loss/corruption
- ✅ Performance meets targets
- ✅ All critical test scenarios pass
- ✅ Automated tests passing (100%)
- ✅ User feedback positive

**NO-GO Criteria** (Any triggers delay):
- ❌ Any P0 bugs open
- ❌ Data corruption detected
- ❌ Performance regression >30%
- ❌ Critical feature broken
- ❌ User feedback negative

---

## Timeline

### Day 19: Setup & Core Testing
- Morning: Environment setup, pre-testing checks
- Afternoon: Test Scenarios 1-5 (entry CRUD, search)
- Evening: Document findings

### Day 20: Advanced Testing
- Morning: Test Scenarios 6-8 (deletion, validation, Unicode)
- Afternoon: Test Scenarios 9-10 (performance, concurrency)
- Evening: Bug fixes, retesting

### Day 21: Validation & Sign-off
- Morning: Retest fixed bugs
- Afternoon: Final validation, UAT report
- Evening: Go/No-Go decision

---

## Post-UAT Actions

### If GO
1. Create production deployment plan
2. Schedule cutover window
3. Prepare rollback procedure
4. Notify stakeholders
5. Proceed to Week 4

### If NO-GO
1. Document blocking issues
2. Create fix plan with timeline
3. Reschedule UAT
4. Communicate delays
5. Reassess Week 4 timeline

---

## Appendix

### Test Data Sets

**Simple Entry**:
```xml
<entry id="simple_001">
  <lexical-unit>
    <form lang="en"><text>simple test</text></form>
  </lexical-unit>
  <sense id="sense_001" order="0">
    <grammatical-info value="Noun"/>
    <gloss lang="pl"><text>prosty test</text></gloss>
  </sense>
</entry>
```

**Complex Entry**:
```xml
<entry id="complex_001">
  <lexical-unit>
    <form lang="en"><text>comprehensive test</text></form>
  </lexical-unit>
  <sense id="sense_001" order="0">
    <grammatical-info value="Noun"/>
    <gloss lang="pl"><text>test kompleksowy</text></gloss>
    <definition>
      <form lang="en"><text>A thorough test covering many aspects</text></form>
    </definition>
    <example>
      <form lang="en"><text>This is a comprehensive test.</text></form>
      <translation>
        <form lang="pl"><text>To jest test kompleksowy.</text></form>
      </translation>
    </example>
  </sense>
  <sense id="sense_002" order="1">
    <grammatical-info value="Adjective"/>
    <gloss lang="pl"><text>kompleksowy</text></gloss>
  </sense>
  <relation type="synonym" ref="thorough_test"/>
</entry>
```

### Resources

- **LIFT Schema**: `schemas/lift-0.13.rng`
- **API Docs**: `API_DOCUMENTATION.md`
- **Test Scripts**: `tests/integration/`
- **Benchmark Tool**: `scripts/benchmark_xml_performance.py`

---

**Document Owner**: Development Team  
**Last Updated**: December 1, 2025  
**Version**: 1.0
