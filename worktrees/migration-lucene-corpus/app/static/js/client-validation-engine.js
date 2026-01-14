/**
 * ClientValidationEngine - Client-side validation using centralized rules
 * 
 * Provides client-side validation using the same rules as the server-side
 * validation system, fetched from the centralized validation API.
 * 
 * @author Dictionary System
 * @version 1.0.0
 */

class ClientValidationEngine {
    /**
     * Initialize ClientValidationEngine
     */
    constructor() {
        this.rules = null;
        this.customValidators = new Map();
        this.validationCache = new Map();
        this.ready = this.loadValidationRules();
        
        console.log('[ClientValidationEngine] Initialized');
    }
    
    /**
     * Load validation rules from server
     * @returns {Promise} Promise that resolves when rules are loaded
     */
    async loadValidationRules() {
        try {
            const response = await fetch('/api/validation/rules');
            if (!response.ok) {
                throw new Error(`Failed to load validation rules: ${response.status}`);
            }
            
            const rulesData = await response.json();
            this.rules = rulesData.rules || rulesData;
            
            // Set up custom validators
            this.setupCustomValidators();
            
            console.log(`[ClientValidationEngine] Loaded ${Object.keys(this.rules).length} validation rules`);
            return this.rules;
            
        } catch (error) {
            console.error('[ClientValidationEngine] Failed to load validation rules:', error);
            // Fallback to basic validation if server rules unavailable
            this.setupFallbackValidation();
            throw error;
        }
    }
    
    /**
     * Set up custom validation functions
     */
    setupCustomValidators() {
        // Language code validation
        this.customValidators.set('validate_language_codes', (value, context) => {
            const validLanguages = ['seh', 'en', 'pt', 'es', 'fr'];
            if (typeof value === 'object' && value !== null) {
                const invalidLangs = Object.keys(value).filter(lang => !validLanguages.includes(lang));
                return {
                    valid: invalidLangs.length === 0,
                    errors: invalidLangs.length > 0 ? [`Invalid language codes: ${invalidLangs.join(', ')}`] : []
                };
            }
            return { valid: true, errors: [] };
        });
        
        // Note type uniqueness validation
        this.customValidators.set('validate_unique_note_types', (value, context) => {
            if (typeof value === 'object' && value !== null) {
                const types = Object.keys(value);
                const uniqueTypes = new Set(types);
                return {
                    valid: types.length === uniqueTypes.size,
                    errors: types.length !== uniqueTypes.size ? ['Duplicate note types found'] : []
                };
            }
            return { valid: true, errors: [] };
        });
        
        // IPA pronunciation validation
        this.customValidators.set('validate_ipa_pronunciation', (value, context) => {
            if (!value || typeof value !== 'string') return { valid: true, errors: [] };
            
            const validIpaChars = /^[bdfghjklmnprstwvzðθŋʃʒɑæɒəɜɪiʊuʌeɔːˈˌ\s\-\[\]]+$/;
            const doubleStressPattern = /[ˈˌ]{2,}/;
            const doubleLengthPattern = /ː{2,}/;
            
            const errors = [];
            
            if (!validIpaChars.test(value)) {
                errors.push('Contains invalid IPA characters');
            }
            
            if (doubleStressPattern.test(value)) {
                errors.push('Contains consecutive stress markers');
            }
            
            if (doubleLengthPattern.test(value)) {
                errors.push('Contains consecutive length markers');
            }
            
            return { valid: errors.length === 0, errors };
        });
        
        console.log(`[ClientValidationEngine] Set up ${this.customValidators.size} custom validators`);
    }
    
    /**
     * Set up fallback validation when server rules are unavailable
     */
    setupFallbackValidation() {
        this.rules = {
            'R1.1.1': {
                id: 'R1.1.1',
                message: 'Entry ID is required and must be non-empty',
                priority: 'critical',
                json_path: '$.id',
                validation_function: 'required'
            },
            'R1.1.2': {
                id: 'R1.1.2',
                message: 'Lexical unit is required and must contain at least one language entry',
                priority: 'critical',
                json_path: '$.lexical_unit',
                validation_function: 'required_object'
            },
            'R1.1.3': {
                id: 'R1.1.3',
                message: 'At least one sense is required per entry',
                priority: 'critical',
                json_path: '$.senses',
                validation_function: 'required_array'
            }
        };
        
        console.warn('[ClientValidationEngine] Using fallback validation rules');
    }
    
    /**
     * Validate a single field
     * @param {string} jsonPath - JSON path of the field
     * @param {*} value - Field value
     * @param {Object} context - Complete form context
     * @returns {Promise<Array>} Array of validation errors
     */
    async validateField(jsonPath, value, context = {}) {
        await this.ready; // Ensure rules are loaded
        
        const cacheKey = `${jsonPath}:${JSON.stringify(value)}`;
        if (this.validationCache.has(cacheKey)) {
            return this.validationCache.get(cacheKey);
        }
        
        const applicableRules = this.getRulesForPath(jsonPath);
        const results = [];
        
        for (const rule of applicableRules) {
            const result = await this.executeRule(rule, value, context);
            if (!result.valid) {
                results.push({
                    ruleId: rule.id,
                    message: rule.message,
                    priority: rule.priority,
                    fieldPath: jsonPath,
                    errors: result.errors || [rule.message]
                });
            }
        }
        
        // Cache result for performance
        this.validationCache.set(cacheKey, results);
        
        return results;
    }
    
    /**
     * Validate complete form data
     * @param {Object} formData - Complete form data
     * @returns {Promise<Object>} Validation result
     */
    async validateCompleteForm(formData) {
        try {
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
            const headers = { 'Content-Type': 'application/json' };
            if (csrfToken) {
                headers['X-CSRF-TOKEN'] = csrfToken;
            }

            // Send to server for comprehensive validation
            const response = await fetch('/api/validate', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                throw new Error(`Validation request failed: ${response.status}`);
            }

            const result = await response.json();
            return this.normalizeValidationResult(result);

        } catch (error) {
            console.error('[ClientValidationEngine] Server validation failed:', error);

            // Fallback to client-side validation
            return await this.validateFormDataLocally(formData);
        }
    }
    
    /**
     * Validate form data using client-side rules only
     * @param {Object} formData - Form data to validate
     * @returns {Promise<Object>} Validation result
     */
    async validateFormDataLocally(formData) {
        await this.ready;
        
        const errors = [];
        const warnings = [];
        
        // Validate each field path in the form data
        const fieldPaths = this.extractFieldPaths(formData);
        
        for (const path of fieldPaths) {
            const value = this.getValueAtPath(formData, path);
            const fieldResults = await this.validateField(path, value, formData);
            
            fieldResults.forEach(result => {
                if (result.priority === 'critical') {
                    errors.push(result);
                } else if (result.priority === 'warning') {
                    warnings.push(result);
                }
            });
        }
        
        return {
            valid: errors.length === 0,
            errors,
            warnings,
            validatedAt: new Date().toISOString()
        };
    }
    
    /**
     * Get validation rules applicable to a JSON path
     * @param {string} jsonPath - JSON path
     * @returns {Array} Array of applicable rules
     */
    getRulesForPath(jsonPath) {
        if (!this.rules) return [];
        
        return Object.values(this.rules).filter(rule => {
            if (!rule.json_path) return false;
            
            // Exact match
            if (rule.json_path === jsonPath) return true;
            
            // Pattern match (simplified)
            const rulePath = rule.json_path.replace(/\[\d+\]/g, '[*]');
            const testPath = jsonPath.replace(/\[\d+\]/g, '[*]');
            
            return rulePath === testPath;
        });
    }
    
    /**
     * Execute a validation rule
     * @param {Object} rule - Validation rule
     * @param {*} value - Value to validate
     * @param {Object} context - Validation context
     * @returns {Promise<Object>} Validation result
     */
    async executeRule(rule, value, context) {
        const validationFunction = rule.validation_function;
        
        // Check custom validators first
        if (this.customValidators.has(validationFunction)) {
            return this.customValidators.get(validationFunction)(value, context);
        }
        
        // Built-in validation functions
        switch (validationFunction) {
            case 'required':
                return this.validateRequired(value);
            case 'required_object':
                return this.validateRequiredObject(value);
            case 'required_array':
                return this.validateRequiredArray(value);
            case 'non_empty_string':
                return this.validateNonEmptyString(value);
            case 'valid_id_format':
                return this.validateIdFormat(value);
            default:
                console.warn(`[ClientValidationEngine] Unknown validation function: ${validationFunction}`);
                return { valid: true, errors: [] };
        }
    }
    
    /**
     * Normalize validation result from server
     * @param {Object} result - Server validation result
     * @returns {Object} Normalized result
     */
    normalizeValidationResult(result) {
        return {
            valid: result.valid || result.success || false,
            errors: (result.errors || []).map(error => ({
                ruleId: error.rule_id || error.ruleId,
                message: error.message,
                priority: error.priority || 'critical',
                fieldPath: error.field_path || error.fieldPath
            })),
            warnings: (result.warnings || []).map(warning => ({
                ruleId: warning.rule_id || warning.ruleId,
                message: warning.message,
                priority: warning.priority || 'warning',
                fieldPath: warning.field_path || warning.fieldPath
            })),
            validatedAt: result.validatedAt || new Date().toISOString()
        };
    }
    
    /**
     * Extract all field paths from form data
     * @param {Object} data - Form data
     * @param {string} prefix - Path prefix
     * @returns {Array} Array of field paths
     */
    extractFieldPaths(data, prefix = '$') {
        const paths = [];
        
        if (Array.isArray(data)) {
            data.forEach((item, index) => {
                paths.push(`${prefix}[${index}]`);
                if (typeof item === 'object' && item !== null) {
                    paths.push(...this.extractFieldPaths(item, `${prefix}[${index}]`));
                }
            });
        } else if (typeof data === 'object' && data !== null) {
            Object.keys(data).forEach(key => {
                const currentPath = prefix === '$' ? `$.${key}` : `${prefix}.${key}`;
                paths.push(currentPath);
                
                if (typeof data[key] === 'object' && data[key] !== null) {
                    paths.push(...this.extractFieldPaths(data[key], currentPath));
                }
            });
        }
        
        return paths;
    }
    
    /**
     * Get value at JSON path
     * @param {Object} data - Data object
     * @param {string} path - JSON path
     * @returns {*} Value at path
     */
    getValueAtPath(data, path) {
        const pathParts = path.replace(/^\$\./, '').split(/[\.\[\]]+/).filter(Boolean);
        let current = data;
        
        for (const part of pathParts) {
            if (current && typeof current === 'object' && part in current) {
                current = current[part];
            } else {
                return undefined;
            }
        }
        
        return current;
    }
    
    // === Built-in validation functions ===
    
    validateRequired(value) {
        const valid = value !== null && value !== undefined && value !== '';
        return {
            valid,
            errors: valid ? [] : ['This field is required']
        };
    }
    
    validateRequiredObject(value) {
        const valid = value && typeof value === 'object' && Object.keys(value).length > 0;
        return {
            valid,
            errors: valid ? [] : ['This field must be a non-empty object']
        };
    }
    
    validateRequiredArray(value) {
        const valid = Array.isArray(value) && value.length > 0;
        return {
            valid,
            errors: valid ? [] : ['This field must be a non-empty array']
        };
    }
    
    validateNonEmptyString(value) {
        const valid = typeof value === 'string' && value.trim().length > 0;
        return {
            valid,
            errors: valid ? [] : ['This field must be a non-empty string']
        };
    }
    
    validateIdFormat(value) {
        const valid = typeof value === 'string' && /^[a-zA-Z0-9_-]+$/.test(value);
        return {
            valid,
            errors: valid ? [] : ['ID must contain only letters, numbers, hyphens, and underscores']
        };
    }
    
    /**
     * Clear validation cache
     */
    clearCache() {
        this.validationCache.clear();
        console.log('[ClientValidationEngine] Validation cache cleared');
    }
    
    /**
     * Get validation statistics
     * @returns {Object} Validation statistics
     */
    getStats() {
        return {
            rulesLoaded: this.rules ? Object.keys(this.rules).length : 0,
            customValidators: this.customValidators.size,
            cacheSize: this.validationCache.size,
            ready: this.ready
        };
    }
    
    /**
     * Register a custom validation function
     * @param {string} name - Validator name
     * @param {Function} validator - Validator function
     */
    registerCustomValidator(name, validator) {
        this.customValidators.set(name, validator);
        console.log(`[ClientValidationEngine] Registered custom validator: ${name}`);
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.ClientValidationEngine = ClientValidationEngine;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ClientValidationEngine;
}
