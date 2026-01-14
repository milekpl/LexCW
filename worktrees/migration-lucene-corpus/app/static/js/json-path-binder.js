/**
 * JSONPathBinder - Automatic binding between form fields and JSON paths
 * 
 * Provides automatic synchronization between form fields and JSON state
 * using data-json-path attributes and JSONPath expressions.
 * 
 * @author Dictionary System
 * @version 1.0.0
 */

class JSONPathBinder {
    /**
     * Initialize JSONPathBinder with FormStateManager
     * @param {FormStateManager} stateManager - Form state manager instance
     */
    constructor(stateManager) {
        this.stateManager = stateManager;
        this.boundFields = new Map(); // field -> binding info
        this.pathFields = new Map();  // path -> field(s)
        this.initialized = false;
        
        console.log('[JSONPathBinder] Initialized');
    }
    
    /**
     * Initialize all field bindings in the form
     */
    initializeBindings() {
        if (this.initialized) {
            console.warn('[JSONPathBinder] Already initialized');
            return;
        }
        
        // Find all fields with data-json-path attributes
        const fieldsWithPaths = document.querySelectorAll('[data-json-path]');
        
        fieldsWithPaths.forEach(field => {
            const jsonPath = field.getAttribute('data-json-path');
            if (jsonPath) {
                this.bindField(field, jsonPath);
            }
        });
        
        this.initialized = true;
        console.log(`[JSONPathBinder] Initialized ${fieldsWithPaths.length} field bindings`);
    }
    
    /**
     * Bind a specific field to a JSON path
     * @param {HTMLElement} field - Form field element
     * @param {string} jsonPath - JSONPath expression
     * @param {Object} options - Binding options
     */
    bindField(field, jsonPath, options = {}) {
        const bindingInfo = {
            field,
            jsonPath,
            bidirectional: options.bidirectional !== false, // Default true
            debounce: options.debounce || 0,
            validator: options.validator || null,
            transform: options.transform || null
        };
        
        // Store binding information
        this.boundFields.set(field, bindingInfo);
        
        if (!this.pathFields.has(jsonPath)) {
            this.pathFields.set(jsonPath, []);
        }
        this.pathFields.get(jsonPath).push(field);
        
        // Set up field-to-JSON synchronization
        if (bindingInfo.bidirectional) {
            this.setupFieldToJSONSync(bindingInfo);
        }
        
        // Set up JSON-to-field synchronization
        this.setupJSONToFieldSync(bindingInfo);
        
        // Register with state manager
        this.stateManager.registerFieldBinding(field, jsonPath);
        
        console.log(`[JSONPathBinder] Bound field ${field.name || field.id} to ${jsonPath}`);
    }
    
    /**
     * Set up field-to-JSON synchronization
     * @param {Object} bindingInfo - Binding information
     */
    setupFieldToJSONSync(bindingInfo) {
        const { field, jsonPath, debounce } = bindingInfo;
        
        let handler = () => {
            this.updateJSONFromField(bindingInfo);
        };
        
        // Add debouncing if specified
        if (debounce > 0) {
            handler = this.debounce(handler, debounce);
        }
        
        // Listen for various field events
        const events = this.getRelevantEvents(field);
        events.forEach(eventType => {
            field.addEventListener(eventType, handler);
        });
    }
    
    /**
     * Set up JSON-to-field synchronization
     * @param {Object} bindingInfo - Binding information
     */
    setupJSONToFieldSync(bindingInfo) {
        // This would be triggered when JSON state changes
        // For now, we'll implement manual updates
        bindingInfo.updateFromJSON = () => {
            this.updateFieldFromJSON(bindingInfo);
        };
    }
    
    /**
     * Update JSON state from field value
     * @param {Object} bindingInfo - Binding information
     */
    updateJSONFromField(bindingInfo) {
        const { field, jsonPath, validator, transform } = bindingInfo;
        
        try {
            let value = this.extractFieldValue(field);
            
            // Apply transformation if specified
            if (transform && transform.fieldToJSON) {
                value = transform.fieldToJSON(value);
            }
            
            // Validate if validator specified
            if (validator) {
                const validationResult = validator(value);
                if (!validationResult.valid) {
                    console.warn(`[JSONPathBinder] Validation failed for ${jsonPath}:`, validationResult.error);
                    return;
                }
            }
            
            // Update state manager
            this.stateManager.setValueAtPath(jsonPath, value);
            
            console.log(`[JSONPathBinder] Updated JSON: ${jsonPath} = ${value}`);
            
        } catch (error) {
            console.error(`[JSONPathBinder] Error updating JSON from field ${jsonPath}:`, error);
        }
    }
    
    /**
     * Update field value from JSON state
     * @param {Object} bindingInfo - Binding information
     */
    updateFieldFromJSON(bindingInfo) {
        const { field, jsonPath, transform } = bindingInfo;
        
        try {
            let value = this.stateManager.getValueAtPath(jsonPath);
            
            // Apply transformation if specified
            if (transform && transform.jsonToField) {
                value = transform.jsonToField(value);
            }
            
            // Update field value
            this.setFieldValue(field, value);
            
            console.log(`[JSONPathBinder] Updated field: ${jsonPath} = ${value}`);
            
        } catch (error) {
            console.error(`[JSONPathBinder] Error updating field from JSON ${jsonPath}:`, error);
        }
    }
    
    /**
     * Extract value from form field
     * @param {HTMLElement} field - Form field
     * @returns {*} Field value
     */
    extractFieldValue(field) {
        switch (field.type) {
            case 'checkbox':
                return field.checked;
            case 'radio':
                // For radio buttons, return value only if checked
                return field.checked ? field.value : undefined;
            case 'number':
                const numValue = parseFloat(field.value);
                return isNaN(numValue) ? null : numValue;
            case 'select-multiple':
                return Array.from(field.selectedOptions).map(option => option.value);
            default:
                return field.value;
        }
    }
    
    /**
     * Set field value
     * @param {HTMLElement} field - Form field
     * @param {*} value - Value to set
     */
    setFieldValue(field, value) {
        switch (field.type) {
            case 'checkbox':
                field.checked = Boolean(value);
                break;
            case 'radio':
                field.checked = (field.value === value);
                break;
            case 'select-multiple':
                if (Array.isArray(value)) {
                    Array.from(field.options).forEach(option => {
                        option.selected = value.includes(option.value);
                    });
                }
                break;
            default:
                field.value = value || '';
        }
        
        // Trigger change event to notify other listeners
        field.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    /**
     * Get relevant events for field type
     * @param {HTMLElement} field - Form field
     * @returns {Array} Array of event names
     */
    getRelevantEvents(field) {
        const commonEvents = ['change'];
        
        switch (field.type) {
            case 'text':
            case 'textarea':
            case 'email':
            case 'url':
            case 'password':
                return [...commonEvents, 'input'];
            case 'checkbox':
            case 'radio':
                return [...commonEvents, 'click'];
            case 'select-one':
            case 'select-multiple':
                return commonEvents;
            default:
                return [...commonEvents, 'input'];
        }
    }
    
    /**
     * Update all fields bound to a specific JSON path
     * @param {string} jsonPath - JSON path
     */
    updateFieldsForPath(jsonPath) {
        const fields = this.pathFields.get(jsonPath);
        if (fields) {
            fields.forEach(field => {
                const bindingInfo = this.boundFields.get(field);
                if (bindingInfo && bindingInfo.updateFromJSON) {
                    bindingInfo.updateFromJSON();
                }
            });
        }
    }
    
    /**
     * Update all bound fields from current JSON state
     */
    updateAllFieldsFromJSON() {
        this.boundFields.forEach((bindingInfo) => {
            if (bindingInfo.updateFromJSON) {
                bindingInfo.updateFromJSON();
            }
        });
    }
    
    /**
     * Unbind a field
     * @param {HTMLElement} field - Field to unbind
     */
    unbindField(field) {
        const bindingInfo = this.boundFields.get(field);
        if (bindingInfo) {
            const { jsonPath } = bindingInfo;
            
            // Remove from pathFields
            const fieldsForPath = this.pathFields.get(jsonPath);
            if (fieldsForPath) {
                const index = fieldsForPath.indexOf(field);
                if (index !== -1) {
                    fieldsForPath.splice(index, 1);
                }
                if (fieldsForPath.length === 0) {
                    this.pathFields.delete(jsonPath);
                }
            }
            
            // Remove from boundFields
            this.boundFields.delete(field);
            
            console.log(`[JSONPathBinder] Unbound field ${field.name || field.id} from ${jsonPath}`);
        }
    }
    
    /**
     * Get binding information for a field
     * @param {HTMLElement} field - Form field
     * @returns {Object|null} Binding information
     */
    getBindingInfo(field) {
        return this.boundFields.get(field) || null;
    }
    
    /**
     * Get all fields bound to a JSON path
     * @param {string} jsonPath - JSON path
     * @returns {Array} Array of bound fields
     */
    getFieldsForPath(jsonPath) {
        return this.pathFields.get(jsonPath) || [];
    }
    
    /**
     * Debounce function
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * Create field binding from data attributes
     * @param {HTMLElement} field - Form field with data attributes
     * @returns {Object} Binding options
     */
    createBindingFromDataAttributes(field) {
        const options = {};
        
        // Get debounce setting
        const debounceAttr = field.getAttribute('data-debounce');
        if (debounceAttr) {
            options.debounce = parseInt(debounceAttr, 10);
        }
        
        // Get bidirectional setting
        const bidirectionalAttr = field.getAttribute('data-bidirectional');
        if (bidirectionalAttr !== null) {
            options.bidirectional = bidirectionalAttr !== 'false';
        }
        
        // Get validation rules
        const validationRulesAttr = field.getAttribute('data-validation-rules');
        if (validationRulesAttr) {
            options.validationRules = validationRulesAttr.split(',').map(rule => rule.trim());
        }
        
        return options;
    }
    
    /**
     * Validate all bound fields
     * @returns {Object} Validation results
     */
    validateAllFields() {
        const results = {
            valid: true,
            errors: [],
            warnings: []
        };
        
        this.boundFields.forEach((bindingInfo, field) => {
            if (bindingInfo.validator) {
                const value = this.extractFieldValue(field);
                const validationResult = bindingInfo.validator(value);
                
                if (!validationResult.valid) {
                    results.valid = false;
                    results.errors.push({
                        field: field.name || field.id,
                        path: bindingInfo.jsonPath,
                        error: validationResult.error
                    });
                }
            }
        });
        
        return results;
    }
    
    /**
     * Get debug information about all bindings
     * @returns {Object} Debug information
     */
    getDebugInfo() {
        return {
            boundFieldsCount: this.boundFields.size,
            pathsCount: this.pathFields.size,
            initialized: this.initialized,
            bindings: Array.from(this.boundFields.entries()).map(([field, bindingInfo]) => ({
                fieldName: field.name || field.id,
                jsonPath: bindingInfo.jsonPath,
                bidirectional: bindingInfo.bidirectional,
                debounce: bindingInfo.debounce
            }))
        };
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.JSONPathBinder = JSONPathBinder;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = JSONPathBinder;
}
