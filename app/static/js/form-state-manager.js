/**
 * FormStateManager - Core form state management with JSON serialization
 * 
 * Manages complete form state as JSON, tracks changes, handles serialization
 * between form fields and entry JSON format compatible with centralized validation.
 * 
 * @author Dictionary System
 * @version 1.0.0
 */

class FormStateManager {
    /**
     * Initialize FormStateManager with entry data
     * @param {Object} initialData - Initial entry data in JSON format
     */
    constructor(initialData = {}) {
        this.originalState = this.deepClone(initialData);
        this.currentState = this.deepClone(initialData);
        this.changeListeners = new Set();
        this.fieldBindings = new Map(); // field -> JSONPath mapping
        this.validationResults = new Map(); // field -> validation results
        
        console.log('[FormStateManager] Initialized with data:', initialData);
    }
    
    /**
     * Deep clone an object to avoid reference issues
     * @param {Object} obj - Object to clone
     * @returns {Object} Deep cloned object
     */
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (typeof obj === 'object') {
            const cloned = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    cloned[key] = this.deepClone(obj[key]);
                }
            }
            return cloned;
        }
        return obj;
    }
    
    /**
     * Capture current form state as the baseline for change detection
     */
    captureInitialState() {
        this.originalState = this.serializeFormToJSON();
        this.currentState = this.deepClone(this.originalState);
        console.log('[FormStateManager] Initial state captured:', this.originalState);
    }
    
    /**
     * Serialize current form state to entry JSON format
     * @returns {Object} Entry data in JSON format
     */
    serializeFormToJSON() {
        const entryData = {
            id: this.getFieldValue('entry-id') || this.currentState.id || '',
            lexical_unit: this.getLexicalUnit(),
            senses: this.getSenses(),
            pronunciations: this.getPronunciations(),
            notes: this.getNotes(),
            variants: this.getVariants(),
            etymologies: this.getEtymologies(),
            custom_fields: this.getCustomFields()
        };
        
        // Remove empty arrays and objects to match server expectations
        Object.keys(entryData).forEach(key => {
            if (Array.isArray(entryData[key]) && entryData[key].length === 0) {
                delete entryData[key];
            } else if (typeof entryData[key] === 'object' && 
                       entryData[key] !== null && 
                       Object.keys(entryData[key]).length === 0) {
                delete entryData[key];
            }
        });
        
        return entryData;
    }
    
    /**
     * Update form state from JSON data
     * @param {Object} data - Entry data in JSON format
     */
    updateFromJSON(data) {
        this.currentState = this.deepClone(data);
        this.populateFormFromData(data);
        this.notifyChangeListeners();
        console.log('[FormStateManager] Updated from JSON:', data);
    }
    
    /**
     * Get list of fields that have been modified
     * @returns {Array} Array of changed field paths
     */
    getChangedFields() {
        const changes = [];
        const current = this.serializeFormToJSON();
        
        this.findChanges(this.originalState, current, '', changes);
        
        return changes;
    }
    
    /**
     * Recursively find changes between two objects
     * @param {Object} original - Original object
     * @param {Object} current - Current object
     * @param {string} path - Current path
     * @param {Array} changes - Array to store changes
     */
    findChanges(original, current, path, changes) {
        if (original === current) return;
        
        if (typeof original !== typeof current) {
            changes.push({ path, original, current, type: 'type_change' });
            return;
        }
        
        if (Array.isArray(original) && Array.isArray(current)) {
            const maxLength = Math.max(original.length, current.length);
            for (let i = 0; i < maxLength; i++) {
                const itemPath = path ? `${path}[${i}]` : `[${i}]`;
                this.findChanges(original[i], current[i], itemPath, changes);
            }
        } else if (typeof original === 'object' && original !== null && current !== null) {
            const allKeys = new Set([...Object.keys(original), ...Object.keys(current)]);
            for (const key of allKeys) {
                const keyPath = path ? `${path}.${key}` : key;
                this.findChanges(original[key], current[key], keyPath, changes);
            }
        } else if (original !== current) {
            changes.push({ path, original, current, type: 'value_change' });
        }
    }
    
    /**
     * Register a field binding to a JSON path
     * @param {HTMLElement} field - Form field element
     * @param {string} jsonPath - JSONPath expression
     */
    registerFieldBinding(field, jsonPath) {
        this.fieldBindings.set(field, jsonPath);
        
        // Add change listener to field
        field.addEventListener('input', () => {
            this.captureFieldChange(field);
        });
        
        field.addEventListener('change', () => {
            this.captureFieldChange(field);
        });
        
        console.log(`[FormStateManager] Registered binding: ${field.name || field.id} -> ${jsonPath}`);
    }
    
    /**
     * Capture a field change and update state
     * @param {HTMLElement} field - Changed field
     */
    captureFieldChange(field) {
        const jsonPath = this.fieldBindings.get(field);
        if (!jsonPath) {
            console.warn('[FormStateManager] No binding found for field:', field);
            return;
        }
        
        const value = this.extractFieldValue(field);
        this.setValueAtPath(jsonPath, value);
        this.notifyChangeListeners();
        
        console.log(`[FormStateManager] Field changed: ${jsonPath} = ${value}`);
    }
    
    /**
     * Extract value from a form field
     * @param {HTMLElement} field - Form field
     * @returns {*} Field value
     */
    extractFieldValue(field) {
        if (field.type === 'checkbox') {
            return field.checked;
        } else if (field.type === 'radio') {
            return field.checked ? field.value : undefined;
        } else if (field.tagName === 'SELECT' && field.multiple) {
            return Array.from(field.selectedOptions).map(option => option.value);
        } else {
            return field.value;
        }
    }
    
    /**
     * Set value at a JSONPath in current state
     * @param {string} jsonPath - JSONPath expression (simplified)
     * @param {*} value - Value to set
     */
    setValueAtPath(jsonPath, value) {
        // Simplified JSONPath implementation for basic paths
        // Supports: $.field, $.field.subfield, $.array[0], $.array[0].field
        
        const path = jsonPath.replace(/^\$\./, '').split(/[\.\[\]]+/).filter(Boolean);
        let current = this.currentState;
        
        for (let i = 0; i < path.length - 1; i++) {
            const key = path[i];
            const nextKey = path[i + 1];
            
            if (!current[key]) {
                // Create object or array based on next key
                current[key] = /^\d+$/.test(nextKey) ? [] : {};
            }
            current = current[key];
        }
        
        const finalKey = path[path.length - 1];
        current[finalKey] = value;
    }
    
    /**
     * Get value at a JSONPath from current state
     * @param {string} jsonPath - JSONPath expression
     * @returns {*} Value at path
     */
    getValueAtPath(jsonPath) {
        const path = jsonPath.replace(/^\$\./, '').split(/[\.\[\]]+/).filter(Boolean);
        let current = this.currentState;
        
        for (const key of path) {
            if (current && typeof current === 'object' && key in current) {
                current = current[key];
            } else {
                return undefined;
            }
        }
        
        return current;
    }
    
    /**
     * Add change listener
     * @param {Function} listener - Change listener function
     */
    addChangeListener(listener) {
        this.changeListeners.add(listener);
    }
    
    /**
     * Remove change listener
     * @param {Function} listener - Change listener function
     */
    removeChangeListener(listener) {
        this.changeListeners.delete(listener);
    }
    
    /**
     * Notify all change listeners
     */
    notifyChangeListeners() {
        this.changeListeners.forEach(listener => {
            try {
                listener(this.getChangedFields());
            } catch (error) {
                console.error('[FormStateManager] Error in change listener:', error);
            }
        });
    }
    
    /**
     * Check if form has unsaved changes
     * @returns {boolean} True if there are unsaved changes
     */
    hasUnsavedChanges() {
        return this.getChangedFields().length > 0;
    }
    
    // === Specialized extraction methods ===
    
    /**
     * Extract lexical unit data from form
     * @returns {Object} Lexical unit object
     */
    getLexicalUnit() {
        const lexicalUnit = {};
        const fields = document.querySelectorAll('[name^="lexical_unit_"]');
        
        fields.forEach(field => {
            const lang = field.name.replace('lexical_unit_', '');
            if (field.value.trim()) {
                lexicalUnit[lang] = field.value.trim();
            }
        });
        
        return Object.keys(lexicalUnit).length > 0 ? lexicalUnit : this.currentState.lexical_unit || {};
    }
    
    /**
     * Extract senses data from form
     * @returns {Array} Array of sense objects
     */
    getSenses() {
        const senses = [];
        const senseContainers = document.querySelectorAll('.sense-item');
        
        senseContainers.forEach((container, index) => {
            const sense = {
                id: this.getFieldValue(`sense_${index}_id`) || `sense_${index + 1}`,
                definition: this.getMultilingualField(container, 'definition'),
                gloss: this.getMultilingualField(container, 'gloss'),
                grammatical_info: this.getGrammaticalInfo(container),
                examples: this.getExamples(container)
            };
            
            // Remove empty fields
            Object.keys(sense).forEach(key => {
                if (!sense[key] || (typeof sense[key] === 'object' && Object.keys(sense[key]).length === 0)) {
                    delete sense[key];
                }
            });
            
            if (Object.keys(sense).length > 1) { // More than just ID
                senses.push(sense);
            }
        });
        
        return senses.length > 0 ? senses : this.currentState.senses || [];
    }
    
    /**
     * Extract pronunciations data from form
     * @returns {Array} Array of pronunciation objects
     */
    getPronunciations() {
        const pronunciations = [];
        const pronunciationContainers = document.querySelectorAll('.pronunciation-item');
        
        pronunciationContainers.forEach(container => {
            const langField = container.querySelector('[name*="pronunciation_lang"]');
            const textField = container.querySelector('[name*="pronunciation_text"]');
            
            if (textField && textField.value.trim()) {
                pronunciations.push({
                    lang: langField ? langField.value : 'seh-fonipa',
                    text: textField.value.trim()
                });
            }
        });
        
        return pronunciations.length > 0 ? pronunciations : this.currentState.pronunciations || [];
    }
    
    /**
     * Extract notes data from form
     * @returns {Object} Notes object
     */
    getNotes() {
        const notes = {};
        const noteContainers = document.querySelectorAll('.note-item');
        
        noteContainers.forEach(container => {
            const typeField = container.querySelector('[name*="note_type"]');
            const textField = container.querySelector('[name*="note_text"]');
            
            if (typeField && textField && textField.value.trim()) {
                notes[typeField.value] = textField.value.trim();
            }
        });
        
        return Object.keys(notes).length > 0 ? notes : this.currentState.notes || {};
    }
    
    /**
     * Extract variants data from form
     * @returns {Array} Array of variant objects
     */
    getVariants() {
        const variants = [];
        const variantContainers = document.querySelectorAll('.variant-item');
        
        variantContainers.forEach(container => {
            const formField = container.querySelector('[name*="variant_form"]');
            const typeField = container.querySelector('[name*="variant_type"]');
            
            if (formField && formField.value.trim()) {
                variants.push({
                    form: formField.value.trim(),
                    type: typeField ? typeField.value : 'variant'
                });
            }
        });
        
        return variants.length > 0 ? variants : this.currentState.variants || [];
    }
    
    /**
     * Extract etymologies data from form
     * @returns {Array} Array of etymology objects
     */
    getEtymologies() {
        // Implementation depends on etymology form structure
        return this.currentState.etymologies || [];
    }
    
    /**
     * Extract custom fields data from form
     * @returns {Object} Custom fields object
     */
    getCustomFields() {
        const customFields = {};
        const customFieldContainers = document.querySelectorAll('.custom-field-item');
        
        customFieldContainers.forEach(container => {
            const keyField = container.querySelector('[name*="custom_key"]');
            const valueField = container.querySelector('[name*="custom_value"]');
            
            if (keyField && valueField && keyField.value.trim() && valueField.value.trim()) {
                customFields[keyField.value.trim()] = valueField.value.trim();
            }
        });
        
        return Object.keys(customFields).length > 0 ? customFields : this.currentState.custom_fields || {};
    }
    
    // === Helper methods ===
    
    /**
     * Get field value by name or ID
     * @param {string} fieldName - Field name or ID
     * @returns {string} Field value
     */
    getFieldValue(fieldName) {
        const field = document.querySelector(`[name="${fieldName}"], #${fieldName}`);
        return field ? field.value : '';
    }
    
    /**
     * Get multilingual field data from container
     * @param {HTMLElement} container - Container element
     * @param {string} fieldType - Field type (definition, gloss, etc.)
     * @returns {Object} Multilingual field object
     */
    getMultilingualField(container, fieldType) {
        const multilingual = {};
        const fields = container.querySelectorAll(`[name*="${fieldType}_"]`);
        
        fields.forEach(field => {
            const langMatch = field.name.match(new RegExp(`${fieldType}_(\\w+)`));
            if (langMatch && field.value.trim()) {
                multilingual[langMatch[1]] = field.value.trim();
            }
        });
        
        return multilingual;
    }
    
    /**
     * Get grammatical info from sense container
     * @param {HTMLElement} container - Sense container
     * @returns {Object} Grammatical info object
     */
    getGrammaticalInfo(container) {
        const grammaticalInfo = {};
        const posField = container.querySelector('[name*="pos"]');
        
        if (posField && posField.value) {
            grammaticalInfo.pos = posField.value;
        }
        
        return grammaticalInfo;
    }
    
    /**
     * Get examples from sense container
     * @param {HTMLElement} container - Sense container
     * @returns {Array} Array of example objects
     */
    getExamples(container) {
        const examples = [];
        const exampleContainers = container.querySelectorAll('.example-item');
        
        exampleContainers.forEach(exampleContainer => {
            const textField = exampleContainer.querySelector('[name*="example_text"]');
            if (textField && textField.value.trim()) {
                examples.push({
                    text: textField.value.trim(),
                    translation: this.getMultilingualField(exampleContainer, 'translation')
                });
            }
        });
        
        return examples;
    }
    
    /**
     * Populate form fields from JSON data
     * @param {Object} data - Entry data
     */
    populateFormFromData(data) {
        // This method would update form fields from JSON data
        // Implementation depends on specific form structure
        console.log('[FormStateManager] Populating form from data:', data);
        
        // Basic implementation for common fields
        if (data.id) {
            const idField = document.querySelector('[name="entry-id"], #entry-id');
            if (idField) idField.value = data.id;
        }
        
        // Lexical unit
        if (data.lexical_unit) {
            Object.entries(data.lexical_unit).forEach(([lang, value]) => {
                const field = document.querySelector(`[name="lexical_unit_${lang}"]`);
                if (field) field.value = value;
            });
        }
        
        // Additional field population would be handled by component-specific managers
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.FormStateManager = FormStateManager;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FormStateManager;
}
