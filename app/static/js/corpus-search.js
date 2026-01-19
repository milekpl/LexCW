/**
 * Corpus Search Module
 *
 * Provides corpus search functionality from within the entry form,
 * allowing lexicographers to search for example sentences and
 * insert them as templates.
 */

(function() {
    'use strict';

    /**
     * Escape HTML to prevent XSS
     * @param {string} text
     * @returns {string}
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * CorpusSearch class - manages corpus search modal and actions
     */
    class CorpusSearch {
        constructor() {
            this.targetField = null;      // 'example' or 'definition'
            this.targetIndex = null;      // sense index
            this.headword = null;
            this.results = [];
            this.defaultLimit = 500;
            this.currentQuery = '';
            this.modalElement = null;
            this.searchInput = null;
            this.resultsContainer = null;
            this.resultsInfo = null;
            this.resultCount = null;
            this.loadingIndicator = null;
            this.errorIndicator = null;
            this.errorMessage = null;

            this._initialized = false;
        }

        /**
         * Initialize the corpus search module
         */
        init() {
            if (this._initialized) {
                return;
            }

            this.modalElement = document.getElementById('corpusSearchModal');
            if (!this.modalElement) {
                Logger.warn('CorpusSearch: Modal element not found');
                return;
            }

            // Cache DOM elements
            this.searchInput = document.getElementById('corpusSearchInput');
            this.resultsContainer = document.getElementById('corpusSearchResults');
            this.resultsInfo = document.getElementById('corpusResultsInfo');
            this.resultCount = document.getElementById('corpusResultCount');
            this.loadingIndicator = document.getElementById('corpusSearchLoading');
            this.errorIndicator = document.getElementById('corpusSearchError');
            this.errorMessage = document.getElementById('corpusErrorMessage');

            // Bind event handlers
            this._bindEvents();

            // Mark as initialized
            this._initialized = true;
            Logger.info('CorpusSearch: Initialized');
        }

        /**
         * Bind event handlers for the modal
         * @private
         */
        _bindEvents() {
            const self = this;

            // Search button click
            const searchBtn = document.getElementById('corpusSearchBtn');
            if (searchBtn) {
                searchBtn.addEventListener('click', function() {
                    self._performSearch();
                });
            }

            // Enter key in search input
            if (this.searchInput) {
                this.searchInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        self._performSearch();
                    }
                });
            }

            // Retry button
            const retryBtn = document.getElementById('corpusRetryBtn');
            if (retryBtn) {
                retryBtn.addEventListener('click', function() {
                    self._performSearch();
                });
            }

            // Reset modal state when hidden
            this.modalElement.addEventListener('hidden.bs.modal', function() {
                self._resetState();
            });

            // Handle search corpus buttons in the entry form
            document.addEventListener('click', function(e) {
                const btn = e.target.closest('.search-corpus-btn');
                if (btn) {
                    e.preventDefault();
                    self._openFromButton(btn);
                }
            });
        }

        /**
         * Open modal from a button click
         * @private
         * @param {HTMLElement} button - The clicked button element
         */
        _openFromButton(button) {
            const senseIndex = button.dataset.senseIndex;
            const field = button.dataset.field || 'example';

            // Get headword from the entry form
            const headword = this._getHeadword();

            this.open(field, senseIndex, headword);
        }

        /**
         * Get the current entry's headword
         * @private
         * @returns {string} The headword or empty string
         */
        _getHeadword() {
            // Try to get from the lexical unit input using class selector
            const lexicalUnitInputs = document.querySelectorAll('.lexical-unit-text');
            if (lexicalUnitInputs && lexicalUnitInputs.length > 0) {
                // Get the first non-empty value from primary language input
                for (const input of lexicalUnitInputs) {
                    if (input.value && input.value.trim()) {
                        return input.value.trim();
                    }
                }
            }

            // Fallback: look for the entry title/heading
            // The h2 contains "Edit Entry: headword" so we need to extract just the headword
            const entryTitle = document.querySelector('h2 .text-primary');
            if (entryTitle && entryTitle.textContent) {
                const text = entryTitle.textContent.trim();
                // If the title contains "Edit Entry: ", extract just the headword
                const match = text.match(/^Edit Entry:\s*(.+)$/);
                if (match) {
                    return match[1].trim();
                }
                return text;
            }

            return '';
        }

        /**
         * Open the corpus search modal
         * @param {string} targetField - 'example' or 'definition'
         * @param {number} targetIndex - Sense index
         * @param {string} headword - Headword to pre-fill
         */
        open(targetField, targetIndex, headword) {
            if (!this._initialized) {
                this.init();
            }

            this.targetField = targetField;
            this.targetIndex = targetIndex;
            this.headword = headword || '';

            // Pre-fill search input with headword
            if (this.searchInput && this.headword) {
                this.searchInput.value = this.headword;
            }

            // Show initial state
            this._showInitialState();

            // Show the modal
            const modal = new bootstrap.Modal(this.modalElement);
            modal.show();

            // If we have a headword, auto-search
            if (this.headword) {
                setTimeout(() => this._performSearch(), 100);
            }
        }

        /**
         * Close the modal
         */
        close() {
            const modal = bootstrap.Modal.getInstance(this.modalElement);
            if (modal) {
                modal.hide();
            }
        }

        /**
         * Reset modal to initial state
         * @private
         */
        _resetState() {
            this.results = [];
            this.currentQuery = '';
            this.targetField = null;
            this.targetIndex = null;
            this.headword = null;

            if (this.searchInput) {
                this.searchInput.value = '';
            }

            this._showInitialState();
        }

        /**
         * Show initial empty state
         * @private
         */
        _showInitialState() {
            this.resultsContainer.innerHTML = '';
            const emptyDiv = document.createElement('div');
            emptyDiv.className = 'text-center text-muted py-5';

            const icon = document.createElement('i');
            icon.className = 'fas fa-search fa-3x mb-3';
            emptyDiv.appendChild(icon);

            const p = document.createElement('p');
            p.textContent = 'Enter a search term to find corpus examples';
            emptyDiv.appendChild(p);

            this.resultsContainer.appendChild(emptyDiv);
            this.resultsContainer.style.display = 'block';
            this.resultsInfo.style.display = 'none';
            this.loadingIndicator.style.display = 'none';
            this.errorIndicator.style.display = 'none';
        }

        /**
         * Perform the search
         * @private
         */
        async _performSearch() {
            const query = this.searchInput ? this.searchInput.value.trim() : '';

            if (!query) {
                this._showError('Please enter a search term');
                return;
            }

            this.currentQuery = query;

            // Show loading
            this._showLoading(true);

            try {
                const limit = this.defaultLimit;

                const url = `/api/corpus/search?q=${encodeURIComponent(query)}&limit=${limit}`;

                const response = await fetch(url);

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.error || `HTTP ${response.status}`);
                }

                const data = await response.json();

                if (!data.success) {
                    throw new Error(data.error || 'Search failed');
                }

                this.results = data.results;
                this._showResults(data);

            } catch (error) {
                Logger.error('CorpusSearch: Search failed', error);
                this._showError(error.message || 'Search failed. Please try again.');
            } finally {
                this._showLoading(false);
            }
        }

        /**
         * Show loading state
         * @private
         * @param {boolean} isLoading
         */
        _showLoading(isLoading) {
            if (this.loadingIndicator) {
                this.loadingIndicator.style.display = isLoading ? 'block' : 'none';
            }
            this.resultsContainer.style.display = isLoading ? 'none' : 'block';
            this.errorIndicator.style.display = 'none';
        }

        /**
         * Show error state
         * @private
         * @param {string} message
         */
        _showError(message) {
            this.resultsContainer.style.display = 'none';
            this.loadingIndicator.style.display = 'none';
            this.errorIndicator.style.display = 'block';
            this.resultsInfo.style.display = 'none';

            if (this.errorMessage) {
                this.errorMessage.textContent = message;
            }
        }

        /**
         * Show search results
         * @private
         * @param {Object} data - Response data from API
         */
        _showResults(data) {
            const total = data.total || data.results.length;
            const query = data.query;

            // Update results info
            if (this.resultCount) {
                this.resultCount.textContent = total;
            }
            this.resultsInfo.style.display = 'block';

            // Hide loading and error
            this.loadingIndicator.style.display = 'none';
            this.errorIndicator.style.display = 'none';
            this.resultsContainer.style.display = 'block';

            // Clear container
            this.resultsContainer.innerHTML = '';

            if (total === 0) {
                const emptyDiv = document.createElement('div');
                emptyDiv.className = 'text-center text-muted py-5';

                const icon = document.createElement('i');
                icon.className = 'fas fa-search fa-3x mb-3';
                emptyDiv.appendChild(icon);

                const p = document.createElement('p');
                p.textContent = `No examples found for "${escapeHtml(query)}"`;
                emptyDiv.appendChild(p);

                const small = document.createElement('small');
                small.className = 'text-muted';
                small.textContent = 'Try a different search term or check spelling';
                emptyDiv.appendChild(small);

                this.resultsContainer.appendChild(emptyDiv);
                return;
            }

            // Render results
            data.results.forEach((result, index) => {
                const resultEl = this._createResultElement(result, index);
                this.resultsContainer.appendChild(resultEl);
            });

            // Bind insert/copy actions
            this._bindResultActions();
        }

        /**
         * Create a single result element
         * @private
         * @param {Object} result - Result data
         * @param {number} index - Result index
         * @returns {HTMLElement}
         */
        _createResultElement(result, index) {
            const div = document.createElement('div');
            div.className = 'corpus-result';
            div.dataset.index = index;

            // Use source text as the sentence for insertion
            const fullSentence = result.source || '';
            div.dataset.sentence = fullSentence;

            // Parallel corpus display (source/target)
            const parallelDiv = document.createElement('div');
            parallelDiv.className = 'corpus-parallel';

            // Source text
            if (result.source) {
                const sourceDiv = document.createElement('div');
                sourceDiv.className = 'corpus-source mb-1';
                sourceDiv.textContent = result.source;
                parallelDiv.appendChild(sourceDiv);
            }

            // Target translation
            if (result.target) {
                const targetDiv = document.createElement('div');
                targetDiv.className = 'corpus-target text-muted small';
                targetDiv.textContent = result.target;
                parallelDiv.appendChild(targetDiv);
            }

            div.appendChild(parallelDiv);

            // Actions
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'corpus-result-actions';

            // Insert as Example button
            const insertBtn = document.createElement('button');
            insertBtn.type = 'button';
            insertBtn.className = 'btn btn-sm btn-primary insert-example-btn';
            insertBtn.dataset.index = index;
            insertBtn.title = 'Add as new example';

            const insertIcon = document.createElement('i');
            insertIcon.className = 'fas fa-plus';
            insertBtn.appendChild(insertIcon);
            insertBtn.appendChild(document.createTextNode(' Insert as Example'));

            actionsDiv.appendChild(insertBtn);

            // Copy button
            const copyBtn = document.createElement('button');
            copyBtn.type = 'button';
            copyBtn.className = 'btn btn-sm btn-outline-secondary copy-btn';
            copyBtn.dataset.index = index;
            copyBtn.title = 'Copy to clipboard';

            const copyIcon = document.createElement('i');
            copyIcon.className = 'fas fa-copy';
            copyBtn.appendChild(copyIcon);
            copyBtn.appendChild(document.createTextNode(' Copy'));

            actionsDiv.appendChild(copyBtn);

            div.appendChild(actionsDiv);

            return div;
        }

        /**
         * Bind actions for result items
         * @private
         */
        _bindResultActions() {
            const self = this;

            // Insert as example buttons
            this.resultsContainer.querySelectorAll('.insert-example-btn').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const index = parseInt(this.dataset.index, 10);
                    self._insertAsExample(index);
                });
            });

            // Copy buttons
            this.resultsContainer.querySelectorAll('.copy-btn').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const index = parseInt(this.dataset.index, 10);
                    self._copyToClipboard(index);
                });
            });
        }

        /**
         * Insert result as a new example
         * @private
         * @param {number} index - Result index
         */
        _insertAsExample(index) {
            const result = this.results[index];
            if (!result) return;

            // Build full sentence - support both source field and left/match/right fields
            let fullSentence = '';
            if (result.source) {
                fullSentence = result.source;
            } else if (result.left !== undefined || result.match !== undefined || result.right !== undefined) {
                fullSentence = `${result.left || ''} ${result.match || ''} ${result.right || ''}`.trim();
            } else {
                Logger.warn('_insertAsExample: Result has no sentence data', { result });
            }

            if (this.targetField === 'example' && this.targetIndex !== null) {
                // Trigger add example event
                const event = new CustomEvent('corpusExampleSelected', {
                    detail: {
                        senseIndex: this.targetIndex,
                        sentence: fullSentence,
                        translation: result.target || ''
                    }
                });
                document.dispatchEvent(event);

                Logger.info('CorpusSearch: Example selected', { senseIndex: this.targetIndex, hasTranslation: !!result.target });
            } else {
                // For definitions, copy to clipboard
                navigator.clipboard.writeText(fullSentence).then(() => {
                    this._showToast('Copied to clipboard');
                });
            }

            // Close modal
            this.close();
        }

        /**
         * Copy result to clipboard
         * @private
         * @param {number} index - Result index
         */
        _copyToClipboard(index) {
            const result = this.results[index];
            if (!result) return;

            const fullSentence = `${result.left || ''} ${result.match || ''} ${result.right || ''}`.trim();

            navigator.clipboard.writeText(fullSentence).then(() => {
                this._showToast('Copied to clipboard');
            }).catch(err => {
                Logger.error('CorpusSearch: Copy failed', err);
                this._showError('Failed to copy to clipboard');
            });
        }

        /**
         * Show toast notification
         * @private
         * @param {string} message
         */
        _showToast(message) {
            if (typeof Toast !== 'undefined') {
                Toast.success(message);
            } else if (typeof showToast === 'function') {
                showToast(message, 'success');
            } else {
                // Fallback: log to console
                Logger.info('CorpusSearch:', message);
            }
        }

        /**
         * Check if the corpus service is available
         * @returns {Promise<boolean>}
         */
        async checkAvailability() {
            try {
                const response = await fetch('/api/corpus/stats');
                const data = await response.json();
                return data.success && data.total_records > 0;
            } catch (e) {
                return false;
            }
        }
    }

    // Singleton instance
    let instance = null;

    /**
     * Get the singleton instance
     * @returns {CorpusSearch}
     */
    CorpusSearch.getInstance = function() {
        if (!instance) {
            instance = new CorpusSearch();
        }
        return instance;
    };

    // Export to window
    window.CorpusSearch = CorpusSearch;

})();
