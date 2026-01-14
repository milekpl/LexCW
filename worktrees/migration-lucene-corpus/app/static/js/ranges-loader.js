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
        this.baseUrl = '/api/ranges-editor';
    }

    log(message, ...args) {
        Logger.debug(`[RangesLoader] ${message}`, ...args);
    }
    
    /**
     * Load a specific range by ID with caching
     */
    async loadRange(rangeId) {
        // Return from cache if available
        if (this.cache.has(rangeId)) {
            return this.cache.get(rangeId);
        }

        this.log(`Loading range: ${rangeId}`);

        try {
            // Try direct per-range endpoint first
            let response = await fetch(`${this.baseUrl}/${rangeId}`);

            if (response.ok) {
                const result = await response.json();
                if (result && result.success && result.data) {
                    this.cache.set(rangeId, result.data);
                    this.log(`Successfully cached range ${rangeId} with ${result.data.values?.length || 0} values`);
                    return result.data;
                }
                this.log(`API returned success=false or no data for ${rangeId}:`, result);
            } else if (response.status === 404) {
                // If the per-range endpoint is not found, refresh the full ranges index and retry
                this.log(`Range ${rangeId} returned 404 - refreshing /api/ranges-editor and retrying`);
                const all = await this.loadAllRanges();
                if (all && all[rangeId]) {
                    this.log(`Found ${rangeId} after refresh in /api/ranges-editor; caching and returning`);
                    this.cache.set(rangeId, all[rangeId]);
                    return all[rangeId];
                }
                this.log(`Range ${rangeId} still not present after refreshing /api/ranges-editor`);
            } else {
                this.log(`HTTP error ${response.status} for range ${rangeId}`);
            }
        } catch (error) {
            this.log(`Failed to load range ${rangeId}:`, error);
        }

        // No data available
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
            valueField = 'id',
            labelField = 'effective_label',
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
        if (searchable && typeof $ !== 'undefined' && typeof $.fn.select2 === 'function') {
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
            // Prefer explicit effective_label/effective_abbrev when available, then fall back
            const itemLabel = item[labelField] || item.effective_label || item.value || item.label || item.id || item.name || '';
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
            
            // Handle selected values for single- and multi-selects
            if (selectElement.multiple) {
                // Normalize selectedValue into an array
                let selArray = [];
                if (Array.isArray(selectedValue)) selArray = selectedValue.map(String);
                else if (selectedValue) {
                    try {
                        const parsed = JSON.parse(selectedValue);
                        if (Array.isArray(parsed)) selArray = parsed.map(String);
                        else selArray = String(selectedValue).split(/[,;]+/).map(s => s.trim()).filter(Boolean);
                    } catch (e) {
                        selArray = String(selectedValue).split(/[,;]+/).map(s => s.trim()).filter(Boolean);
                    }
                } else {
                    // Also check for existing selected options on the select (e.g., server-rendered)
                    selArray = Array.from(selectElement.querySelectorAll('option[selected]')).map(o => o.value);
                }

                if (selArray.includes(String(option.value)) || selArray.includes(String(item.id))) {
                    option.selected = true;
                }
            } else {
                if (selectedValue && (option.value === selectedValue || item.id === selectedValue)) {
                    option.selected = true;
                }
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
            option.textContent = item[labelField] || item.effective_label || item.value || item.id || '';

            if (selectElement.multiple) {
                // Normalize selectedValue into an array
                let selArray = [];
                if (Array.isArray(selectedValue)) selArray = selectedValue.map(String);
                else if (selectedValue) {
                    try {
                        const parsed = JSON.parse(selectedValue);
                        if (Array.isArray(parsed)) selArray = parsed.map(String);
                        else selArray = String(selectedValue).split(/[,;]+/).map(s => s.trim()).filter(Boolean);
                    } catch (e) {
                        selArray = String(selectedValue).split(/[,;]+/).map(s => s.trim()).filter(Boolean);
                    }
                } else {
                    selArray = Array.from(selectElement.querySelectorAll('option[selected]')).map(o => o.value);
                }

                if (selArray.includes(String(option.value)) || selArray.includes(String(item.id))) {
                    option.selected = true;
                }
            } else {
                if (selectedValue && (option.value === selectedValue || item.id === selectedValue)) {
                    option.selected = true;
                }
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
            // Show a user-visible banner telling them to use the Ranges Editor
            this._showRangesMissingBanner();
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

    _showRangesMissingBanner() {
        // If banner already present, do nothing
        if (document.getElementById('ranges-missing-banner')) return;

        const container = document.querySelector('main') || document.body;
        const banner = document.createElement('div');
        banner.id = 'ranges-missing-banner';
        banner.className = 'alert alert-warning mt-3';
        banner.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>Ranges not configured.</strong>
                    <div class="small">This project has no LIFT ranges loaded. Use the <a href="/ranges-editor">Ranges Editor</a> to add ranges, or install a minimal recommended set to get started.</div>
                </div>
                <div>
                    <button id="install-recommended-ranges" class="btn btn-sm btn-primary me-2">Install recommended ranges</button>
                    <a href="/ranges-editor" class="btn btn-sm btn-outline-secondary">Open Ranges Editor</a>
                </div>
            </div>
        `;

        container.prepend(banner);

        document.getElementById('install-recommended-ranges').addEventListener('click', async () => {
            try {
                // Get CSRF token
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
                const headers = {};
                if (csrfToken) {
                    headers['X-CSRF-TOKEN'] = csrfToken;
                }
                const resp = await fetch('/api/ranges-editor/install_recommended', { method: 'POST', headers: headers });
                const data = await resp.json();
                if (resp.ok && data.success) {
                    banner.className = 'alert alert-success mt-3';
                    banner.querySelector('strong').textContent = 'Recommended ranges installed.';
                    // Reload ranges
                    await this.loadAllRanges();
                    // Try populating selects again
                    await this.populateAllRangeSelects();
                } else {
                    throw new Error(data.error || 'Failed to install recommended ranges');
                }
            } catch (err) {
                banner.className = 'alert alert-danger mt-3';
                banner.querySelector('strong').textContent = 'Failed to install recommended ranges.';
                console.error('[RangesLoader] install recommended failed', err);
            }
        });
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
