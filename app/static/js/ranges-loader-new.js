/**
 * Ranges Loader Utility - Simplified Version
 * 
 * JavaScript utility for loading LIFT ranges from the API
 * and populating dropdown/select elements dynamically.
 * 
 * Focus: Just load ranges from API, no complex fallback system.
 */

class RangesLoader {
    constructor() {
        this.cache = new Map();
        this.baseUrl = '/api/ranges';
        this.debug = true;
    }
    
    log(message, ...args) {
        if (this.debug) {
            console.log(`[RangesLoader] ${message}`, ...args);
        }
    }
    
    /**
     * Load a specific range by ID with caching
     */
    async loadRange(rangeId) {
        if (this.cache.has(rangeId)) {
            return this.cache.get(rangeId);
        }
        
        try {
            this.log(`Loading range: ${rangeId}`);
            const response = await fetch(`${this.baseUrl}/${rangeId}`);
            
            if (response.ok) {
                const result = await response.json();
                
                if (result.success && result.data) {
                    this.cache.set(rangeId, result.data);
                    this.log(`Successfully cached range ${rangeId} with ${result.data.values?.length || 0} values`);
                    return result.data;
                } else {
                    this.log(`API returned success=false or no data for ${rangeId}:`, result);
                }
            } else {
                this.log(`HTTP error ${response.status} for range ${rangeId}`);
            }
        } catch (error) {
            this.log(`Failed to load range ${rangeId}:`, error);
        }
        
        return null;
    }
    
    /**
     * Load all ranges at once with caching
     */
    async loadAllRanges() {
        if (this.cache.has('__all__')) {
            return this.cache.get('__all__');
        }
        
        try {
            this.log('Loading all ranges from API');
            const response = await fetch(this.baseUrl);
            
            if (response.ok) {
                const result = await response.json();
                
                if (result.success && result.data) {
                    this.cache.set('__all__', result.data);
                    
                    // Cache individual ranges too
                    Object.keys(result.data).forEach(rangeId => {
                        this.cache.set(rangeId, result.data[rangeId]);
                    });
                    
                    this.log(`Successfully loaded ${Object.keys(result.data).length} ranges`);
                    return result.data;
                } else {
                    this.log('API returned success=false or no data for all ranges:', result);
                }
            } else {
                this.log(`HTTP error ${response.status} when loading all ranges`);
            }
        } catch (error) {
            this.log('Failed to load all ranges:', error);
        }
        
        return null;
    }
    
    /**
     * Populate a select element with values from a range
     */
    async populateSelect(selectElement, rangeId, options = {}) {
        const {
            emptyOption = 'Select option',
            selectedValue = null,
            valueField = 'value',
            labelField = 'value'
        } = options;
        
        this.log(`Populating select for range: ${rangeId}`);
        
        const range = await this.loadRange(rangeId);
        if (!range || !range.values) {
            this.log(`No values found for range ${rangeId}`);
            return false;
        }
        
        // Clear existing options
        selectElement.innerHTML = '';
        
        // Add empty option
        const emptyOpt = document.createElement('option');
        emptyOpt.value = '';
        emptyOpt.textContent = emptyOption;
        selectElement.appendChild(emptyOpt);
        
        // Add range values
        range.values.forEach(item => {
            const option = document.createElement('option');
            option.value = item[valueField] || item.id || item.value;
            option.textContent = item[labelField] || item.value || item.id;
            
            if (selectedValue && (option.value === selectedValue || item.id === selectedValue)) {
                option.selected = true;
            }
            
            selectElement.appendChild(option);
        });
        
        this.log(`Populated select with ${range.values.length} options`);
        return true;
    }
    
    /**
     * Populate all selects marked with data-range-id attributes
     */
    async populateAllRangeSelects() {
        this.log('Populating all range selects on page');
        
        // Load all ranges first
        const allRanges = await this.loadAllRanges();
        if (!allRanges) {
            this.log('Failed to load ranges, skipping populate');
            return false;
        }
        
        // Find all selects with data-range-id
        const selects = document.querySelectorAll('select[data-range-id]');
        this.log(`Found ${selects.length} selects with data-range-id`);
        
        for (const select of selects) {
            const rangeId = select.dataset.rangeId;
            const selectedValue = select.dataset.selected || select.value || '';
            
            this.log(`Processing select for range: ${rangeId}`);
            
            const success = await this.populateSelect(select, rangeId, {
                emptyOption: select.dataset.emptyOption || `Select ${rangeId.replace('-', ' ')}`,
                selectedValue: selectedValue
            });
            
            if (!success) {
                this.log(`Failed to populate select for range: ${rangeId}`);
            }
        }
        
        this.log('Finished populating all range selects');
        return true;
    }
    
    /**
     * Clear cache (useful for testing or when ranges are updated)
     */
    clearCache() {
        this.cache.clear();
        this.log('Cache cleared');
    }
}

// Create global instance
window.rangesLoader = new RangesLoader();

// Auto-populate on DOM loaded if not already done
document.addEventListener('DOMContentLoaded', function() {
    if (!window.rangesLoaderInitialized) {
        window.rangesLoaderInitialized = true;
        
        // Wait a bit for other scripts to initialize, then populate ranges
        setTimeout(() => {
            window.rangesLoader.populateAllRangeSelects().catch(error => {
                console.error('[RangesLoader] Failed to auto-populate ranges:', error);
            });
        }, 100);
    }
});
