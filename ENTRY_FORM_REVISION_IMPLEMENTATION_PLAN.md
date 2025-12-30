# Entry Form Revision Implementation Plan

## Overview

This document outlines the implementation plan for enhancing the entry form in the dictionary application. The plan addresses four key requirements:

1. **DELETE Button** - Add a delete button with warning for dictionary artifacts
2. **Sense-level Variant Relations** - Extend variant relations to work at the sense level
3. **Hierarchical Dropdowns** - Convert usage type and domain type to hierarchical dropdowns with multiple selection
4. **Refactor Field Visibility Modal** - Extract from inline HTML, connect via proper JS architecture

---

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

---

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

---

## 3. Hierarchical Dropdowns for Usage Type and Domain Type

### Current State
- Semantic domain has hierarchical support with multiple selection
- Usage type and domain type use basic dropdowns
- No consistent approach across similar fields
- Domain type `multiple` attribute exists but no proper hierarchical UI

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

---

## 4. Refactor Field Visibility Modal

### Current Issues

1. **Inline HTML** - Modal is embedded directly in `entry_form.html` (lines 1410-1495)
2. **No JavaScript Connection** - Checkboxes have `data-target` attributes but no JS to handle them
3. **No State Management** - Settings are not saved or loaded from backend
4. **Not Reusable** - Cannot be used across different forms

### Solution Overview

Create a modular, event-driven approach:
1. Extract modal to reusable macro template
2. Create `FieldVisibilityManager` class with proper API
3. Integrate with display profiles/settings system
4. Use CustomEvents for component communication

### Implementation Steps

#### Step 4.1: Extract Modal to Macro Template

**New File**: `app/templates/macros/field_visibility_modal.html`

```html
{% macro field_visibility_modal(modal_id='fieldVisibilityModal', sections=None) %}
{% if sections is None %}
{% set sections = [
    {'id': 'basic-info', 'label': 'Basic Information', 'target': '.basic-info-section'},
    {'id': 'custom-fields', 'label': 'Custom Fields', 'target': '.custom-fields-section'},
    {'id': 'notes', 'label': 'Entry Notes', 'target': '.notes-section'},
    {'id': 'pronunciation', 'label': 'Pronunciation', 'target': '.pronunciation-section'},
    {'id': 'variants', 'label': 'Variants', 'target': '.variants-section'},
    {'id': 'direct-variants', 'label': 'Direct Variants', 'target': '.direct-variants-section'},
    {'id': 'relations', 'label': 'Relations', 'target': '.relations-section'},
    {'id': 'senses', 'label': 'Senses & Definitions', 'target': '.senses-section'},
] %}
{% endif %}
<div class="modal fade" id="{{ modal_id }}" tabindex="-1" aria-labelledby="{{ modal_id }}Label" aria-hidden="true">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="{{ modal_id }}Label">
                    <i class="fas fa-cog"></i> Field Visibility Settings
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <p class="text-muted mb-4">
                    Control which field sections are visible in the entry form. Settings are saved automatically.
                </p>

                <div class="row">
                    {% for section in sections %}
                    <div class="col-md-6">
                        <div class="form-check mb-2">
                            <input class="form-check-input field-visibility-toggle"
                                   type="checkbox"
                                   id="show-{{ section.id }}"
                                   data-section-id="{{ section.id }}"
                                   data-target="{{ section.target }}"
                                   checked>
                            <label class="form-check-label" for="show-{{ section.id }}">
                                {{ section.label }}
                            </label>
                        </div>
                    </div>
                    {% endfor %}
                </div>

                <hr class="my-4">

                <div class="d-flex justify-content-between">
                    <button type="button" class="btn btn-outline-secondary reset-field-visibility-btn">
                        <i class="fas fa-undo"></i> Reset to Defaults
                    </button>
                    <div>
                        <button type="button" class="btn btn-outline-primary hide-empty-sections-btn">
                            <i class="fas fa-eye-slash"></i> Hide Empty Sections
                        </button>
                        <button type="button" class="btn btn-outline-primary show-all-sections-btn">
                            <i class="fas fa-eye"></i> Show All Sections
                        </button>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>
{% endmacro %}
```

#### Step 4.2: Create Field Visibility Manager

**New File**: `app/static/js/field-visibility-manager.js`

```javascript
/**
 * FieldVisibilityManager - Handles field visibility settings for forms
 * Uses event-driven architecture for component communication
 */
class FieldVisibilityManager {
    constructor(options = {}) {
        this.options = {
            storageKey: 'fieldVisibilitySettings',
            defaultSettings: {
                'basic-info': true,
                'custom-fields': true,
                'notes': true,
                'pronunciation': true,
                'variants': true,
                'direct-variants': true,
                'relations': true,
                'senses': true
            },
            onChange: null,  // Callback when visibility changes
            ...options
        };

        this.settings = this._loadSettings();
        this._setupEventListeners();
        this._applySettings();
    }

    /**
     * Load settings from localStorage or use defaults
     */
    _loadSettings() {
        try {
            const stored = localStorage.getItem(this.options.storageKey);
            if (stored) {
                return { ...this.options.defaultSettings, ...JSON.parse(stored) };
            }
        } catch (e) {
            console.warn('Failed to load field visibility settings:', e);
        }
        return { ...this.options.defaultSettings };
    }

    /**
     * Save settings to localStorage
     */
    _saveSettings() {
        try {
            localStorage.setItem(this.options.storageKey, JSON.stringify(this.settings));
        } catch (e) {
            console.warn('Failed to save field visibility settings:', e);
        }
    }

    /**
     * Set up event listeners using event delegation
     */
    _setupEventListeners() {
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('field-visibility-toggle')) {
                this._handleToggleChange(e.target);
            }
        });

        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('reset-field-visibility-btn')) {
                this._resetToDefaults();
            } else if (e.target.classList.contains('hide-empty-sections-btn')) {
                this._hideEmptySections();
            } else if (e.target.classList.contains('show-all-sections-btn')) {
                this._showAllSections();
            }
        });
    }

    /**
     * Handle checkbox toggle change
     */
    _handleToggleChange(checkbox) {
        const sectionId = checkbox.dataset.sectionId;
        const isVisible = checkbox.checked;

        this.setSectionVisibility(sectionId, isVisible);
    }

    /**
     * Set visibility for a specific section
     */
    setSectionVisibility(sectionId, visible) {
        this.settings[sectionId] = visible;
        this._saveSettings();

        // Find all elements with the target selector
        const checkboxes = document.querySelectorAll(`[data-section-id="${sectionId}"]`);
        checkboxes.forEach(checkbox => {
            checkbox.checked = visible;
        });

        // Apply visibility to target elements
        const targetSelector = checkboxes[0]?.dataset.target;
        if (targetSelector) {
            const targetElements = document.querySelectorAll(targetSelector);
            targetElements.forEach(el => {
                el.style.display = visible ? '' : 'none';
            });
        }

        // Emit change event for other components
        this._emitChangeEvent(sectionId, visible);

        // Call onChange callback
        if (typeof this.options.onChange === 'function') {
            this.options.onChange(sectionId, visible, this.settings);
        }
    }

    /**
     * Apply all settings to the DOM
     */
    _applySettings() {
        Object.entries(this.settings).forEach(([sectionId, isVisible]) => {
            this.setSectionVisibility(sectionId, isVisible);
        });
    }

    /**
     * Reset all settings to defaults
     */
    _resetToDefaults() {
        this.settings = { ...this.options.defaultSettings };
        this._saveSettings();
        this._applySettings();
    }

    /**
     * Hide sections that have no content
     */
    _hideEmptySections() {
        const sections = document.querySelectorAll('[class*="-section"]');
        sections.forEach(section => {
            const isEmpty = section.querySelectorAll('input, textarea, select').length === 0 ||
                           Array.from(section.querySelectorAll('input, textarea, select'))
                               .every(input => !input.value);
            if (isEmpty) {
                const sectionId = Object.entries(this.settings).find(
                    ([_, target]) => section.classList.contains(target.replace('.', ''))
                )?.[0];
                if (sectionId) {
                    this.setSectionVisibility(sectionId, false);
                }
            }
        });
    }

    /**
     * Show all sections
     */
    _showAllSections() {
        Object.keys(this.settings).forEach(sectionId => {
            this.setSectionVisibility(sectionId, true);
        });
    }

    /**
     * Emit CustomEvent for other components
     */
    _emitChangeEvent(sectionId, isVisible) {
        const event = new CustomEvent('fieldVisibilityChanged', {
            detail: {
                sectionId,
                isVisible,
                allSettings: this.settings
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * Get current settings
     */
    getSettings() {
        return { ...this.settings };
    }

    /**
     * Update settings programmatically
     */
    updateSettings(newSettings) {
        this.settings = { ...this.settings, ...newSettings };
        this._saveSettings();
        this._applySettings();
    }
}

// Export for use in other modules
window.FieldVisibilityManager = FieldVisibilityManager;
```

#### Step 4.3: Update entry_form.html to Use Macro

**File**: `app/templates/entry_form.html`

Replace the inline modal (lines 1410-1495) with:

```html
{% import "macros/field_visibility_modal.html" as field_visibility_modal %}
{{ field_visibility_modal.field_visibility_modal() }}
```

#### Step 4.4: Initialize Manager in entry_form Setup

**File**: `app/static/js/entry_form_setup.js` (or add to main JS initialization)

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Field Visibility Manager
    if (typeof FieldVisibilityManager !== 'undefined') {
        window.fieldVisibilityManager = new FieldVisibilityManager({
            storageKey: 'entryFormFieldVisibility'
            // Note: Visibility changes do NOT trigger auto-save or validation
            // since they only affect UI display preferences, not form data
        });

        // Listen for events from other components
        document.addEventListener('fieldVisibilityChanged', (e) => {
            console.log('Visibility changed:', e.detail);
        });
    }
});
```

### Current Limitations & Future Enhancements

The current implementation has the following known limitations that should be addressed in future iterations:

1. **Coarse-Grained Visibility Control**
   - **Current**: Only entire sections can be shown/hidden
   - **Future Enhancement**: Allow per-field visibility control within sections (e.g., hide only "grammatical info" within Basic Information, but keep lexical unit visible)
   - **Implementation**: Add `data-field-id` attributes to individual fields, update FieldVisibilityManager to support field-level targeting

2. **Local Storage Only**
   - **Current**: Settings stored in browser's localStorage
   - **Future Enhancement**: Store visibility preferences in project settings/database
   - **Implementation**:
     - Add API endpoint to save/load user preferences per project
     - Update FieldVisibilityManager to use backend API instead of localStorage
     - Add user preference model and service methods

3. **Section Definitions in Template**
   - **Current**: Section definitions hardcoded in macro
   - **Future Enhancement**: Load section definitions dynamically from configuration
   - **Implementation**: Add section definitions to project settings or a configuration file

4. **No Per-Project Settings**
   - **Current**: Same visibility settings apply to all projects
   - **Future Enhancement**: Different visibility preferences per project
   - **Implementation**: Include project_id in storage key or API requests

---

## 5. Refactor JavaScript Architecture (No DOM Scraping)

### Current Issues

1. **Inline Scripts** - Many inline `<script>` blocks in templates
2. **DOM Scraping** - Querying DOM elements directly throughout code
3. **No Communication** - Components don't communicate with each other
4. **Mixed Concerns** - UI logic mixed with business logic

### Solution: Event-Driven Communication Pattern

#### Step 5.1: Create Form Event Bus

**New File**: `app/static/js/form-event-bus.js`

```javascript
/**
 * FormEventBus - Central event bus for form component communication
 * Replaces direct DOM scraping with event-driven communication
 */
class FormEventBus {
    constructor() {
        this.listeners = new Map();
        this.eventHistory = [];
        this.maxHistoryLength = 50;
    }

    /**
     * Subscribe to an event
     */
    on(eventType, callback, options = {}) {
        if (!this.listeners.has(eventType)) {
            this.listeners.set(eventType, []);
        }

        const listener = {
            callback,
            once: options.once || false,
            priority: options.priority || 0
        };

        this.listeners.get(eventType).push(listener);

        // Sort by priority (higher priority runs first)
        this.listeners.get(eventType).sort((a, b) => b.priority - a.priority);

        // Return unsubscribe function
        return () => this.off(eventType, callback);
    }

    /**
     * Subscribe to an event once
     */
    once(eventType, callback, options = {}) {
        return this.on(eventType, callback, { ...options, once: true });
    }

    /**
     * Unsubscribe from an event
     */
    off(eventType, callback) {
        if (this.listeners.has(eventType)) {
            const listeners = this.listeners.get(eventType);
            const index = listeners.findIndex(l => l.callback === callback);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        }
    }

    /**
     * Emit an event
     */
    emit(eventType, data = {}) {
        const event = {
            type: eventType,
            data,
            timestamp: Date.now(),
            target: null  // Will be set by the emitter
        };

        this.eventHistory.push(event);
        if (this.eventHistory.length > this.maxHistoryLength) {
            this.eventHistory.shift();
        }

        if (this.listeners.has(eventType)) {
            const listeners = this.listeners.get(eventType);
            listeners.forEach(listener => {
                try {
                    listener.callback(event, this);
                } catch (error) {
                    console.error(`Error in event listener for ${eventType}:`, error);
                }
            });

            // Remove once listeners
            const onceListeners = listeners.filter(l => l.once);
            onceListeners.forEach(l => {
                this.off(eventType, l.callback);
            });
        }

        return event;
    }

    /**
     * Get event history
     */
    getHistory(eventType = null) {
        if (eventType) {
            return this.eventHistory.filter(e => e.type === eventType);
        }
        return [...this.eventHistory];
    }

    /**
     * Clear all listeners
     */
    reset() {
        this.listeners.clear();
        this.eventHistory = [];
    }
}

// Singleton instance
window.formEventBus = new FormEventBus();
```

#### Step 5.2: Create Base Component Class

**New File**: `app/static/js/form-component.js`

```javascript
/**
 * Base class for form components
 * Provides event-driven communication and state management
 */
class FormComponent {
    constructor(name, options = {}) {
        this.name = name;
        this.options = {
            eventBus: window.formEventBus,
            ...options
        };

        this.state = {};
        this._boundMethods = new Map();
    }

    /**
     * Get the event bus
     */
    get eventBus() {
        return this.options.eventBus || window.formEventBus;
    }

    /**
     * Subscribe to an event
     */
    on(eventType, callback, options = {}) {
        return this.eventBus.on(`${this.name}:${eventType}`, callback, options);
    }

    /**
     * Subscribe once to an event
     */
    once(eventType, callback, options = {}) {
        return this.once(eventType, callback, { ...options, once: true });
    }

    /**
     * Emit an event
     */
    emit(eventType, data = {}) {
        return this.eventBus.emit(`${this.name}:${eventType}`, {
            ...data,
            component: this.name
        });
    }

    /**
     * Update component state
     */
    setState(newState) {
        const oldState = { ...this.state };
        this.state = { ...this.state, ...newState };

        // Emit state change event
        this.emit('stateChanged', {
            oldState,
            newState: this.state,
            changedKeys: Object.keys(newState)
        });
    }

    /**
     * Get current state
     */
    getState(key = null) {
        if (key) {
            return this.state[key];
        }
        return { ...this.state };
    }

    /**
     * Bind a method to preserve 'this' context
     */
    bind(method) {
        if (!this._boundMethods.has(method)) {
            this._boundMethods.set(method, method.bind(this));
        }
        return this._boundMethods.get(method);
    }

    /**
     * Initialize the component (override in subclasses)
     */
    init() {
        console.warn(`Component ${this.name} should implement init()`);
    }

    /**
     * Destroy the component and clean up
     */
    destroy() {
        this.eventBus.off(`${this.name}:*`);
        this._boundMethods.clear();
        this.state = {};
    }
}

// Export
window.FormComponent = FormComponent;
```

#### Step 5.3: Refactor Existing Components

Example: Refactor Pronunciation Manager

**Before** (scattered DOM queries):
```javascript
document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('pronunciation-container');
    container.querySelectorAll('.remove-pronunciation-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove pronunciation...
        });
    });
});
```

**After** (event-driven):
```javascript
class PronunciationFormsManager extends FormComponent {
    constructor(containerSelector, options = {}) {
        super('pronunciation', options);
        this.container = document.querySelector(containerSelector);
        this.bindMethods();
        this.init();
    }

    bindMethods() {
        this.handleAdd = this.bind(this.handleAdd);
        this.handleRemove = this.bind(this.handleRemove);
    }

    init() {
        // Subscribe to events
        this.on('add', this.handleAdd);
        this.on('remove', this.handleRemove);

        // Listen for form submission events
        this.eventBus.on('form:submitting', this.handleFormSubmitting.bind(this));

        // Set up direct listeners for immediate actions
        this.setupListeners();

        // Emit ready event
        this.emit('ready', { count: this.getPronunciationCount() });
    }

    setupListeners() {
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('add-pronunciation-btn')) {
                this.emit('add');
            } else if (e.target.classList.contains('remove-pronunciation-btn')) {
                const index = e.target.dataset.index;
                this.emit('remove', { index });
            }
        });
    }

    handleAdd() {
        // Add pronunciation logic...
        this.emit('added', { index: newIndex });
    }

    handleRemove(data) {
        // Remove pronunciation logic...
        this.emit('removed', { index: data.index });
    }

    getPronunciationCount() {
        return this.container.querySelectorAll('.pronunciation-item').length;
    }
}
```

---

## 6. Form State Management Integration

### Overview

Create a unified state store that:
1. Tracks all form field changes
2. Provides undo/redo functionality
3. Syncs with server via auto-save
4. Broadcasts changes to all components

**File**: `app/static/js/form-state-manager.js` (already exists, enhance)

```javascript
/**
 * Enhanced FormStateManager with event-driven architecture
 */
class FormStateManager extends FormComponent {
    constructor(formSelector, options = {}) {
        super('formState', options);

        this.form = document.querySelector(formSelector);
        this.history = [];
        this.historyIndex = -1;
        this.maxHistoryLength = 50;
        this.ignoreNextChange = false;

        this.init();
    }

    init() {
        this.setupFormListeners();
        this.setupEventListeners();
        this.saveState('initial');
    }

    setupFormListeners() {
        this.form.addEventListener('input', (e) => {
            if (this.ignoreNextChange) return;

            // Debounce state saves
            clearTimeout(this.inputTimeout);
            this.inputTimeout = setTimeout(() => {
                this.saveState('input');
            }, 500);
        });

        this.form.addEventListener('change', (e) => {
            if (this.ignoreNextChange) return;
            this.saveState('change');
        });
    }

    setupEventListeners() {
        // Listen for undo/redo commands
        this.on('undo', () => this.undo());
        this.on('redo', () => this.redo());

        // Listen for field visibility changes
        this.eventBus.on('fieldVisibilityChanged', (e) => {
            this.saveState('fieldVisibility');
        });

        // Listen for sense additions/removals
        this.eventBus.on('sense:added', () => this.saveState('senseAdded'));
        this.eventBus.on('sense:removed', () => this.saveState('senseRemoved'));
    }

    saveState(reason = 'unknown') {
        const formData = new FormData(this.form);
        const state = {
            formData: Object.fromEntries(formData.entries()),
            timestamp: Date.now(),
            reason
        };

        // Remove future history if we're not at the end
        if (this.historyIndex < this.history.length - 1) {
            this.history = this.history.slice(0, this.historyIndex + 1);
        }

        this.history.push(state);

        // Limit history length
        if (this.history.length > this.maxHistoryLength) {
            this.history.shift();
        } else {
            this.historyIndex++;
        }

        this.emit('stateSaved', {
            state,
            historyIndex: this.historyIndex,
            historyLength: this.history.length
        });
    }

    undo() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.restoreState(this.history[this.historyIndex]);
            this.emit('undone', { historyIndex: this.historyIndex });
        }
    }

    redo() {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            this.restoreState(this.history[this.historyIndex]);
            this.emit('redone', { historyIndex: this.historyIndex });
        }
    }

    restoreState(state) {
        this.ignoreNextChange = true;

        // Restore form values
        Object.entries(state.formData).forEach(([name, value]) => {
            const input = this.form.querySelector(`[name="${name}"]`);
            if (input) {
                if (input.type === 'checkbox') {
                    input.checked = value === 'true' || value === true;
                } else if (input.type === 'radio') {
                    input.checked = input.value === value;
                } else {
                    input.value = value;
                }
            }
        });

        setTimeout(() => {
            this.ignoreNextChange = false;
        }, 100);

        this.emit('restored', { state });
    }

    getCurrentState() {
        return this.history[this.historyIndex];
    }

    canUndo() {
        return this.historyIndex > 0;
    }

    canRedo() {
        return this.historyIndex < this.history.length - 1;
    }
}
```

---

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
  - Update frontend markup for domain type and usage type
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

### Phase 4: Field Visibility Modal Refactor (Infrastructure)
- **Duration**: 2-3 days
- **Tasks**:
  - Extract modal to macro template
  - Create FieldVisibilityManager class
  - Integrate with display profiles
  - Update entry_form.html to use macro
  - Write tests

### Phase 5: JavaScript Architecture Refactor (Infrastructure)
- **Duration**: 4-5 days
- **Tasks**:
  - Create FormEventBus
  - Create FormComponent base class
  - Refactor PronunciationFormsManager
  - Refactor VariantFormsManager
  - Refactor RelationsManager
  - Update all components to use event-driven pattern
  - Write tests

---

## Testing Strategy

### Unit Tests
- DELETE button functionality
- Dependency checking logic
- Hierarchical dropdown rendering
- Multiple selection handling
- Sense-level variant relations serialization
- FieldVisibilityManager
- FormEventBus
- FormComponent base class

### Integration Tests
- DELETE endpoint with various scenarios
- Form submission with hierarchical selections
- XML generation with new fields
- Database updates for new features
- Event bus communication between components

### End-to-End Tests
- Complete workflow for deleting entries
- Sense editing with new hierarchical fields
- Variant relations at sense level
- Field visibility modal interactions
- Undo/redo with event-driven architecture
- Data consistency across operations

---

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

### Field Visibility Modal Risks
- **Risk**: Breaking modal functionality during refactor
- **Mitigation**:
  - Extract modal without changing behavior first
  - Add JS integration incrementally
  - Test with real user scenarios
  - Keep fallback for non-JS users

### JavaScript Architecture Risks
- **Risk**: Breaking existing functionality during refactor
- **Mitigation**:
  - Refactor components one at a time
  - Maintain backwards compatibility with existing API
  - Run full test suite after each refactor
  - Use feature flags for gradual rollout

---

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

4. **Field Visibility Modal**:
   - Modal is extracted to reusable macro
   - Settings are saved and loaded correctly
   - Components communicate via events
   - Modal works across different forms

5. **JavaScript Architecture**:
   - Components communicate via events
   - No scattered DOM scraping
   - Undo/redo works with event-driven architecture
   - Performance is improved or maintained

---

## Documentation Requirements

- Update user documentation for new features
- Add developer documentation for new code
- Update API documentation for new endpoints
- Create examples and tutorials
- Update help text in the UI
- Document JavaScript architecture patterns

---

## Monitoring and Maintenance

- Monitor usage of new features
- Track any errors or issues
- Gather user feedback
- Plan for iterative improvements
- Schedule regular maintenance
- Monitor JavaScript bundle size impact
