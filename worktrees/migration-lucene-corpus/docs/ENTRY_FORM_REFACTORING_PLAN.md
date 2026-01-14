# Entry Form Refactoring Implementation Plan

## Overview

Based on our centralized validation system completion (Phase 1), we're now ready to refactor the entry form to support:
- **Auto-save with debounced validation**
- **JSON data submission** (validated by our centralized engine)
- **Systematic representation of rich structured data** (XML/JSON compatibility)

## ✅ COMPLETED: UI/UX Fixes (December 2024)

### Homograph Number Field Fix
- **Problem**: Field showed "Auto-assigned if needed" placeholder for all entries, taking unnecessary space
- **Solution**: Field now only displays when `entry.homograph_number` exists
- **Implementation**: Added conditional `{% if entry.homograph_number %}` wrapper around the field
- **Benefit**: Cleaner UI, less visual clutter for non-homograph entries

### Tooltip Icon Standardization  
- **Problem**: Inconsistent use of `fa-info-circle` and `fa-question-circle` icons
- **Solution**: Standardized to use `fa-info-circle` for informational tooltips
- **Exception**: Kept `fa-question-circle` only in warning/error alert contexts
- **Result**: 14 info-circle icons, 2 question-circle icons (in appropriate contexts)

### Technical Details
- **Files Modified**: `app/templates/entry_form.html`
- **Testing**: Created comprehensive test suite to verify fixes
- **Validation**: All integration tests passing
- **Browser Testing**: Verified in web interface

## Current State Analysis

### Existing Form Structure (`entry_form.html`)
1. **Complex nested components**: Senses, pronunciations, variants, etymology
2. **JavaScript component managers**: PronunciationFormsManager, VariantFormsManager, etc.
3. **Jinja2 template data binding**: Server-side rendering with JavaScript hydration
4. **Form submission**: Traditional POST with form-encoded data

### Issues to Address
1. **No real-time validation**: Users see errors only on submission
2. **No auto-save**: Risk of data loss during long editing sessions
3. **Inconsistent data formats**: Mix of form data and JSON structures
4. **No change tracking**: Can't detect what fields have been modified

## Implementation Plan

### Phase 2A: Core Infrastructure (3 days)

#### Day 1: JSON Data Binding System

**Files to Create/Modify**:
- `static/js/form-state-manager.js` (new)
- `static/js/json-path-binder.js` (new)
- `app/templates/entry_form.html` (modify)

**1. FormStateManager Class**
```javascript
/**
 * Manages complete form state as JSON, tracks changes, handles serialization
 */
class FormStateManager {
    constructor(initialData) {
        this.originalState = this.deepClone(initialData);
        this.currentState = this.deepClone(initialData);
        this.changeListeners = new Set();
        this.fieldBindings = new Map(); // field -> JSONPath mapping
    }
    
    // Core methods:
    serializeToJSON()           // Convert form to entry JSON format
    updateFromJSON(data)        // Update form from JSON data
    getChangedFields()          // Return list of modified fields
    captureFieldChange(field)   // Register field modification
    registerFieldBinding(field, jsonPath) // Bind field to JSON path
}
```

**2. JSONPath Data Binding**
```javascript
/**
 * Binds form fields to JSON paths for automatic synchronization
 */
class JSONPathBinder {
    constructor(stateManager) {
        this.stateManager = stateManager;
        this.boundFields = new Map();
    }
    
    bindField(fieldElement, jsonPath) {
        // Auto-sync field changes to JSON state
        fieldElement.addEventListener('input', (e) => {
            this.updateJSONFromField(fieldElement, jsonPath);
        });
    }
    
    updateJSONFromField(field, path) {
        const value = this.extractFieldValue(field);
        this.stateManager.setValueAtPath(path, value);
    }
}
```

**3. Entry Form Template Updates**
```html
<!-- Add data-json-path attributes to form fields -->
<input type="text" 
       name="lexical_unit_seh"
       data-json-path="$.lexical_unit.seh"
       data-validation-rules="R1.1.2,R3.2.2"
       value="{{ entry.lexical_unit.seh if entry.lexical_unit else '' }}">

<textarea name="sense_definition_en"
          data-json-path="$.senses[0].definition.en" 
          data-validation-rules="R2.1.2"
          data-debounce="500">{{ entry.senses[0].definition.en if entry.senses else '' }}</textarea>
```

#### Day 2: Client-Side Validation Integration

**Files to Create/Modify**:
- `static/js/client-validation-engine.js` (new)
- `static/js/validation-ui.js` (new)

**1. Client Validation Engine**
```javascript
/**
 * Client-side validation using centralized rules from server
 */
class ClientValidationEngine {
    constructor() {
        this.rules = null;
        this.customValidators = new Map();
        this.loadValidationRules();
    }
    
    async loadValidationRules() {
        // Fetch validation rules from /api/validation/rules
        const response = await fetch('/api/validation/rules');
        this.rules = await response.json();
        this.setupCustomValidators();
    }
    
    async validateField(jsonPath, value, context) {
        const applicableRules = this.getRulesForPath(jsonPath);
        const results = [];
        
        for (const rule of applicableRules) {
            const result = await this.executeRule(rule, value, context);
            if (!result.valid) {
                results.push({
                    ruleId: rule.id,
                    message: rule.message,
                    priority: rule.priority
                });
            }
        }
        
        return results;
    }
    
    async validateCompleteForm(formData) {
        // Send to server for comprehensive validation
        const response = await fetch('/api/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        return await response.json();
    }
}
```

**2. Validation UI Components**
```javascript
/**
 * Handles display of validation errors and feedback
 */
class ValidationUI {
    constructor() {
        this.errorContainers = new Map();
        this.fieldStates = new Map();
    }
    
    displayFieldErrors(field, validationResults) {
        // Show inline error messages
        this.clearFieldErrors(field);
        
        const criticalErrors = validationResults.filter(r => r.priority === 'critical');
        const warnings = validationResults.filter(r => r.priority === 'warning');
        
        if (criticalErrors.length > 0) {
            this.showCriticalErrors(field, criticalErrors);
            this.markFieldInvalid(field);
        } else if (warnings.length > 0) {
            this.showWarnings(field, warnings);
            this.markFieldWarning(field);
        } else {
            this.markFieldValid(field);
        }
    }
    
    showSectionSummary(sectionId, allResults) {
        // Update section headers with validation status
        const section = document.getElementById(sectionId);
        const errorCount = allResults.filter(r => r.priority === 'critical').length;
        const warningCount = allResults.filter(r => r.priority === 'warning').length;
        
        this.updateSectionBadge(section, errorCount, warningCount);
    }
}
```

#### Day 3: Debounced Auto-Save System

**Files to Create/Modify**:
- `static/js/auto-save-manager.js` (new)
- `app/api/entry_autosave.py` (new)

**1. Auto-Save Manager**
```javascript
/**
 * Handles automatic saving with conflict detection
 */
class AutoSaveManager {
    constructor(stateManager, validationEngine) {
        this.stateManager = stateManager;
        this.validationEngine = validationEngine;
        this.saveInterval = 10000; // 10 seconds
        this.debounceDelay = 2000;  // 2 seconds after last change
        this.lastSaveVersion = null;
        this.saveTimer = null;
        this.debouncedSave = this.debounce(this.performSave.bind(this), this.debounceDelay);
    }
    
    start() {
        // Start periodic auto-save
        setInterval(() => {
            if (this.stateManager.hasUnsavedChanges()) {
                this.debouncedSave();
            }
        }, this.saveInterval);
        
        // Save on form changes
        this.stateManager.addChangeListener(() => {
            this.debouncedSave();
        });
    }
    
    async performSave() {
        const formData = this.stateManager.serializeToJSON();
        
        // Validate before saving
        const validationResult = await this.validationEngine.validateCompleteForm(formData);
        const criticalErrors = validationResult.errors.filter(e => e.priority === 'critical');
        
        if (criticalErrors.length > 0) {
            console.log('Auto-save skipped due to critical validation errors');
            return { success: false, reason: 'validation_errors' };
        }
        
        // Attempt to save
        try {
            const response = await fetch('/api/entry/autosave', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    entryData: formData,
                    version: this.lastSaveVersion,
                    timestamp: new Date().toISOString()
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.lastSaveVersion = result.newVersion;
                this.showSaveIndicator('saved');
                return { success: true };
            } else if (result.error === 'version_conflict') {
                this.handleVersionConflict(result.serverData);
                return { success: false, reason: 'conflict' };
            }
        } catch (error) {
            console.error('Auto-save failed:', error);
            this.showSaveIndicator('error');
            return { success: false, reason: 'network_error' };
        }
    }
}
```

**2. Server-Side Auto-Save Endpoint**
```python
# app/api/entry_autosave.py
from flask import Blueprint, request, jsonify
from app.services.validation_engine import ValidationEngine
from app.models.entry import Entry
from app.utils.exceptions import ValidationError, VersionConflictError

autosave_bp = Blueprint('autosave', __name__)

@autosave_bp.route('/api/entry/autosave', methods=['POST'])
def autosave_entry():
    """Auto-save entry data with version checking and validation"""
    data = request.get_json()
    entry_data = data.get('entryData')
    client_version = data.get('version')
    
    # Validate the entry data
    validator = ValidationEngine()
    validation_result = validator.validate_json(entry_data)
    
    # Only save if no critical errors
    critical_errors = [e for e in validation_result.errors if e.priority == 'critical']
    if critical_errors:
        return jsonify({
            'success': False,
            'error': 'validation_failed',
            'validation_errors': [e.to_dict() for e in critical_errors]
        }), 400
    
    # Check for version conflicts
    if entry_data.get('id'):
        current_entry = Entry.query.get(entry_data['id'])
        if current_entry and current_entry.version != client_version:
            return jsonify({
                'success': False,
                'error': 'version_conflict',
                'serverData': current_entry.to_dict(),
                'clientVersion': client_version,
                'serverVersion': current_entry.version
            }), 409
    
    # Perform the save
    try:
        entry = Entry.from_dict(entry_data)
        entry.save()
        
        return jsonify({
            'success': True,
            'newVersion': entry.version,
            'timestamp': entry.updated_at.isoformat(),
            'warnings': [w.to_dict() for w in validation_result.warnings]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'save_failed',
            'message': str(e)
        }), 500
```

### Phase 2B: Rich Data Structure Support (2 days)

#### Day 4: Complex Component Integration

**Files to Modify**:
- `static/js/pronunciation-forms.js` (integrate with JSON state)
- `static/js/variant-forms.js` (integrate with JSON state)
- `static/js/sense-manager.js` (new, replaces inline sense handling)

**1. Unified Component Architecture**
```javascript
/**
 * Base class for all form components (senses, pronunciations, variants)
 */
class FormComponent {
    constructor(containerId, stateManager, jsonBasePath) {
        this.container = document.getElementById(containerId);
        this.stateManager = stateManager;
        this.basePath = jsonBasePath; // e.g., "$.senses", "$.pronunciations"
        this.items = [];
    }
    
    // Standard interface all components must implement
    renderFromData(data) { /* Render component from JSON data */ }
    serializeToData() { /* Extract data to JSON format */ }
    addItem(data = {}) { /* Add new item */ }
    removeItem(index) { /* Remove item */ }
    validateItems() { /* Validate all items */ }
}

/**
 * Manages pronunciation data with IPA validation
 */
class PronunciationComponent extends FormComponent {
    constructor(containerId, stateManager) {
        super(containerId, stateManager, '$.pronunciations');
        this.ipaValidator = new IPAValidator();
    }
    
    renderFromData(pronunciations) {
        this.container.innerHTML = '';
        pronunciations.forEach((pronunciation, index) => {
            this.renderPronunciationItem(pronunciation, index);
        });
    }
    
    renderPronunciationItem(data, index) {
        const template = document.getElementById('pronunciation-template');
        const item = template.content.cloneNode(true);
        
        // Bind fields to JSON paths
        const langField = item.querySelector('[name="pronunciation_lang"]');
        langField.value = data.lang || 'seh-fonipa';
        langField.setAttribute('data-json-path', `$.pronunciations[${index}].lang`);
        
        const textField = item.querySelector('[name="pronunciation_text"]');
        textField.value = data.text || '';
        textField.setAttribute('data-json-path', `$.pronunciations[${index}].text`);
        textField.setAttribute('data-validation-rules', 'R4.1.1,R4.1.2,R4.2.1,R4.2.2');
        
        this.container.appendChild(item);
        
        // Register with state manager
        this.stateManager.bindField(langField, `$.pronunciations[${index}].lang`);
        this.stateManager.bindField(textField, `$.pronunciations[${index}].text`);
    }
}
```

#### Day 5: Complete Form Integration

**Files to Create/Modify**:
- `static/js/entry-form-manager.js` (main orchestrator)
- `app/templates/entry_form.html` (final integration)

**1. Main Entry Form Manager**
```javascript
/**
 * Main orchestrator for the complete entry form
 */
class EntryFormManager {
    constructor(entryData) {
        this.stateManager = new FormStateManager(entryData);
        this.validationEngine = new ClientValidationEngine();
        this.validationUI = new ValidationUI();
        this.autoSaveManager = new AutoSaveManager(this.stateManager, this.validationEngine);
        this.components = new Map();
        
        this.initializeComponents();
        this.setupEventHandlers();
    }
    
    async initialize() {
        // Wait for validation rules to load
        await this.validationEngine.ready;
        
        // Initialize all components
        this.initializeComponents();
        
        // Capture initial state
        this.stateManager.captureInitialState();
        
        // Start auto-save
        this.autoSaveManager.start();
        
        // Setup debounced validation
        this.setupDebouncedValidation();
        
        console.log('Entry form manager initialized successfully');
    }
    
    initializeComponents() {
        // Initialize all form components
        this.components.set('pronunciation', new PronunciationComponent('pronunciation-container', this.stateManager));
        this.components.set('variants', new VariantComponent('variants-container', this.stateManager));
        this.components.set('senses', new SenseComponent('senses-container', this.stateManager));
        this.components.set('etymology', new EtymologyComponent('etymology-container', this.stateManager));
        this.components.set('notes', new NotesComponent('notes-container', this.stateManager));
    }
    
    setupDebouncedValidation() {
        const debouncedValidate = this.debounce(async () => {
            await this.validateCompleteForm();
        }, 500);
        
        // Attach to all form changes
        this.stateManager.addChangeListener(debouncedValidate);
    }
    
    async validateCompleteForm() {
        const formData = this.stateManager.serializeToJSON();
        const validationResult = await this.validationEngine.validateCompleteForm(formData);
        
        // Display validation results
        this.validationUI.displayFormValidation(validationResult);
        
        // Update component-specific validation
        this.components.forEach((component, name) => {
            const componentErrors = validationResult.errors.filter(e => 
                e.field_path && e.field_path.startsWith(component.basePath)
            );
            component.displayValidation(componentErrors);
        });
    }
    
    async handleFormSubmission(event) {
        event.preventDefault();
        
        // Final validation before submission
        const formData = this.stateManager.serializeToJSON();
        const validationResult = await this.validationEngine.validateCompleteForm(formData);
        
        const criticalErrors = validationResult.errors.filter(e => e.priority === 'critical');
        if (criticalErrors.length > 0) {
            this.validationUI.showValidationModal(criticalErrors);
            return false;
        }
        
        // Submit as JSON
        try {
            const response = await fetch(event.target.action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                const result = await response.json();
                window.location.href = result.redirect_url || '/entries';
            } else {
                const error = await response.json();
                this.validationUI.showServerError(error);
            }
        } catch (error) {
            console.error('Form submission failed:', error);
            this.validationUI.showNetworkError();
        }
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', async function() {
    const entryData = {{ entry.to_dict() | tojson | safe }};
    const formManager = new EntryFormManager(entryData);
    await formManager.initialize();
    
    // Make globally available for debugging
    window.entryFormManager = formManager;
});
```

### Phase 2C: Server-Side Integration (1 day)

#### Day 6: API and Route Updates

**Files to Create/Modify**:
- `app/routes/main.py` (update entry routes to handle JSON)
- `app/models/entry.py` (enhance JSON serialization)

**1. Updated Entry Routes**
```python
@main.route('/entry/<entry_id>/edit', methods=['GET', 'POST'])
def edit_entry(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    
    if request.method == 'POST':
        if request.is_json:
            # Handle JSON submission from new form
            entry_data = request.get_json()
            
            # Validate using centralized engine
            validator = ValidationEngine()
            validation_result = validator.validate_json(entry_data)
            
            # Check for critical errors
            critical_errors = [e for e in validation_result.errors if e.priority == 'critical']
            if critical_errors:
                return jsonify({
                    'success': False,
                    'validation_errors': [e.to_dict() for e in critical_errors]
                }), 400
            
            # Update entry
            try:
                entry.update_from_dict(entry_data)
                entry.save();
                
                return jsonify({
                    'success': True,
                    'redirect_url': url_for('main.view_entry', entry_id=entry.id),
                    'warnings': [w.to_dict() for w in validation_result.warnings]
                })
            
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': 'save_failed',
                    'message': str(e)
                }), 500
        
        else:
            # Handle traditional form submission (fallback)
            # ... existing form handling code ...
    
    # GET request - render form with JSON data
    return render_template('entry_form.html', entry=entry)
```

## Testing Strategy

### Unit Tests
- `test_form_state_manager.js` - State management and JSON serialization
- `test_client_validation.js` - Client-side validation rules
- `test_auto_save.py` - Auto-save functionality and conflict handling

### Integration Tests  
- `test_form_integration.py` - Complete form submission workflow
- `test_validation_integration.py` - Client-server validation consistency

### Manual Testing Checklist
- [ ] Form loads with existing entry data
- [ ] Real-time validation displays correctly
- [ ] Auto-save works without data loss
- [ ] Version conflicts are handled gracefully
- [ ] Complex components (pronunciations, senses) work correctly
- [ ] Form submission works with JSON data
- [ ] Validation errors are user-friendly

## Success Criteria

1. **Auto-save**: Form data saved automatically every 10 seconds
2. **Real-time validation**: Errors displayed within 500ms of input
3. **JSON consistency**: Form data matches centralized validation format
4. **No data loss**: Version conflicts resolved without losing user work
5. **Performance**: Form remains responsive during validation and auto-save
6. **Backward compatibility**: Existing form functionality preserved

## Files Summary

### New Files Created
- `static/js/form-state-manager.js`
- `static/js/json-path-binder.js` 
- `static/js/client-validation-engine.js`
- `static/js/validation-ui.js`
- `static/js/auto-save-manager.js`
- `static/js/entry-form-manager.js`
- `app/api/entry_autosave.py`

### Modified Files
- `app/templates/entry_form.html`
- `static/js/pronunciation-forms.js`
- `static/js/variant-forms.js`
- `app/routes/main.py`
- `app/models/entry.py`

This implementation plan provides a systematic approach to refactoring the entry form with auto-save, real-time validation, and JSON data handling while maintaining backward compatibility and following our established TDD principles.
