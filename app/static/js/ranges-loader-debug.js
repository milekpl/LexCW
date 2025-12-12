/**
 * Ranges Loader Utility
 * 
 * JavaScript utility for loading LIFT ranges from the API
 * and populating dropdown/select elements dynamically.
 */

class RangesLoader {
    constructor() {
        this.cache = new Map();
        this.baseUrl = '/api/ranges';
    }
    
    /**
     * Load a specific range by ID with caching
     */
    async loadRange(rangeId) {
        console.log('[RANGES DEBUG] Loading range:', rangeId);
        if (this.cache.has(rangeId)) {
            return this.cache.get(rangeId);
        }
        
        try {
            console.log('[RANGES DEBUG] Fetching:', `${this.baseUrl}/${rangeId}`);
        const response = await fetch(`${this.baseUrl}/${rangeId}`);
        console.log('[RANGES DEBUG] Response status:', response.status);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    this.cache.set(rangeId, result.data);
                    return result.data;
                }
            }
        } catch (error) {
            console.warn(`Failed to load range ${rangeId}:`, error);
        }
        
        return null;
    }
    
    /**
     * Load all ranges at once
     */
    async loadAllRanges() {
        if (this.cache.has('__all__')) {
            return this.cache.get('__all__');
        }
        
        try {
            const response = await fetch(this.baseUrl);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    this.cache.set('__all__', result.data);
                    // Cache individual ranges too
                    Object.keys(result.data).forEach(rangeId => {
                        this.cache.set(rangeId, result.data[rangeId]);
                    });
                    return result.data;
                }
            }
        } catch (error) {
            console.warn('Failed to load all ranges:', error);
        }
        
        return null;
    }
    
    /**
     * Populate a select element with values from a range
     */
    async populateSelect(selectElement, rangeId, options = {}) {
        console.log('[RANGES DEBUG] Populating select for range:', rangeId, 'element:', selectElement);
        const {
            emptyOption = null,
            selectedValue = null,
            valueField = 'value',
            labelField = 'value',
            includeAbbrev = false
        } = options;
        
        const range = await this.loadRange(rangeId);
        if (!range || !range.values) {
            console.warn(`No values found for range ${rangeId}`);
            return false;
        }
        
        // Clear existing options (except empty option if specified)
        selectElement.innerHTML = '';
        
        // Add empty option if requested
        if (emptyOption) {
            const emptyOpt = document.createElement('option');
            emptyOpt.value = '';
            emptyOpt.textContent = emptyOption;
            selectElement.appendChild(emptyOpt);
        }
        
        // Add range values
        range.values.forEach(item => {
            const option = document.createElement('option');
            option.value = item[valueField] || item.id;
            
            let label = item[labelField] || item.value || item.id;
            if (includeAbbrev && item.abbrev) {
                label = `${label} (${item.abbrev})`;
            }
            option.textContent = label;
            
            if (selectedValue && (option.value === selectedValue || item.id === selectedValue)) {
                option.selected = true;
            }
            
            selectElement.appendChild(option);
        });
        
        return true;
    }
    
    /**
     * Get fallback values for a specific range type
     */
    /**
     * Populate select with fallback values if ranges API fails
     */
    async populateSelectWithFallback(selectElement, rangeId, options = {}) {
        console.log('[RANGES DEBUG] PopulateSelectWithFallback called for:', rangeId);
        // Keep compatibility call: we no longer provide fallback values.
        const success = await this.populateSelect(selectElement, rangeId, options);
        if (!success) {
            console.warn(`[RANGES DEBUG] Failed to populate select for ${rangeId}; no fallback values inserted`);
        }
        return success;
    }
    
    /**
     * Clear cache (useful for testing or when ranges are updated)
     */
    clearCache() {
        this.cache.clear();
    }
}

// Create global instance
window.rangesLoader = new RangesLoader();
