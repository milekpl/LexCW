/**
 * EntrySearchSelect - Reusable searchable entry selector
 *
 * Provides a search box that finds entries by headword/definition
 * and displays results for selection. Used for relation targets.
 */

class EntrySearchSelect {
    constructor(container, options = {}) {
        this.container = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        this.options = {
            placeholder: 'Search for an entry...',
            minSearchLength: 2,
            maxResults: 20,
            onSelect: null,  // callback(entryId, entryData) when entry selected
            ...options
        };

        this.selectedId = null;
        this.selectedText = '';
        this.init();
    }

    init() {
        this.render();
        this.setupEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="entry-search-select">
                <div class="input-group">
                    <input type="text"
                           class="form-control form-control-sm search-input"
                           placeholder="${this.options.placeholder}"
                           autocomplete="off">
                    <button type="button" class="btn btn-outline-secondary search-btn">
                        <i class="bi bi-search"></i>
                    </button>
                </div>
                <div class="search-results mt-1" style="display: none; max-height: 300px; overflow-y: auto; position: absolute; z-index: 1000; background: white; border: 1px solid #dee2e6; border-radius: 0.375rem; box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);"></div>
                <input type="hidden" class="selected-id" value="">
            </div>
        `;

        this.input = this.container.querySelector('.search-input');
        this.resultsContainer = this.container.querySelector('.search-results');
        this.hiddenInput = this.container.querySelector('.selected-id');
    }

    setupEventListeners() {
        // Search on input
        this.input.addEventListener('input', (e) => {
            this.handleSearch(e.target.value);
        });

        // Search button
        this.container.querySelector('.search-btn').addEventListener('click', () => {
            this.handleSearch(this.input.value);
        });

        // Keyboard navigation
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideResults();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateResults(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateResults(-1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                this.selectHighlighted();
            }
        });

        // Click outside to close
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.hideResults();
            }
        });
    }

    async handleSearch(searchTerm) {
        if (searchTerm.length < this.options.minSearchLength) {
            this.hideResults();
            return;
        }

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(searchTerm)}&limit=${this.options.maxResults}`);
            if (response.ok) {
                const result = await response.json();
                this.displayResults(result.entries || [], searchTerm);
            }
        } catch (error) {
            console.warn('[EntrySearchSelect] Search failed:', error);
        }
    }

    displayResults(entries, searchTerm) {
        if (entries.length === 0) {
            this.resultsContainer.innerHTML = `
                <div class="p-3 text-center text-muted">No entries found</div>
            `;
            this.resultsContainer.style.display = 'block';
            return;
        }

        const html = entries.map((entry, index) => {
            const headword = this.getEntryHeadword(entry);
            const definition = entry.definition || '';
            const isHighlighted = index === 0;

            return `
                <div class="search-result p-2 border-bottom ${isHighlighted ? 'highlighted' : ''}"
                     data-index="${index}"
                     data-id="${entry.id}"
                     data-headword="${this.escapeHtml(headword)}"
                     style="cursor: pointer; background: ${isHighlighted ? '#f8f9fa' : 'white'};">
                    <div class="fw-bold">${this.escapeHtml(headword)}</div>
                    ${definition ? `<div class="text-muted small text-truncate">${this.escapeHtml(definition)}</div>` : ''}
                </div>
            `;
        }).join('');

        this.resultsContainer.innerHTML = html;
        this.resultsContainer.style.display = 'block';
        this.currentEntries = entries;
        this.highlightIndex = 0;
    }

    navigateResults(direction) {
        if (!this.currentEntries || this.currentEntries.length === 0) return;

        this.highlightIndex = Math.max(0, Math.min(this.highlightIndex + direction, this.currentEntries.length - 1));

        const items = this.resultsContainer.querySelectorAll('.search-result');
        items.forEach((item, index) => {
            const isHighlighted = index === this.highlightIndex;
            item.style.background = isHighlighted ? '#f8f9fa' : 'white';
        });

        items[this.highlightIndex]?.scrollIntoView({ block: 'nearest' });
    }

    selectHighlighted() {
        if (!this.currentEntries || this.highlightIndex >= this.currentEntries.length) return;
        this.selectEntry(this.currentEntries[this.highlightIndex]);
    }

    selectEntry(entry) {
        const entryId = entry.id;
        const headword = this.getEntryHeadword(entry);

        this.selectedId = entryId;
        this.selectedText = headword;
        this.input.value = headword;
        this.hiddenInput.value = entryId;
        this.hideResults();

        if (this.options.onSelect) {
            this.options.onSelect(entryId, entry);
        }

        // Dispatch change event
        this.hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    hideResults() {
        this.resultsContainer.style.display = 'none';
        this.currentEntries = [];
        this.highlightIndex = 0;
    }

    getEntryHeadword(entry) {
        // Try various formats the API might return
        if (typeof entry.lexical_unit === 'string') {
            return entry.lexical_unit;
        }
        if (entry.lexical_unit?.en) {
            return entry.lexical_unit.en;
        }
        if (entry.headword) {
            return entry.headword;
        }
        return entry.id || 'Unknown';
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Public API
    getValue() {
        return this.selectedId;
    }

    setValue(entryId, entryText = '') {
        this.selectedId = entryId;
        this.selectedText = entryText;
        this.input.value = entryText;
        this.hiddenInput.value = entryId;
    }

    clear() {
        this.selectedId = null;
        this.selectedText = '';
        this.input.value = '';
        this.hiddenInput.value = '';
        this.hideResults();
    }
}

// Export for use in other modules
window.EntrySearchSelect = EntrySearchSelect;
