/**
 * Variant Forms Manager
 * 
 * JavaScript component for managing LIFT relation-based variants in the entry editor.
 * Displays variants from relations with variant-type traits, as per project specification.
 */

class VariantFormsManager {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.variantRelations = [];
        
        // Accept variant relations from options (passed during initialization)
        if (options.variantRelations && Array.isArray(options.variantRelations)) {
            console.log('[VARIANT DEBUG] Received variant relations via options:', options.variantRelations);
            this.variantRelations = options.variantRelations;
        }
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        
        // Delay rendering to ensure data is available
        setTimeout(() => {
            this.renderExistingVariants();
        }, 50);
    }
    
    setupEventListeners() {
        // Add variant button
        const addButton = document.getElementById('add-variant-btn');
        if (addButton) {
            addButton.addEventListener('click', () => this.addVariant());
        }
        
        // Delegate removal events
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-variant-btn')) {
                const index = parseInt(e.target.dataset.index);
                this.removeVariant(index);
            }
            
            // Handle search button clicks
            if (e.target.classList.contains('variant-search-btn')) {
                const variantIndex = e.target.dataset.variantIndex;
                this.openEntrySearchModal(variantIndex);
            }
        });
        
        // Handle entry search input
        this.container.addEventListener('input', (e) => {
            if (e.target.classList.contains('variant-search-input')) {
                this.handleEntrySearch(e.target);
            }
        });
        
        // Update header when variant type changes
        this.container.addEventListener('change', (e) => {
            if (e.target.name && e.target.name.includes('variant_type')) {
                const variantItem = e.target.closest('.variant-item');
                if (variantItem) {
                    const index = parseInt(variantItem.dataset.variantIndex);
                    const header = variantItem.querySelector('.card-header h6');
                    if (header) {
                        header.innerHTML = `
                            <i class="fas fa-code-branch me-2"></i>
                            Variant Relation ${index + 1}: ${e.target.value || 'Unknown Type'}
                        `;
                    }
                }
            }
        });
    }
    
    renderExistingVariants() {
        console.log('[VARIANT DEBUG] renderExistingVariants() called');
        console.log('[VARIANT DEBUG] this.variantRelations:', this.variantRelations);
        
        // Use variant_relations passed via constructor options, or fallback to global scope
        let existingVariants = this.variantRelations || [];
        
        // If constructor didn't provide data, try to get it from global scope
        if (existingVariants.length === 0) {
            console.log('[VARIANT DEBUG] No variants in constructor, trying global scope');
            existingVariants = this.getExistingVariantRelationsFromEntry();
        }
        
        console.log('[VARIANT DEBUG] Existing variants:', existingVariants);
        console.log('[VARIANT DEBUG] Variant count:', existingVariants.length);
        
        // Clear container
        this.container.innerHTML = '';
        
        // Render each existing variant relation
        existingVariants.forEach((variantRelation, index) => {
            console.log('[VARIANT DEBUG] Rendering variant', index, ':', variantRelation);
            this.renderVariantRelation(variantRelation, index);
        });
        
        // If no variants exist, show empty state
        if (existingVariants.length === 0) {
            console.log('[VARIANT DEBUG] No variants found, showing empty state');
            this.showEmptyState();
        } else {
            console.log('[VARIANT DEBUG] Rendered', existingVariants.length, 'variants');
        }
        
        // Initialize tooltips for any existing content
        this.initializeTooltips();
    }
    
    getExistingVariantRelationsFromEntry() {
        // Extract variant relations from the global entry data if available
        const variants = [];
        
        console.log('[VARIANT DEBUG] Starting getExistingVariantRelationsFromEntry()');
        
        try {
            // Check if variant relations are available in the window
            if (typeof window.variantRelations !== 'undefined' && Array.isArray(window.variantRelations)) {
                console.log('[VARIANT DEBUG] Found window.variantRelations:', window.variantRelations);
                console.log('[VARIANT DEBUG] Length:', window.variantRelations.length);
                return window.variantRelations;
            }
            
            // Fallback: look for entryData with variant_relations
            if (typeof entryData !== 'undefined' && entryData.variant_relations) {
                console.log('[VARIANT DEBUG] Found variant relations in entryData:', entryData.variant_relations);
                return entryData.variant_relations;
            }
            
            // Additional fallback: check window.entry
            if (typeof window.entry !== 'undefined' && window.entry.variant_relations) {
                console.log('[VARIANT DEBUG] Found variant relations in window.entry:', window.entry.variant_relations);
                return window.entry.variant_relations;
            }
            
            console.log('[VARIANT DEBUG] No variant relations found in global scope');
            console.log('[VARIANT DEBUG] Available window properties:', Object.keys(window).filter(k => k.includes('variant') || k.includes('entry')));
        } catch (e) {
            console.warn('[VARIANT DEBUG] Error accessing variant relations data:', e);
        }
        
        return variants;
    }
    
    addVariant() {
        // Get current variants to determine next index
        const existingVariants = this.getExistingVariantRelationsFromEntry();
        const currentVariantElements = this.container.querySelectorAll('.variant-item');
        const newIndex = Math.max(existingVariants.length, currentVariantElements.length);
        
        // Create a new variant relation template
        const newVariantRelation = {
            ref: '',
            variant_type: 'Unspecified Variant',
            type: '_component-lexeme',
            order: newIndex
        };
        
        // Render the new variant
        this.renderVariantRelation(newVariantRelation, newIndex);
        this.hideEmptyState();
        
        // Scroll to the new variant and focus on the ref input
        const newVariantElement = this.container.querySelector(`[data-variant-index="${newIndex}"]`);
        if (newVariantElement) {
            newVariantElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            
            // Focus on the ref input after a short delay
            setTimeout(() => {
                const refInput = newVariantElement.querySelector('input[name*="ref"]');
                if (refInput) {
                    refInput.focus();
                }
            }, 300);
        }
    }
    
    removeVariant(index) {
        const variantElement = document.querySelector(`[data-variant-index="${index}"]`);
        if (variantElement) {
            variantElement.remove();
            this.reindexVariants();
            
            // Show empty state if no variants remain
            if (this.container.children.length === 0) {
                this.showEmptyState();
            }
        }
    }
    
    renderVariantRelation(variantRelation, index) {
        const variantHtml = this.createVariantRelationHtml(variantRelation, index);
        this.container.insertAdjacentHTML('beforeend', variantHtml);
        // Populate dynamic selects within the newly added variant element
        try {
            const addedElem = this.container.querySelector(`[data-variant-index="${index}"]`);
            if (addedElem && window.rangesLoader) {
                const select = addedElem.querySelector('select.dynamic-lift-range');
                if (select) {
                    const rangeId = select.dataset.rangeId;
                    const selectedValue = select.dataset.selected;
                    window.rangesLoader.populateSelect(select, rangeId, {
                        selectedValue: selectedValue,
                        emptyOption: select.querySelector('option[value=""]')?.textContent || 'Select option'
                    }).catch(err => console.error('[VariantFormsManager] Failed to populate variant select:', err));
                }
            }
        } catch (e) {
            console.warn('[VariantFormsManager] Error populating dynamic selects for variant:', e);
        }
        
        // Initialize tooltips for the newly added content
        this.initializeTooltips();
    }
    
    createVariantRelationHtml(variantRelation, index) {
        return `
            <div class="variant-item card mb-3" data-variant-index="${index}">
                <div class="card-header bg-success text-white">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="fas fa-code-branch me-2"></i>
                            Variant Relation ${index + 1}: ${variantRelation.variant_type || 'Unknown Type'}
                        </h6>
                        <button type="button" class="btn btn-sm btn-light remove-variant-btn" 
                                data-index="${index}" title="Remove variant">
                            <i class="fas fa-trash text-danger"></i>
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <label class="form-label fw-bold">Target Entry</label>
                            ${variantRelation.ref_display_text ? `
                            <!-- Show clickable link to target entry -->
                            <div class="alert alert-light mb-2">
                                <i class="fas fa-external-link-alt me-2"></i>
                                <strong>This entry is a variant of: </strong>
                                <a href="/entries/${variantRelation.ref}/edit" 
                                   class="text-decoration-none text-primary fw-bold"
                                   title="Edit target entry">
                                    ${variantRelation.ref_display_text || variantRelation.ref_lexical_unit || variantRelation.ref}
                                </a>
                            </div>
                            ` : variantRelation.ref ? `
                            <!-- Show error marker for missing target entry -->
                            <div class="alert alert-danger mb-2">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                <strong>Target Entry Not Found: </strong>
                                The referenced entry ID "<code>${variantRelation.ref}</code>" could not be found in the dictionary.
                                <br><small>This may indicate a missing entry or an incorrect ID.</small>
                            </div>
                            ` : ''}
                            
                            <!-- Hidden input fields for form submission -->
                            <input type="hidden" 
                                   name="variant_relations[${index}][ref]"
                                   value="${variantRelation.ref || ''}">
                            <input type="hidden" 
                                   name="variant_relations[${index}][type]"
                                   value="${variantRelation.type || '_component-lexeme'}">
                            <input type="hidden" 
                                   name="variant_relations[${index}][order]"
                                   value="${index}">
                            
                            <!-- Search interface for adding/changing variant targets -->
                            <div class="input-group">
                                <input type="text" class="form-control variant-search-input" 
                                       placeholder="Search for entry to create variant relationship with..."
                                       data-variant-index="${index}">
                                <button type="button" class="btn btn-outline-secondary variant-search-btn" 
                                        data-variant-index="${index}">
                                    <i class="fas fa-search"></i> Search
                                </button>
                            </div>
                            <div class="form-text">Search for entries by headword or definition - no raw IDs needed</div>
                            <div class="search-results mt-2" id="variant-search-results-${index}" style="display: none;"></div>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">
                                Variant Type
                                <i class="fas fa-question-circle ms-1 form-tooltip" 
                                   data-bs-toggle="tooltip" 
                                   data-bs-placement="top"
                                   data-bs-html="true"
                                   title="About Variant Types: Different forms, spellings, or morphological variations of the same lexical item. Examples include 'protestor' vs 'protester', or inflected forms like plurals and past tense forms."></i>
                            </label>
                            <select class="form-control dynamic-lift-range"
                                    name="variant_relations[${index}][variant_type]" required
                                    data-range-id="variant-type"
                                    data-selected="${variantRelation.variant_type || ''}">
                                <option value="">Select variant type</option>
                                <!-- Options will be dynamically populated from LIFT ranges -->
                            </select>
                            <div class="form-text">Type of variant relationship</div>
                        </div>
                    </div>
                    
                    <div class="row mt-3">                        
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Status</label>
                            <div class="mt-2">
                                <span class="badge bg-success fs-6">
                                    <i class="fas fa-check-circle me-1"></i>Active Variant
                                </span>
                                <div class="form-text">This variant will be saved to the LIFT file</div>
                            </div>
                        </div>
                    </div>
                    
                </div>
            </div>
        `;
    }
    
    reindexVariants() {
        const variantElements = this.container.querySelectorAll('.variant-item');
        
        variantElements.forEach((element, newIndex) => {
            // Update data attribute
            element.setAttribute('data-variant-index', newIndex);
            
            // Update header number and variant type display
            const header = element.querySelector('.card-header h6');
            if (header) {
                const variantTypeSelect = element.querySelector('select[name*="variant_type"]');
                const currentVariantType = variantTypeSelect ? variantTypeSelect.value : 'Unknown Type';
                header.innerHTML = `
                    <i class="fas fa-code-branch me-2"></i>
                    Variant Relation ${newIndex + 1}: ${currentVariantType}
                `;
            }
            
            // Update all input names and IDs
            const inputs = element.querySelectorAll('input, select');
            inputs.forEach(input => {
                const name = input.getAttribute('name');
                if (name && name.includes('variant_relations')) {
                    const newName = name.replace(/variant_relations\[\d+\]/, `variant_relations[${newIndex}]`);
                    input.setAttribute('name', newName);
                }
            });
            
            // Update remove button
            const removeBtn = element.querySelector('.remove-variant-btn');
            if (removeBtn) {
                removeBtn.setAttribute('data-index', newIndex);
            }
        });
    }
    
    showEmptyState() {
        this.container.innerHTML = `
            <div class="empty-state text-center py-5">
                <i class="fas fa-code-branch fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Variants Found</h5>
            </div>
        `;
    }
    
    hideEmptyState() {
        const emptyState = this.container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
    }
    
    async handleEntrySearch(input) {
        const searchTerm = input.value.trim();
        const variantIndex = input.dataset.variantIndex;
        const resultsContainer = document.getElementById(`variant-search-results-${variantIndex}`);
        
        if (searchTerm.length < 2) {
            resultsContainer.style.display = 'none';
            return;
        }
        
        try {
            // Search for entries using the API
            const response = await fetch(`/api/search?q=${encodeURIComponent(searchTerm)}&limit=5`);
            if (response.ok) {
                const result = await response.json();
                this.displaySearchResults(result.entries || [], resultsContainer, variantIndex);
            }
        } catch (error) {
            console.warn('[VariantFormsManager] Entry search failed:', error);
        }
    }
    
    getEntryDisplayText(entry) {
        // First try headword (simple string)
        if (entry.headword && typeof entry.headword === 'string') {
            return entry.headword;
        }
        
        // Then try lexical_unit (may be object or string)
        if (entry.lexical_unit) {
            if (typeof entry.lexical_unit === 'string') {
                return entry.lexical_unit;
            } else if (typeof entry.lexical_unit === 'object') {
                // Extract first available language value
                const languages = ['en', 'pl', 'cs', 'sk']; // Common languages
                for (const lang of languages) {
                    if (entry.lexical_unit[lang]) {
                        return entry.lexical_unit[lang];
                    }
                }
                // If no common language found, use first available value
                const firstKey = Object.keys(entry.lexical_unit)[0];
                if (firstKey) {
                    return entry.lexical_unit[firstKey];
                }
            }
        }
        
        // Fallback to entry ID if nothing else available
        return entry.id || 'Unknown Entry';
    }
    
    displaySearchResults(entries, container, variantIndex) {
        if (entries.length === 0) {
            container.innerHTML = `
                <div class="text-muted p-2 border rounded">No entries found</div>
            `;
            container.style.display = 'block';
            return;
        }

        const resultsHtml = entries.map(entry => {
            // Extract display text from headword or lexical_unit (which may be an object)
            const displayText = this.getEntryDisplayText(entry);
            return `
            <div class="search-result-item p-2 border-bottom"
                 data-entry-id="${entry.id}"
                 data-entry-headword="${displayText}"
                 data-variant-index="${variantIndex}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="fw-bold">${displayText}</div>
                        ${entry.definition ? `<div class="text-muted small">${entry.definition}</div>` : ''}
                    </div>
                    <i class="fas fa-plus-circle text-success" title="Select this entry" style="cursor: pointer;"></i>
                </div>
            </div>
        `}).join('');

        container.innerHTML = `
            <div class="border rounded bg-white shadow-sm">
                ${resultsHtml}
            </div>
        `;
        container.style.display = 'block';

        // Add click handlers for search results and selection icons
        container.querySelectorAll('.search-result-item').forEach(item => {
            // Click on the entire item selects the result
            item.addEventListener('click', (e) => {
                if (!e.target.classList.contains('fa-plus-circle')) {
                    this.selectSearchResult(item);
                }
            });

            // Click on the plus icon also selects the result
            const plusIcon = item.querySelector('.fa-plus-circle');
            if (plusIcon) {
                plusIcon.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.selectSearchResult(item);
                });
            }
        });
    }
    
    selectSearchResult(resultItem) {
        const entryId = resultItem.dataset.entryId;
        const entryHeadword = resultItem.dataset.entryHeadword;
        const variantIndex = resultItem.dataset.variantIndex;
        
        // Update the hidden input with the entry ID
        const hiddenInput = this.container.querySelector(`input[name="variant_relations[${variantIndex}][ref]"]`);
        if (hiddenInput) {
            hiddenInput.value = entryId;
        }
        
        // Update the search input to show the selected entry
        const searchInput = this.container.querySelector(`input[data-variant-index="${variantIndex}"]`);
        if (searchInput) {
            searchInput.value = entryHeadword;
        }
        
        // Hide the search results
        const resultsContainer = document.getElementById(`variant-search-results-${variantIndex}`);
        if (resultsContainer) {
            resultsContainer.style.display = 'none';
        }
        
        console.log(`[VariantFormsManager] Selected entry "${entryHeadword}" (${entryId}) for variant ${variantIndex}`);
    }
    
    openEntrySearchModal(variantIndex) {
        // For now, just focus on the search input
        // Could be extended to open a more sophisticated search modal
        const searchInput = this.container.querySelector(`input[data-variant-index="${variantIndex}"]`);
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    /**
     * Force re-render of variants - useful when called from template after data is loaded
     */
    forceRender() {
        console.log('[VARIANT DEBUG] forceRender() called');
        this.renderExistingVariants();
    }
    
    /**
     * Initialize Bootstrap tooltips for all tooltip elements in the container
     */
    initializeTooltips() {
        // Check if Bootstrap tooltip is available
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            // Initialize tooltips for any elements with data-bs-toggle="tooltip"
            const tooltipTriggerList = this.container.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltipTriggerList.forEach(tooltipTriggerEl => {
                new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }
}

// Don't auto-initialize - let the template initialize with data
// The template will create the instance with options including variantRelations
/*
document.addEventListener('DOMContentLoaded', function() {
    console.log('[VARIANT DEBUG] DOMContentLoaded event fired');
    if (document.getElementById('variants-container')) {
        console.log('[VARIANT DEBUG] variants-container found, creating VariantFormsManager');
        window.variantFormsManager = new VariantFormsManager('variants-container');
    } else {
        console.log('[VARIANT DEBUG] variants-container not found in DOM');
    }
});
*/

// Also make the class available immediately
console.log('[VARIANT DEBUG] VariantFormsManager class defined');

// Expose the class globally for template initialization
window.VariantFormsManager = VariantFormsManager;
