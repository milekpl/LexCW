/**
 * Relations Manager
 * 
 * JavaScript component for managing LIFT relation elements in the entry editor.
 * Provides dynamic add/remove functionality and proper LIFT structure support.
 * 
 * Key features:
 * - Loads relation types from LIFT ranges (lexical-relation)
 * - Filters out variant-type relations (they belong in variants container)
 * - Shows clickable links for target entries, not raw IDs
 * - Provides search interface for adding relations
 */

class RelationsManager {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.rangeId = 'lexical-relation'; // Use lexical-relation range for relation types
        this.relationTypes = [];
        this.relations = options.relations || [];
        
        this.init();
    }
    
    async init() {
        await this.loadRelationTypes();
        this.setupEventListeners();
        this.initializeExistingRelationDropdowns();
    }
    
    async loadRelationTypes() {
        try {
            // Use the global rangesLoader if available
            if (window.rangesLoader) {
                const rangeData = await window.rangesLoader.loadRange(this.rangeId);
                if (rangeData?.values) {
                    this.relationTypes = rangeData.values;
                    console.log('[RelationsManager] Loaded relation types from ranges:', this.relationTypes.length);
                    return;
                }
            }
            
            // Fallback to direct API call if rangesLoader isn't available
            const response = await fetch(`/api/ranges/${this.rangeId}`);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data?.values) {
                    this.relationTypes = result.data.values;
                    console.log('[RelationsManager] Loaded relation types from API:', this.relationTypes.length);
                    return;
                }
            }
        } catch (error) {
            console.warn(`[RelationsManager] Failed to load relation types from range '${this.rangeId}':`, error);
        }
        
        // No fallback types: relationTypes remains empty if loading fails
        this.relationTypes = [];
        console.warn('[RelationsManager] Failed to load relation types from ranges/API and no fallback values will be used.');
    }
    
    initializeExistingRelationDropdowns() {
        // Initialize any existing relation type dropdowns that were server-side rendered
        const relationSelects = this.container.querySelectorAll('.relation-type-select');
        
        relationSelects.forEach((select, index) => {
            this.populateRelationTypeSelect(select);
        });
        
        console.log(`[RelationsManager] Initialized ${relationSelects.length} existing relation dropdowns`);
    }
    
    populateRelationTypeSelect(selectElement) {
        if (!selectElement || this.relationTypes.length === 0) return;
        
        // Get the currently selected value
        const currentValue = selectElement.dataset.selectedValue || selectElement.value;
        
        // Clear existing options except the first one
        selectElement.innerHTML = '<option value="">Select type</option>';
        
        // Add options from loaded relation types
        this.relationTypes.forEach(relationType => {
            const option = document.createElement('option');
            option.value = relationType.id || relationType.value;
            option.textContent = relationType.value || relationType.id;
            
            // Add description as title if available
            if (relationType.description && relationType.description.en) {
                option.title = relationType.description.en;
            }
            
            // Select if this was the current value
            if (option.value === currentValue) {
                option.selected = true;
            }
            
            selectElement.appendChild(option);
        });
    }
    
    setupEventListeners() {
        // Add relation button
        const addButton = document.getElementById('add-relation-btn');
        if (addButton) {
            addButton.addEventListener('click', () => this.addRelation());
        }
        
        // Delegate removal events
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-relation-btn')) {
                const index = parseInt(e.target.dataset.index);
                this.removeRelation(index);
            }
            
            // Handle search button clicks
            if (e.target.classList.contains('relation-search-btn')) {
                const relationIndex = e.target.dataset.relationIndex;
                this.openEntrySearchModal(relationIndex);
            }
        });
        
        // Handle entry search input
        this.container.addEventListener('input', (e) => {
            if (e.target.classList.contains('relation-search-input')) {
                this.handleEntrySearch(e.target);
            }
        });
    }
    
    addRelation() {
        // Get the current number of relations for indexing
        const existingRelations = this.container.querySelectorAll('.relation-item').length;
        const newIndex = existingRelations;
        
        const newRelation = {
            type: '',
            ref: ''
        };
        
        // Create new relation HTML
        const relationHtml = this.createRelationHtml(newRelation, newIndex);
        
        // Remove empty state if it exists
        const emptyState = this.container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        // Add the new relation
        this.container.insertAdjacentHTML('beforeend', relationHtml);
        
        // Initialize the new relation's dropdown
        const newSelect = this.container.querySelector(`.relation-item[data-relation-index="${newIndex}"] .relation-type-select`);
        if (newSelect) {
            this.populateRelationTypeSelect(newSelect);
        }
        
        console.log(`[RelationsManager] Added new relation at index ${newIndex}`);
    }
    
    removeRelation(index) {
        const relationElement = this.container.querySelector(`[data-relation-index="${index}"]`);
        if (relationElement) {
            relationElement.remove();
            this.reindexRelations();
            
            // Show empty state if no relations remain
            if (this.container.querySelectorAll('.relation-item').length === 0) {
                this.showEmptyState();
            }
            
            console.log(`[RelationsManager] Removed relation at index ${index}`);
        }
    }
    
    reindexRelations() {
        const relationItems = this.container.querySelectorAll('.relation-item');
        relationItems.forEach((item, newIndex) => {
            // Update data attributes
            item.dataset.relationIndex = newIndex;
            
            // Update all form field names and IDs within this relation
            const inputs = item.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                if (input.name) {
                    input.name = input.name.replace(/relations\[\d+\]/, `relations[${newIndex}]`);
                }
                if (input.id) {
                    input.id = input.id.replace(/relations-\d+/, `relations-${newIndex}`);
                }
            });
            
            // Update button data attributes
            const buttons = item.querySelectorAll('[data-index], [data-relation-index]');
            buttons.forEach(button => {
                if (button.dataset.index !== undefined) {
                    button.dataset.index = newIndex;
                }
                if (button.dataset.relationIndex !== undefined) {
                    button.dataset.relationIndex = newIndex;
                }
            });
            
            // Update search results container ID
            const searchResults = item.querySelector('.search-results');
            if (searchResults) {
                searchResults.id = `search-results-${newIndex}`;
            }
        });
    }
    
    createRelationHtml(relation, index) {
        return `
            <div class="relation-item card mb-3" data-relation-index="${index}">
                <div class="card-header bg-primary text-white">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="fas fa-link me-2"></i>
                            Relation ${index + 1}
                        </h6>
                        <button type="button" class="btn btn-sm btn-light remove-relation-btn" 
                                data-index="${index}" title="Remove relation">
                            <i class="fas fa-trash text-danger"></i>
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Relation Type</label>
                            <select class="form-control relation-type-select" 
                                    name="relations[${index}][type]" 
                                    data-range-id="${this.rangeId}"
                                    data-hierarchical="true"
                                    data-searchable="true"
                                    required>
                                <option value="">Select type</option>
                            </select>
                            <div class="form-text">Type of semantic relation</div>
                        </div>
                        <div class="col-md-8">
                            <label class="form-label fw-bold">Target Entry</label>
                            
                            <!-- Hidden input field for form submission (NO raw ID visible to user) -->
                            <input type="hidden" 
                                   name="relations[${index}][ref]"
                                   value="${relation.ref || ''}">
                            
                            <!-- Search interface for adding/changing relations -->
                            <div class="input-group">
                                <input type="text" class="form-control relation-search-input" 
                                       placeholder="Search for entry to relate to..."
                                       data-relation-index="${index}">
                                <button type="button" class="btn btn-outline-secondary relation-search-btn" 
                                        data-relation-index="${index}">
                                    <i class="fas fa-search"></i> Search
                                </button>
                            </div>
                            <div class="form-text">Search for entries by headword or definition - no raw IDs needed</div>
                            <div class="search-results mt-2" id="search-results-${index}" style="display: none;"></div>
                        </div>
                    </div>
                    
                    <div class="alert alert-info mt-3">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>Semantic Relationship:</strong> This entry will have the selected relationship 
                        with the target entry you choose. In LIFT format, this creates a relation element with the specified type.
                    </div>
                </div>
            </div>
        `;
    }
    
    async handleEntrySearch(input) {
        const searchTerm = input.value.trim();
        const relationIndex = input.dataset.relationIndex;
        const resultsContainer = document.getElementById(`search-results-${relationIndex}`);
        
        if (searchTerm.length < 2) {
            resultsContainer.style.display = 'none';
            return;
        }
        
        try {
            // Search for entries using the API
            const response = await fetch(`/api/search?q=${encodeURIComponent(searchTerm)}&limit=5`);
            if (response.ok) {
                const result = await response.json();
                this.displaySearchResults(result.entries || [], resultsContainer, relationIndex);
            }
        } catch (error) {
            console.warn('[RelationsManager] Entry search failed:', error);
        }
    }
    
    displaySearchResults(entries, container, relationIndex) {
        if (entries.length === 0) {
            container.innerHTML = `
                <div class="text-muted p-2 border rounded">No entries found</div>
            `;
            container.style.display = 'block';
            return;
        }
        
        const resultsHtml = entries.map(entry => `
            <div class="search-result-item p-2 border-bottom cursor-pointer" 
                 data-entry-id="${entry.id}" 
                 data-entry-headword="${entry.headword || entry.lexical_unit}"
                 data-relation-index="${relationIndex}">
                <div class="fw-bold">${entry.headword || entry.lexical_unit}</div>
                ${entry.definition ? `<div class="text-muted small">${entry.definition}</div>` : ''}
            </div>
        `).join('');
        
        container.innerHTML = `
            <div class="border rounded bg-white shadow-sm">
                ${resultsHtml}
            </div>
        `;
        container.style.display = 'block';
        
        // Add click handlers for search results
        container.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => {
                this.selectSearchResult(item);
            });
        });
    }
    
    selectSearchResult(resultItem) {
        const entryId = resultItem.dataset.entryId;
        const entryHeadword = resultItem.dataset.entryHeadword;
        const relationIndex = resultItem.dataset.relationIndex;
        
        // Update the hidden input with the entry ID
        const hiddenInput = this.container.querySelector(`input[name="relations[${relationIndex}][ref]"]`);
        if (hiddenInput) {
            hiddenInput.value = entryId;
        }
        
        // Update the search input to show the selected entry
        const searchInput = this.container.querySelector(`input[data-relation-index="${relationIndex}"]`);
        if (searchInput) {
            searchInput.value = entryHeadword;
        }
        
        // Hide the search results
        const resultsContainer = document.getElementById(`search-results-${relationIndex}`);
        if (resultsContainer) {
            resultsContainer.style.display = 'none';
        }
        
        console.log(`[RelationsManager] Selected entry "${entryHeadword}" (${entryId}) for relation ${relationIndex}`);
    }
    
    openEntrySearchModal(relationIndex) {
        // For now, just focus on the search input
        // Could be extended to open a more sophisticated search modal
        const searchInput = this.container.querySelector(`input[data-relation-index="${relationIndex}"]`);
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    showEmptyState() {
        this.container.innerHTML = `
            <div class="empty-state text-center py-4">
                <i class="fas fa-link fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Semantic Relations</h5>
                <p class="text-muted">This entry does not have any semantic relations defined.</p>
                <p class="text-muted">
                    <strong>What are relations?</strong> Relations connect this entry to other entries through semantic relationships 
                    like synonymy, antonymy, hyponymy, etc. These help build the semantic network of the dictionary.
                </p>
                <p class="text-muted">
                    <strong>How relations work:</strong> Relations are stored as LIFT relation elements. 
                    They differ from variants, which represent different forms of the same lexical item.
                </p>
            </div>
        `;
    }
}

// Expose the class globally for template initialization
window.RelationsManager = RelationsManager;
