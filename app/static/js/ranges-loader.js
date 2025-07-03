/**
 * Enhanced Ranges Loader Utility
 * 
 * JavaScript utility for loading LIFT ranges from the API
 * and populating dropdown/select elements dynamically with support for
 * hierarchical (nested) range values.
 */

class RangesLoader {
    constructor() {
        this.cache = new Map();
        this.baseUrl = '/api/ranges';
        this.debug = true;
        
        // Fallback data for key ranges when API is unavailable
        this.fallbackData = {
            'grammatical-info': {
                id: 'grammatical-info',
                values: [
                    { value: 'Noun', text: 'Noun' },
                    { value: 'Verb', text: 'Verb' },
                    { value: 'Adjective', text: 'Adjective' },
                    { value: 'Adverb', text: 'Adverb' },
                    { value: 'Pronoun', text: 'Pronoun' },
                    { value: 'Preposition', text: 'Preposition' },
                    { value: 'Conjunction', text: 'Conjunction' },
                    { value: 'Interjection', text: 'Interjection' }
                ]
            },
            'relation-types': {
                id: 'relation-types',
                values: [
                    { value: 'synonym', text: 'synonym' },
                    { value: 'antonym', text: 'antonym' },
                    { value: 'hypernym', text: 'hypernym' },
                    { value: 'hyponym', text: 'hyponym' },
                    { value: 'meronym', text: 'meronym' },
                    { value: 'holonym', text: 'holonym' }
                ]
            },
            'variant-types': {
                id: 'variant-types',
                values: [
                    { value: 'dialectal', text: 'dialectal' },
                    { value: 'spelling', text: 'spelling variant' },
                    { value: 'phonetic', text: 'phonetic variant' },
                    { value: 'formal', text: 'formal' },
                    { value: 'informal', text: 'informal' }
                ]
            }
        };
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
        
        // Use fallback data if API fails
        if (this.fallbackData[rangeId]) {
            this.log(`Using fallback data for range: ${rangeId}`);
            this.cache.set(rangeId, this.fallbackData[rangeId]);
            return this.fallbackData[rangeId];
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
     * Now with support for hierarchical values
     */
    async populateSelect(selectElement, rangeId, options = {}) {
        const {
            emptyOption = 'Select option',
            selectedValue = null,
            valueField = 'value',
            labelField = 'value',
            hierarchical = true, // Enable hierarchical display by default
            indentChar = '—', // Character used for indentation
            searchable = true, // Enable searchable dropdowns for hierarchical data
            flattenParents = false // Option to include parent items at the same level (useful for semantic domains)
        } = options;
        
        this.log(`Populating select for range: ${rangeId} (hierarchical: ${hierarchical})`);
        
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
        
        // Handle the hierarchical or flat display
        if (hierarchical) {
            this._populateHierarchicalOptions(selectElement, range.values, {
                selectedValue,
                valueField,
                labelField,
                indentChar,
                level: 0,
                flattenParents
            });
        } else {
            // Add range values as flat list
            this._populateFlatOptions(selectElement, range.values, {
                selectedValue,
                valueField,
                labelField
            });
        }
        
        // Initialize Select2 for searchable dropdowns if option enabled and library available
        if (searchable && typeof $.fn.select2 === 'function') {
            $(selectElement).select2({
                theme: 'bootstrap-5',
                width: '100%',
                // Allow proper indentation in dropdown
                templateResult: (data) => {
                    if (!data.id) return data.text;
                    const $option = $(data.element);
                    const indent = $option.data('indent') || 0;
                    const $result = $('<span></span>');
                    if (indent > 0) {
                        $result.html('&nbsp;'.repeat(indent * 2) + indentChar + ' ' + data.text);
                    } else {
                        $result.text(data.text);
                    }
                    return $result;
                }
            });
        }
        
        this.log(`Populated select with options from range ${rangeId}`);
        return true;
    }
    
    /**
     * Recursively populate options for hierarchical data
     */
    _populateHierarchicalOptions(selectElement, items, options, parentPath = '') {
        const {
            selectedValue,
            valueField,
            labelField,
            indentChar,
            level,
            flattenParents
        } = options;
        
        items.forEach(item => {
            const itemValue = item[valueField] || item.id || item.value;
            const itemLabel = item[labelField] || item.value || item.id;
            let displayLabel = itemLabel;
            
            // Add indentation for child items
            if (level > 0) {
                displayLabel = `${indentChar.repeat(level)} ${itemLabel}`;
            }
            
            const option = document.createElement('option');
            option.value = itemValue;
            option.textContent = displayLabel;
            option.dataset.indent = level;
            option.dataset.path = parentPath ? `${parentPath}/${itemValue}` : itemValue;
            
            if (selectedValue && (option.value === selectedValue || item.id === selectedValue)) {
                option.selected = true;
            }
            
            selectElement.appendChild(option);
            
            // Process child items if any
            if (item.children && item.children.length > 0) {
                this._populateHierarchicalOptions(
                    selectElement,
                    item.children,
                    {
                        ...options,
                        level: level + 1
                    },
                    option.dataset.path
                );
            }
        });
    }
    
    /**
     * Populate options for flat display (no hierarchy)
     */
    _populateFlatOptions(selectElement, items, options) {
        const { selectedValue, valueField, labelField } = options;
        
        // Create a flattened list of all items including children
        const flattenedItems = this._flattenItems(items);
        
        // Add all items to the select
        flattenedItems.forEach(item => {
            const option = document.createElement('option');
            option.value = item[valueField] || item.id || item.value;
            option.textContent = item[labelField] || item.value || item.id;
            
            if (selectedValue && (option.value === selectedValue || item.id === selectedValue)) {
                option.selected = true;
            }
            
            selectElement.appendChild(option);
        });
    }
    
    /**
     * Recursively flatten a hierarchical structure into a single array
     */
    _flattenItems(items, result = []) {
        items.forEach(item => {
            result.push(item);
            
            if (item.children && item.children.length > 0) {
                this._flattenItems(item.children, result);
            }
        });
        
        return result;
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
            const hierarchical = select.dataset.hierarchical !== 'false'; // Default to true
            const searchable = select.dataset.searchable !== 'false'; // Default to true
            const flattenParents = select.dataset.flattenParents === 'true'; // Default to false
            
            this.log(`Processing select for range: ${rangeId} (hierarchical: ${hierarchical})`);
            
            const success = await this.populateSelect(select, rangeId, {
                emptyOption: select.dataset.emptyOption || `Select ${rangeId.replace(/-/g, ' ')}`,
                selectedValue: selectedValue,
                hierarchical: hierarchical,
                searchable: searchable,
                flattenParents: flattenParents
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
