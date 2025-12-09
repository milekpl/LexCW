# LIFT Ranges Editor - Architecture Diagrams

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ Ranges List View │  │ Tree View Editor │  │ Migration    │ │
│  │ - Table display  │  │ - Hierarchy tree │  │ Wizard       │ │
│  │ - Search/filter  │  │ - Drag-and-drop  │  │ - Usage scan │ │
│  │ - CRUD actions   │  │ - Inline edit    │  │ - Preview    │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
│          │                      │                      │        │
└──────────┼──────────────────────┼──────────────────────┼────────┘
           │                      │                      │
           └──────────────────────┴──────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                         REST API LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  /api/ranges-editor/                                           │
│    ├── GET    /                    (list all ranges)           │
│    ├── POST   /                    (create range)              │
│    ├── GET    /{range_id}          (get range)                 │
│    ├── PUT    /{range_id}          (update range)              │
│    ├── DELETE /{range_id}          (delete range)              │
│    │                                                            │
│    ├── GET    /{range_id}/elements (list elements)             │
│    ├── POST   /{range_id}/elements (create element)            │
│    ├── PUT    /{range_id}/elements/{element_id}                │
│    ├── DELETE /{range_id}/elements/{element_id}                │
│    │                                                            │
│    ├── GET    /{range_id}/usage    (find usage)                │
│    └── POST   /{range_id}/migrate  (migrate values)            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                       SERVICE LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               RangesService (Python)                     │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                                                          │  │
│  │  Range Management:                                       │  │
│  │   • get_all_ranges()                                     │  │
│  │   • create_range(range_data)                             │  │
│  │   • update_range(range_id, data)                         │  │
│  │   • delete_range(range_id, migration)                    │  │
│  │                                                          │  │
│  │  Element Management:                                     │  │
│  │   • get_range_elements(range_id)                         │  │
│  │   • create_range_element(range_id, data)                 │  │
│  │   • update_range_element(range_id, element_id, data)     │  │
│  │   • delete_range_element(range_id, element_id, migration)│  │
│  │                                                          │  │
│  │  Data Integrity:                                         │  │
│  │   • find_range_usage(range_id, element_id?)              │  │
│  │   • migrate_range_values(range_id, old, new, operation)  │  │
│  │                                                          │  │
│  │  Validation:                                             │  │
│  │   • validate_range_id(range_id)                          │  │
│  │   • validate_element_id(range_id, element_id)            │  │
│  │   • validate_parent_reference(range_id, elem, parent)    │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│                          │ Uses                                 │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          LIFTRangesParser (XML Parsing)                  │  │
│  │   • parse_string(xml) → Dict[str, Any]                   │  │
│  │   • _parse_range(range_elem)                             │  │
│  │   • _parse_range_element(elem)                           │  │
│  │   • _parse_nested_hierarchy(range_elem)                  │  │
│  │   • _parse_parent_based_hierarchy(range_elem)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     XQUERY OPERATIONS LAYER                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         ranges_operations.xq (XQuery Module)             │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                                                          │  │
│  │  Read Operations:                                        │  │
│  │   • local:get-all-ranges($db-name)                       │  │
│  │   • local:get-range($db-name, $range-id)                 │  │
│  │                                                          │  │
│  │  Write Operations:                                       │  │
│  │   • local:create-range($db, $id, $guid, $labels, ...)    │  │
│  │   • local:update-range($db, $id, $labels, ...)           │  │
│  │   • local:delete-range($db, $id)                         │  │
│  │                                                          │  │
│  │  Element Operations:                                     │  │
│  │   • local:create-range-element($db, $range, $id, ...)    │  │
│  │   • local:update-range-element($db, $range, $id, ...)    │  │
│  │   • local:delete-range-element($db, $range, $id)         │  │
│  │                                                          │  │
│  │  Data Integrity:                                         │  │
│  │   • local:find-range-usage($db, $range, $element?)       │  │
│  │   • local:migrate-range-values-replace($db, ...)         │  │
│  │   • local:migrate-range-values-remove($db, ...)          │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BASEX DATABASE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Database: {db_name}                                           │
│  ├── sample-lift-file.lift                                     │
│  ├── sample-lift-file.lift-ranges ◀── RANGES DOCUMENT         │
│  │    └── <lift-ranges>                                        │
│  │         ├── <range id="grammatical-info">                   │
│  │         │    ├── <range-element id="Noun">                  │
│  │         │    │    ├── <range-element id="Countable Noun"/>  │
│  │         │    │    └── <range-element id="Uncountable Noun"/>│
│  │         │    ├── <range-element id="Verb">                  │
│  │         │    └── ...                                         │
│  │         ├── <range id="semantic-domain-ddp4">               │
│  │         ├── <range id="domain-type">                        │
│  │         └── ...                                              │
│  └── entry_*.xml (entry documents)                             │
│                                                                 │
│  XQuery Access:                                                │
│   collection('{db_name}')//lift-ranges                         │
│   collection('{db_name}')//range[@id='grammatical-info']       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Create Range Element

```
User Action: "Create new element 'Proper Noun' under 'Noun'"
│
├─ Frontend (range-element-editor.js)
│   └─ POST /api/ranges-editor/grammatical-info/elements
│      {
│        "id": "Proper Noun",
│        "parent": "Noun",
│        "labels": {"en": "Proper Noun"},
│        "abbrevs": {"en": "prop.n"}
│      }
│
├─ API Layer (ranges_editor.py)
│   └─ create_element(range_id='grammatical-info')
│       ├─ Validate element ID uniqueness
│       ├─ Validate parent exists
│       └─ Call RangesService.create_range_element()
│
├─ Service Layer (RangesService)
│   └─ create_range_element(range_id, element_data)
│       ├─ Generate GUID
│       ├─ Build XML structure
│       └─ Execute XQuery: local:create-range-element(...)
│
├─ XQuery Layer (ranges_operations.xq)
│   └─ local:create-range-element($db, 'grammatical-info', 'Proper Noun', ...)
│       ├─ Find parent: //range[@id='grammatical-info']//range-element[@id='Noun']
│       ├─ Build new element:
│       │    <range-element id="Proper Noun" guid="{$guid}" parent="Noun">
│       │      <label><form lang="en"><text>Proper Noun</text></form></label>
│       │      <abbrev><form lang="en"><text>prop.n</text></form></abbrev>
│       │    </range-element>
│       └─ insert node $new-element into $parent
│
└─ BaseX Database
    └─ XML updated:
        <range id="grammatical-info">
          <range-element id="Noun">
            <range-element id="Proper Noun" guid="..."> ◀── NEW ELEMENT
              <label><form lang="en"><text>Proper Noun</text></form></label>
              <abbrev><form lang="en"><text>prop.n</text></form></abbrev>
            </range-element>
          </range-element>
        </range>

Result: Frontend receives success response, tree view updates
```

---

## Data Flow: Delete Element with Migration

```
User Action: "Delete 'Noun' element (used in 1,234 entries)"
│
├─ Frontend (migration-wizard.js)
│   ├─ Step 1: Check usage
│   │   GET /api/ranges-editor/grammatical-info/usage?element_id=Noun
│   │   Response: { "count": 1234, "sample_entries": [...] }
│   │
│   ├─ Step 2: Show modal
│   │   ⚠️ "Used in 1,234 entries"
│   │   Options:
│   │     ( ) Cancel
│   │     ( ) Remove value
│   │     (•) Replace with: [Noun-Alt]
│   │
│   └─ Step 3: Execute migration
│       DELETE /api/ranges-editor/grammatical-info/elements/Noun
│       {
│         "migration": {
│           "operation": "replace",
│           "new_value": "Noun-Alt"
│         }
│       }
│
├─ API Layer (ranges_editor.py)
│   └─ delete_element(range_id='grammatical-info', element_id='Noun')
│       ├─ Validate migration data
│       └─ Call RangesService.delete_range_element(migration)
│
├─ Service Layer (RangesService)
│   └─ delete_range_element(range_id, element_id, migration)
│       ├─ Step 1: Migrate values
│       │   migrate_range_values('grammatical-info', 'Noun', 'replace', 'Noun-Alt')
│       │
│       └─ Step 2: Delete element
│           Execute XQuery: local:delete-range-element(...)
│
├─ XQuery Layer - Migration
│   └─ local:migrate-range-values-replace($db, 'grammatical-info', 'Noun', 'Noun-Alt')
│       ├─ Find all grammatical-info elements with value='Noun'
│       │   for $gi in collection($db)//grammatical-info[@value='Noun']
│       │
│       └─ Replace values
│           replace value of node $gi/@value with 'Noun-Alt'
│
├─ BaseX Database - Entry Updates
│   └─ BEFORE:
│       <entry id="cat_001">
│         <sense>
│           <grammatical-info value="Noun"/> ◀── OLD VALUE
│         </sense>
│       </entry>
│
│   └─ AFTER:
│       <entry id="cat_001">
│         <sense>
│           <grammatical-info value="Noun-Alt"/> ◀── NEW VALUE
│         </sense>
│       </entry>
│
├─ XQuery Layer - Element Deletion
│   └─ local:delete-range-element($db, 'grammatical-info', 'Noun')
│       delete node collection($db)//range[@id='grammatical-info']//range-element[@id='Noun']
│
└─ BaseX Database - Ranges Update
    └─ BEFORE:
        <range id="grammatical-info">
          <range-element id="Noun"> ◀── DELETED
            ...
          </range-element>
          <range-element id="Noun-Alt">
            ...
          </range-element>
        </range>

    └─ AFTER:
        <range id="grammatical-info">
          <range-element id="Noun-Alt">
            ...
          </range-element>
        </range>

Result: 
  - 1,234 entries updated (Noun → Noun-Alt)
  - Element 'Noun' deleted from ranges
  - Frontend shows success message
```

---

## Component Interaction: Usage Detection

```
┌────────────────────────────────────────────────────────────────┐
│ USAGE DETECTION WORKFLOW                                       │
└────────────────────────────────────────────────────────────────┘

Frontend                API Layer           Service Layer        XQuery Layer         BaseX
   │                       │                     │                    │                 │
   │ GET usage?element=Noun│                     │                    │                 │
   ├──────────────────────►│                     │                    │                 │
   │                       │ find_range_usage()  │                    │                 │
   │                       ├────────────────────►│                    │                 │
   │                       │                     │ Build XQuery       │                 │
   │                       │                     │ based on range type│                 │
   │                       │                     ├───────────────────►│                 │
   │                       │                     │                    │ Search entries  │
   │                       │                     │                    ├────────────────►│
   │                       │                     │                    │                 │
   │                       │                     │                    │ Query:          │
   │                       │                     │                    │ //entry[        │
   │                       │                     │                    │   .//grammatical│
   │                       │                     │                    │   -info[        │
   │                       │                     │                    │   @value='Noun']│
   │                       │                     │                    │ ]               │
   │                       │                     │                    │                 │
   │                       │                     │                    │ Results (JSON)  │
   │                       │                     │                    │◄────────────────┤
   │                       │                     │ Parse JSON results │                 │
   │                       │                     │◄───────────────────┤                 │
   │                       │ Return usage data   │                    │                 │
   │                       │◄────────────────────┤                    │                 │
   │ JSON response         │                     │                    │                 │
   │◄──────────────────────┤                     │                    │                 │
   │                       │                     │                    │                 │
   │ Display modal:        │                     │                    │                 │
   │ ┌──────────────────┐  │                     │                    │                 │
   │ │ ⚠️ Used in 1,234 │  │                     │                    │                 │
   │ │   entries        │  │                     │                    │                 │
   │ │                  │  │                     │                    │                 │
   │ │ Sample:          │  │                     │                    │                 │
   │ │ • cat (entry_001)│  │                     │                    │                 │
   │ │ • dog (entry_042)│  │                     │                    │                 │
   │ │ • ...            │  │                     │                    │                 │
   │ └──────────────────┘  │                     │                    │                 │
   │                       │                     │                    │                 │
```

---

## Hierarchical Range Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ LIFT Ranges Hierarchical Structure                             │
└─────────────────────────────────────────────────────────────────┘

TWO HIERARCHY PATTERNS SUPPORTED:

1. NESTED HIERARCHY (Direct Children):
   
   <range id="grammatical-info">
     <range-element id="Noun">
       <label>...</label>
       <range-element id="Common Noun">          ◀── NESTED
         <label>...</label>
       </range-element>
       <range-element id="Proper Noun">          ◀── NESTED
         <label>...</label>
       </range-element>
     </range-element>
   </range>

   Tree Representation:
   ├─ Noun
   │  ├─ Common Noun
   │  └─ Proper Noun
   └─ Verb
      ├─ Transitive Verb
      └─ Intransitive Verb


2. PARENT-BASED HIERARCHY (Flat with parent attribute):

   <range id="semantic-domain">
     <range-element id="1" guid="...">
       <label>...</label>
     </range-element>
     <range-element id="1.1" guid="..." parent="1">    ◀── PARENT ATTR
       <label>...</label>
     </range-element>
     <range-element id="1.1.1" guid="..." parent="1.1"> ◀── PARENT ATTR
       <label>...</label>
     </range-element>
   </range>

   Tree Representation:
   ├─ 1 (Universe)
   │  ├─ 1.1 (Sky)
   │  │  └─ 1.1.1 (Sun)
   │  └─ 1.2 (Earth)
   └─ 2 (Person)
      └─ 2.1 (Body)

AUTOMATIC DETECTION:
  LIFTRangesParser._parse_range() checks:
    if any(elem.get('parent') for elem in range_elements):
        return _parse_parent_based_hierarchy()
    else:
        return _parse_nested_hierarchy()
```

---

## Validation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ VALIDATION WORKFLOW                                             │
└─────────────────────────────────────────────────────────────────┘

User Input: Create element "Proper Noun" with parent="Noun"
│
├─ FRONTEND VALIDATION
│   ├─ Check: ID not empty
│   ├─ Check: Label not empty
│   └─ Check: Parent exists in tree
│
├─ API VALIDATION
│   ├─ validate_element_id(range_id='grammatical-info', element_id='Proper Noun')
│   │   Query: collection($db)//range[@id='grammatical-info']//range-element[@id='Proper Noun']
│   │   Result: Not found ✓
│   │
│   ├─ validate_parent_reference(range_id, element_id, parent_id='Noun')
│   │   Algorithm:
│   │     1. Check parent exists
│   │     2. Build parent chain: Noun → (no parent) → ROOT
│   │     3. Check if 'Proper Noun' appears in chain
│   │     4. Result: No circular reference ✓
│   │
│   └─ Validation passed ✓
│
└─ PROCEED TO CREATE

CIRCULAR REFERENCE PREVENTION:

  Scenario: User tries to set parent of "Noun" to "Proper Noun"
  
  Parent Chain for "Proper Noun":
    Proper Noun → Noun → (root)
    
  If we set parent of "Noun" to "Proper Noun":
    Noun → Proper Noun → Noun → Proper Noun → ...  ❌ CIRCULAR!
    
  Algorithm detects cycle:
    visited = {'Proper Noun'}
    current = parent of 'Proper Noun' = 'Noun'  ← ALREADY IN VISITED!
    
  Validation fails: "Cannot set parent: would create circular reference"
```

---

## Cache Management

```
┌─────────────────────────────────────────────────────────────────┐
│ CACHE INVALIDATION STRATEGY                                     │
└─────────────────────────────────────────────────────────────────┘

DictionaryService.ranges (in-memory cache)
│
├─ CACHE HITS (Read Operations)
│   └─ get_ranges()
│       if self.ranges:
│           return self.ranges  ◀── FAST PATH
│       else:
│           query BaseX
│           self.ranges = result
│           return result
│
└─ CACHE INVALIDATION (Write Operations)
    └─ Any RangesService write operation
        ├─ create_range()      → invalidate_ranges_cache()
        ├─ update_range()      → invalidate_ranges_cache()
        ├─ delete_range()      → invalidate_ranges_cache()
        ├─ create_element()    → invalidate_ranges_cache()
        ├─ update_element()    → invalidate_ranges_cache()
        └─ delete_element()    → invalidate_ranges_cache()

invalidate_ranges_cache():
    dict_service.ranges = {}  ◀── CLEAR CACHE
    
Next read will re-query BaseX for fresh data.

ALTERNATIVE: Event-driven cache invalidation
    
    @cache_invalidator
    def update_range(self, range_id, data):
        # ... perform update ...
        self.trigger_cache_clear()

Or use Flask-Caching with TTL:
    
    @cache.cached(timeout=3600, key_prefix='lift_ranges')
    def get_ranges(self):
        # ... query BaseX ...
    
    @cache.delete('lift_ranges')
    def update_range(self, ...):
        # ... perform update ...
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ ERROR HANDLING CHAIN                                            │
└─────────────────────────────────────────────────────────────────┘

User Action → API Call → Service → XQuery → BaseX
     ↓           ↓         ↓         ↓         ↓
   ERROR      ERROR     ERROR     ERROR     ERROR
     ↓           ↓         ↓         ↓         ↓
 Validation  HTTP 400  Business  XQuery    DB
   Error      Error    Logic     Error   Error
     │           │        │         │        │
     └───────────┴────────┴─────────┴────────┘
                      ↓
              Centralized Error Handler
                      ↓
         ┌────────────┴────────────┐
         │                         │
    Log Error                 Format Response
         │                         │
         │                    ┌────┴────┐
         │                    │         │
         │               User-friendly  Technical
         │                 message      details
         │                    │         │
         └────────────────────┴─────────┘
                      ↓
              JSON Response to Frontend
                      ↓
         Frontend Error Display
         ┌────────────────────────┐
         │ ⚠️ Error               │
         │                        │
         │ Unable to delete range │
         │                        │
         │ Reason: Range is in use│
         │ in 1,234 entries       │
         │                        │
         │ [View Details] [Close] │
         └────────────────────────┘

ERROR TYPES:

1. Validation Errors (HTTP 400)
   - Duplicate ID
   - Missing required fields
   - Circular hierarchy
   - Invalid parent reference

2. Business Logic Errors (HTTP 409)
   - Range in use (cannot delete)
   - Element has children (cannot delete)
   - Migration required

3. Database Errors (HTTP 500)
   - XQuery execution failed
   - BaseX connection error
   - Transaction rollback

4. Not Found Errors (HTTP 404)
   - Range ID not found
   - Element ID not found
```

---

This architecture ensures:
- ✅ **Data integrity** through usage analysis
- ✅ **Performance** via caching and XQuery optimization
- ✅ **Reliability** through comprehensive error handling
- ✅ **Maintainability** through clear separation of concerns
- ✅ **LIFT compliance** through proper XML manipulation
