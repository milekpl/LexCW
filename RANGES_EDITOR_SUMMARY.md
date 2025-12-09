# LIFT Ranges Editor - Executive Summary

**Date**: December 9, 2025  
**Priority**: HIGH  
**Estimated Effort**: 20 development days (4 weeks)

---

## What's Missing?

The LexCW application currently has a **critical gap**: there is no UI to manage LIFT ranges (controlled vocabularies like parts of speech, semantic domains, etc.). Ranges are loaded from BaseX but cannot be edited, and there's **no data integrity protection** when ranges change.

---

## Key Problems Solved

### 1. **No Range Management UI**
- **Current State**: Ranges must be edited manually in XML files outside the app
- **Solution**: Full-featured web UI with tree views, inline editing, and multilingual support

### 2. **No Data Integrity Protection**
- **Current State**: If you delete a grammatical-info value (e.g., "Noun") used in 1000 entries, those entries break
- **Solution**: Pre-deletion usage analysis + migration wizard (replace/remove values)

### 3. **No Hierarchy Support**
- **Current State**: Hierarchical ranges (e.g., Noun → Countable Noun) can only be viewed, not edited
- **Solution**: Drag-and-drop tree UI supporting both nested and parent-based hierarchies

---

## Core Features

### Range CRUD
- ✅ Create new ranges (e.g., custom field types)
- ✅ Edit range metadata (labels, descriptions)
- ✅ Delete ranges (with usage check)
- ✅ Multilingual support (labels in multiple languages)

### Range Element CRUD
- ✅ Create hierarchical elements
- ✅ Edit elements (labels, abbreviations, traits)
- ✅ Move elements in hierarchy
- ✅ Delete elements (with usage check + migration)

### Data Integrity
- ✅ **Usage Analysis**: Find all entries using a specific range value
- ✅ **Migration Wizard**: Bulk replace/remove values when deleting
- ✅ **Dry-Run Mode**: Preview changes before applying
- ✅ **Validation**: Prevent circular hierarchies, duplicate IDs

---

## Technical Architecture

### Backend
```
RangesService (Python)
  ├── Range CRUD methods
  ├── Element CRUD methods
  ├── Usage detection (XQuery)
  └── Migration operations (XQuery Update)

XQuery Operations Module
  ├── get-all-ranges()
  ├── create-range()
  ├── update-range()
  ├── delete-range()
  ├── find-range-usage()
  └── migrate-range-values()

REST API Blueprint
  └── /api/ranges-editor/* endpoints
```

### Frontend
```
Ranges Editor UI
  ├── ranges_editor.html (list view)
  ├── range_elements_editor.html (tree view)
  ├── range-editor.js (modals)
  ├── migration-wizard.js (migration UI)
  └── multilingual-editor.js (language forms)
```

### Database (BaseX)
```
XQuery queries directly manipulate:
  collection('{db_name}')//lift-ranges
    ├── range[@id='grammatical-info']
    │   └── range-element[@id='Noun']
    │       └── range-element[@id='Countable Noun']
    └── range[@id='semantic-domain-ddp4']
```

---

## Usage Scenarios

### Scenario 1: Delete Grammatical Info Value
**Problem**: User wants to delete "Noun" from grammatical-info, but it's used in 1,234 entries.

**Solution**:
1. User clicks delete on "Noun"
2. System shows usage analysis modal:
   - "⚠️ Used in 1,234 entries"
   - Sample entry list (first 100)
3. User selects migration option:
   - **Option A**: Cancel deletion
   - **Option B**: Remove value (set to null)
   - **Option C**: Replace with "Noun-Alt"
4. User enables dry-run → sees preview
5. User confirms → system bulk updates all 1,234 entries
6. Success: "Updated 1,234 entries, deleted range element"

### Scenario 2: Create Custom Range
**Problem**: User needs a custom range for publication status.

**Solution**:
1. User clicks "+ New Range"
2. Fills form:
   - ID: `publication-status`
   - Label (en): `Publication Status`
   - Description: `Editorial workflow stages`
3. Creates elements:
   - `draft` → "Draft"
   - `review` → "Under Review"
   - `published` → "Published"
4. Range is immediately available in dropdown menus throughout app

### Scenario 3: Reorganize Hierarchy
**Problem**: User wants to move "Countable Noun" under a new parent "Concrete Noun".

**Solution**:
1. User creates new element "Concrete Noun" under "Noun"
2. Drag "Countable Noun" from "Noun" to "Concrete Noun"
3. System validates (no circular reference)
4. Hierarchy updated:
   ```
   Noun
   ├── Concrete Noun
   │   └── Countable Noun  ← moved here
   └── Abstract Noun
   ```

---

## Data Integrity Implementation

### Usage Detection Query (Example)
```xquery
(: Find all entries using "Noun" as grammatical-info :)
for $entry in collection('{db_name}')//entry[
  .//grammatical-info[@value = 'Noun']
]
return map {
  'entry_id': $entry/@id/string(),
  'headword': $entry/lexical-unit/form[1]/text/string(),
  'contexts': array {
    for $gi in $entry//grammatical-info[@value = 'Noun']
    return map {
      'field': 'grammatical_info',
      'sense_id': $gi/ancestor::sense/@id/string()
    }
  }
}
```

### Migration Query (Replace)
```xquery
(: Replace "Noun" with "Noun-Alt" in all entries :)
for $gi in collection('{db_name}')//grammatical-info[@value = 'Noun']
return replace value of node $gi/@value with 'Noun-Alt'
```

---

## Implementation Phases

### Phase 1: Backend (Days 1-3) ✅
- RangesService class
- XQuery operations module
- 30 unit tests

### Phase 2: API (Days 4-5) ✅
- REST API endpoints
- Swagger docs
- 20 integration tests

### Phase 3: Migration (Days 6-8) ✅
- Usage detection
- Migration operations
- Dry-run mode
- 25 tests

### Phase 4-6: Frontend (Days 9-16) 🎨
- List view
- Tree view
- Edit modals
- Migration wizard

### Phase 7-8: Testing & Deploy (Days 17-20) 🚀
- E2E tests (15 tests)
- Performance testing
- UAT
- Production deployment

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Accidental data loss** | Pre-deletion usage analysis, confirmation dialogs, dry-run mode |
| **Performance issues** | XQuery indexing, pagination, lazy loading |
| **Circular hierarchies** | Validation algorithm, comprehensive tests |
| **XQuery failures** | Transactional updates, backup requirement |
| **Cache staleness** | Invalidate cache on every write operation |

---

## Success Metrics

**MVP (Must Have)**:
- ✅ Range CRUD (create, read, update, delete)
- ✅ Element CRUD with hierarchy
- ✅ Usage detection before deletion
- ✅ Basic migration (replace, remove)
- ✅ Multilingual editing

**Post-MVP**:
- Drag-and-drop tree
- Import/export ranges
- Audit trail
- Undo/redo

---

## Testing Coverage

| Test Type | Target | Actual |
|-----------|--------|--------|
| Unit Tests | 30 | TBD |
| Integration Tests | 30 | TBD |
| E2E Tests | 15 | TBD |
| **Total** | **75** | **TBD** |

---

## Key XQuery Operations

### Read Operations
```xquery
(: Get all ranges :)
collection('{db_name}')//lift-ranges

(: Get specific range :)
collection('{db_name}')//range[@id='grammatical-info']

(: Get usage count :)
count(collection('{db_name}')//entry[
  .//grammatical-info[@value='Noun']
])
```

### Write Operations
```xquery
(: Create range :)
insert node 
  <range id="new-range" guid="{$guid}">
    <label><form lang="en"><text>New Range</text></form></label>
  </range>
into collection('{db_name}')//lift-ranges

(: Update range :)
replace value of node 
  collection('{db_name}')//range[@id='test-range']/label/form[@lang='en']/text
with 'Updated Label'

(: Delete range :)
delete node collection('{db_name}')//range[@id='test-range']

(: Migrate values :)
for $gi in collection('{db_name}')//grammatical-info[@value='Noun']
return replace value of node $gi/@value with 'Noun-Alt'
```

---

## API Endpoints

### Ranges
- `GET /api/ranges-editor/` - List all ranges
- `POST /api/ranges-editor/` - Create range
- `GET /api/ranges-editor/{range_id}` - Get range details
- `PUT /api/ranges-editor/{range_id}` - Update range
- `DELETE /api/ranges-editor/{range_id}` - Delete range

### Range Elements
- `GET /api/ranges-editor/{range_id}/elements` - List elements (hierarchical)
- `POST /api/ranges-editor/{range_id}/elements` - Create element
- `PUT /api/ranges-editor/{range_id}/elements/{element_id}` - Update element
- `DELETE /api/ranges-editor/{range_id}/elements/{element_id}` - Delete element

### Data Integrity
- `GET /api/ranges-editor/{range_id}/usage` - Find usage
- `POST /api/ranges-editor/{range_id}/migrate` - Migrate values

---

## Files to Create

### Backend
1. `app/services/ranges_service.py` (~500 lines)
2. `app/xquery/ranges_operations.xq` (~400 lines)
3. `app/api/ranges_editor.py` (~300 lines)

### Frontend
4. `app/templates/ranges_editor.html` (~200 lines)
5. `app/templates/range_elements_editor.html` (~300 lines)
6. `app/static/js/range-editor.js` (~400 lines)
7. `app/static/js/range-element-editor.js` (~500 lines)
8. `app/static/js/migration-wizard.js` (~300 lines)
9. `app/static/css/ranges-editor.css` (~200 lines)

### Tests
10. `tests/unit/test_ranges_service.py` (~600 lines)
11. `tests/integration/test_ranges_crud_integration.py` (~800 lines)
12. `tests/integration/test_ranges_migration.py` (~500 lines)
13. `tests/e2e/test_ranges_editor_ui.py` (~400 lines)

### Docs
14. `docs/RANGES_EDITOR_USER_GUIDE.md`
15. `docs/RANGES_EDITOR_TECHNICAL.md`

**Total**: ~15 new files, ~6,000 lines of code

---

## Dependencies

**None** - All required components already exist:
- ✅ BaseXConnector (XQuery execution)
- ✅ LIFTRangesParser (XML parsing)
- ✅ DictionaryService (cache management)
- ✅ Flask app structure
- ✅ Bootstrap UI framework

---

## Deployment Checklist

- [ ] Run full test suite (75 tests)
- [ ] Backup production database
- [ ] Deploy to staging
- [ ] Run UAT with 3 lexicographers
- [ ] Performance test (1000+ ranges, 10,000+ elements)
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Create user training materials
- [ ] Deploy to production
- [ ] Monitor error logs for 1 week

---

## Questions for Stakeholders

1. **Permissions**: Should ranges editing be admin-only or role-based?
2. **Backup**: Should we auto-backup before destructive operations?
3. **Concurrency**: How to handle simultaneous edits by multiple users?
4. **Validation**: Should we validate against FieldWorks standard ranges?
5. **Undo**: Is undo/redo required for MVP or can it wait?

---

## Conclusion

The LIFT Ranges Editor is a **critical missing piece** in the LexCW application. Without it, users cannot manage controlled vocabularies, and there's no protection against data corruption when ranges change.

**This specification provides**:
- Complete functional requirements
- Detailed technical architecture
- XQuery-based persistence strategy
- Data integrity protection mechanisms
- Comprehensive testing strategy
- 20-day implementation roadmap

**Ready to proceed**: All dependencies exist, no blockers identified.

---

**For full details, see**: `LIFT_RANGES_EDITOR_SPECIFICATION.md` (100+ pages)
