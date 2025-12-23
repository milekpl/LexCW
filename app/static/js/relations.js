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
        
        // If loading fails, keep relationTypes empty — no fallback values allowed
        this.relationTypes = [];
        console.warn('[RelationsManager] No relation types loaded from ranges or API; relation dropdowns will remain empty');
    }
    
    initializeExistingRelationDropdowns() {
        // Initialize any existing relation type dropdowns that were server-side rendered
        const relationSelects = this.container.querySelectorAll('.lexical-relation-select');
        
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
        
        // Track if we found the current value in the loaded types
        let currentValueFound = false;
        
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
                currentValueFound = true;
            }
            
            selectElement.appendChild(option);
        });
        
        // If the current value wasn't found in the loaded types, do NOT add it as fallback.
        // Selecting an absent value should be handled by server/UI validation instead.
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
        
        // Handle relation type changes (to update XML preview)
        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('lexical-relation-select')) {
                // Trigger XML preview update when relation type changes
                if (window.updateXmlPreview) {
                    window.updateXmlPreview();
                }
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

        // Initialize the new relation's dropdown with range data
        const newSelect = this.container.querySelector(`.relation-item[data-relation-index="${newIndex}"] .lexical-relation-select`);
        if (newSelect) {
            // Populate with loaded relation types or use rangesLoader if available
            if (this.relationTypes && this.relationTypes.length > 0) {
                this.populateRelationTypeSelect(newSelect);
            } else if (window.rangesLoader) {
                // If rangesLoader is available, use it to populate the select
                window.rangesLoader.populateSelect(newSelect, this.rangeId, {
                    emptyOption: 'Select type'
                }).catch(err => {
                    console.error(`[RelationsManager] Failed to populate select via rangesLoader:`, err);
                });
            }
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
                            <select class="form-control lexical-relation-select"
                                    name="relations[${index}].type"
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
                                   name="relations[${index}].ref"
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

    async handleEntrySearch(input) {
        const searchTerm = input.value.trim();
        const relationIndex = input.dataset.relationIndex;
        const resultsContainer = document.getElementById(`search-results-${relationIndex}`);

        if (searchTerm.length < 2) {
            resultsContainer.style.display = 'none';
            return;
        }

        try {
            // Use a higher limit for more comprehensive search results
            const response = await fetch(`/api/search?q=${encodeURIComponent(searchTerm)}&limit=100`);
            if (response.ok) {
                const result = await response.json();
                const prioritizedEntries = this.prioritizeSearchResults(result.entries || [], searchTerm);
                this.displaySearchResults(prioritizedEntries, resultsContainer, relationIndex);
            }
        } catch (error) {
            console.warn('[RelationsManager] Entry search failed:', error);
        }
    }

    /**
     * Prioritize search results by placing exact matches at the top
     * @param {Array} entries - Array of search results
     * @param {string} searchTerm - The term being searched for
     * @returns {Array} - Prioritized array of entries
     */
    prioritizeSearchResults(entries, searchTerm) {
        // Create a normalized search term for comparison
        const normalizedSearchTerm = searchTerm.toLowerCase().trim();

        // Separate exact matches, partial matches, and others
        const exactMatches = [];
        const partialMatches = [];
        const otherMatches = [];

        entries.forEach(entry => {
            // Get the headword for comparison
            const headword = this.getEntryDisplayText(entry).toLowerCase();

            if (headword === normalizedSearchTerm) {
                exactMatches.push(entry);
            } else if (headword.includes(normalizedSearchTerm)) {
                partialMatches.push(entry);
            } else {
                otherMatches.push(entry);
            }
        });

        // Combine the arrays with exact matches first
        return [...exactMatches, ...partialMatches, ...otherMatches];
    }
    
    displaySearchResults(entries, container, relationIndex) {
        if (entries.length === 0) {
            container.innerHTML = `
                <div class="text-muted p-2 border rounded">No entries found</div>
            `;
            container.style.display = 'block';
            return;
        }

        // Create scrollable container with better styling
        const maxResultsToShow = 50; // Show first 50 results to prevent UI freezing
        const resultsToShow = entries.slice(0, maxResultsToShow);
        const remainingCount = entries.length - maxResultsToShow;

        // Get the search input element to access the current search term
        const input = document.querySelector(
            `.relation-search-input[data-relation-index="${relationIndex}"]`
        );
        const currentSearchTerm = input ? input.value.trim().toLowerCase() : '';

        const resultsHtml = resultsToShow.map(entry => {
            const displayText = this.getEntryDisplayText(entry);
            const isExactMatch = displayText.toLowerCase() === currentSearchTerm;
            const matchIndicator = isExactMatch ? '<span class="badge bg-success ms-2">Exact Match</span>' : '';

            return `
            <div class="search-result-item p-2 border-bottom cursor-pointer"
                 data-entry-id="${entry.id}"
                 data-entry-headword="${displayText}"
                 data-relation-index="${relationIndex}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="fw-bold">${displayText}</div>
                        ${entry.definition ? `<div class="text-muted small">${entry.definition}</div>` : ''}
                    </div>
                    <div>
                        ${matchIndicator}
                    </div>
                </div>
            </div>
        `}).join('');

        container.innerHTML = `
            <div class="search-results-container bg-white shadow-sm" style="max-height: 400px; overflow-y: auto;">
                ${resultsHtml}
            </div>
        `;

        if (remainingCount > 0) {
            const remainingDiv = document.createElement('div');
            remainingDiv.className = 'text-center text-muted p-2';
            remainingDiv.innerHTML = `+ ${remainingCount} more results (refine search for better results)`;
            container.querySelector('.search-results-container').appendChild(remainingDiv);
        }

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
        // Use DOT notation to match the template's field naming convention
        const hiddenInput = this.container.querySelector(`input[name="relations[${relationIndex}].ref"]`);
        if (hiddenInput) {
            hiddenInput.value = entryId;
            // Dispatch change event to trigger any listeners
            hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
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

        // Trigger XML preview update
        if (window.updateXmlPreview) {
            window.updateXmlPreview();
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
            </div>
        `;
    }
}

// Expose the class globally for template initialization
window.RelationsManager = RelationsManager;
