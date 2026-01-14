# LIFT Element Registry API

## Overview

The LIFT Element Registry API provides comprehensive metadata about LIFT (Lexicon Interchange FormaT) elements to support display profile configuration and UI customization.

**Base URL:** `/api/lift`  
**Format:** JSON  
**Authentication:** None (public read-only access)

## Endpoints

### 1. Get All Elements

```
GET /api/lift/elements
```

Returns all LIFT elements with complete metadata.

**Response:**
```json
{
  "elements": [
    {
      "name": "entry",
      "display_name": "Entry",
      "category": "root",
      "description": "Root element for a dictionary entry",
      "level": 0,
      "parent": null,
      "allowed_children": ["lexical-unit", "citation", "sense", ...],
      "required": false,
      "attributes": {...},
      "default_css": "lift-entry",
      "default_visibility": "always",
      "typical_order": 0
    },
    ...
  ],
  "count": 27
}
```

---

### 2. Get Element by Name

```
GET /api/lift/elements/{element_name}
```

Returns metadata for a specific LIFT element.

**Parameters:**
- `element_name` (path, required) - Name of the LIFT element (e.g., "lexical-unit")

**Response (200):**
```json
{
  "name": "lexical-unit",
  "display_name": "Lexical Unit / Headword",
  "category": "entry",
  "description": "The headword or main lexical form",
  "level": 1,
  "parent": "entry",
  "allowed_children": ["form"],
  "attributes": {},
  "default_css": "headword lexical-unit",
  "default_visibility": "always",
  "typical_order": 1
}
```

**Response (404):**
```json
{
  "error": "Element 'unknown-element' not found"
}
```

---

### 3. Get Displayable Elements

```
GET /api/lift/elements/displayable
```

Returns only elements suitable for display configuration (excludes technical/low-level elements).

**Response:**
```json
{
  "elements": [...],
  "count": 24
}
```

---

### 4. Get Elements by Category

```
GET /api/lift/elements/category/{category}
```

Returns all elements in a specific category.

**Parameters:**
- `category` (path, required) - Category name (root, entry, sense, example, basic, annotation, multimedia, reversal, extensibility)

**Response (200):**
```json
{
  "category": "entry",
  "elements": [...],
  "count": 6
}
```

**Response (400):**
```json
{
  "error": "Invalid category 'invalid-category'"
}
```

---

### 5. Get Categories

```
GET /api/lift/categories
```

Returns all available element categories with descriptions.

**Response:**
```json
{
  "categories": [
    {
      "name": "root",
      "display_name": "Root Elements",
      "description": "Top-level container elements"
    },
    {
      "name": "entry",
      "display_name": "Entry Elements",
      "description": "Direct children of entry element"
    },
    ...
  ]
}
```

---

### 6. Get Visibility Options

```
GET /api/lift/visibility-options
```

Returns available visibility options for element display configuration.

**Response:**
```json
{
  "options": [
    {
      "value": "always",
      "label": "Always Visible",
      "description": "Show regardless of content"
    },
    {
      "value": "if-content",
      "label": "Visible if Content",
      "description": "Show only when element has content"
    },
    {
      "value": "never",
      "label": "Hidden",
      "description": "Never display this element"
    }
  ]
}
```

---

### 7. Get Element Hierarchy

```
GET /api/lift/hierarchy
```

Returns parent-child relationships for all elements.

**Response:**
```json
{
  "hierarchy": {
    "entry": ["lexical-unit", "citation", "pronunciation", "variant", "sense", ...],
    "sense": ["grammatical-info", "gloss", "definition", "example", ...],
    "example": ["form", "translation", "note"],
    ...
  }
}
```

---

### 8. Get Metadata

```
GET /api/lift/metadata
```

Returns all metadata vocabularies (relation types, note types, grammatical categories).

**Response:**
```json
{
  "relation_types": [
    "synonym",
    "antonym",
    "derivation",
    "etymological-source",
    ...
  ],
  "note_types": [
    "grammar",
    "phonology",
    "usage",
    "encyclopedia",
    ...
  ],
  "grammatical_categories": [
    "Noun",
    "Verb",
    "Adjective",
    ...
  ]
}
```

---

### 9. Get Default Profile

```
GET /api/lift/default-profile
```

Returns default display profile configuration for all elements.

**Response:**
```json
{
  "profile": [
    {
      "lift_element": "lexical-unit",
      "display_order": 1,
      "css_class": "headword lexical-unit",
      "visibility": "always",
      "prefix": "",
      "suffix": ""
    },
    ...
  ],
  "name": "default",
  "description": "Default display profile for LIFT entries"
}
```

---

## Data Models

### Element Metadata

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Element name (identifier) |
| `display_name` | string | Human-readable display name |
| `category` | string | Element category |
| `description` | string | Element description |
| `level` | integer | Hierarchy level (0=root) |
| `parent` | string\|null | Parent element name |
| `allowed_children` | array | Valid child element names |
| `required` | boolean | Whether element is required in parent |
| `attributes` | object | Element attributes with types |
| `default_css` | string | Default CSS classes |
| `default_visibility` | string | Default visibility setting |
| `typical_order` | integer | Typical display order |

### Category

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Category identifier |
| `display_name` | string | Human-readable name |
| `description` | string | Category description |

### Visibility Option

| Field | Type | Description |
|-------|------|-------------|
| `value` | string | Option value (always\|if-content\|never) |
| `label` | string | Display label |
| `description` | string | Option description |

### Profile Element

| Field | Type | Description |
|-------|------|-------------|
| `lift_element` | string | LIFT element name |
| `display_order` | integer | Display order |
| `css_class` | string | CSS classes |
| `visibility` | string | Visibility setting |
| `prefix` | string | Text prefix |
| `suffix` | string | Text suffix |

---

## Error Responses

All endpoints return consistent error responses:

**404 Not Found:**
```json
{
  "error": "Element 'element-name' not found"
}
```

**400 Bad Request:**
```json
{
  "error": "Invalid category 'category-name'"
}
```

---

## Usage Examples

### JavaScript/Fetch

```javascript
// Get all elements
const response = await fetch('/api/lift/elements');
const data = await response.json();
console.log(`Found ${data.count} elements`);

// Get specific element
const element = await fetch('/api/lift/elements/sense');
const senseData = await element.json();
console.log(senseData.display_name); // "Sense"

// Get default profile
const profile = await fetch('/api/lift/default-profile');
const profileData = await profile.json();
console.log(profileData.profile.length); // Number of configured elements
```

### Python/Requests

```python
import requests

# Get all elements
response = requests.get('http://localhost:5000/api/lift/elements')
data = response.json()
print(f"Found {data['count']} elements")

# Get elements by category
response = requests.get('http://localhost:5000/api/lift/elements/category/entry')
entry_elements = response.json()
for elem in entry_elements['elements']:
    print(elem['display_name'])
```

---

## Integration with Display Profiles

The registry API is designed to support the Display Profile Editor UI:

1. **Profile Configuration:** Use `/elements/displayable` to populate element selection
2. **Category Filtering:** Use `/categories` and `/elements/category/{cat}` for organized display
3. **Visibility Options:** Use `/visibility-options` for dropdown menus
4. **Hierarchy Validation:** Use `/hierarchy` to validate parent-child relationships
5. **Default Profiles:** Use `/default-profile` as starting point for new profiles

---

## Versioning

Current version: **1.0**  
LIFT Specification: **0.13**  
Element coverage: **27/56** (48% - display-oriented elements only)

---

## See Also

- [LIFT Specification](https://github.com/sillsdev/lift-standard)
- [Display Profile Editor](CSS_EDITOR_SUBTASKS.md)
- [API Documentation (Swagger)](http://localhost:5000/apidocs/)
