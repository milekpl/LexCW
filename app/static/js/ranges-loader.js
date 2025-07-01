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
        if (this.cache.has(rangeId)) {
            return this.cache.get(rangeId);
        }
        
        try {
            const response = await fetch(`${this.baseUrl}/${rangeId}`);
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
    getFallbackValues(rangeId) {
        const fallbacks = {
            'grammatical-info': [
                { id: 'Noun', value: 'Noun', abbrev: 'n' },
                { id: 'Verb', value: 'Verb', abbrev: 'v' },
                { id: 'Adjective', value: 'Adjective', abbrev: 'adj' },
                { id: 'Adverb', value: 'Adverb', abbrev: 'adv' },
                { id: 'Pronoun', value: 'Pronoun', abbrev: 'pr' },
                { id: 'Preposition', value: 'Preposition', abbrev: 'prep' },
                { id: 'Conjunction', value: 'Conjunction', abbrev: 'conj' },
                { id: 'Interjection', value: 'Interjection', abbrev: 'interj' },
                { id: 'Article', value: 'Article', abbrev: 'art' }
            ],
            'relation-types': [
                { id: 'synonym', value: 'synonym', abbrev: 'syn' },
                { id: 'antonym', value: 'antonym', abbrev: 'ant' },
                { id: 'hypernym', value: 'hypernym', abbrev: 'hyper' },
                { id: 'hyponym', value: 'hyponym', abbrev: 'hypo' },
                { id: 'meronym', value: 'meronym', abbrev: 'mero' }
            ],
            'variant-types': [
                { id: 'dialectal', value: 'dialectal', abbrev: 'dial' },
                { id: 'spelling', value: 'spelling', abbrev: 'sp' },
                { id: 'morphological', value: 'morphological', abbrev: 'morph' },
                { id: 'phonetic', value: 'phonetic', abbrev: 'phon' }
            ]
        };
        
        return fallbacks[rangeId] || [];
    }
    
    /**
     * Populate select with fallback values if ranges API fails
     */
    async populateSelectWithFallback(selectElement, rangeId, options = {}) {
        const success = await this.populateSelect(selectElement, rangeId, options);
        
        if (!success) {
            console.warn(`Using fallback values for range ${rangeId}`);
            const fallbackValues = this.getFallbackValues(rangeId);
            
            // Clear and populate with fallback
            selectElement.innerHTML = '';
            
            if (options.emptyOption) {
                const emptyOpt = document.createElement('option');
                emptyOpt.value = '';
                emptyOpt.textContent = options.emptyOption;
                selectElement.appendChild(emptyOpt);
            }
            
            fallbackValues.forEach(item => {
                const option = document.createElement('option');
                option.value = item.value;
                option.textContent = options.includeAbbrev && item.abbrev ? 
                    `${item.value} (${item.abbrev})` : item.value;
                
                if (options.selectedValue && option.value === options.selectedValue) {
                    option.selected = true;
                }
                
                selectElement.appendChild(option);
            });
        }
        
        return true;
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
