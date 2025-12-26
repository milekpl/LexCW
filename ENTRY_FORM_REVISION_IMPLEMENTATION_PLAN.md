# Entry Form Revision Implementation Plan

## Overview

This document outlines the implementation plan for enhancing the entry form in the dictionary application. The plan addresses three key requirements:

1. **DELETE Button** - Add a delete button with warning for dictionary artifacts
2. **Sense-level Variant Relations** - Extend variant relations to work at the sense level
3. **Hierarchical Dropdowns** - Convert usage type and domain type to hierarchical dropdowns with multiple selection

## 1. DELETE Button for Dictionary Artifacts

### Location
- Top action bar in entry form, next to existing buttons
- Only visible when editing existing entries (not for new entries)

### Implementation Details

#### Frontend Changes
**File**: `app/templates/entry_form.html`

```html
<!-- Add to top action bar, after existing buttons -->
{% if entry.id %}
<button type="button" class="btn btn-outline-danger me-2" id="delete-entry-btn">
    <i class="fas fa-trash-alt"></i> DELETE ENTRY
</button>
<span class="text-danger small" id="delete-warning" style="display: none;">
    <i class="fas fa-exclamation-triangle"></i> This will permanently delete this entry!
</span>
{% endif %}
```

**JavaScript**: Add to entry form initialization
```javascript
document.getElementById('delete-entry-btn')?.addEventListener('click', function() {
    const warning = document.getElementById('delete-warning');
    if (warning.style.display === 'none') {
        warning.style.display = 'inline';
        this.textContent = 'CONFIRM DELETE';
        this.classList.remove('btn-outline-danger');
        this.classList.add('btn-danger');
    } else {
        // Proceed with deletion
        if (confirm('Are you sure you want to permanently delete this entry?')) {
            fetch(`/entries/${entryId}/delete`, {
                method: 'POST',
                headers: {
                    'X-CSRF-TOKEN': getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                if (response.ok) {
                    window.location.href = '/entries';
                } else {
                    alert('Failed to delete entry');
                }
            });
        }
    }
});
```

#### Backend Changes

**File**: `app/routes/main_routes.py`
```python
@app.route('/entries/<entry_id>/delete', methods=['POST'])
@login_required
def delete_entry(entry_id):
    """Delete an entry after confirmation."""
    try:
        entry_service = current_app.injector.get(EntryService)
        entry_service.delete_entry(entry_id)
        flash('Entry deleted successfully', 'success')
        return redirect(url_for('main.entries'))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('main.edit_entry', entry_id=entry_id))
    except Exception as e:
        current_app.logger.error(f"Failed to delete entry {entry_id}: {str(e)}")
        flash('An error occurred while deleting the entry', 'error')
        return redirect(url_for('main.edit_entry', entry_id=entry_id))
```

**File**: `app/services/entry_service.py`
```python
def delete_entry(self, entry_id: str) -> None:
    """Delete an entry from the database."""
    # Verify entry exists
    entry = self.get_entry(entry_id)
    if not entry:
        raise ValueError("Entry not found")
    
    # Check for dependencies (relations, components, etc.)
    if self._has_dependencies(entry_id):
        raise ValueError("Cannot delete entry that is referenced by other entries")
    
    # Delete from database
    self.database.delete_entry(entry_id)
    
    # Log the deletion
    self.logger.info(f"Entry {entry_id} deleted successfully")

def _has_dependencies(self, entry_id: str) -> bool:
    """Check if entry has dependencies that would prevent deletion."""
    # Check if this entry is referenced in relations
    relations = self.database.get_relations_by_target(entry_id)
    if relations:
        return True
    
    # Check if this entry is used as a component
    components = self.database.get_entries_by_component(entry_id)
    if components:
        return True
    
    return False
```

### Security Considerations

- Require login and proper permissions
- Add CSRF protection
- Implement dependency checking to prevent orphaned references
- Add logging for audit trail
- Consider soft delete option for safety

## 2. Variant Relations at Sense Level

### Current State
- Variant relations only exist at entry level
- Sense-level variant relations are not supported

### Implementation Details

#### Frontend Changes

**File**: `app/templates/entry_form.html` - Sense Template

```html
<!-- Add to sense template, after examples section -->
<div class="variant-relations-section mt-3">
    <div class="d-flex justify-content-between align-items-center mb-2">
        <h6><i class="fas fa-project-diagram"></i> Variant Relations</h6>
        <button type="button" class="btn btn-sm btn-outline-primary add-variant-relation-btn"
                data-sense-index="INDEX"
                title="Add variant relation for this sense">
            <i class="fas fa-plus"></i> Add Variant Relation
        </button>
    </div>
    
    <div class="variant-relations-container" data-sense-index="INDEX">
        <div class="no-variant-relations text-center text-muted py-2 border rounded">
            <p><small>No variant relations added for this sense</small></p>
        </div>
    </div>
</div>
```

**File**: Create new template for sense-level variant relations
```html
<template id="sense-variant-relation-template">
    <div class="variant-relation-item card mb-2 border-info" data-variant-relation-index="VARIANT_INDEX" data-sense-index="SENSE_INDEX">
        <div class="card-body p-2">
            <div class="row g-2">
                <div class="col-md-4">
                    <label class="form-label small">Relation Type</label>
                    <select class="form-select form-select-sm dynamic-lift-range variant-relation-type"
                            name="senses[SENSE_INDEX].variant_relations[VARIANT_INDEX].type"
                            data-range-id="variant-type">
                        <option value="">Select type</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label small">Target Entry</label>
                    <div class="input-group input-group-sm">
                        <input type="text" class="form-control variant-relation-target"
                               name="senses[SENSE_INDEX].variant_relations[VARIANT_INDEX].target"
                               placeholder="Search for entry...">
                        <button class="btn btn-outline-secondary search-variant-target-btn" type="button"
                                data-sense-index="SENSE_INDEX" data-variant-index="VARIANT_INDEX">
                            <i class="fas fa-search"></i>
                        </button>
                    </div>
                </div>
                <div class="col-md-2 d-flex align-items-end">
                    <button type="button" class="btn btn-sm btn-outline-danger remove-variant-relation-btn"
                            data-sense-index="SENSE_INDEX" data-variant-index="VARIANT_INDEX"
                            title="Remove this variant relation">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
```

#### JavaScript Changes

**File**: `app/static/js/variant-forms.js` - Extend for sense level

```javascript
class SenseVariantRelationsManager {
    constructor(containerSelector) {
        this.container = document.querySelector(containerSelector);
        this.variantRelations = [];
        this._setupEventListeners();
    }
    
    _setupEventListeners() {
        // Add variant relation button
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('add-variant-relation-btn')) {
                const senseIndex = e.target.dataset.senseIndex;
                this.addVariantRelation(senseIndex);
            }
        });
        
        // Remove variant relation button
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-variant-relation-btn')) {
                const senseIndex = e.target.dataset.senseIndex;
                const variantIndex = e.target.dataset.variantIndex;
                this.removeVariantRelation(senseIndex, variantIndex);
            }
        });
        
        // Search for target entry
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('search-variant-target-btn')) {
                const senseIndex = e.target.dataset.senseIndex;
                const variantIndex = e.target.dataset.variantIndex;
                this.searchVariantTarget(senseIndex, variantIndex);
            }
        });
    }
    
    addVariantRelation(senseIndex) {
        const template = document.getElementById('sense-variant-relation-template');
        const variantIndex = this._getNextVariantIndex(senseIndex);
        
        const html = template.innerHTML
            .replace(/SENSE_INDEX/g, senseIndex)
            .replace(/VARIANT_INDEX/g, variantIndex);
        
        const container = this.container.querySelector(`[data-sense-index="${senseIndex}"] .variant-relations-container`);
        
        // Remove empty state
        const emptyState = container.querySelector('.no-variant-relations');
        if (emptyState) emptyState.remove();
        
        // Add new relation
        container.insertAdjacentHTML('beforeend', html);
        
        // Initialize the variant type dropdown
        this._initializeVariantTypeDropdown(senseIndex, variantIndex);
        
        // Add to our tracking
        this.variantRelations.push({ senseIndex, variantIndex });
    }
    
    _initializeVariantTypeDropdown(senseIndex, variantIndex) {
        const select = document.querySelector(
            `[data-sense-index="${senseIndex}"][data-variant-relation-index="${variantIndex}"] .variant-relation-type`
        );
        
        if (window.rangesData && window.rangesData['variant-type']) {
            populateDropdownOptions(select, window.rangesData['variant-type'].values);
            $(select).select2({
                theme: 'bootstrap-5',
                placeholder: 'Select variant type',
                allowClear: true
            });
        }
    }
    
    searchVariantTarget(senseIndex, variantIndex) {
        // Implement search functionality similar to entry-level variant relations
        // This would open a modal to search for entries
        const modal = new EntrySearchModal((selectedEntry) => {
            const input = document.querySelector(
                `[data-sense-index="${senseIndex}"][data-variant-relation-index="${variantIndex}"] .variant-relation-target`
            );
            if (input) {
                input.value = selectedEntry.id;
                // Optionally show the entry's lexical unit for user reference
                input.placeholder = selectedEntry.lexical_unit;
            }
        });
        modal.show();
    }
    
    removeVariantRelation(senseIndex, variantIndex) {
        const relationElement = document.querySelector(
            `[data-sense-index="${senseIndex}"][data-variant-relation-index="${variantIndex}"]`
        );
        
        if (relationElement) {
            relationElement.remove();
            
            // Check if container is now empty
            const container = this.container.querySelector(`[data-sense-index="${senseIndex}"] .variant-relations-container`);
            if (container.children.length === 0) {
                container.innerHTML = `
                    <div class="no-variant-relations text-center text-muted py-2 border rounded">
                        <p><small>No variant relations added for this sense</small></p>
                    </div>
                `;
            }
        }
    }
    
    _getNextVariantIndex(senseIndex) {
        const existingRelations = this.container.querySelectorAll(
            `[data-sense-index="${senseIndex}"] .variant-relation-item`
        );
        return existingRelations.length;
    }
}

// Initialize in entry form setup
document.addEventListener('DOMContentLoaded', function() {
    if (window.SenseVariantRelationsManager) {
        window.senseVariantRelationsManager = new SenseVariantRelationsManager('#senses-container');
    }
});
```

#### Backend Changes

**File**: `app/models/sense.py` - Add variant relations support
```python
class Sense:
    # ... existing code ...
    
    def __init__(self, **kwargs):
        self.variant_relations = kwargs.get('variant_relations', [])
        # ... rest of initialization ...
    
    def add_variant_relation(self, relation_type: str, target_entry_id: str) -> None:
        """Add a variant relation to this sense."""
        self.variant_relations.append({
            'type': relation_type,
            'target': target_entry_id
        })
    
    def remove_variant_relation(self, target_entry_id: str) -> bool:
        """Remove a variant relation from this sense."""
        original_count = len(self.variant_relations)
        self.variant_relations = [
            rel for rel in self.variant_relations 
            if rel.get('target') != target_entry_id
        ]
        return len(self.variant_relations) < original_count
```

**File**: `app/services/sense_service.py` - Handle sense-level variant relations
```python
def update_sense_variant_relations(self, sense_id: str, variant_relations: list) -> None:
    """Update variant relations for a sense."""
    sense = self.get_sense(sense_id)
    if not sense:
        raise ValueError(f"Sense {sense_id} not found")
    
    # Clear existing relations
    sense.variant_relations = []
    
    # Add new relations
    for relation in variant_relations:
        sense.add_variant_relation(
            relation.get('type'),
            relation.get('target')
        )
    
    # Save changes
    self.database.update_sense(sense)
```

### XML Serialization

**File**: `app/static/js/lift-xml-serializer.js`
```javascript
// Add to sense serialization
function serializeSense(sense, senseIndex) {
    const senseElement = createElement('sense');
    
    // ... existing sense serialization ...
    
    // Add variant relations
    if (sense.variant_relations && sense.variant_relations.length > 0) {
        sense.variant_relations.forEach(relation => {
            const relationElement = createElement('relation');
            relationElement.setAttribute('type', relation.type);
            relationElement.setAttribute('ref', relation.target);
            senseElement.appendChild(relationElement);
        });
    }
    
    return senseElement;
}
```

## 3. Hierarchical Dropdowns for Usage Type and Domain Type

### Current State
- Semantic domain has hierarchical support with multiple selection
- Usage type and domain type use basic dropdowns
- No consistent approach across similar fields

### Implementation Details

#### Frontend Changes

**File**: `app/templates/entry_form.html` - Update existing dropdowns

```html
<!-- Replace existing usage-type dropdown -->
<div class="mb-3">
    <label class="form-label">Usage Type</label>
    <select class="form-select dynamic-lift-range hierarchical-multiple-select"
            name="senses[INDEX].usage_type"
            data-range-id="usage-type"
            data-hierarchical="true"
            data-searchable="true"
            data-placeholder="Select usage type(s)"
            multiple>
        <option value="">Select usage type(s)</option>
    </select>
    <div class="form-text">Usage classification for this sense (can select multiple).</div>
</div>

<!-- Replace existing domain-type dropdown -->
<div class="mb-3">
    <label class="form-label">Domain type</label>
    <select class="form-select dynamic-lift-range hierarchical-multiple-select"
            name="senses[INDEX].domain_type"
            data-range-id="domain-type"
            data-hierarchical="true"
            data-searchable="true"
            data-placeholder="Select domain(s)"
            multiple>
        <option value="">Select domain</option>
    </select>
    <div class="form-text">Academic or disciplinary domain this sense belongs to.</div>
</div>
```

#### JavaScript Changes

**File**: `app/static/js/ranges-loader.js` - Add hierarchical multiple select support

```javascript
// Add to existing ranges loader initialization
function initializeHierarchicalMultipleSelects() {
    document.querySelectorAll('.hierarchical-multiple-select').forEach(select => {
        const rangeId = select.dataset.rangeId;
        
        if (window.rangesData && window.rangesData[rangeId]) {
            // Populate hierarchical options
            populateHierarchicalOptions(select, window.rangesData[rangeId].values);
            
            // Initialize Select2 with hierarchical support
            $(select).select2({
                theme: 'bootstrap-5',
                placeholder: select.dataset.placeholder || 'Select options',
                allowClear: true,
                closeOnSelect: false,  // Allow multiple selections
                templateResult: formatHierarchicalOption,
                templateSelection: formatHierarchicalSelection
            });
        } else {
            console.warn(`Range data not found for: ${rangeId}`);
            // Fallback to basic select
            $(select).select2({
                theme: 'bootstrap-5',
                placeholder: select.dataset.placeholder || 'Select options',
                allowClear: true
            });
        }
    });
}

function populateHierarchicalOptions(select, values) {
    // Clear existing options (except placeholder)
    const placeholderOption = select.querySelector('option[value=""]');
    select.innerHTML = '';
    if (placeholderOption) {
        select.appendChild(placeholderOption);
    }
    
    // Add hierarchical options
    addHierarchicalOptions(select, values, '');
}

function addHierarchicalOptions(select, values, indent) {
    values.forEach(value => {
        const option = document.createElement('option');
        option.value = value.id;
        option.textContent = indent + value.label;
        option.dataset.hierarchy = value.hierarchy || '';
        select.appendChild(option);
        
        // Add child options if they exist
        if (value.children && value.children.length > 0) {
            addHierarchicalOptions(select, value.children, indent + '  ');
        }
    });
}

function formatHierarchicalOption(option) {
    if (!option.id) return option.text;  // Return placeholder text
    
    const $option = $(
        `<span class="hierarchical-option">${option.text}</span>`
    );
    
    // Add hierarchy indicator if this has children
    if (option.element && option.element.dataset.childrenCount > 0) {
        $option.prepend('<i class="fas fa-folder me-2"></i>');
    }
    
    return $option;
}

function formatHierarchicalSelection(option) {
    if (!option.id) return option.text;  // Return placeholder text
    
    // Show just the label without hierarchy indicators
    return option.text.trim();
}

// Call this during form initialization
document.addEventListener('DOMContentLoaded', function() {
    initializeHierarchicalMultipleSelects();
});
```

#### Form Serialization

**File**: `app/static/js/form-serializer.js` - Handle multiple selections

```javascript
// Extend existing serializeForm function
function serializeForm(form) {
    const formData = new FormData(form);
    
    // Handle multiple select fields
    const multipleSelects = form.querySelectorAll('select[multiple]');
    multipleSelects.forEach(select => {
        const name = select.name;
        const selectedOptions = Array.from(select.selectedOptions).map(option => option.value);
        
        if (selectedOptions.length > 0) {
            // Remove any existing single values
            formData.delete(name);
            
            // Add all selected values
            selectedOptions.forEach(value => {
                formData.append(name, value);
            });
        }
    });
    
    return formData;
}

// For XML serialization
function serializeMultipleSelectsForXml(formData, xmlElement, fieldName) {
    const values = formData.getAll(fieldName);
    if (values && values.length > 0) {
        values.forEach(value => {
            const traitElement = createElement('trait');
            traitElement.setAttribute('name', fieldName);
            traitElement.setAttribute('value', value);
            xmlElement.appendChild(traitElement);
        });
    }
}
```

#### Backend Changes

**File**: `app/models/sense.py` - Handle multiple values
```python
class Sense:
    def __init__(self, **kwargs):
        # Handle multiple values for usage_type and domain_type
        self.usage_type = kwargs.get('usage_type', [])
        self.domain_type = kwargs.get('domain_type', [])
        
        # Ensure they are lists
        if isinstance(self.usage_type, str):
            self.usage_type = [self.usage_type]
        if isinstance(self.domain_type, str):
            self.domain_type = [self.domain_type]
    
    def add_usage_type(self, usage_type: str) -> None:
        """Add a usage type to this sense."""
        if usage_type and usage_type not in self.usage_type:
            self.usage_type.append(usage_type)
    
    def add_domain_type(self, domain_type: str) -> None:
        """Add a domain type to this sense."""
        if domain_type and domain_type not in self.domain_type:
            self.domain_type.append(domain_type)
```

**File**: `app/services/sense_service.py` - Update handling
```python
def update_sense_fields(self, sense_id: str, field_data: dict) -> None:
    """Update various fields for a sense."""
    sense = self.get_sense(sense_id)
    if not sense:
        raise ValueError(f"Sense {sense_id} not found")
    
    # Handle usage_type
    if 'usage_type' in field_data:
        usage_types = field_data['usage_type']
        if isinstance(usage_types, str):
            usage_types = [usage_types]
        sense.usage_type = usage_types
    
    # Handle domain_type
    if 'domain_type' in field_data:
        domain_types = field_data['domain_type']
        if isinstance(domain_types, str):
            domain_types = [domain_types]
        sense.domain_type = domain_types
    
    # Save changes
    self.database.update_sense(sense)
```

## Implementation Priority and Timeline

### Phase 1: DELETE Button (High Priority - Safety Feature)
- **Duration**: 2-3 days
- **Tasks**:
  - Add frontend button and warning
  - Implement backend endpoint
  - Add dependency checking
  - Implement logging and security
  - Write tests

### Phase 2: Hierarchical Dropdowns (Medium Priority - UX Improvement)
- **Duration**: 3-4 days
- **Tasks**:
  - Update frontend markup
  - Extend JavaScript for hierarchical support
  - Update form serialization
  - Modify backend models and services
  - Write tests and validate XML output

### Phase 3: Sense-level Variant Relations (Lower Priority - Feature Enhancement)
- **Duration**: 4-5 days
- **Tasks**:
  - Add frontend UI to sense template
  - Extend JavaScript managers
  - Update backend models and services
  - Implement XML serialization
  - Write comprehensive tests

## Testing Strategy

### Unit Tests
- DELETE button functionality
- Dependency checking logic
- Hierarchical dropdown rendering
- Multiple selection handling
- Sense-level variant relations serialization

### Integration Tests
- DELETE endpoint with various scenarios
- Form submission with hierarchical selections
- XML generation with new fields
- Database updates for new features

### End-to-End Tests
- Complete workflow for deleting entries
- Sense editing with new hierarchical fields
- Variant relations at sense level
- Data consistency across operations

## Risk Assessment and Mitigation

### DELETE Button Risks
- **Risk**: Accidental data loss
- **Mitigation**: 
  - Two-step confirmation process
  - Dependency checking
  - Comprehensive logging
  - Permission requirements
  - Consider soft-delete option

### Hierarchical Dropdowns Risks
- **Risk**: Breaking existing functionality
- **Mitigation**:
  - Maintain backward compatibility
  - Extensive testing of existing features
  - Feature flags for gradual rollout
  - Clear documentation

### Sense-level Variant Relations Risks
- **Risk**: Complexity and performance impact
- **Mitigation**:
  - Reuse existing code patterns
  - Performance testing with large datasets
  - Clear user interface guidance
  - Comprehensive error handling

## Success Criteria

1. **DELETE Button**: 
   - Users can delete entries with proper confirmation
   - System prevents deletion of referenced entries
   - All deletions are logged for audit purposes

2. **Hierarchical Dropdowns**:
   - Usage type and domain type support hierarchical selection
   - Multiple selections are properly saved and displayed
   - XML output is valid and consistent
   - Performance is acceptable with large hierarchies

3. **Sense-level Variant Relations**:
   - Users can add variant relations at sense level
   - Relations are properly serialized to XML
   - Search functionality works correctly
   - Data integrity is maintained

## Documentation Requirements

- Update user documentation for new features
- Add developer documentation for new code
- Update API documentation for new endpoints
- Create examples and tutorials
- Update help text in the UI

## Monitoring and Maintenance

- Monitor usage of new features
- Track any errors or issues
- Gather user feedback
- Plan for iterative improvements
- Schedule regular maintenance

This comprehensive plan provides a clear roadmap for implementing the requested enhancements while maintaining code quality, ensuring backward compatibility, and minimizing risks.