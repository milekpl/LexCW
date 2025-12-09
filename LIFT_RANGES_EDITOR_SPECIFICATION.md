# LIFT Ranges Editor - Detailed Specification

**Version**: 1.0  
**Date**: December 9, 2025  
**Status**: Design Phase  
**Related**: LIFT_COMPLETE_IMPLEMENTATION_PLAN.md

---

## 1. Executive Summary

### 1.1 Purpose

The LIFT Ranges Editor is a missing critical component in the LexCW application that enables lexicographers to manage controlled vocabularies (ranges) used throughout the dictionary. Currently, ranges are loaded from the `.lift-ranges` XML file in BaseX, but there is no UI to **create, edit, or delete** range elements, nor is there any data integrity protection when ranges are modified.

### 1.2 Key Requirements

1. **Full CRUD operations** for LIFT ranges stored in BaseX
2. **Hierarchical editing** support (parent-child range elements)
3. **Multilingual label/description** editing
4. **Data integrity protection**: Prevent deletion of ranges in use, or offer migration paths
5. **XQuery-based persistence** to BaseX database
6. **Real-time validation** and conflict detection
7. **Audit trail** for range modifications

### 1.3 Scope

**In Scope**:
- Range CRUD operations (create, read, update, delete)
- Range element CRUD operations (hierarchical)
- Multilingual content editing (labels, descriptions, abbreviations)
- Usage analysis (find entries using specific range values)
- Data migration wizard (when deleting/modifying ranges in use)
- BaseX XQuery operations for persistence

**Out of Scope**:
- Bulk import/export of ranges (use existing LIFT file import)
- Range merging/splitting (manual process)
- Historical versioning beyond audit trail
- Custom range validation rules (beyond LIFT spec)

---

## 2. LIFT Ranges Structure Analysis

### 2.1 LIFT 0.13 Ranges XML Format

```xml
<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
  <range id="grammatical-info" guid="12345-abcdef">
    <label>
      <form lang="en"><text>Grammatical Information</text></form>
    </label>
    <description>
      <form lang="en"><text>Parts of speech and grammatical categories</text></form>
    </description>
    
    <!-- Flat range elements (no hierarchy) -->
    <range-element id="Adverb" guid="46e4fe08-ffa0-4c8b-bf98-2c56f38904d9">
      <label>
        <form lang="en"><text>Adverb</text></form>
      </label>
      <abbrev>
        <form lang="en"><text>adv</text></form>
      </abbrev>
      <description>
        <form lang="en"><text>An adverb modifies verbs...</text></form>
      </description>
      <trait name="catalog-source-id" value="Adverb"/>
    </range-element>
    
    <!-- Nested hierarchy (using nested elements) -->
    <range-element id="Noun" guid="a8e41fd3-e343-4c7c-aa05-01ea3dd5cfb5">
      <label>
        <form lang="en"><text>Noun</text></form>
      </label>
      <abbrev>
        <form lang="en"><text>n</text></form>
      </abbrev>
      
      <range-element id="Countable Noun" guid="b4c74c31-58fc-4feb-86bf-c2235bda8d3c">
        <label>
          <form lang="en"><text>Countable Noun</text></form>
        </label>
        <abbrev>
          <form lang="en"><text>n [C]</text></form>
        </abbrev>
      </range-element>
      
      <range-element id="Uncountable Noun" guid="e03b7635-ab0d-444e-895b-f9648a6774cc">
        <label>
          <form lang="en"><text>Uncountable Noun</text></form>
        </label>
        <abbrev>
          <form lang="en"><text>n [U]</text></form>
        </abbrev>
      </range-element>
    </range-element>
    
    <!-- Parent-based hierarchy (flat structure with parent attribute) -->
    <range-element id="Verb" guid="12345678">
      <label>
        <form lang="en"><text>Verb</text></form>
      </label>
    </range-element>
    <range-element id="Transitive Verb" guid="87654321" parent="Verb">
      <label>
        <form lang="en"><text>Transitive Verb</text></form>
      </label>
    </range-element>
  </range>
  
  <range id="semantic-domain-ddp4" guid="abcdef-12345">
    <label>
      <form lang="en"><text>Semantic Domains</text></form>
    </label>
    <!-- Hierarchical semantic domain structure -->
  </range>
</lift-ranges>
```

### 2.2 Range Types in LexCW

Based on codebase analysis, the following range types are used:

| Range ID | Description | Hierarchy | Usage Context |
|----------|-------------|-----------|---------------|
| `grammatical-info` | Parts of speech | Yes (nested + parent) | Entry, Sense, Variant, Reversal |
| `semantic-domain-ddp4` | Semantic domains | Yes (nested) | Sense |
| `domain-type` | Academic domains | No | Sense |
| `usage-type` | Usage types | No | Sense |
| `lexical-relation` | Relation types | No | Entry, Sense relations |
| `etymology` | Etymology types | No | Entry etymology |
| `note-type` | Note types | No | Entry notes |
| `variant-type` | Variant types | Yes (extracted from traits) | Entry variants |
| `Publications` | Publication lists | No | Trait metadata |

### 2.3 Hierarchical Structure Patterns

The codebase (`LIFTRangesParser`) supports two hierarchy patterns:

1. **Nested Hierarchy**: Range elements contain child elements directly
   ```xml
   <range-element id="Noun">
     <range-element id="Countable Noun"/>
     <range-element id="Uncountable Noun"/>
   </range-element>
   ```

2. **Parent-Based Hierarchy**: Flat structure with `parent` attribute
   ```xml
   <range-element id="Noun"/>
   <range-element id="Countable Noun" parent="Noun"/>
   <range-element id="Uncountable Noun" parent="Noun"/>
   ```

**Design Decision**: The editor should support **both patterns** for maximum compatibility, with automatic detection via `LIFTRangesParser._parse_range()`.

---

## 3. Functional Requirements

### 3.1 Range-Level Operations

#### FR-1: List All Ranges
- **Description**: Display all ranges from the LIFT ranges document
- **UI**: Table view with columns: ID, Label (default lang), Description, # Elements
- **API**: `GET /api/ranges`
- **XQuery**: 
  ```xquery
  for $range in collection('{db_name}')//range
  return $range
  ```

#### FR-2: Create New Range
- **Description**: Create a new empty range
- **Required Fields**:
  - `id` (unique, validated)
  - `label` (multilingual, at least one language)
  - `description` (optional, multilingual)
  - `guid` (auto-generated UUID)
- **UI**: Modal form with multilingual text editors
- **API**: `POST /api/ranges`
- **XQuery**: Insert new `<range>` element into `<lift-ranges>`

#### FR-3: Edit Range Metadata
- **Description**: Edit range ID, labels, descriptions
- **Constraints**:
  - Cannot change ID if range is referenced in entries
  - Must preserve GUID
- **UI**: Inline editing for labels, modal for ID changes
- **API**: `PUT /api/ranges/{range_id}`
- **XQuery**: Update `<range>` attributes and child elements

#### FR-4: Delete Range
- **Description**: Remove entire range from database
- **Pre-Deletion Checks**:
  1. Search all entries for references to this range
  2. If in use, show usage count and offer migration options:
     - **Cancel deletion** (default)
     - **Remove values from entries** (set to null)
     - **Replace with another range** (show compatible ranges)
- **UI**: Confirmation modal with usage analysis
- **API**: `DELETE /api/ranges/{range_id}`
- **XQuery**: Delete `<range>` element + cascade updates to entries

---

### 3.2 Range Element Operations

#### FR-5: List Range Elements
- **Description**: Display hierarchical tree of range elements
- **UI**: Expandable tree view with:
  - Element ID
  - Label (default language)
  - Abbreviation
  - Child count (for parent elements)
- **API**: `GET /api/ranges/{range_id}/elements`
- **Return Format**: Hierarchical JSON (parsed via `LIFTRangesParser`)

#### FR-6: Create Range Element
- **Description**: Add new element to a range
- **Required Fields**:
  - `id` (unique within range)
  - `label` (multilingual)
  - `abbrev` (optional, multilingual)
  - `description` (optional, multilingual)
  - `parent` (optional, for hierarchical ranges)
  - `guid` (auto-generated)
- **Validation**:
  - ID must be unique within range
  - Parent ID must exist if specified
  - No circular dependencies
- **UI**: 
  - Inline "Add" button in tree view
  - Modal form for details
  - Parent selector dropdown (hierarchical)
- **API**: `POST /api/ranges/{range_id}/elements`
- **XQuery**: Insert `<range-element>` with proper positioning

#### FR-7: Edit Range Element
- **Description**: Modify element properties
- **Editable Fields**:
  - Labels (all languages)
  - Abbreviations (all languages)
  - Descriptions (all languages)
  - Parent (move in hierarchy)
  - Traits (name-value pairs)
- **Constraints**:
  - Cannot change ID if element is in use (show usage first)
  - Cannot create circular parent references
- **UI**: 
  - Inline editing for labels/abbrev
  - Modal for full details
  - Drag-and-drop for reordering (within same parent)
- **API**: `PUT /api/ranges/{range_id}/elements/{element_id}`
- **XQuery**: Update `<range-element>` attributes and children

#### FR-8: Delete Range Element
- **Description**: Remove element from range
- **Pre-Deletion Checks**:
  1. Check if element has children → Must delete/move children first
  2. Search entries for usage of this value
  3. If in use, offer migration:
     - **Cancel deletion**
     - **Remove value from entries**
     - **Replace with another element** (from same range)
- **UI**: Confirmation modal with usage count
- **API**: `DELETE /api/ranges/{range_id}/elements/{element_id}`
- **XQuery**: Delete `<range-element>` + cascade to entries

#### FR-9: Move Element in Hierarchy
- **Description**: Change parent of an element
- **Validation**:
  - New parent must exist
  - No circular references
  - Target parent must be in same range
- **UI**: Drag-and-drop in tree view, or parent selector in edit modal
- **API**: `PATCH /api/ranges/{range_id}/elements/{element_id}/parent`
- **XQuery**: Update `parent` attribute or move nested element

---

### 3.3 Data Integrity & Usage Analysis

#### FR-10: Find Range Usage in Entries
- **Description**: Identify all entries using a specific range or element
- **Search Contexts**:
  - `grammatical-info` → Entry, Sense, Variant `grammatical_info` attribute
  - `semantic-domain-ddp4` → Sense `domain_type` list
  - `usage-type` → Sense `usage_type` list
  - `domain-type` → Sense `academic_domain`
  - `lexical-relation` → Entry/Sense `relations` list
  - Trait values → Entry/Sense/Example `traits` dict
- **XQuery Strategy**:
  ```xquery
  (: Find entries with specific grammatical-info value :)
  collection('{db_name}')//entry[
    .//grammatical-info[@value = '{element_id}']
  ]
  
  (: Find entries with trait value :)
  collection('{db_name}')//entry[
    .//trait[@name = '{range_id}' and @value = '{element_id}']
  ]
  ```
- **API**: `GET /api/ranges/{range_id}/usage?element_id={element_id}`
- **Return**: List of entry IDs with affected field paths

#### FR-11: Migrate Range Values
- **Description**: Bulk update entries when deleting/renaming range elements
- **Migration Operations**:
  1. **Remove Value**: Set field to null/empty
  2. **Replace Value**: Change to different element ID
  3. **Split Value**: For multi-value fields, remove specific value
- **Affected Fields** (by range type):
  - `grammatical-info`: Replace in `<grammatical-info value="..."/>`
  - `domain-type`: Replace in `<trait name="domain-type" value="..."/>`
  - `usage-type`: Replace in `<trait name="usage-type" value="..."/>`
  - Custom traits: Replace in `<trait name="{range_id}" value="..."/>`
- **UI**: 
  - Migration wizard modal
  - Preview affected entries (max 100)
  - Confirm/Cancel actions
- **API**: `POST /api/ranges/{range_id}/migrate`
- **Request Body**:
  ```json
  {
    "old_value": "Noun",
    "operation": "replace|remove",
    "new_value": "Noun-Alt",  // Only for 'replace'
    "dry_run": false
  }
  ```
- **XQuery**: Bulk update using XQuery Update Facility

---

### 3.4 Multilingual Content Management

#### FR-12: Add/Edit Language Variants
- **Description**: Manage multilingual labels, descriptions, abbreviations
- **UI Components**:
  - Language selector dropdown
  - "Add Language" button
  - Text input per language
  - "Remove Language" button (except default)
- **Default Language**: Configurable (default: `en`)
- **Validation**:
  - At least one language required for labels
  - Language codes must be valid IANA codes
- **Storage**: LIFT `<form lang="..."><text>...</text></form>` structure

#### FR-13: Trait Management
- **Description**: Edit traits on range elements
- **Trait Types** (from LIFT spec):
  - `catalog-source-id`: Source system ID
  - `inflectable-feat`: Inflection features
  - Custom traits (name-value pairs)
- **UI**: 
  - Table view of traits
  - Add/Edit/Delete trait rows
  - Name and value inputs
- **API**: Part of range element edit (FR-7)

---

### 3.5 Validation & Error Handling

#### FR-14: Range ID Uniqueness
- **Validation**: Range ID must be unique across all ranges
- **Error**: `400 Bad Request` with message "Range ID '{id}' already exists"
- **UI**: Real-time validation on ID input field

#### FR-15: Element ID Uniqueness (Within Range)
- **Validation**: Element ID must be unique within parent range
- **Error**: `400 Bad Request` with message "Element ID '{id}' already exists in range '{range_id}'"
- **UI**: Real-time validation

#### FR-16: Circular Hierarchy Prevention
- **Validation**: Parent references must not create cycles
- **Algorithm**: Traverse parent chain, detect if current element ID appears
- **Error**: `400 Bad Request` with message "Cannot set parent: would create circular reference"
- **UI**: Disable invalid parent options in dropdown

#### FR-17: GUID Preservation
- **Validation**: GUIDs must be preserved during edits
- **Auto-Generation**: Generate UUIDs for new ranges/elements
- **UI**: GUID shown as read-only field

---

## 4. Technical Architecture

### 4.1 Backend Components

#### 4.1.1 New Service: `RangesService`
**File**: `app/services/ranges_service.py`

```python
from typing import Dict, List, Any, Optional
from app.database.basex_connector import BaseXConnector
from app.parsers.lift_parser import LIFTRangesParser
import uuid

class RangesService:
    """Service for managing LIFT ranges in BaseX."""
    
    def __init__(self, db_connector: BaseXConnector):
        self.db_connector = db_connector
        self.ranges_parser = LIFTRangesParser()
        self.logger = logging.getLogger(__name__)
    
    # Range CRUD
    def get_all_ranges(self) -> Dict[str, Any]:
        """Retrieve all ranges from database."""
        pass
    
    def get_range(self, range_id: str) -> Dict[str, Any]:
        """Get single range by ID."""
        pass
    
    def create_range(self, range_data: Dict[str, Any]) -> str:
        """Create new range, return GUID."""
        pass
    
    def update_range(self, range_id: str, range_data: Dict[str, Any]) -> None:
        """Update range metadata."""
        pass
    
    def delete_range(self, range_id: str, migration: Optional[Dict] = None) -> None:
        """Delete range with optional data migration."""
        pass
    
    # Range Element CRUD
    def get_range_elements(self, range_id: str) -> List[Dict[str, Any]]:
        """Get hierarchical list of elements."""
        pass
    
    def create_range_element(
        self, range_id: str, element_data: Dict[str, Any]
    ) -> str:
        """Create new element, return GUID."""
        pass
    
    def update_range_element(
        self, range_id: str, element_id: str, element_data: Dict[str, Any]
    ) -> None:
        """Update element properties."""
        pass
    
    def delete_range_element(
        self, range_id: str, element_id: str, migration: Optional[Dict] = None
    ) -> None:
        """Delete element with migration."""
        pass
    
    # Usage Analysis
    def find_range_usage(
        self, range_id: str, element_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find entries using range/element."""
        pass
    
    def migrate_range_values(
        self, range_id: str, old_value: str, operation: str, new_value: Optional[str] = None
    ) -> Dict[str, int]:
        """Bulk update entry range values."""
        pass
    
    # Validation
    def validate_range_id(self, range_id: str) -> bool:
        """Check if range ID is unique."""
        pass
    
    def validate_element_id(self, range_id: str, element_id: str) -> bool:
        """Check if element ID is unique within range."""
        pass
    
    def validate_parent_reference(
        self, range_id: str, element_id: str, parent_id: str
    ) -> bool:
        """Check for circular parent references."""
        pass
```

#### 4.1.2 XQuery Operations Module
**File**: `app/xquery/ranges_operations.xq`

```xquery
xquery version "3.1";

declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13/ranges";

(: Get all ranges :)
declare function local:get-all-ranges($db-name as xs:string) {
    collection($db-name)//lift-ranges
};

(: Get single range by ID :)
declare function local:get-range($db-name as xs:string, $range-id as xs:string) {
    collection($db-name)//range[@id = $range-id]
};

(: Create new range :)
declare function local:create-range(
    $db-name as xs:string,
    $range-id as xs:string,
    $guid as xs:string,
    $labels as element()*,
    $descriptions as element()*
) {
    let $lift-ranges := collection($db-name)//lift-ranges
    let $new-range := 
        <range id="{$range-id}" guid="{$guid}">
            {$labels}
            {$descriptions}
        </range>
    return insert node $new-range into $lift-ranges
};

(: Update range metadata :)
declare function local:update-range(
    $db-name as xs:string,
    $range-id as xs:string,
    $new-labels as element()*,
    $new-descriptions as element()*
) {
    let $range := collection($db-name)//range[@id = $range-id]
    return (
        delete node $range/label,
        delete node $range/description,
        insert node ($new-labels, $new-descriptions) into $range
    )
};

(: Delete range :)
declare function local:delete-range($db-name as xs:string, $range-id as xs:string) {
    delete node collection($db-name)//range[@id = $range-id]
};

(: Create range element :)
declare function local:create-range-element(
    $db-name as xs:string,
    $range-id as xs:string,
    $element-id as xs:string,
    $guid as xs:string,
    $parent-id as xs:string?,
    $labels as element()*,
    $abbrevs as element()*,
    $descriptions as element()*
) {
    let $range := collection($db-name)//range[@id = $range-id]
    let $new-element :=
        <range-element id="{$element-id}" guid="{$guid}">
            {if ($parent-id) then attribute parent { $parent-id } else ()}
            {$labels}
            {$abbrevs}
            {$descriptions}
        </range-element>
    return 
        if ($parent-id) then
            (: Insert as child of parent element :)
            let $parent := $range//range-element[@id = $parent-id]
            return insert node $new-element into $parent
        else
            (: Insert as direct child of range :)
            insert node $new-element into $range
};

(: Update range element :)
declare function local:update-range-element(
    $db-name as xs:string,
    $range-id as xs:string,
    $element-id as xs:string,
    $new-labels as element()*,
    $new-abbrevs as element()*,
    $new-descriptions as element()*
) {
    let $element := collection($db-name)//range[@id = $range-id]//range-element[@id = $element-id]
    return (
        delete node $element/label,
        delete node $element/abbrev,
        delete node $element/description,
        insert node ($new-labels, $new-abbrevs, $new-descriptions) into $element
    )
};

(: Delete range element :)
declare function local:delete-range-element(
    $db-name as xs:string,
    $range-id as xs:string,
    $element-id as xs:string
) {
    delete node collection($db-name)//range[@id = $range-id]//range-element[@id = $element-id]
};

(: Find range usage in entries :)
declare function local:find-range-usage(
    $db-name as xs:string,
    $range-id as xs:string,
    $element-id as xs:string?
) {
    let $entries := collection($db-name)//entry
    return
        if ($element-id) then
            (: Search for specific element value :)
            $entries[
                .//grammatical-info[@value = $element-id] or
                .//trait[@name = $range-id and @value = $element-id]
            ]
        else
            (: Search for any value in range (trait name match) :)
            $entries[
                .//trait[@name = $range-id]
            ]
};

(: Migrate range values (replace) :)
declare function local:migrate-range-values-replace(
    $db-name as xs:string,
    $range-id as xs:string,
    $old-value as xs:string,
    $new-value as xs:string
) {
    (: Update grammatical-info values :)
    for $gram-info in collection($db-name)//grammatical-info[@value = $old-value]
    return replace value of node $gram-info/@value with $new-value,
    
    (: Update trait values :)
    for $trait in collection($db-name)//trait[@name = $range-id and @value = $old-value]
    return replace value of node $trait/@value with $new-value
};

(: Migrate range values (remove) :)
declare function local:migrate-range-values-remove(
    $db-name as xs:string,
    $range-id as xs:string,
    $old-value as xs:string
) {
    (: Delete grammatical-info elements :)
    delete node collection($db-name)//grammatical-info[@value = $old-value],
    
    (: Delete trait elements :)
    delete node collection($db-name)//trait[@name = $range-id and @value = $old-value]
};
```

#### 4.1.3 New API Blueprint
**File**: `app/api/ranges_editor.py`

```python
from flask import Blueprint, jsonify, request, current_app
from typing import Union, Tuple
from app.services.ranges_service import RangesService

ranges_editor_bp = Blueprint('ranges_editor', __name__, url_prefix='/api/ranges-editor')

@ranges_editor_bp.route('/', methods=['GET'])
def list_ranges():
    """Get all ranges."""
    pass

@ranges_editor_bp.route('/', methods=['POST'])
def create_range():
    """Create new range."""
    pass

@ranges_editor_bp.route('/<range_id>', methods=['GET'])
def get_range(range_id: str):
    """Get single range with elements."""
    pass

@ranges_editor_bp.route('/<range_id>', methods=['PUT'])
def update_range(range_id: str):
    """Update range metadata."""
    pass

@ranges_editor_bp.route('/<range_id>', methods=['DELETE'])
def delete_range(range_id: str):
    """Delete range (with usage check)."""
    pass

@ranges_editor_bp.route('/<range_id>/elements', methods=['GET'])
def list_elements(range_id: str):
    """Get hierarchical list of range elements."""
    pass

@ranges_editor_bp.route('/<range_id>/elements', methods=['POST'])
def create_element(range_id: str):
    """Create new range element."""
    pass

@ranges_editor_bp.route('/<range_id>/elements/<element_id>', methods=['PUT'])
def update_element(range_id: str, element_id: str):
    """Update range element."""
    pass

@ranges_editor_bp.route('/<range_id>/elements/<element_id>', methods=['DELETE'])
def delete_element(range_id: str, element_id: str):
    """Delete range element (with usage check)."""
    pass

@ranges_editor_bp.route('/<range_id>/usage', methods=['GET'])
def get_usage(range_id: str):
    """Find entries using range/element."""
    pass

@ranges_editor_bp.route('/<range_id>/migrate', methods=['POST'])
def migrate_values(range_id: str):
    """Bulk migrate range values in entries."""
    pass

@ranges_editor_bp.route('/<range_id>/elements/<element_id>/validate', methods=['GET'])
def validate_element(range_id: str, element_id: str):
    """Validate element ID uniqueness."""
    pass
```

---

### 4.2 Frontend Components

#### 4.2.1 Ranges List View
**File**: `app/templates/ranges_editor.html`

**Features**:
- Table with range ID, label, element count
- "Create Range" button
- Edit/Delete actions per row
- Search/filter by range ID or label

**UI Mockup**:
```
+----------------------------------------------------------+
| LIFT Ranges Editor                          [+ New Range]|
+----------------------------------------------------------+
| Search: [____________]                                    |
+----------------------------------------------------------+
| ID                  | Label              | Elements | Acti|
|---------------------|--------------------|-----------|----|
| grammatical-info    | Grammatical Info   | 45        | ✏️ 🗑|
| semantic-domain-ddp4| Semantic Domains   | 1200      | ✏️ 🗑|
| domain-type         | Academic Domains   | 12        | ✏️ 🗑|
| usage-type          | Usage Types        | 8         | ✏️ 🗑|
+----------------------------------------------------------+
```

#### 4.2.2 Range Elements Tree View
**File**: `app/templates/range_elements_editor.html`

**Features**:
- Expandable tree with drag-and-drop
- Inline edit for labels/abbrev
- "Add Child" button on each node
- Delete button with usage check

**UI Mockup**:
```
+----------------------------------------------------------+
| Range: grammatical-info                    [+ Add Element]|
+----------------------------------------------------------+
| ▼ Noun (n)                                    [✏️] [🗑] [+]|
|   ▸ Countable Noun (n [C])                   [✏️] [🗑] [+]|
|   ▸ Uncountable Noun (n [U])                 [✏️] [🗑] [+]|
| ▼ Verb (v)                                    [✏️] [🗑] [+]|
|   ▸ Transitive Verb (vt)                     [✏️] [🗑] [+]|
|   ▸ Intransitive Verb (vi)                   [✏️] [🗑] [+]|
| ▸ Adverb (adv)                                [✏️] [🗑] [+]|
+----------------------------------------------------------+
```

#### 4.2.3 Range Element Edit Modal
**File**: `app/static/js/range-element-editor.js`

**Features**:
- ID input (with uniqueness validation)
- GUID display (read-only)
- Parent selector (hierarchical dropdown)
- Multilingual label/abbrev/description editors
- Trait editor (key-value table)

**UI Mockup**:
```
+----------------------------------------------------------+
| Edit Range Element                              [✕ Close]|
+----------------------------------------------------------+
| ID:          [Countable Noun              ]  ⚠️ In use    |
| GUID:        b4c74c31-58fc-4feb-86bf-c2235bda8d3c        |
| Parent:      [▼ Noun                       ]             |
|                                                           |
| Labels:                                                   |
| ┌──────────┬───────────────────────────────────┬─────┐  |
| | Language | Text                              | Del |  |
| ├──────────┼───────────────────────────────────┼─────┤  |
| | en       | [Countable Noun             ]     | [🗑] |  |
| | pl       | [Rzeczownik policzalny      ]     | [🗑] |  |
| └──────────┴───────────────────────────────────┴─────┘  |
| [+ Add Language]                                          |
|                                                           |
| Abbreviations: (same structure)                           |
|                                                           |
| Descriptions: (same structure)                            |
|                                                           |
| Traits:                                                   |
| ┌────────────────────┬────────────────────────┬─────┐   |
| | Name               | Value                  | Del |   |
| ├────────────────────┼────────────────────────┼─────┤   |
| | catalog-source-id  | [Countable Noun   ]    | [🗑] |   |
| └────────────────────┴────────────────────────┴─────┘   |
| [+ Add Trait]                                             |
|                                                           |
|                               [Cancel] [Save Changes]     |
+----------------------------------------------------------+
```

#### 4.2.4 Usage Analysis Modal
**File**: `app/static/js/usage-analysis.js`

**Features**:
- Show count of affected entries
- Preview first 100 affected entries
- Migration options (remove, replace)
- Dry-run mode

**UI Mockup**:
```
+----------------------------------------------------------+
| Range Element Usage Analysis                   [✕ Close]|
+----------------------------------------------------------+
| Element: Noun                                             |
| Range:   grammatical-info                                 |
|                                                           |
| ⚠️ This element is used in 1,234 entries                  |
|                                                           |
| Sample Entries (showing first 100):                       |
| ┌────────────┬──────────────────┬─────────────────────┐  |
| | Entry ID   | Headword         | Usage Context       |  |
| ├────────────┼──────────────────┼─────────────────────┤  |
| | entry_001  | cat              | Sense #1 gramm-info |  |
| | entry_042  | dog              | Sense #1 gramm-info |  |
| | entry_103  | house            | Sense #2 gramm-info |  |
| | ...        | ...              | ...                 |  |
| └────────────┴──────────────────┴─────────────────────┘  |
|                                                           |
| Migration Options:                                        |
| ( ) Cancel deletion                                       |
| ( ) Remove value from all entries                         |
| (•) Replace with: [▼ Noun-Alt                 ]          |
|                                                           |
| [☑] Dry run (preview changes only)                        |
|                                                           |
|                         [Cancel] [Execute Migration]      |
+----------------------------------------------------------+
```

---

### 4.3 Database Operations

#### 4.3.1 BaseX Storage Strategy

**Current Structure**:
```
BaseX Database: {db_name}
├── sample-lift-file.lift           (main LIFT file)
├── sample-lift-file.lift-ranges    (ranges file)
└── entry_*.xml                     (individual entries, optional)
```

**XQuery Access**:
```xquery
(: Get ranges document :)
collection('{db_name}')//lift-ranges

(: Get specific range :)
collection('{db_name}')//range[@id='grammatical-info']
```

**Update Strategy**:
- Use XQuery Update Facility (`insert node`, `delete node`, `replace value of node`)
- All updates must be transactional
- Preserve XML formatting where possible

#### 4.3.2 XQuery Performance Optimization

**Indexes** (to be added):
```xquery
(: Create index on range IDs :)
db:create-index('{db_name}', 'range', 'id')

(: Create index on range-element IDs :)
db:create-index('{db_name}', 'range-element', 'id')
```

**Caching Strategy**:
- Cache parsed ranges in `DictionaryService.ranges` dict
- Invalidate cache on any ranges modification
- TTL: 1 hour or manual invalidation

---

### 4.4 Data Integrity Implementation

#### 4.4.1 Usage Detection Query

```python
def find_range_usage(self, range_id: str, element_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Find all entries using a specific range or element.
    
    Returns:
        List of dicts with structure:
        {
            'entry_id': str,
            'headword': str,
            'usage_contexts': [
                {'field': 'grammatical_info', 'sense_id': 's1', 'value': 'Noun'},
                {'field': 'trait', 'trait_name': 'domain-type', 'value': 'Science'}
            ]
        }
    """
    db_name = self.db_connector.database
    
    # Build XQuery based on range type
    if range_id == 'grammatical-info':
        # Search in grammatical-info elements
        query = f"""
        for $entry in collection('{db_name}')//entry
        let $usage := (
            for $gi in $entry//grammatical-info[@value = '{element_id}']
            return map {{
                'field': 'grammatical_info',
                'sense_id': $gi/ancestor::sense/@id/string(),
                'value': $gi/@value/string()
            }}
        )
        where count($usage) > 0
        return map {{
            'entry_id': $entry/@id/string(),
            'headword': $entry/lexical-unit/form[1]/text/string(),
            'usage_contexts': array {{ $usage }}
        }}
        """
    else:
        # Search in traits
        query = f"""
        for $entry in collection('{db_name}')//entry
        let $usage := (
            for $trait in $entry//trait[@name = '{range_id}']
            {'where $trait/@value = "' + element_id + '"' if element_id else ''}
            return map {{
                'field': 'trait',
                'trait_name': $trait/@name/string(),
                'value': $trait/@value/string()
            }}
        )
        where count($usage) > 0
        return map {{
            'entry_id': $entry/@id/string(),
            'headword': $entry/lexical-unit/form[1]/text/string(),
            'usage_contexts': array {{ $usage }}
        }}
        """
    
    result = self.db_connector.execute_query(query)
    # Parse JSON result
    return json.loads(result)
```

#### 4.4.2 Migration Operations

**Replace Operation**:
```python
def migrate_replace(self, range_id: str, old_value: str, new_value: str, dry_run: bool = False) -> Dict[str, int]:
    """
    Replace old_value with new_value in all entries.
    
    Returns:
        {'entries_affected': int, 'fields_updated': int}
    """
    db_name = self.db_connector.database
    
    if dry_run:
        # Count only
        count_query = f"""
        count(
            collection('{db_name}')//entry[
                .//grammatical-info[@value = '{old_value}'] or
                .//trait[@name = '{range_id}' and @value = '{old_value}']
            ]
        )
        """
        count = int(self.db_connector.execute_query(count_query))
        return {'entries_affected': count, 'fields_updated': 0}
    
    # Execute update
    update_query = f"""
    (: Replace in grammatical-info :)
    for $gi in collection('{db_name}')//grammatical-info[@value = '{old_value}']
    return replace value of node $gi/@value with '{new_value}',
    
    (: Replace in traits :)
    for $trait in collection('{db_name}')//trait[@name = '{range_id}' and @value = '{old_value}']
    return replace value of node $trait/@value with '{new_value}'
    """
    
    self.db_connector.execute_update(update_query)
    
    # Count affected entries
    count = int(self.db_connector.execute_query(count_query))
    return {'entries_affected': count, 'fields_updated': count}
```

**Remove Operation**:
```python
def migrate_remove(self, range_id: str, old_value: str, dry_run: bool = False) -> Dict[str, int]:
    """
    Remove old_value from all entries (delete elements).
    """
    # Similar to replace, but use `delete node` instead
    pass
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

**File**: `tests/unit/test_ranges_service.py`

**Test Cases**:
1. `test_create_range_valid()` - Create range with valid data
2. `test_create_range_duplicate_id()` - Reject duplicate range ID
3. `test_update_range_labels()` - Update multilingual labels
4. `test_delete_range_unused()` - Delete range with no usage
5. `test_delete_range_in_use_reject()` - Prevent deletion of range in use
6. `test_create_element_valid()` - Create element with parent
7. `test_create_element_circular_parent()` - Reject circular parent reference
8. `test_update_element_move_parent()` - Move element to different parent
9. `test_delete_element_with_children()` - Reject deletion if has children
10. `test_validate_element_id_unique()` - Uniqueness check

### 5.2 Integration Tests

**File**: `tests/integration/test_ranges_crud_integration.py`

**Test Cases**:
1. `test_range_roundtrip()` - Create, read, update, delete range
2. `test_element_hierarchy_nested()` - Create nested hierarchy
3. `test_element_hierarchy_parent_attr()` - Create parent-based hierarchy
4. `test_usage_detection_grammatical_info()` - Find grammatical-info usage
5. `test_usage_detection_traits()` - Find trait usage
6. `test_migrate_replace_values()` - Replace range values in entries
7. `test_migrate_remove_values()` - Remove range values from entries
8. `test_multilingual_content_crud()` - Add/edit/delete language variants
9. `test_trait_crud()` - Add/edit/delete traits on elements
10. `test_cache_invalidation()` - Verify cache invalidates on update

### 5.3 End-to-End Tests

**File**: `tests/e2e/test_ranges_editor_ui.py` (Playwright)

**Test Cases**:
1. `test_create_range_ui()` - Create range via UI
2. `test_edit_range_labels_ui()` - Edit multilingual labels
3. `test_delete_range_with_usage_warning()` - Deletion warning modal
4. `test_create_nested_elements()` - Tree UI interaction
5. `test_drag_drop_reorder()` - Drag-and-drop hierarchy
6. `test_migration_wizard()` - Migration workflow
7. `test_real_time_validation()` - ID uniqueness validation

---

## 6. User Interface Design

### 6.1 Navigation

**Menu Integration**:
- Add "Ranges Editor" link to main navigation
- Location: Under "Settings" or "Admin Tools" section
- Icon: 📋 or 📚
- Requires admin role

### 6.2 Workflow Examples

#### Workflow 1: Create New Range
1. Click "Ranges Editor" in navigation
2. Click "+ New Range" button
3. Fill modal form:
   - ID: `custom-field-type`
   - Label (en): `Custom Field Types`
   - Description (en): `Types for custom fields`
4. Click "Create"
5. See new range in list

#### Workflow 2: Add Hierarchical Elements
1. Open range "grammatical-info"
2. Click "+ Add Element" button
3. Create parent: ID=`Noun`, Label=`Noun`, Abbrev=`n`
4. Click "+" next to "Noun" node
5. Create child: ID=`Proper Noun`, Parent=`Noun`, Abbrev=`prop.n`
6. See nested structure in tree

#### Workflow 3: Delete Element with Data Migration
1. Open range "grammatical-info"
2. Click 🗑 button next to "Noun"
3. See usage analysis modal:
   - "⚠️ Used in 1,234 entries"
   - Sample entry list
4. Select migration option: "Replace with Noun-Alt"
5. Check "Dry run" checkbox
6. Click "Execute Migration"
7. See preview: "Would update 1,234 entries"
8. Uncheck "Dry run"
9. Click "Execute Migration"
10. See success: "Updated 1,234 entries"

---

## 7. Implementation Roadmap

### Phase 1: Backend Foundation (Days 1-3)
**Goal**: Build core CRUD functionality for ranges

**Tasks**:
- [ ] Create `RangesService` class
- [ ] Implement range CRUD methods
- [ ] Implement element CRUD methods
- [ ] Write XQuery operations module
- [ ] Unit tests for service layer (target: 30 tests)

**Deliverables**:
- `app/services/ranges_service.py`
- `app/xquery/ranges_operations.xq`
- `tests/unit/test_ranges_service.py`

### Phase 2: API Endpoints (Days 4-5)
**Goal**: Expose ranges management via REST API

**Tasks**:
- [ ] Create `ranges_editor_bp` blueprint
- [ ] Implement all API endpoints
- [ ] Add Swagger/Flasgger documentation
- [ ] Integration tests for API (target: 20 tests)

**Deliverables**:
- `app/api/ranges_editor.py`
- `tests/integration/test_ranges_api.py`

### Phase 3: Usage Analysis & Migration (Days 6-8)
**Goal**: Implement data integrity protection

**Tasks**:
- [ ] Implement `find_range_usage()` with XQuery
- [ ] Implement `migrate_replace()` XQuery operation
- [ ] Implement `migrate_remove()` XQuery operation
- [ ] Add dry-run mode
- [ ] Unit tests for usage detection (target: 15 tests)
- [ ] Integration tests for migration (target: 10 tests)

**Deliverables**:
- Enhanced `RangesService` with migration methods
- Migration XQuery operations
- `tests/integration/test_ranges_migration.py`

### Phase 4: Frontend - List & Tree Views (Days 9-11)
**Goal**: Build core UI components

**Tasks**:
- [ ] Create `ranges_editor.html` template
- [ ] Implement ranges list table
- [ ] Create `range_elements_editor.html` template
- [ ] Implement tree view with jsTree or similar
- [ ] Add search/filter functionality
- [ ] CSS styling for consistency

**Deliverables**:
- `app/templates/ranges_editor.html`
- `app/templates/range_elements_editor.html`
- `app/static/css/ranges-editor.css`

### Phase 5: Frontend - Edit Modals (Days 12-14)
**Goal**: Build interactive editing UI

**Tasks**:
- [ ] Create range edit modal
- [ ] Create element edit modal
- [ ] Implement multilingual text editors
- [ ] Implement trait editor
- [ ] Real-time validation (ID uniqueness)
- [ ] Parent selector with hierarchy display

**Deliverables**:
- `app/static/js/range-editor.js`
- `app/static/js/range-element-editor.js`
- `app/static/js/multilingual-editor.js`

### Phase 6: Frontend - Migration Wizard (Days 15-16)
**Goal**: Build data migration UI

**Tasks**:
- [ ] Create usage analysis modal
- [ ] Implement migration options UI
- [ ] Add dry-run preview
- [ ] Progress indicator for bulk updates
- [ ] Confirmation dialogs

**Deliverables**:
- `app/static/js/migration-wizard.js`

### Phase 7: Testing & Polish (Days 17-18)
**Goal**: Comprehensive testing and UX improvements

**Tasks**:
- [ ] End-to-end tests with Playwright (target: 15 tests)
- [ ] Performance testing (large ranges)
- [ ] Accessibility testing (ARIA labels, keyboard nav)
- [ ] Error handling polish
- [ ] User documentation

**Deliverables**:
- `tests/e2e/test_ranges_editor_ui.py`
- `docs/RANGES_EDITOR_USER_GUIDE.md`

### Phase 8: Integration & Deployment (Days 19-20)
**Goal**: Integrate with existing app and deploy

**Tasks**:
- [ ] Add menu navigation link
- [ ] Configure permissions (admin-only)
- [ ] Database backup before deployment
- [ ] Deploy to staging
- [ ] User acceptance testing
- [ ] Production deployment

**Deliverables**:
- Production-ready ranges editor

---

## 8. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Accidental deletion of critical ranges** | MEDIUM | HIGH | Pre-deletion usage analysis, confirmation dialogs, backup requirement |
| **Performance issues with large ranges** | LOW | MEDIUM | Pagination, lazy loading, XQuery indexing |
| **Circular hierarchy bugs** | MEDIUM | MEDIUM | Validation algorithm, comprehensive tests |
| **XQuery update failures** | LOW | HIGH | Transactional updates, rollback mechanism |
| **Cache invalidation bugs** | MEDIUM | LOW | Clear cache on every write operation |
| **Migration data loss** | LOW | CRITICAL | Dry-run mode, database backup requirement |

---

## 9. Success Criteria

**Must Have (MVP)**:
1. ✅ Create, read, update, delete ranges
2. ✅ Create, read, update, delete range elements
3. ✅ Hierarchical element support (both patterns)
4. ✅ Multilingual content editing
5. ✅ Usage detection before deletion
6. ✅ Basic migration (replace, remove)

**Should Have**:
1. ✅ Tree view with drag-and-drop
2. ✅ Real-time validation
3. ✅ Dry-run migration preview
4. ✅ Bulk operations (delete multiple elements)

**Nice to Have**:
1. Import/export ranges as JSON
2. Range templates (quick setup for common types)
3. Audit trail (who changed what, when)
4. Undo/redo for edits

---

## 10. Acceptance Tests

### AT-1: Create Range
**Given**: User is on ranges editor page  
**When**: User creates range with ID "test-range" and label "Test Range"  
**Then**: Range appears in list with correct ID and label

### AT-2: Delete Unused Range
**Given**: Range "test-range" exists with no usage  
**When**: User deletes range  
**Then**: Range is removed from list and database

### AT-3: Prevent Deletion of Range in Use
**Given**: Range "grammatical-info" is used in 1000 entries  
**When**: User attempts to delete range  
**Then**: Warning modal shows usage count and requires migration

### AT-4: Migrate Range Values
**Given**: Element "Noun" is used in 500 entries  
**When**: User deletes element and selects "Replace with Noun-Alt"  
**Then**: All 500 entries are updated with "Noun-Alt"

### AT-5: Validate Hierarchy
**Given**: Element "Noun" has ID "Noun"  
**When**: User tries to set parent of "Noun" to its child "Countable Noun"  
**Then**: Validation error prevents circular reference

---

## 11. Documentation Requirements

### 11.1 User Documentation
**File**: `docs/RANGES_EDITOR_USER_GUIDE.md`

**Sections**:
1. Introduction to LIFT Ranges
2. Accessing the Ranges Editor
3. Creating and Managing Ranges
4. Working with Hierarchical Elements
5. Multilingual Content Editing
6. Understanding Range Usage
7. Data Migration Best Practices
8. Troubleshooting Common Issues

### 11.2 Technical Documentation
**File**: `docs/RANGES_EDITOR_TECHNICAL.md`

**Sections**:
1. Architecture Overview
2. API Reference
3. XQuery Operations
4. Data Model
5. Testing Strategy
6. Deployment Notes

### 11.3 API Documentation
**Integration**: Add to existing Swagger/Flasgger docs

**Example**:
```yaml
/api/ranges-editor/{range_id}:
  get:
    summary: Get range by ID
    parameters:
      - name: range_id
        in: path
        required: true
        schema:
          type: string
    responses:
      200:
        description: Range data with hierarchical elements
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Range'
      404:
        description: Range not found
```

---

## 12. Open Questions

1. **Permissions**: Should range editing be admin-only or role-based?
   - **Recommendation**: Admin-only for MVP, role-based in future

2. **Validation**: Should we validate against FieldWorks standard ranges?
   - **Recommendation**: No, support custom ranges for flexibility

3. **Backup**: Should we auto-backup before deletions?
   - **Recommendation**: Yes, create automatic backup before destructive operations

4. **Undo**: Should we implement undo/redo?
   - **Recommendation**: Deferred to Phase 2, use audit trail instead

5. **Concurrency**: How to handle simultaneous edits?
   - **Recommendation**: Last-write-wins for MVP, optimistic locking in future

---

## 13. Appendix

### A. LIFT 0.13 Ranges Specification
- **Source**: https://github.com/sillsdev/lift-standard
- **Key Elements**:
  - `<lift-ranges>` - Root element
  - `<range>` - Range definition (ID, GUID, labels, descriptions)
  - `<range-element>` - Range value (ID, GUID, labels, abbrevs, traits, children)
  - `<label>` - Multilingual label
  - `<description>` - Multilingual description
  - `<abbrev>` - Multilingual abbreviation
  - `<trait>` - Name-value metadata pair

### B. BaseX XQuery Update Facility Reference
- **Documentation**: https://docs.basex.org/wiki/XQuery_Update
- **Key Operations**:
  - `insert node` - Add new nodes
  - `delete node` - Remove nodes
  - `replace node` - Replace entire nodes
  - `replace value of node` - Update node content
  - `rename node` - Change node name

### C. Sample Range XML Snippets

**Simple Flat Range**:
```xml
<range id="note-type">
  <label>
    <form lang="en"><text>Note Types</text></form>
  </label>
  <range-element id="general">
    <label>
      <form lang="en"><text>General</text></form>
    </label>
  </range-element>
  <range-element id="grammar">
    <label>
      <form lang="en"><text>Grammar</text></form>
    </label>
  </range-element>
</range>
```

**Nested Hierarchy Range**:
```xml
<range id="grammatical-info">
  <label>
    <form lang="en"><text>Grammatical Information</text></form>
  </label>
  <range-element id="Noun">
    <label>
      <form lang="en"><text>Noun</text></form>
    </label>
    <range-element id="Common Noun">
      <label>
        <form lang="en"><text>Common Noun</text></form>
      </label>
    </range-element>
    <range-element id="Proper Noun">
      <label>
        <form lang="en"><text>Proper Noun</text></form>
      </label>
    </range-element>
  </range-element>
</range>
```

**Parent-Based Hierarchy Range**:
```xml
<range id="semantic-domain">
  <range-element id="1" guid="abc123">
    <label>
      <form lang="en"><text>Universe</text></form>
    </label>
  </range-element>
  <range-element id="1.1" guid="def456" parent="1">
    <label>
      <form lang="en"><text>Sky</text></form>
    </label>
  </range-element>
  <range-element id="1.1.1" guid="ghi789" parent="1.1">
    <label>
      <form lang="en"><text>Sun</text></form>
    </label>
  </range-element>
</range>
```

---

## 14. Conclusion

This specification provides a comprehensive blueprint for implementing a production-ready LIFT Ranges Editor in the LexCW application. The design prioritizes:

1. **Data Integrity**: Pre-deletion usage analysis and migration workflows
2. **LIFT Compliance**: Support for all LIFT 0.13 ranges features
3. **Usability**: Intuitive tree-based UI with inline editing
4. **Performance**: XQuery-optimized operations with caching
5. **Testing**: Comprehensive test coverage (unit, integration, E2E)

**Estimated Effort**: 20 development days (4 weeks)  
**Priority**: HIGH (blocking production deployment)  
**Dependencies**: None (all required components exist)

**Next Steps**:
1. Review and approve specification
2. Create GitHub issues for each phase
3. Begin Phase 1 implementation
4. Schedule weekly progress reviews

---

**Document Prepared By**: GitHub Copilot  
**Review Status**: Pending  
**Approvers**: Project Lead, Technical Architect
