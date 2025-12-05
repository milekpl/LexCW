/**
 * Sense Relation Search Handler
 * Provides search functionality for selecting target senses in sense relations
 */

class SenseRelationSearchHandler {
    constructor() {
        this.currentEntryId = null;
        this.init();
    }
    
    init() {
        // Get current entry ID from form
        const entryIdInput = document.querySelector('input[name="id"]');
        if (entryIdInput && entryIdInput.value) {
            this.currentEntryId = entryIdInput.value;
        }
        
        // Add event delegation for sense relation search
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('sense-relation-search-input')) {
                this.handleSenseRelationSearch(e.target);
            }
        });
        
        // Add event delegation for search button clicks
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('sense-relation-search-btn') || 
                e.target.closest('.sense-relation-search-btn')) {
                const btn = e.target.classList.contains('sense-relation-search-btn') ? 
                           e.target : e.target.closest('.sense-relation-search-btn');
                const input = document.querySelector(
                    `.sense-relation-search-input[data-sense-index="${btn.dataset.senseIndex}"][data-relation-index="${btn.dataset.relationIndex}"]`
                );
                if (input && input.value.trim()) {
                    this.handleSenseRelationSearch(input);
                }
            }
        });
        
        // Hide search results when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.sense-relation-search-input') && 
                !e.target.closest('.sense-relation-search-results')) {
                document.querySelectorAll('.sense-relation-search-results').forEach(container => {
                    container.style.display = 'none';
                });
            }
        });
    }
    
    async handleSenseRelationSearch(input) {
        const searchTerm = input.value.trim();
        const senseIndex = input.dataset.senseIndex;
        const relationIndex = input.dataset.relationIndex;
        const resultsContainer = document.getElementById(`sense-search-results-${senseIndex}-${relationIndex}`);
        
        if (searchTerm.length < 2) {
            resultsContainer.style.display = 'none';
            return;
        }
        
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(searchTerm)}&limit=10`);
            if (response.ok) {
                const result = await response.json();
                this.displaySenseSearchResults(result.entries || [], resultsContainer, senseIndex, relationIndex);
            }
        } catch (error) {
            console.warn('[SenseRelationSearchHandler] Entry search failed:', error);
        }
    }
    
    displaySenseSearchResults(entries, container, senseIndex, relationIndex) {
        if (entries.length === 0) {
            container.innerHTML = '<div class="alert alert-info mt-2">No entries found</div>';
            container.style.display = 'block';
            return;
        }
        
        const resultsHtml = entries.map(entry => {
            const headword = this.getEntryHeadword(entry);
            const sensesHtml = entry.senses ? entry.senses.map((sense, idx) => {
                const gloss = sense.gloss?.en || sense.definition?.en || sense.definition?.pl || 'No definition';
                const senseId = sense.id || `${entry.id}_sense_${idx}`;
                return `
                    <div class="sense-result-item p-2 border-top" 
                         style="cursor: pointer;"
                         data-sense-id="${senseId}"
                         data-entry-headword="${headword}"
                         data-sense-gloss="${gloss}"
                         data-sense-index="${senseIndex}"
                         data-relation-index="${relationIndex}">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <small class="text-muted">Sense ${idx + 1}:</small>
                                <span class="text-dark">${gloss}</span>
                            </div>
                            <i class="fas fa-check-circle text-success"></i>
                        </div>
                    </div>
                `;
            }).join('') : '';
            
            return `
                <div class="entry-result-group border rounded mb-2 mt-2 bg-white">
                    <div class="entry-result-header p-2 bg-light border-bottom">
                        <div class="fw-bold">${headword}</div>
                        <small class="text-muted">${entry.senses ? entry.senses.length : 0} sense(s)</small>
                    </div>
                    ${sensesHtml}
                </div>
            `;
        }).join('');
        
        container.innerHTML = resultsHtml;
        container.style.display = 'block';
        
        // Add click handlers for sense selection
        container.querySelectorAll('.sense-result-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectSenseRelationTarget(item);
            });
        });
    }
    
    selectSenseRelationTarget(senseItem) {
        const senseId = senseItem.dataset.senseId;
        const headword = senseItem.dataset.entryHeadword;
        const gloss = senseItem.dataset.senseGloss;
        const senseIndex = senseItem.dataset.senseIndex;
        const relationIndex = senseItem.dataset.relationIndex;
        
        // Check for circular reference (sense within same entry)
        if (this.currentEntryId && senseId.startsWith(this.currentEntryId)) {
            alert('Cannot create relation to a sense within the same entry (circular reference detected)');
            return;
        }
        
        // Update the hidden input with the sense ID
        const hiddenInput = document.querySelector(
            `input[name="senses[${senseIndex}].relations[${relationIndex}].ref"]`
        );
        if (hiddenInput) {
            hiddenInput.value = senseId;
        }
        
        // Find the relation card and update display
        const searchInput = document.querySelector(
            `.sense-relation-search-input[data-sense-index="${senseIndex}"][data-relation-index="${relationIndex}"]`
        );
        const relationCard = searchInput ? searchInput.closest('.sense-relation-item') : null;
        
        if (relationCard) {
            const colMd8 = relationCard.querySelector('.col-md-8');
            if (colMd8) {
                // Remove old alert if exists
                const oldAlert = colMd8.querySelector('.alert');
                if (oldAlert) {
                    oldAlert.remove();
                }
                
                // Add new alert showing selected target
                const newAlert = document.createElement('div');
                newAlert.className = 'alert alert-light mb-2';
                newAlert.innerHTML = `
                    <i class="fas fa-project-diagram me-2"></i>
                    <strong>Related to: </strong>
                    <span class="fw-bold text-dark">${headword}</span>
                    <span class="text-muted"> — ${gloss}</span>
                `;
                const hiddenInputEl = colMd8.querySelector('.sense-relation-ref-hidden');
                if (hiddenInputEl) {
                    colMd8.insertBefore(newAlert, hiddenInputEl);
                }
            }
        }
        
        // Hide search results
        const resultsContainer = document.getElementById(`sense-search-results-${senseIndex}-${relationIndex}`);
        if (resultsContainer) {
            resultsContainer.style.display = 'none';
        }
        
        // Clear search input
        if (searchInput) {
            searchInput.value = '';
        }
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
    window.senseRelationSearchHandler = new SenseRelationSearchHandler();
});
