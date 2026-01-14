(function(global) {
    function normalizeIndexedArray(value) {
        if (value === undefined || value === null) {
            return [];
        }

        if (Array.isArray(value)) {
            return value;
        }

        if (typeof value === 'object') {
            const entries = Object.entries(value)
                .filter(([key]) => key !== '__proto__' && key !== 'constructor' && key !== 'prototype' && !Number.isNaN(Number(key)))
                .sort((a, b) => Number(a[0]) - Number(b[0]));

            return entries.map(([, val]) => val);
        }

        return [];
    }

    // Expose globally for browser usage
    global.normalizeIndexedArray = normalizeIndexedArray;

    // Export for Node/testing environments
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { normalizeIndexedArray };
    }
})(typeof window !== 'undefined' ? window : globalThis);
