# Implementation Plan: Full LIFT Support for Allomorphs and Header Information

## Background

After analyzing the LIFT 0.13 schema and current parser implementation, I identified gaps in handling direct variant elements (allomorphs) and header information from LIFT files.

## Current State Assessment

### What's Working
- **LIFTRangesParser**: Separate range file parsing is implemented and well-tested
- **Basic Variant Parsing**: LIFT `<variant>` elements with basic form content are parsed
- **UI Support**: Entry form has JavaScript-based variant management
- **Model Support**: `Variant` model exists with `form` and `grammatical_traits`

### What's Missing
1. **Direct Trait Support in Variants**: Traits directly inside `<variant>` elements (like `<trait name="morph-type" value="stem"/>`) are not parsed
2. **Header Information**: LIFT file header metadata is not supported
3. **UI Integration**: LIFT-style variants with traits are not fully integrated into the entry form UI

### Example of Missing Functionality
```xml
<variant>
  <form lang="en"><text>grass roots</text></form>
  <trait name="morph-type" value="stem"/>
</variant>
```

The current parser handles the form content but misses the `morph-type` trait.

## Implementation Tasks

### 1. Enhance Parser to Handle Direct Traits in Variants
**File**: `app/parsers/lift_parser.py`
**Function**: `_parse_entry()` in the variant parsing section

```python
# Current code only handles traits within grammatical-info
# Need to add support for direct trait elements within variant
for trait_elem in self._find_elements(variant_elem, './lift:trait', './trait'):
    trait_name = trait_elem.get('name')
    trait_value = trait_elem.get('value')
    if trait_name and trait_value:
        # Add to variant traits, not just grammatical_traits
        if not hasattr(variant, 'traits') or variant.traits is None:
            variant.traits = {}
        variant.traits[trait_name] = trait_value
```

### 2. Add Header Information Parser
**File**: `app/parsers/lift_parser.py`
**New Function**: `_parse_header()` method in `LIFTParser` class

```python
def _parse_header(self, lift_root: ET.Element) -> Dict[str, Any]:
    header_elem = self._find_element(lift_root, './lift:header', './header')
    if header_elem is None:
        return {}
    
    header_data = {}
    
    # Parse description
    description = {}
    for desc_elem in self._find_elements(header_elem, './lift:description', './description'):
        lang = desc_elem.get('lang')
        text_elem = self._find_element(desc_elem, './lift:text', './text')
        if lang and text_elem is not None and text_elem.text:
            description[lang] = text_elem.text
    header_data['description'] = description if description else {}
    
    # Parse ranges reference (just the href to external range files)
    ranges_elem = self._find_element(header_elem, './lift:ranges', './ranges')
    if ranges_elem is not None:
        href = ranges_elem.get('href')
        if href:
            header_data['ranges_href'] = href
    
    # Parse fields
    fields_elem = self._find_element(header_elem, './lift:fields', './fields')
    if fields_elem is not None:
        fields = []
        for field_elem in self._find_elements(fields_elem, './lift:field', './field'):
            field_type = field_elem.get('type')
            if field_type:
                field_data = {'type': field_type}
                # Parse field description, etc.
                fields.append(field_data)
        header_data['fields'] = fields
    
    return header_data
```

### 3. Update Entry Model to Support Header Data
**File**: `app/models/entry.py`
**Add new fields to Entry class**:
- `header_info: Optional[Dict]` - to store header metadata from LIFT files

### 4. Enhance UI to Show/Handle Allomorphs with Traits
**File**: `app/templates/entry_form.html`
- Add a dedicated section for "Direct Variants" (LIFT `<variant>` elements with forms and traits)
- Separate from the current "Variant Relations" (which are entry-to-entry relationships)
- Create form elements that allow editing of variant forms and their associated traits

**File**: `static/js/variant-forms.js`
- Extend the current manager to handle direct variant forms with traits
- Add UI controls for adding/removing traits on variant forms

### 5. Update Form Processor to Handle LIFT Variants
**File**: `app/utils/multilingual_form_processor.py`
- Modify to handle direct variant forms with traits during form processing
- Ensure that both types of variants (direct forms and relations) are properly handled

### 6. Update Serialization Logic
**File**: `app/serializers/entry_serializer.py` (or similar)
- Ensure that variants with traits are properly serialized and deserialized
- Handle both the `grammatical_traits` and direct `traits` in variants

## Implementation Priority

### Phase 1 (Critical)
1. Enhance parser to handle direct traits in variants
2. Add header information parser

### Phase 2 (UI Enhancement)  
3. Update UI to support direct variant forms with traits
4. Update JavaScript variant manager

### Phase 3 (Integration & Testing)
5. Update form processor
6. Update serialization logic
7. Add comprehensive tests for all new functionality
8. Verify proper round-trip import/export of LIFT files

## Expected Outcomes

After implementation:
- LIFT files with `<variant><form>...<trait name="morph-type" value="stem"/></variant>` will be properly parsed
- Header metadata will be extracted and preserved from LIFT imports
- UI will support entering both relation-based variants and direct form-based variants
- Full compatibility with LIFT 0.13 specification for variants and header information

This plan addresses the core issue: the current implementation handles variants as inter-entry relations rather than as direct LIFT `<variant>` elements with embedded traits, which is what's needed to properly support allomorphs as defined in the LIFT specification.
