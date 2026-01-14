/**
 * Component Search Handler
 * Provides search functionality for adding complex form components
 */

class ComponentSearchHandler {
    constructor(existingComponents = []) {
        this.selectedComponents = existingComponents || [];
        this.currentEntryId = null;
        this.init();
    }
    
    init() {
        // Get current entry ID from form
        const entryIdInput = document.querySelector('input[name="id"]');
        if (entryIdInput && entryIdInput.value) {
            this.currentEntryId = entryIdInput.value;
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
                this.displayComponentSearchResults(result.entries || []);
            }
        } catch (error) {
            console.warn('[ComponentSearchHandler] Entry search failed:', error);
        }
    }
    
    displayComponentSearchResults(entries) {
        const resultsContainer = document.getElementById('component-search-results');
        
        if (entries.length === 0) {
            resultsContainer.innerHTML = '<div class="alert alert-info mt-2">No entries found</div>';
            resultsContainer.style.display = 'block';
            return;
        }
        
        const resultsHtml = entries.map(entry => {
            const headword = this.getEntryHeadword(entry);
            const entryId = entry.id;
            
            return `
                <div class="entry-result-item p-2 border rounded mb-2 mt-2 bg-white" 
                     style="cursor: pointer;"
                     data-entry-id="${entryId}"
                     data-entry-headword="${headword}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="fw-bold text-dark">${headword}</span>
                            <br>
                            <small class="text-muted">ID: ${entryId}</small>
                        </div>
                        <i class="fas fa-plus-circle text-success"></i>
                    </div>
                </div>
            `;
        }).join('');
        
        resultsContainer.innerHTML = resultsHtml;
        resultsContainer.style.display = 'block';
        
        // Add click handlers for entry selection
        resultsContainer.querySelectorAll('.entry-result-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectComponentEntry(item);
            });
        });
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
