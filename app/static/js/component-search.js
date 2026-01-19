/**
 * Component Search Handler
 * Provides search functionality for adding complex form components
 * Supports creating new entries from search results
 */

class ComponentSearchHandler {
    constructor(existingComponents = []) {
        this.selectedComponents = existingComponents || [];
        this.currentEntryId = null;
        this.sourceLanguage = this._getSourceLanguage();

        // Initialize EntryCreationManager for creating entries from search results
        this.entryCreationManager = new EntryCreationManager({
            sourceLanguage: this.sourceLanguage,
            onSenseSelected: (senseId, entryId, context) => {
                this._handleCreatedEntrySelected(senseId, entryId, context);
            },
            onError: (error) => {
                console.error('[ComponentSearchHandler] Entry creation error:', error);
                alert(`Failed to create entry: ${error.message}`);
            }
        });

        this.init();
    }

    /**
     * Get source language from entry form data attribute
     * @private
     */
    _getSourceLanguage() {
        const form = document.getElementById('entry-form');
        return form?.dataset.sourceLanguage || 'en';
    }

    /**
     * Get current entry ID for circular reference detection
     * @private
     */
    _getCurrentEntryId() {
        const entryIdInput = document.querySelector('input[name="id"]');
        return entryIdInput?.value || null;
    }

    init() {
        // Get current entry ID from form
        const entryIdInput = document.querySelector('input[name="id"]');
        if (entryIdInput && entryIdInput.value) {
            this.currentEntryId = entryIdInput.value;
            this.entryCreationManager.setCurrentEntryId(this.currentEntryId);
        }

        const searchInput = document.getElementById('component-search-input');
        const searchBtn = document.getElementById('component-search-btn');

        if (searchInput) {
            searchInput.addEventListener('input', () => {
                this.handleComponentSearch();
            });
        }

        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                this.handleComponentSearch();
            });
        }

        // Hide search results when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.component-search-input') &&
                !e.target.closest('.component-search-results')) {
                const resultsContainer = document.getElementById('component-search-results');
                if (resultsContainer) {
                    resultsContainer.style.display = 'none';
                }
            }
        });
    }

    async handleComponentSearch() {
        const searchInput = document.getElementById('component-search-input');
        const searchTerm = searchInput.value.trim();
        const resultsContainer = document.getElementById('component-search-results');

        if (searchTerm.length < 2) {
            resultsContainer.style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(searchTerm)}&limit=10`);
            if (response.ok) {
                const result = await response.json();
                const prioritizedEntries = this._prioritizeSearchResults(result.entries || [], searchTerm);
                this.displayComponentSearchResults(prioritizedEntries, resultsContainer, searchTerm);
            }
        } catch (error) {
            console.warn('[ComponentSearchHandler] Entry search failed:', error);
        }
    }

    /**
     * Prioritize search results by placing exact matches at the top
     * @private
     */
    _prioritizeSearchResults(entries, searchTerm) {
        const normalizedSearchTerm = searchTerm.toLowerCase().trim();
        const exactMatches = [];
        const partialMatches = [];
        const otherMatches = [];

        entries.forEach(entry => {
            const headword = this.getEntryHeadword(entry).toLowerCase();
            if (headword === normalizedSearchTerm) {
                exactMatches.push(entry);
            } else if (headword.includes(normalizedSearchTerm)) {
                partialMatches.push(entry);
            } else {
                otherMatches.push(entry);
            }
        });

        return [...exactMatches, ...partialMatches, ...otherMatches];
    }

    /**
     * Escape HTML to prevent XSS
     * @private
     */
    _escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Handle when a newly created entry is selected from the sense selection modal
     * @private
     */
    _handleCreatedEntrySelected(senseId, entryId, context) {
        const typeSelect = document.getElementById('new-component-type');
        const componentType = typeSelect?.value;

        // Check if component type is selected, if not, set default
        if (!componentType) {
            // Set default component type
            if (typeSelect) {
                typeSelect.value = '_component-lexeme';
            }
        }

        // Get the headword from the entry creation (the search term)
        // The entryId is the UUID, but we stored the headword in a way we can retrieve it
        const headword = entryId; // Use ID as headword since we just created it

        // Check for circular reference
        if (this.currentEntryId && entryId === this.currentEntryId) {
            alert('Cannot add this entry as its own component (circular reference detected)');
            return;
        }

        // Check if already added
        if (this.selectedComponents.some(comp => comp.id === entryId)) {
            alert('This component has already been added');
            return;
        }

        // Add to selected components list
        this.selectedComponents.push({
            id: entryId,
            headword: headword,
            type: componentType || '_component-lexeme',
            order: this.selectedComponents.length
        });

        // Update display
        this.updateSelectedComponentsDisplay();

        // Hide search results
        const resultsContainer = document.getElementById('component-search-results');
        if (resultsContainer) {
            resultsContainer.style.display = 'none';
        }

        // Clear search input
        const searchInput = document.getElementById('component-search-input');
        if (searchInput) {
            searchInput.value = '';
        }

        // Reset type selector
        if (typeSelect) {
            typeSelect.value = '';
        }

        console.log(`[ComponentSearchHandler] Created entry selected: "${headword}" (${entryId})`);
    }

    /**
     * Create the HTML for the "Create new entry" option
     * @private
     */
    _getCreateOptionHtml(searchTerm) {
        const escapedTerm = this._escapeHtml(searchTerm);
        return (
            '<div class="search-result-item create-entry-option p-2 border-bottom bg-light" ' +
            `data-search-term="${escapedTerm}" ` +
            'style="cursor: pointer; border-left: 3px solid #0d6efd;">' +
            '<div class="d-flex justify-content-between align-items-center">' +
            '<div>' +
            '<div class="fw-bold text-primary">' +
            '<i class="fas fa-plus-circle me-1"></i> ' +
            `Create new entry: "${escapedTerm}"` +
            '</div>' +
            '<div class="text-muted small">Click to create and select a sense</div>' +
            '</div>' +
            '<i class="fas fa-arrow-right text-primary"></i>' +
            '</div></div>'
        );
    }

    /**
     * Handle click on create entry option
     * @private
     */
    async _handleCreateEntryClick(searchTerm) {
        console.log(`[ComponentSearchHandler] Create entry clicked for: "${searchTerm}"`);

        try {
            // Step 1: Create the entry
            const createdEntry = await this.entryCreationManager.createEntry(searchTerm);
            console.log(`[ComponentSearchHandler] Entry created: ${createdEntry.id}`);

            // Step 2: Fetch senses
            const senses = await this.entryCreationManager.fetchEntrySenses(createdEntry.id);

            // Step 3: If senses exist, show modal; otherwise use entry directly
            if (senses.length > 0) {
                await this.entryCreationManager._showSenseSelectionModal(createdEntry, senses, { type: 'component' });
            } else {
                // No senses - use entry directly
                this._handleCreatedEntrySelected(createdEntry.id, createdEntry.id, { type: 'component' });
            }
        } catch (error) {
            console.error('[ComponentSearchHandler] Failed to create entry:', error);
            alert(`Failed to create entry: ${error.message}`);
        }
    }

    displayComponentSearchResults(entries, container, currentSearchTerm = '') {
        const resultsContainer = container || document.getElementById('component-search-results');

        // Build the complete HTML for results
        let resultsHtml = '';

        // Add "Create new entry" option at the top (if search term is long enough)
        if (currentSearchTerm && currentSearchTerm.length >= 2) {
            resultsHtml += this._getCreateOptionHtml(currentSearchTerm);
        }

        if (entries.length === 0 && !resultsHtml) {
            resultsContainer.innerHTML = '<div class="alert alert-info mt-2">No entries found</div>';
            resultsContainer.style.display = 'block';
            return;
        }

        // Build results HTML - all user content is escaped via _escapeHtml()
        const entriesHtml = entries.map(entry => {
            const headword = this.getEntryHeadword(entry);
            const entryId = entry.id;
            const isExactMatch = headword.toLowerCase() === currentSearchTerm.toLowerCase();
            const matchBadge = isExactMatch
                ? '<span class="badge bg-success ms-2">Exact Match</span>'
                : '';

            return `
                <div class="entry-result-item p-2 border rounded mb-2 mt-2 bg-white"
                     style="cursor: pointer;"
                     data-entry-id="${entryId}"
                     data-entry-headword="${headword}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="fw-bold text-dark">${this._escapeHtml(headword)}</span>
                            ${matchBadge}
                            <br>
                            <small class="text-muted">ID: ${entryId}</small>
                        </div>
                        <i class="fas fa-plus-circle text-success"></i>
                    </div>
                </div>
            `;
        }).join('');

        resultsHtml += entriesHtml;
        resultsContainer.innerHTML = resultsHtml;
        resultsContainer.style.display = 'block';

        // Add click handlers for entry selection (excluding create option)
        resultsContainer.querySelectorAll('.entry-result-item:not(.create-entry-option)').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectComponentEntry(item);
            });
        });

        // Add click handler for create entry option using event delegation
        const createOption = resultsContainer.querySelector('.create-entry-option');
        if (createOption) {
            // Remove any existing listeners by cloning the node
            const newCreateOption = createOption.cloneNode(true);
            createOption.parentNode.replaceChild(newCreateOption, createOption);

            newCreateOption.addEventListener('click', (e) => {
                e.stopPropagation();
                const searchTerm = newCreateOption.dataset.searchTerm;
                if (searchTerm) {
                    this._handleCreateEntryClick(searchTerm);
                }
            });
        }
    }
    
    selectComponentEntry(entryItem) {
        const entryId = entryItem.dataset.entryId;
        const headword = entryItem.dataset.entryHeadword;
        const typeSelect = document.getElementById('new-component-type');
        const componentType = typeSelect.value;
        
        if (!componentType) {
            alert('Please select a component type first');
            return;
        }
        
        // Check for circular reference
        if (this.currentEntryId && entryId === this.currentEntryId) {
            alert('Cannot add this entry as its own component (circular reference detected)');
            return;
        }
        
        // Check if already added
        if (this.selectedComponents.some(comp => comp.id === entryId)) {
            alert('This component has already been added');
            return;
        }
        
        // Add to selected components list
        this.selectedComponents.push({
            id: entryId,
            headword: headword,
            type: componentType,
            order: this.selectedComponents.length
        });
        
        // Update display
        this.updateSelectedComponentsDisplay();
        
        // Hide search results
        const resultsContainer = document.getElementById('component-search-results');
        resultsContainer.style.display = 'none';
        
        // Clear search input
        const searchInput = document.getElementById('component-search-input');
        searchInput.value = '';
        
        // Reset type selector
        typeSelect.value = '';
    }
    
    updateSelectedComponentsDisplay() {
        const listContainer = document.getElementById('new-components-list');
        const componentsContainer = document.getElementById('new-components-container');
        
        if (this.selectedComponents.length === 0) {
            listContainer.style.display = 'none';
            return;
        }
        
        listContainer.style.display = 'block';
        
        const componentsHtml = this.selectedComponents.map((component, index) => {
            return `
                <div class="alert alert-success d-flex justify-content-between align-items-center mb-2" 
                     data-component-index="${index}">
                    <div>
                        <i class="fas fa-puzzle-piece me-2"></i>
                        <strong>${component.headword}</strong>
                        <span class="badge bg-dark ms-2">${component.type}</span>
                        <br>
                        <small class="text-muted">Order: ${component.order + 1}</small>
                        
                        <!-- Hidden inputs for form submission -->
                        <input type="hidden" 
                               name="components[${index}].ref" 
                               value="${component.id}">
                        <input type="hidden" 
                               name="components[${index}].type" 
                               value="${component.type}">
                        <input type="hidden" 
                               name="components[${index}].order" 
                               value="${component.order}">
                    </div>
                    <button type="button" 
                            class="btn btn-sm btn-outline-danger remove-new-component-btn"
                            data-component-index="${index}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        }).join('');
        
        componentsContainer.innerHTML = componentsHtml;
        
        // Add click handlers for remove buttons
        componentsContainer.querySelectorAll('.remove-new-component-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.componentIndex);
                this.removeSelectedComponent(index);
            });
        });
    }
    
    removeSelectedComponent(index) {
        this.selectedComponents.splice(index, 1);
        // Update order values
        this.selectedComponents.forEach((comp, idx) => {
            comp.order = idx;
        });
        this.updateSelectedComponentsDisplay();
    }
    
    getEntryHeadword(entry) {
        if (entry.headword) {
            return entry.headword;
        }
        if (entry.lexical_unit) {
            if (typeof entry.lexical_unit === 'string') {
                return entry.lexical_unit;
            }
            if (typeof entry.lexical_unit === 'object') {
                const firstKey = Object.keys(entry.lexical_unit)[0];
                if (firstKey) {
                    return entry.lexical_unit[firstKey];
                }
            }
        }
        return entry.id || 'Unknown Entry';
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Try to get existing components from global scope
    let existingComponents = [];
    
    // Check if component relations are available in the global scope
    if (typeof window.componentRelations !== 'undefined' && Array.isArray(window.componentRelations)) {
        existingComponents = window.componentRelations;
    }
    
    // Check if entry data is available
    if (typeof entryData !== 'undefined' && entryData.component_relations) {
        existingComponents = entryData.component_relations;
    }
    
    // Check if window.entry is available
    if (typeof window.entry !== 'undefined' && window.entry.component_relations) {
        existingComponents = window.entry.component_relations;
    }
    
    // Convert component relations to the format expected by the search handler
    const componentsForHandler = existingComponents.map(comp => ({
        id: comp.ref,
        headword: comp.ref_display_text || comp.ref_lexical_unit || comp.ref,
        type: '_component-lexeme',  // Always use _component-lexeme for component relations
        complex_form_type: comp.complex_form_type || 'Compound',
        order: comp.order || 0
    }));
    
    window.componentSearchHandler = new ComponentSearchHandler(componentsForHandler);
    
    // If there are existing components, show them in the UI
    if (componentsForHandler.length > 0) {
        window.componentSearchHandler.updateSelectedComponentsDisplay();
    }
});
