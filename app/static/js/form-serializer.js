/**
 * Form Serialization Utility
 * 
 * A robust utility for converting HTML form data to structured JSON objects.
 * Supports complex field naming conventions including:
 * - Simple fields: name, email
 * - Dot notation: user.name, address.city
 * - Array notation: items[0], items[1]
 * - Complex notation: items[0].name, users[2].addresses[0].street
 * 
 * @author Dictionary App Team
 * @version 1.0.0
 */

/**
 * Serializes a form to a structured JSON object
 * @param {HTMLFormElement|FormData} input - Form element or FormData object
 * @param {Object} options - Configuration options
 * @param {boolean} options.includeEmpty - Include empty string values (default: true)
 * @param {boolean} options.includeDisabled - Include disabled fields (default: false)
 * @param {Function} options.transform - Transform function for values
 * @returns {Object} Structured JSON object
 */
function serializeFormToJSON(input, options = {}) {
    const config = {
        includeEmpty: true,
        includeDisabled: false,
        transform: null,
        ...options
    };
    
    let formData;
    
    // Handle different input types
    if (typeof HTMLFormElement !== 'undefined' && input instanceof HTMLFormElement) {
        formData = new FormData(input);
        
        // If we don't want disabled fields, we need to filter them out manually
        if (!config.includeDisabled) {
            const disabledFields = input.querySelectorAll('[disabled]');
            disabledFields.forEach(field => {
                if (field.name) {
                    formData.delete(field.name);
                }
            });
        }
    } else if (typeof FormData !== 'undefined' && input instanceof FormData) {
        formData = input;
    } else if (input && typeof input.forEach === 'function') {
        // Duck typing for FormData-like objects (for testing)
        formData = input;
    } else {
        throw new Error('Input must be an HTMLFormElement, FormData object, or FormData-like object');
    }
    
    const result = {};
    
    // Process each form field
    formData.forEach((value, key) => {
        // Skip empty values if configured to do so
        if (!config.includeEmpty && value === '') {
            return;
        }
        
        // Apply transform function if provided
        const processedValue = config.transform ? config.transform(value, key) : value;
        
        // Parse the field path and set the value
        setNestedValue(result, key, processedValue);
    });
    
    return result;
}

/**
 * Sets a value in a nested object using a field path
 * @param {Object} obj - Target object
 * @param {string} path - Field path (e.g., 'users[0].name', 'address.city')
 * @param {*} value - Value to set
 */
function setNestedValue(obj, path, value) {
    const keys = parseFieldPath(path);
    let current = obj;
    for (let i = 0; i < keys.length; i++) {
        const { key, isArrayIndex } = keys[i];
        const isLast = i === keys.length - 1;

        if (isLast) {
            if (isArrayIndex) {
                // If the last key is an array index, ensure current is an array
                if (!Array.isArray(current)) {
                    // Convert to array if not already
                    const arr = [];
                    Object.keys(current).forEach(k => {
                        if (!isNaN(Number(k))) arr[Number(k)] = current[k];
                    });
                    current = arr;
                }
                const index = parseInt(key);
                while (current.length <= index) {
                    current.push(undefined);
                }
                current[index] = value;
            } else {
                current[key] = value;
            }
            return;
        }

        if (isArrayIndex) {
            // This is an array index - current should be an array
            if (!Array.isArray(current)) {
                // Convert to array if not already
                const arr = [];
                Object.keys(current).forEach(k => {
                    if (!isNaN(Number(k))) arr[Number(k)] = current[k];
                });
                current = arr;
            }
            const index = parseInt(key);
            while (current.length <= index) {
                current.push({});
            }
            if (typeof current[index] !== 'object' || current[index] === null) {
                current[index] = {};
            }
            current = current[index];
        } else {
            // This is an object key
            if (!current[key]) {
                // Look ahead to see if next key is array index
                const nextIsArrayIndex = i + 1 < keys.length && keys[i + 1].isArrayIndex;
                current[key] = nextIsArrayIndex ? [] : {};
            }
            current = current[key];
        }
    }
}

/**
 * Parses a field path into an array of key objects
 * @param {string} path - Field path to parse
 * @returns {Array<{key: string, isArrayIndex: boolean}>} Parsed keys
 */
function parseFieldPath(path) {
    const keys = [];
    let currentPath = path;
    
    // Keep parsing until we've consumed the entire path
    while (currentPath.length > 0) {
        // Check for array notation first: name[index]
        const arrayMatch = currentPath.match(/^([^.[]+)\[(\d+)\]/);
        if (arrayMatch) {
            const [fullMatch, arrayName, index] = arrayMatch;
            keys.push({ key: arrayName, isArrayIndex: false });
            keys.push({ key: index, isArrayIndex: true });
            currentPath = currentPath.substring(fullMatch.length);
            
            // Check if there's more after the bracket (like ].property)
            if (currentPath.startsWith('.')) {
                currentPath = currentPath.substring(1); // Remove leading dot
            }
            continue;
        }
        
        // Check for simple property with dots: property.subproperty
        const dotIndex = currentPath.indexOf('.');
        const bracketIndex = currentPath.indexOf('[');
        
        if (dotIndex === -1 && bracketIndex === -1) {
            // No more dots or brackets - take the rest
            keys.push({ key: currentPath, isArrayIndex: false });
            break;
        } else if (dotIndex !== -1 && (bracketIndex === -1 || dotIndex < bracketIndex)) {
            // Next separator is a dot
            const propertyName = currentPath.substring(0, dotIndex);
            keys.push({ key: propertyName, isArrayIndex: false });
            currentPath = currentPath.substring(dotIndex + 1);
        } else {
            // Next separator is a bracket - continue to next iteration to handle it
            const propertyName = currentPath.substring(0, bracketIndex);
            if (propertyName) {
                keys.push({ key: propertyName, isArrayIndex: false });
                currentPath = currentPath.substring(bracketIndex);
            }
        }
    }
    
    return keys;
}

/**
 * Validates that a form can be serialized without errors
 * @param {HTMLFormElement} form - Form to validate
 * @returns {Object} Validation result with success flag and any errors
 */
function validateFormForSerialization(form) {
    const result = {
        success: true,
        errors: [],
        warnings: []
    };
    
    const formData = new FormData(form);
    const fieldNames = [];
    
    formData.forEach((value, key) => {
        fieldNames.push(key);
        
        // Check for potentially problematic field names
        if (key.includes('..')) {
            result.warnings.push(`Field "${key}" contains consecutive dots which may cause issues`);
        }
        
        if (key.includes('[]') && !key.endsWith('[]')) {
            result.warnings.push(`Field "${key}" contains empty array notation in middle of path`);
        }
        
        // Try to parse the field path
        try {
            parseFieldPath(key);
        } catch (error) {
            result.success = false;
            result.errors.push(`Cannot parse field path "${key}": ${error.message}`);
        }
    });
    
    // Check for duplicate array indices that might indicate missing fields
    const arrayFields = fieldNames.filter(name => name.includes('[') && name.includes(']'));
    const arrayGroups = {};
    
    arrayFields.forEach(fieldName => {
        const match = fieldName.match(/^([^[]+)\[(\d+)\]/);
        if (match) {
            const [, arrayName, index] = match;
            if (!arrayGroups[arrayName]) {
                arrayGroups[arrayName] = [];
            }
            arrayGroups[arrayName].push(parseInt(index));
        }
    });
    
    // Check for gaps in array indices
    Object.entries(arrayGroups).forEach(([arrayName, indices]) => {
        const sortedIndices = [...new Set(indices)].sort((a, b) => a - b);
        for (let i = 0; i < sortedIndices.length - 1; i++) {
            if (sortedIndices[i + 1] - sortedIndices[i] > 1) {
                result.warnings.push(`Array "${arrayName}" has gaps in indices: missing index ${sortedIndices[i] + 1}`);
            }
        }
    });
    
    return result;
}

// Export for both Node.js and browser environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        serializeFormToJSON,
        setNestedValue,
        parseFieldPath,
        validateFormForSerialization
    };
} else if (typeof window !== 'undefined') {
    window.FormSerializer = {
        serializeFormToJSON,
        setNestedValue,
        parseFieldPath,
        validateFormForSerialization
    };
}
