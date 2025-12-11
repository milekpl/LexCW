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
 * @version 1.0.1-bugfix-sense-deletion
 */

console.log('[FormSerializer] Version 1.0.1-bugfix-sense-deletion loaded');

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

        // Filter out fields from template elements (specifically #default-sense-template)
        // BUT ONLY if there are other real sense items present
        // (On add page with no senses, the default-sense-template IS the first sense)
        const templateElement = input.querySelector('#default-sense-template');
        const realSenses = input.querySelectorAll('.sense-item:not(#default-sense-template):not(.default-sense-template)');
        
        if (templateElement && realSenses.length > 0) {
            // There are real senses, so default-sense-template is truly just a template
            const templateFields = templateElement.querySelectorAll('[name]');
            templateFields.forEach(field => {
                if (field.name) {
                    formData.delete(field.name);
                }
            });
        } else if (templateElement && realSenses.length === 0) {
            // No real senses - template IS the first sense
            // Rename fields from senses[TEMPLATE] to senses[0]
            const templateFields = templateElement.querySelectorAll('[name]');
            const renamedEntries = [];
            templateFields.forEach(field => {
                if (field.name && field.name.includes('[TEMPLATE]')) {
                    const newName = field.name.replace('[TEMPLATE]', '[0]');
                    const value = formData.get(field.name);
                    if (value !== null && value !== undefined) {
                        renamedEntries.push({ oldName: field.name, newName: newName, value: value });
                    }
                }
            });
            
            // Apply renames
            renamedEntries.forEach(entry => {
                formData.delete(entry.oldName);
                formData.set(entry.newName, entry.value);
            });
        }

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
    let fieldCount = 0;
    let lastField = null;
    // Process each form field
    formData.forEach((value, key) => {
        fieldCount++;
        lastField = key;
        if (fieldCount % 100 === 0) {
            console.debug(`[FormSerializer] Processed ${fieldCount} fields, last: ${key}`);
        }
        // Skip empty values if configured to do so
        if (!config.includeEmpty && value === '') {
            return;
        }

        // Apply transform function if provided
        const processedValue = config.transform ? config.transform(value, key) : value;

        try {
            // Defensive: try parsing the field path first to catch errors
            parseFieldPath(key);
            // Parse the field path and set the value
            setNestedValue(result, key, processedValue, 0, key);
        } catch (e) {
            console.error(`[FormSerializer] Error setting value for field '${key}':`, e);
            // Log the problematic field name and value for diagnosis
            if (typeof window !== 'undefined' && window.FormSerializerProblemFields) {
                window.FormSerializerProblemFields.push({ key, value, error: e.message });
            } else if (typeof window !== 'undefined') {
                window.FormSerializerProblemFields = [{ key, value, error: e.message }];
            }
            // Do not throw, just skip this field so the form can be saved
        }
    });
    if (typeof window !== 'undefined' && window.FormSerializerProblemFields && window.FormSerializerProblemFields.length > 0) {
        console.warn(`[FormSerializer] Skipped ${window.FormSerializerProblemFields.length} problematic fields. See window.FormSerializerProblemFields for details.`);
    }
    console.debug(`[FormSerializer] Finished processing ${fieldCount} fields. Last field: ${lastField}`);
    return result;
}

/**
 * Sets a value in a nested object using a field path
 * @param {Object} obj - Target object
 * @param {string} path - Field path (e.g., 'users[0].name', 'address.city')
 * @param {*} value - Value to set
 */
function setNestedValue(obj, path, value, depth = 0, fieldName = null) {
    const MAX_DEPTH = 30;
    const MAX_ARRAY_SIZE = 10000;
    if (depth > MAX_DEPTH) {
        console.error(`[FormSerializer] Max depth exceeded at field '${fieldName || path}'`);
        throw new Error(`Max object depth exceeded at field '${fieldName || path}'`);
    }
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
                if (index > MAX_ARRAY_SIZE) {
                    console.error(`[FormSerializer] Array index too large (${index}) at field '${fieldName || path}'`);
                    throw new Error(`Array index too large (${index}) at field '${fieldName || path}'`);
                }
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
            if (index > MAX_ARRAY_SIZE) {
                console.error(`[FormSerializer] Array index too large (${index}) at field '${fieldName || path}'`);
                throw new Error(`Array index too large (${index}) at field '${fieldName || path}'`);
            }
            while (current.length <= index) {
                current.push({});
            }
            if (typeof current[index] !== 'object' || current[index] === null) {
                current[index] = {};
            }
            // Defensive: log progress for large arrays
            if (index % 1000 === 0 && index > 0) {
                console.debug(`[FormSerializer] Large array index: ${index} at field '${fieldName || path}'`);
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
        // Defensive: log deep recursion
        if (depth + i > 0 && (depth + i) % 10 === 0) {
            console.debug(`[FormSerializer] Deep recursion at field '${fieldName || path}', depth: ${depth + i}`);
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
    let parseStep = 0;
    // Keep parsing until we've consumed the entire path
    while (currentPath.length > 0) {
        parseStep++;
        if (parseStep > 50) {
            console.error(`[FormSerializer] parseFieldPath: Too many parse steps for path '${path}'`);
            throw new Error(`parseFieldPath: Too many parse steps for path '${path}'`);
        }
        // Check for array notation first: name[index]
        const arrayMatch = currentPath.match(/^([^.[]+)\[(.+?)\]/);
        if (arrayMatch) {
            const [fullMatch, arrayName, index] = arrayMatch;
            if (!/^\d+$/.test(index)) {
                // Not a numeric index, this is a malformed field name
                throw new Error(`Invalid array index '[${index}]' in field path '${path}' (only numeric indices allowed)`);
            }
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
    if (keys.length > 20) {
        console.debug(`[FormSerializer] parseFieldPath: Long key path (${keys.length} segments) for '${path}'`);
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

/**
 * Serializes a form to a structured JSON object with safety measures
 * @param {HTMLFormElement|FormData} input - Form element or FormData object
 * @param {Object} options - Configuration options
 * @returns {Promise<Object>} Structured JSON object
 */
function serializeFormToJSONSafe(input, options = {}) {
    return new Promise((resolve, reject) => {
        // Set a reasonable timeout
        const timeout = setTimeout(() => {
            reject(new Error('Form serialization timed out. The form may be too complex.'));
        }, options.timeout || 10000);
        
        try {
            // Use a worker if available to prevent UI freezing
            if (window.Worker) {
                    try {
                    // Add a cache-busting query param so tests pick up latest worker file
                    const worker = new Worker(`/static/js/form-serializer-worker.js?v=${Date.now()}`);
                    
                    worker.onmessage = function(e) {
                        // Worker may send diagnostic messages under __debug
                        if (e.data && e.data.__debug) {
                            console.debug('[FormSerializer] Worker debug:', e.data.__debug);
                            // do not clear timeout or terminate yet; wait for real result
                            return;
                        }
                        clearTimeout(timeout);
                        if (e.data.error) {
                            // Include stack if provided by worker
                            const msg = e.data.error + (e.data.stack ? '\n' + e.data.stack : '');
                            reject(new Error(msg));
                        } else {
                            // Ensure returned result has an id to avoid older serializers throwing later
                            try {
                                if (e.data.result && !e.data.result.id) {
                                    const tempId = `temp-${Date.now()}-${Math.floor(Math.random()*10000)}`;
                                    e.data.result.id = tempId;
                                    console.warn('[FormSerializer] Worker result missing id; assigned temporary id:', tempId);
                                }
                            } catch (fixErr) {
                                console.debug('[FormSerializer] Failed to assign temp id to worker result', fixErr);
                            }
                            resolve(e.data.result);
                        }
                        worker.terminate();
                    };
                    
                    worker.onerror = function(error) {
                        clearTimeout(timeout);
                        reject(new Error(`Worker error: ${error.message}`));
                        worker.terminate();
                    };
                    
                    // Convert form to serializable format and apply the same
                    // template-field preprocessing that the synchronous
                    // serializer performs so the worker receives sanitized data.
                    let formEntries;
                    if (input instanceof HTMLFormElement) {
                        // Start with FormData entries snapshot
                        formEntries = Array.from(new FormData(input).entries());

                        // Apply template preprocessing similar to serializeFormToJSON
                        const templateElement = input.querySelector('#default-sense-template');
                        const realSenses = input.querySelectorAll('.sense-item:not(#default-sense-template):not(.default-sense-template)');

                        if (templateElement && realSenses.length > 0) {
                            // Remove template fields from entries
                            const templateFields = Array.from(templateElement.querySelectorAll('[name]')).map(f => f.name);
                            formEntries = formEntries.filter(([name, value]) => !templateFields.includes(name));
                        } else if (templateElement && realSenses.length === 0) {
                            // Rename TEMPLATE indices to 0
                            formEntries = formEntries.map(([name, value]) => {
                                if (typeof name === 'string' && name.includes('[TEMPLATE]')) {
                                    return [name.replace('[TEMPLATE]', '[0]'), value];
                                }
                                return [name, value];
                            });
                        }
                    } else {
                        formEntries = Array.from(input.entries());
                    }

                    // Log what we're about to post to the worker for diagnosis
                    try {
                        const sample = formEntries.slice(0, 10).map(e => e[0]);
                        console.debug('[FormSerializer] Posting to worker', { count: formEntries.length, sampleNames: sample });
                    } catch (logErr) {
                        console.debug('[FormSerializer] Posting to worker (could not stringify sample)', logErr);
                    }

                    worker.postMessage({
                        formData: formEntries,
                        options: options
                    });
                } catch (workerError) {
                    console.warn('Web Worker failed, falling back to synchronous processing:', workerError);
                    // Fallback to synchronous processing
                    const result = serializeFormToJSON(input, options);
                    clearTimeout(timeout);
                    resolve(result);
                }
            } else {
                // Fallback to synchronous processing
                const result = serializeFormToJSON(input, options);
                clearTimeout(timeout);
                resolve(result);
            }
        } catch (error) {
            clearTimeout(timeout);
            reject(error);
        }
    });
}

// Export for both Node.js and browser environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        serializeFormToJSON,
        serializeFormToJSONSafe,
        setNestedValue,
        parseFieldPath,
        validateFormForSerialization
    };
} else if (typeof window !== 'undefined') {
    window.FormSerializer = {
        serializeFormToJSON,
        serializeFormToJSONSafe,
        setNestedValue,
        parseFieldPath,
        validateFormForSerialization
    };
}
