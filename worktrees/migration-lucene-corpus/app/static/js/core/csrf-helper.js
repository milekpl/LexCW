/**
 * CSRF Helper Utilities
 *
 * Provides consistent CSRF token retrieval and header construction
 * for API requests. Eliminates code duplication across the codebase.
 *
 * Usage:
 *   const headers = getCsrfHeaders({ 'Content-Type': 'application/json' });
 *   // Returns: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': 'token' }
 */

/**
 * Get CSRF token from meta tag or DictionaryApp config
 * @returns {string} CSRF token or empty string if not found
 */
function getCsrfToken() {
    // Try meta tag first
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
        return metaTag.getAttribute('content') || '';
    }

    // Fall back to DictionaryApp config
    if (typeof DictionaryApp !== 'undefined' &&
        DictionaryApp.config &&
        DictionaryApp.config.csrfToken) {
        return DictionaryApp.config.csrfToken;
    }

    return '';
}

/**
 * Build request headers with CSRF token
 * @param {Object} additionalHeaders - Additional headers to include
 * @returns {Object} Headers object with CSRF token if available
 */
function getCsrfHeaders(additionalHeaders = {}) {
    const csrfToken = getCsrfToken();

    if (csrfToken) {
        return {
            ...additionalHeaders,
            'X-CSRF-TOKEN': csrfToken
        };
    }

    return additionalHeaders;
}

/**
 * Check if CSRF token is available
 * @returns {boolean} True if CSRF token is present
 */
function hasCsrfToken() {
    return !!getCsrfToken();
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { getCsrfToken, getCsrfHeaders, hasCsrfToken };
}

// Make available globally
window.getCsrfToken = getCsrfToken;
window.getCsrfHeaders = getCsrfHeaders;
window.hasCsrfToken = hasCsrfToken;
