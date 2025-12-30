/**
 * API Utility Functions
 * 
 * Provides common functions for handling API requests and responses
 * to reduce code duplication across JavaScript files.
 */

/**
 * Makes an API request with common error handling and response formatting
 * 
 * @param {string} url - The API endpoint URL
 * @param {string} method - HTTP method (GET, POST, PUT, DELETE, etc.)
 * @param {Object} options - Additional options for the request
 * @param {Object} options.data - Data to send with the request (for POST/PUT)
 * @param {Object} options.headers - Additional headers to include
 * @param {Function} options.onSuccess - Callback for successful response
 * @param {Function} options.onError - Callback for error response
 * @param {boolean} options.showLoading - Whether to show loading indicator
 * @returns {Promise} The API response
 */
function makeApiRequest(url, method = 'GET', options = {}) {
    const {
        data = null,
        headers = {},
        onSuccess = null,
        onError = null,
        showLoading = true
    } = options;

    // Show loading indicator if requested
    if (showLoading && typeof showLoadingIndicator === 'function') {
        showLoadingIndicator();
    }

    // Default headers
    const defaultHeaders = {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        ...headers
    };

    // Prepare request options
    const requestOptions = {
        method: method.toUpperCase(),
        headers: defaultHeaders,
    };

    // Add body for methods that support it
    if (data && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase())) {
        requestOptions.body = JSON.stringify(data);
    }

    return fetch(url, requestOptions)
        .then(response => {
            // Hide loading indicator
            if (showLoading && typeof hideLoadingIndicator === 'function') {
                hideLoadingIndicator();
            }

            // Handle non-JSON responses (like redirects)
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            } else {
                // For non-JSON responses, return text
                return response.text();
            }
        })
        .then(result => {
            // Check if the API response follows the standard format {success: boolean, data/error: ...}
            if (result && typeof result === 'object' && 'success' in result) {
                if (result.success) {
                    if (onSuccess && typeof onSuccess === 'function') {
                        onSuccess(result.data, result);
                    }
                    return result.data;
                } else {
                    // Handle API-level error
                    const errorMsg = result.error || 'API request failed';
                    throw new Error(errorMsg);
                }
            } else {
                // Response doesn't follow standard format, return as-is
                if (onSuccess && typeof onSuccess === 'function') {
                    onSuccess(result);
                }
                return result;
            }
        })
        .catch(error => {
            // Hide loading indicator in case of error
            if (showLoading && typeof hideLoadingIndicator === 'function') {
                hideLoadingIndicator();
            }

            console.error('API request failed:', error);

            // Call error callback if provided
            if (onError && typeof onError === 'function') {
                onError(error);
            } else {
                // Show generic error message
                showToast(`Request failed: ${error.message}`, 'error');
            }

            // Re-throw the error for further handling if needed
            throw error;
        });
}

/**
 * GET request helper
 */
function apiGet(url, options = {}) {
    return makeApiRequest(url, 'GET', options);
}

/**
 * POST request helper
 */
function apiPost(url, data, options = {}) {
    return makeApiRequest(url, 'POST', { ...options, data });
}

/**
 * PUT request helper
 */
function apiPut(url, data, options = {}) {
    return makeApiRequest(url, 'PUT', { ...options, data });
}

/**
 * DELETE request helper
 */
function apiDelete(url, options = {}) {
    return makeApiRequest(url, 'DELETE', options);
}

/**
 * Shows a loading indicator
 * This is a placeholder - implement based on your UI framework
 */
function showLoadingIndicator() {
    // Example implementation - adjust based on your UI
    const loadingEl = document.getElementById('loading-indicator');
    if (loadingEl) {
        loadingEl.style.display = 'block';
    }
}

/**
 * Hides the loading indicator
 */
function hideLoadingIndicator() {
    // Example implementation - adjust based on your UI
    const loadingEl = document.getElementById('loading-indicator');
    if (loadingEl) {
        loadingEl.style.display = 'none';
    }
}

/**
 * Common error handler for API responses
 */
function handleApiError(error, context = '') {
    console.error(`API Error in ${context}:`, error);
    showToast(`An error occurred: ${error.message}`, 'error');
}

/**
 * Validates form data before submission
 * @param {HTMLElement} form - The form element to validate
 * @returns {Object} Validation result with isValid boolean and errors array
 */
function validateForm(form) {
    const errors = [];
    let isValid = true;

    // Check for required fields
    const requiredFields = form.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            errors.push(`${field.name || field.id || 'Field'} is required`);
            isValid = false;
        }
    });

    // Check for custom validation patterns
    const patternFields = form.querySelectorAll('[pattern]');
    patternFields.forEach(field => {
        if (field.value.trim()) {
            const regex = new RegExp(field.getAttribute('pattern'));
            if (!regex.test(field.value)) {
                errors.push(`${field.name || field.id || 'Field'} format is invalid`);
                isValid = false;
            }
        }
    });

    return { isValid, errors };
}

/**
 * Serializes form data to JSON object
 * @param {HTMLFormElement} form - The form to serialize
 * @returns {Object} JSON object with form field values
 */
function serializeForm(form) {
    const formData = new FormData(form);
    const object = {};
    
    for (let [key, value] of formData.entries()) {
        // Handle multiple values for the same key (like checkboxes)
        if (object[key]) {
            if (Array.isArray(object[key])) {
                object[key].push(value);
            } else {
                object[key] = [object[key], value];
            }
        } else {
            object[key] = value;
        }
    }
    
    return object;
}