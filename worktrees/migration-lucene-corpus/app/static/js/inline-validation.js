/**
 * Inline Validation Manager
 * 
 * Handles real-time validation as users type and interact with form fields.
 * Integrates with ValidationUI for display and validation API for logic.
 */

class InlineValidationManager {
    constructor() {
        this.validationEndpoint = '/api/validation/field';
        this.sectionEndpoint = '/api/validation/section';
        this.debounceDelay = 500; // milliseconds
        this.validationTimeouts = new Map();
        this.validationCache = new Map();
        this.activeValidations = new Set();

        this.init();
    }

    /**
     * Get CSRF token from meta tag
     */
    getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    /**
     * Get fetch headers with CSRF token
     */
    getHeaders() {
        return {
            'Content-Type': 'application/json',
            'X-CSRF-Token': this.getCsrfToken()
        };
    }

    init() {
        this.setupFieldValidation();
        this.setupSectionValidation();
        
        console.log('✅ InlineValidationManager initialized');
    }
    
    /**
     * Setup real-time field validation
     */
    setupFieldValidation() {
        const formFields = document.querySelectorAll('input, textarea, select');

        formFields.forEach(field => {
            // Skip hidden fields, buttons, and fields marked to skip validation
            if (field.type === 'hidden' || field.type === 'submit' || field.type === 'button') {
                return;
            }

            // Skip fields marked with data-skip-validation attribute
            if (field.hasAttribute('data-skip-validation')) {
                return;
            }

            const fieldId = field.getAttribute('data-validation-target') ||
                           field.id || field.name;

            if (!fieldId) return;

            // Add validation rules attribute if not present
            if (!field.hasAttribute('data-validation-rules')) {
                const rules = this.getFieldValidationRules(field);
                field.setAttribute('data-validation-rules', JSON.stringify(rules));
            }

            // Setup event listeners
            this.setupFieldEventListeners(field, fieldId);
        });
    }
    
    /**
     * Setup field event listeners for validation
     */
    setupFieldEventListeners(field, fieldId) {
        // Real-time validation on input (debounced)
        field.addEventListener('input', (event) => {
            this.debounceValidation(fieldId, () => {
                this.validateField(fieldId, event.target.value);
            });
        });
        
        // Immediate validation on blur
        field.addEventListener('blur', (event) => {
            this.clearDebounce(fieldId);
            this.validateField(fieldId, event.target.value);
        });
        
        // Clear validation on focus if field is valid
        field.addEventListener('focus', () => {
            const currentState = window.validationUI?.getFieldValidationState(fieldId);
            if (currentState && currentState.valid) {
                // Keep valid state but allow new validation
            }
        });
        
        // Handle special field types
        if (field.type === 'select-one' || field.tagName === 'SELECT') {
            field.addEventListener('change', (event) => {
                this.validateField(fieldId, event.target.value);
            });
        }
    }
    
    /**
     * Setup section-level validation
     */
    setupSectionValidation() {
        // Monitor form sections for changes
        const sections = document.querySelectorAll('.card');
        
        sections.forEach(section => {
            const sectionId = this.getSectionId(section);
            if (!sectionId) return;
            
            // Add validation trigger when any field in section changes
            const sectionFields = section.querySelectorAll('input, textarea, select');
            sectionFields.forEach(field => {
                field.addEventListener('blur', () => {
                    this.debounceValidation(`section_${sectionId}`, () => {
                        this.validateSection(sectionId);
                    });
                });
            });
        });
    }
    
    /**
     * Validate a single field
     */
    async validateField(fieldId, value) {
        console.log(`[InlineValidation] validateField called for field: ${fieldId}, value: ${value}`);
        try {
            // Check if validation should be skipped
            const skipValidationCheckbox = document.getElementById('skip-validation-checkbox');
            if (skipValidationCheckbox && skipValidationCheckbox.checked) {
                // Clear any existing validation state for this field
                window.validationUI?.clearFieldValidation(fieldId);
                return null;
            }
            
            // Check cache first
            const cacheKey = `${fieldId}:${value}`;
            if (this.validationCache.has(cacheKey)) {
                const cachedResult = this.validationCache.get(cacheKey);
                window.validationUI?.displayFieldValidation(fieldId, cachedResult);
                return cachedResult;
            }
            
            // Prevent duplicate validations
            if (this.activeValidations.has(fieldId)) {
                return;
            }
            
            this.activeValidations.add(fieldId);
            
            // Show loading state
            window.validationUI?.showValidationLoading(fieldId);
            
            // Get field context
            const context = this.getFieldContext(fieldId);
            
            // Make validation request
            const response = await fetch(this.validationEndpoint, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    field: fieldId,
                    value: value,
                    context: context
                })
            });
            
            if (!response.ok) {
                throw new Error(`Validation request failed: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Cache the result
            this.validationCache.set(cacheKey, result);
            
            // Display the result
            window.validationUI?.hideValidationLoading(fieldId);
            window.validationUI?.displayFieldValidation(fieldId, result);
            
            // Trigger section validation if field is valid or has only warnings
            if (result.valid || (result.errors.length === 0 && result.warnings.length > 0)) {
                const sectionId = this.getFieldSection(fieldId);
                if (sectionId) {
                    this.debounceValidation(`section_${sectionId}`, () => {
                        this.validateSection(sectionId);
                    });
                }
            }
            
            return result;
            
        } catch (error) {
            console.error(`[InlineValidation] Field validation error for ${fieldId}:`, error);
            console.error(`[InlineValidation] Error name: ${error.name}, message: ${error.message}`);
            
            // Show error state
            window.validationUI?.hideValidationLoading(fieldId);
            window.validationUI?.displayFieldValidation(fieldId, {
                valid: false,
                errors: ['Validation temporarily unavailable'],
                warnings: [],
                field: fieldId
            });
            
        } finally {
            this.activeValidations.delete(fieldId);
        }
    }
    
    /**
     * Validate a form section
     */
    async validateSection(sectionId) {
        try {
            // Prevent duplicate validations
            if (this.activeValidations.has(`section_${sectionId}`)) {
                return;
            }
            
            this.activeValidations.add(`section_${sectionId}`);
            
            // Collect section fields and values
            const fields = this.getSectionFields(sectionId);
            const context = this.getSectionContext(sectionId);
            
            // Make section validation request
            const response = await fetch(this.sectionEndpoint, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    section: sectionId,
                    fields: fields,
                    context: context
                })
            });
            
            if (!response.ok) {
                throw new Error(`Section validation request failed: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Update section badge
            window.validationUI?.updateSectionStatus(sectionId, result);
            
            // Update individual field results if provided
            if (result.field_results) {
                Object.entries(result.field_results).forEach(([fieldId, fieldResult]) => {
                    window.validationUI?.displayFieldValidation(fieldId, fieldResult);
                });
            }
            
            return result;
            
        } catch (error) {
            console.error(`Section validation error for ${sectionId}:`, error);
            
        } finally {
            this.activeValidations.delete(`section_${sectionId}`);
        }
    }
    
    /**
     * Debounce validation calls
     */
    debounceValidation(key, validationFunction) {
        // Clear existing timeout
        this.clearDebounce(key);
        
        // Set new timeout
        const timeoutId = setTimeout(() => {
            validationFunction();
            this.validationTimeouts.delete(key);
        }, this.debounceDelay);
        
        this.validationTimeouts.set(key, timeoutId);
    }
    
    /**
     * Clear debounce timeout
     */
    clearDebounce(key) {
        if (this.validationTimeouts.has(key)) {
            clearTimeout(this.validationTimeouts.get(key));
            this.validationTimeouts.delete(key);
        }
    }
    
    /**
     * Get validation rules for a field
     */
    getFieldValidationRules(field) {
        const rules = {
            required: field.hasAttribute('required'),
            type: field.type,
            maxLength: field.maxLength || null,
            pattern: field.pattern || null
        };
        
        // Add field-specific rules based on name/id
        const fieldName = field.name || field.id;
        
        if (fieldName === 'lexical_unit') {
            rules.minLength = 1;
            rules.custom = ['unique_check'];
        } else if (fieldName === 'part_of_speech') {
            rules.enum = ['noun', 'verb', 'adjective', 'adverb', 'preposition', 'conjunction', 'interjection', 'pronoun', 'article', 'numeral'];
        } else if (fieldName.includes('definition')) {
            rules.minLength = 5;
        }
        
        return rules;
    }
    
    /**
     * Get context for field validation
     */
    getFieldContext(fieldId) {
        const field = document.querySelector(`[data-validation-target="${fieldId}"]`) || 
                     document.getElementById(fieldId) ||
                     document.querySelector(`[name="${fieldId}"]`);
        
        const context = {
            entry_id: this.getEntryId(),
            field_type: field?.type || 'text',
            section: this.getFieldSection(fieldId)
        };
        
        // Add form data context for relationship validation
        const formData = window.formSerializer?.serialize() || {};
        context.form_data = formData;
        
        return context;
    }
    
    /**
     * Get context for section validation
     */
    getSectionContext(sectionId) {
        return {
            entry_id: this.getEntryId(),
            section_id: sectionId,
            form_data: window.formSerializer?.serialize() || {}
        };
    }
    
    /**
     * Get all fields and values in a section
     */
    getSectionFields(sectionId) {
        const sectionElement = this.getSectionElement(sectionId);
        if (!sectionElement) return {};
        
        const fields = {};
        const fieldElements = sectionElement.querySelectorAll('input, textarea, select');
        
        fieldElements.forEach(field => {
            const fieldId = field.getAttribute('data-validation-target') || 
                           field.id || field.name;
            
            if (fieldId) {
                fields[fieldId] = field.value;
            }
        });
        
        return fields;
    }
    
    /**
     * Get section element for a section ID
     */
    getSectionElement(sectionId) {
        // Try different approaches to find the section
        const selectors = [
            `#${sectionId}`,
            `.${sectionId}-section`,
            `[data-section="${sectionId}"]`
        ];
        
        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element) return element;
        }
        
        // Fallback: search by header text
        const headers = document.querySelectorAll('.card-header h5, .card-header h4');
        for (const header of headers) {
            if (header.textContent.toLowerCase().includes(sectionId.replace('_', ' '))) {
                return header.closest('.card');
            }
        }
        
        return null;
    }
    
    /**
     * Get section ID from element
     */
    getSectionId(element) {
        if (element.id) return element.id;
        
        // Try to determine from classes
        const classList = Array.from(element.classList);
        for (const className of classList) {
            if (className.endsWith('-section')) {
                return className.replace('-section', '');
            }
        }
        
        // Try to determine from header text
        const header = element.querySelector('.card-header h5, .card-header h4');
        if (header) {
            const text = header.textContent.toLowerCase();
            if (text.includes('basic')) return 'basic_info';
            if (text.includes('sense')) return 'senses';
            if (text.includes('pronunciation')) return 'pronunciation';
            if (text.includes('etymology')) return 'etymology';
        }
        
        return null;
    }
    
    /**
     * Get section for a field
     */
    getFieldSection(fieldId) {
        const field = document.querySelector(`[data-validation-target="${fieldId}"]`) || 
                     document.getElementById(fieldId) ||
                     document.querySelector(`[name="${fieldId}"]`);
        
        if (!field) return null;
        
        const card = field.closest('.card');
        return this.getSectionId(card);
    }
    
    /**
     * Get current entry ID
     */
    getEntryId() {
        // Try to get from URL
        const urlMatch = window.location.pathname.match(/\/entry\/edit\/([^\/]+)/);
        if (urlMatch) return urlMatch[1];
        
        // Try to get from form data
        const entryIdField = document.querySelector('[name="entry_id"], [name="id"]');
        if (entryIdField) return entryIdField.value;
        
        // Try to get from hidden field
        const hiddenId = document.querySelector('input[type="hidden"][name*="id"]');
        if (hiddenId) return hiddenId.value;
        
        return null;
    }
    
    /**
     * Validate entire form
     */
    async validateForm() {
        try {
            const formData = window.formSerializer?.serialize() || {};
            
            const response = await fetch('/api/validation/form', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    entry_data: formData
                })
            });
            
            if (!response.ok) {
                throw new Error(`Form validation request failed: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Update UI with results
            if (result.sections) {
                Object.entries(result.sections).forEach(([sectionId, sectionResult]) => {
                    window.validationUI?.updateSectionStatus(sectionId, sectionResult);
                    
                    if (sectionResult.field_results) {
                        Object.entries(sectionResult.field_results).forEach(([fieldId, fieldResult]) => {
                            window.validationUI?.displayFieldValidation(fieldId, fieldResult);
                        });
                    }
                });
            }
            
            return result;
            
        } catch (error) {
            console.error('Form validation error:', error);
            return null;
        }
    }
    
    /**
     * Clear all validation cache
     */
    clearCache() {
        this.validationCache.clear();
    }
    
    /**
     * Validate specific fields
     */
    async validateFields(fieldIds) {
        const results = {};
        
        for (const fieldId of fieldIds) {
            const field = document.querySelector(`[data-validation-target="${fieldId}"]`) || 
                         document.getElementById(fieldId) ||
                         document.querySelector(`[name="${fieldId}"]`);
            
            if (field) {
                results[fieldId] = await this.validateField(fieldId, field.value);
            }
        }
        
        return results;
    }
}

// Global inline validation manager instance
window.inlineValidationManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.inlineValidationManager = new InlineValidationManager();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InlineValidationManager;
}
