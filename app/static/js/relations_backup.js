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
        
        // No fallback relation types in this implementation
        this.relationTypes = [];
        console.warn('[RelationsManager] No relation types loaded; relation dropdowns will be empty');
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
        const relations = [];
        const formData = new FormData(document.getElementById('entry-form'));
        
        // Look for relation inputs
        for (let [key, value] of formData.entries()) {
            const match = key.match(/relations\[(\d+)\]\.(type|ref)/);
            if (match) {
                const index = parseInt(match[1]);
                const field = match[2];
                
                if (!relations[index]) {
                    relations[index] = {};
                }
                
                relations[index][field] = value;
            }
        }
        
        return relations.filter(r => r && r.type && r.ref);
    }
    
    addRelation() {
        const relations = this.getExistingRelationsFromForm();
        const newIndex = relations.length;
        
        const newRelation = {
            type: '',
            ref: ''
        };
        
        this.renderRelation(newRelation, newIndex);
        this.hideEmptyState();
    }
    
    removeRelation(index) {
        const relationElement = document.querySelector(`[data-relation-index="${index}"]`);
        if (relationElement) {
            relationElement.remove();
            this.reindexRelations();
            
            // Show empty state if no relations remain
            if (this.container.children.length === 0) {
                this.showEmptyState();
            }
        }
    }
    
    renderRelation(relation, index) {
        const relationHtml = this.createRelationHtml(relation, index);
        this.container.insertAdjacentHTML('beforeend', relationHtml);
        
        // Initialize the relation type dropdown using the ranges loader
        if (window.rangesLoader) {
            const typeSelect = this.container.querySelector(`.relation-item[data-relation-index="${index}"] .relation-type-select`);
            if (typeSelect) {
                window.rangesLoader.populateSelect(typeSelect, this.rangeId, {
                    selectedValue: relation.type || '',
                    hierarchical: true,
                    searchable: true
                });
            }
        }
        
        // Initialize search for the reference input
        this.initializeEntrySearch(index);
    }
    
    createRelationHtml(relation, index) {
        return `
            <div class="relation-item card mb-3" data-relation-index="${index}">
                <div class="card-header bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="fas fa-link text-primary me-2"></i>
                            Relation ${index + 1}
                        </h6>
                        <button type="button" class="btn btn-sm btn-outline-danger remove-relation-btn" 
                                data-index="${index}">
                            <i class="fas fa-trash"></i> Remove
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <label class="form-label">Relation Type</label>
                            <select class="form-select relation-type-select" 
                                    name="relations[${index}].type" 
                                    data-range-id="${this.rangeId}"
                                    data-selected="${relation.type || ''}"
                                    data-index="${index}" required>
                                <option value="">Select type</option>
                            </select>
                            <div class="form-text">Type of semantic relation</div>
                        </div>
                        <div class="col-md-8">
                            <label class="form-label">Target Entry</label>
                            <div class="input-group">
                                <input type="text" class="form-control relation-ref-input" 
                                       name="relations[${index}].ref"
                                       value="${relation.ref || ''}" 
                                       placeholder="Enter entry ID or search for entry" required>
                                <button type="button" class="btn btn-outline-secondary search-entry-btn" 
                                        data-index="${index}">
                                    <i class="fas fa-search"></i> Search
                                </button>
                            </div>
                            <div class="form-text">ID of the target entry for this relation</div>
                            <div class="search-results mt-2" id="search-results-${index}" style="display: none;"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    initializeEntrySearch(index) {
        const searchButton = document.querySelector(`[data-index="${index}"].search-entry-btn`);
        if (searchButton) {
            searchButton.addEventListener('click', () => this.openEntrySearchModal(index));
        }
    }
    
    async handleEntrySearch(input) {
        const searchTerm = input.value.trim();
        const index = this.getRelationIndexFromElement(input);
        const resultsContainer = document.getElementById(`search-results-${index}`);
        
        if (searchTerm.length < 2) {
            resultsContainer.style.display = 'none';
            return;
        }
        
        try {
            // Search for entries using the correct API endpoint
            const response = await fetch(`/api/search?q=${encodeURIComponent(searchTerm)}&limit=5`);
            if (response.ok) {
                const result = await response.json();
                this.displaySearchResults(result.entries || [], resultsContainer, index);
            }
        } catch (error) {
            console.warn('Entry search failed:', error);
        }
    }
    
    displaySearchResults(entries, container, index) {
        if (entries.length === 0) {
            container.innerHTML = `
                <div class="text-muted p-2">No entries found</div>
                <div class="border-top p-2">
                    <button type="button" class="btn btn-sm btn-outline-success me-2 create-new-entry-btn" 
                            data-index="${index}">
                        <i class="fas fa-plus"></i> Create New Entry
                    </button>
                    <small class="text-muted">Create a new entry as relation target</small>
                </div>
            `;
            container.style.display = 'block';
            this.addCreateNewEntryListener(container);
            return;
        }
        
        let resultsHtml = '';
        
        entries.forEach(entry => {
            // Add entry option
            resultsHtml += `
                <div class="search-result-item p-2 border-bottom" data-entry-id="${entry.id}" data-index="${index}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${this.getEntryDisplayText(entry)}</strong>
                            <div class="text-muted small">${entry.id}</div>
                        </div>
                        <button type="button" class="btn btn-sm btn-primary select-entry-btn" 
                                data-entry-id="${entry.id}" data-index="${index}">
                            Select Entry
                        </button>
                    </div>
                </div>
            `;
            
            // Add sense options if entry has senses
            if (entry.senses && entry.senses.length > 0) {
                entry.senses.forEach((sense, senseIndex) => {
                    const senseRef = `${entry.id}#${sense.id}`;
                    const senseDisplay = this.getSenseDisplayText(sense, senseIndex);
                    
                    resultsHtml += `
                        <div class="search-result-item p-2 border-bottom ms-3" data-sense-ref="${senseRef}" data-index="${index}">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <span class="text-muted">↳ Sense ${senseIndex + 1}:</span>
                                    <span>${senseDisplay}</span>
                                    <div class="text-muted small">${sense.id}</div>
                                </div>
                                <button type="button" class="btn btn-sm btn-outline-primary select-sense-btn" 
                                        data-sense-ref="${senseRef}" data-index="${index}">
                                    Select Sense
                                </button>
                            </div>
                        </div>
                    `;
                });
                
                // Add option to add new sense to this entry
                resultsHtml += `
                    <div class="search-result-item p-2 border-bottom ms-3 bg-light" data-entry-id="${entry.id}" data-index="${index}">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="text-muted">↳ <i class="fas fa-plus-circle"></i> Add new sense to this entry</span>
                            </div>
                            <button type="button" class="btn btn-sm btn-outline-success create-new-sense-btn" 
                                    data-entry-id="${entry.id}" data-index="${index}">
                                Add Sense
                            </button>
                        </div>
                    </div>
                `;
            }
        });
        
        // Add option to create completely new entry
        resultsHtml += `
            <div class="border-top p-2 bg-light">
                <button type="button" class="btn btn-sm btn-outline-success me-2 create-new-entry-btn" 
                        data-index="${index}">
                    <i class="fas fa-plus"></i> Create New Entry
                </button>
                <small class="text-muted">Create a new entry as relation target</small>
            </div>
        `;
        
        container.innerHTML = resultsHtml;
        container.style.display = 'block';
        
        // Add event listeners for selection
        container.addEventListener('click', (e) => {
            if (e.target.classList.contains('select-entry-btn')) {
                const entryId = e.target.dataset.entryId;
                const index = parseInt(e.target.dataset.index);
                this.selectEntry(entryId, index);
                container.style.display = 'none';
            } else if (e.target.classList.contains('select-sense-btn')) {
                const senseRef = e.target.dataset.senseRef;
                const index = parseInt(e.target.dataset.index);
                this.selectSense(senseRef, index);
                container.style.display = 'none';
            }
        });
        
        this.addCreateNewEntryListener(container);
        this.addCreateNewSenseListener(container);
    }
    
    getEntryDisplayText(entry) {
        // Get the first lexical unit form for display
        if (entry.lexical_unit) {
            const forms = Object.values(entry.lexical_unit);
            if (forms.length > 0) {
                return forms[0];
            }
        }
        return entry.id;
    }
    
    selectEntry(entryId, index) {
        const input = document.querySelector(`input[name="relations[${index}].ref"]`);
        if (input) {
            input.value = entryId;
        }
    }
    
    getSenseDisplayText(sense, senseIndex) {
        // Try to get a meaningful display text for the sense
        if (sense.glosses) {
            const glosses = Object.values(sense.glosses);
            if (glosses.length > 0) {
                return glosses[0];
            }
        }
        
        if (sense.definition) {
            const definitions = Object.values(sense.definition);
            if (definitions.length > 0) {
                // Truncate long definitions
                const def = definitions[0];
                return def.length > 50 ? def.substring(0, 50) + '...' : def;
            }
        }
        
        return `Sense ${senseIndex + 1}`;
    }
    
    selectSense(senseRef, index) {
        const input = document.querySelector(`input[name="relations[${index}].ref"]`);
        if (input) {
            input.value = senseRef;
        }
    }
    
    getRelationIndexFromElement(element) {
        const relationItem = element.closest('.relation-item');
        return parseInt(relationItem.dataset.relationIndex);
    }
    
    openEntrySearchModal(index) {
        // This could open a modal for more advanced entry search
        // For now, focus on the input field
        const input = document.querySelector(`input[name="relations[${index}].ref"]`);
        if (input) {
            input.focus();
        }
    }
    
    addCreateNewEntryListener(container) {
        const createButtons = container.querySelectorAll('.create-new-entry-btn');
        createButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                this.openCreateNewEntryModal(index);
            });
        });
    }
    
    addCreateNewSenseListener(container) {
        const createSenseButtons = container.querySelectorAll('.create-new-sense-btn');
        createSenseButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const entryId = e.target.dataset.entryId;
                const index = parseInt(e.target.dataset.index);
                this.openCreateNewSenseModal(entryId, index);
            });
        });
    }
    
    openCreateNewEntryModal(index) {
        // For now, open the new entry page in a new tab
        // In a future enhancement, this could be a modal dialog
        const newEntryUrl = '/entry/new';
        const newWindow = window.open(newEntryUrl, '_blank');
        
        // Show a message to the user
        const input = document.querySelector(`input[name="relations[${index}].ref"]`);
        if (input) {
            input.placeholder = 'Create new entry in the opened tab, then paste its ID here';
        }
    }
    
    openCreateNewSenseModal(entryId, index) {
        // For now, open the entry edit page in a new tab
        // In a future enhancement, this could add a sense inline
        const editEntryUrl = `/entry/${entryId}/edit`;
        const newWindow = window.open(editEntryUrl, '_blank');
        
        // Show a message to the user
        const input = document.querySelector(`input[name="relations[${index}].ref"]`);
        if (input) {
            input.placeholder = `Add sense to entry ${entryId} in the opened tab, then use ${entryId}#<sense_id>`;
        }
    }
    
    reindexRelations() {
        const relationElements = this.container.querySelectorAll('.relation-item');
        
        relationElements.forEach((element, newIndex) => {
            // Update data attribute
            element.setAttribute('data-relation-index', newIndex);
            
            // Update header number
            const header = element.querySelector('.card-header h6');
            if (header) {
                header.innerHTML = `
                    <i class="fas fa-link text-primary me-2"></i>
                    Relation ${newIndex + 1}
                `;
            }
            
            // Update all input names and IDs
            const inputs = element.querySelectorAll('input, select');
            inputs.forEach(input => {
                const name = input.getAttribute('name');
                if (name) {
                    const newName = name.replace(/relations\[\d+\]/, `relations[${newIndex}]`);
                    input.setAttribute('name', newName);
                }
                
                const dataIndex = input.getAttribute('data-index');
                if (dataIndex !== null) {
                    input.setAttribute('data-index', newIndex);
                }
            });
            
            // Update remove button
            const removeBtn = element.querySelector('.remove-relation-btn');
            if (removeBtn) {
                removeBtn.setAttribute('data-index', newIndex);
            }
            
            // Update search results container
            const searchResults = element.querySelector('.search-results');
            if (searchResults) {
                searchResults.id = `search-results-${newIndex}`;
            }
        });
    }
    
    showEmptyState() {
        this.container.innerHTML = `
            <div class="empty-state text-center py-4">
                <i class="fas fa-link fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Relations</h5>
                <p class="text-muted">Add semantic relations to connect this entry with other entries in the dictionary.</p>
            </div>
        `;
    }
    
    hideEmptyState() {
        const emptyState = this.container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
    }
    
    // Validation helper
    validateRelations() {
        const relations = this.getExistingRelationsFromForm();
        const errors = [];
        
        relations.forEach((relation, index) => {
            if (!relation.type) {
                errors.push(`Relation ${index + 1}: Relation type is required`);
            }
            
            if (!relation.ref) {
                errors.push(`Relation ${index + 1}: Target entry reference is required`);
            }
            
            // Check for duplicate relations
            const duplicates = relations.filter(r => 
                r.type === relation.type && r.ref === relation.ref
            );
            if (duplicates.length > 1) {
                errors.push(`Relation ${index + 1}: Duplicate relation "${relation.type}" to "${relation.ref}"`);
            }
        });
        
        return errors;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('relations-container')) {
        window.relationsManager = new RelationsManager('relations-container');
    }
});

// Expose class to global window object for debugging
window.RelationsManager = RelationsManager;
