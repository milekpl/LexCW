/**
 * EntryCreationManager - Centralized entry creation and sense selection
 *
 * Responsibilities:
 * - Create minimal entries from search terms
 * - Fetch senses for newly created entries
 * - Manage sense selection modal
 * - Handle circular reference detection
 *
 * Note: This module uses innerHTML intentionally for dynamic UI generation.
 * All user input (search terms, entry data) is properly escaped via _escapeHtml().
 */

(function() {
    'use strict';

    class EntryCreationManager {
        constructor(options = {}) {
            this.options = {
                apiEndpoint: '/api/entries',
                sensesEndpoint: '/api/entries',
                sourceLanguage: 'en',
                currentEntryId: null,
                onEntryCreated: null,        // callback(entryId, entryData)
                onSenseSelected: null,       // callback(senseId, entryId, context)
                onError: null,               // callback(error)
                ...options
            };

            this._currentContext = null;
            this._modalInstance = null;
            this._currentEntryId = this.options.currentEntryId;

            // Bind methods for event handling
            this._boundMethods = new WeakMap();
            this._bind = this._bind.bind(this);
        }

        /**
         * Bind method to preserve 'this' context
         * @private
         */
        _bind(method) {
            if (!this._boundMethods.has(method)) {
                this._boundMethods.set(method, method.bind(this));
            }
            return this._boundMethods.get(method);
        }

        /**
         * Set the current entry ID (for circular reference detection)
         * @param {string} entryId - Current entry being edited
         */
        setCurrentEntryId(entryId) {
            this._currentEntryId = entryId;
        }

        /**
         * Generate a UUID for new entries
         * @returns {string}
         */
        generateUUID() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }

        /**
         * Create a minimal entry with a lexical unit and a default empty sense
         * (sense must have definition/gloss to pass validation, user can edit later)
         * @param {string} searchTerm - The search term to use as lexical unit
         * @param {string} sourceLang - Source language code (default from options)
         * @returns {Promise<Object>} Created entry data
         */
        async createEntry(searchTerm, sourceLang = null) {
            const lang = sourceLang || this.options.sourceLanguage;
            const entryId = this.generateUUID();
            const senseId = `${entryId}_sense_1`;

            // Include a default empty sense with minimal definition to pass validation
            // The definition uses the lexical unit as placeholder - user can edit later
            const payload = {
                id: entryId,
                lexical_unit: {
                    [lang]: searchTerm
                },
                senses: [
                    {
                        id: senseId,
                        definition: {
                            [lang]: {
                                text: `[Edit: ${searchTerm}]`,
                                lang: lang
                            }
                        },
                        gloss: {}
                    }
                ]
            };

            console.log(`[EntryCreationManager] Creating entry with term "${searchTerm}" (${lang}) and default sense`);

            try {
                const response = await fetch(this.options.apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-CSRF-Token': this._getCsrfToken()
                    },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.error || `HTTP ${response.status}: Failed to create entry`);
                }

                const result = await response.json();

                console.log(`[EntryCreationManager] Entry created: ${entryId}`);

                // Call callback if provided
                if (this.options.onEntryCreated) {
                    this.options.onEntryCreated(entryId, { id: entryId, lexical_unit: payload.lexical_unit });
                }

                return {
                    id: entryId,
                    ...payload,
                    success: true
                };
            } catch (error) {
                console.error('[EntryCreationManager] Failed to create entry:', error);

                if (this.options.onError) {
                    this.options.onError(error);
                }

                throw error;
            }
        }

        /**
         * Fetch senses for a newly created entry
         * @param {string} entryId - The entry ID to fetch senses for
         * @returns {Promise<Object[]>} Array of sense objects
         */
        async fetchEntrySenses(entryId) {
            try {
                const response = await fetch(`${this.options.sensesEndpoint}/${entryId}`);

                if (!response.ok) {
                    throw new Error(`Failed to fetch entry ${entryId}`);
                }

                const entry = await response.json();

                // Return senses array (may be empty for new entries)
                return entry.senses || [];
            } catch (error) {
                console.error('[EntryCreationManager] Failed to fetch senses:', error);
                return [];
            }
        }

        /**
         * Add "Create new entry" option to search results
         * @param {string} searchTerm - The current search term
         * @param {HTMLElement} resultsContainer - Container for search results
         * @param {Object} context - Context info (relationIndex, variantIndex, etc.)
         */
        addCreateOptionToResults(searchTerm, resultsContainer, context = {}) {
            if (!searchTerm || searchTerm.length < 2) return;

            const createOptionHtml = this._getCreateOptionHtml(searchTerm, context);

            // Insert at the top of results
            const existingResults = resultsContainer.innerHTML;
            resultsContainer.innerHTML = createOptionHtml + existingResults;

            // Add click handler
            const createOption = resultsContainer.querySelector('.create-entry-option');
            if (createOption) {
                createOption.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    await this._handleCreateAndSelect(searchTerm, context);
                });
            }
        }

        /**
         * Generate HTML for "Create new entry" option
         * @private
         */
        _getCreateOptionHtml(searchTerm, context) {
            // All user input is properly escaped before being inserted
            const escapedTerm = this._escapeHtml(searchTerm);
            const contextJson = this._escapeHtml(JSON.stringify(context));

            return (
                '<div class="search-result-item create-entry-option p-2 border-bottom bg-light" ' +
                `data-search-term="${escapedTerm}" ` +
                `data-context='${contextJson}' ` +
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
         * Handle the complete flow: create entry -> fetch senses -> show modal -> select sense
         * @param {string} searchTerm - The search term
         * @param {Object} context - Context info (relationIndex, variantIndex, etc.)
         * @private
         */
        async _handleCreateAndSelect(searchTerm, context) {
            // Store context for callbacks
            this._currentContext = context;

            try {
                // Show loading state
                this._showLoading(context);

                // Step 1: Create the entry
                const createdEntry = await this.createEntry(searchTerm);

                // Step 2: Fetch senses (new entries will typically have none)
                const senses = await this.fetchEntrySenses(createdEntry.id);

                // Step 3: If senses exist, show modal; otherwise use entry directly
                if (senses.length > 0) {
                    await this._showSenseSelectionModal(createdEntry, senses, context);
                } else {
                    // No senses - use entry directly (will need user to add sense later)
                    this._handleNoSensesCase(createdEntry, context);
                }
            } catch (error) {
                this._showError(error, context);
            } finally {
                this._hideLoading(context);
            }
        }

        /**
         * Show sense selection modal
         * @param {Object} entry - The created entry
         * @param {Object[]} senses - Array of senses
         * @param {Object} context - Context info
         * @private
         */
        async _showSenseSelectionModal(entry, senses, context) {
            // Remove existing modal if any
            this._removeModal();

            const modalHtml = this._createSenseModalHtml(entry, senses);
            document.body.insertAdjacentHTML('beforeend', modalHtml);

            const modal = document.getElementById('sense-selection-modal');
            if (!modal) return;

            // Setup event handlers
            modal.querySelectorAll('.sense-option-item').forEach(item => {
                item.addEventListener('click', () => {
                    const senseId = item.dataset.senseId;
                    const senseData = JSON.parse(item.dataset.senseData);

                    this._selectSense(senseId, entry.id, senseData, context);
                    this._hideModal();
                });
            });

            // Cancel button
            const cancelBtn = modal.querySelector('#sense-modal-cancel');
            if (cancelBtn) {
                cancelBtn.addEventListener('click', () => {
                    this._handleCancel(entry.id, context);
                    this._hideModal();
                });
            }

            // Click outside to close
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this._handleCancel(entry.id, context);
                    this._hideModal();
                }
            });

            // Show modal using Bootstrap
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                this._modalInstance = new bootstrap.Modal(modal);
                this._modalInstance.show();
            } else {
                modal.style.display = 'block';
                modal.classList.add('show');
            }
        }

        /**
         * Create HTML for sense selection modal
         * @private
         */
        _createSenseModalHtml(entry, senses) {
            const headword = this._getEntryHeadword(entry);
            const escapedHeadword = this._escapeHtml(headword);

            // Build senses list HTML
            const sensesHtml = senses.map((sense, index) => {
                const gloss = this._getSenseGloss(sense);
                const definition = this._getSenseDefinition(sense);
                const escapedGloss = gloss ? this._escapeHtml(gloss) : '';
                const escapedDefinition = definition ? this._escapeHtml(definition) : '';
                const senseDataJson = this._escapeHtml(JSON.stringify(sense));

                return (
                    '<div class="sense-option-item list-group-item list-group-item-action p-3" ' +
                    `data-sense-id="${sense.id}" ` +
                    `data-sense-data='${senseDataJson}' ` +
                    'style="cursor: pointer;">' +
                    '<div class="d-flex justify-content-between align-items-start">' +
                    '<div>' +
                    `<div class="fw-bold"><i class="fas fa-layer-group me-2"></i>Sense ${index + 1}</div>` +
                    (escapedGloss ? `<div class="text-muted">${escapedGloss}</div>` : '') +
                    (escapedDefinition ? `<div class="mt-1"><small class="text-primary">${escapedDefinition}</small></div>` : '') +
                    '</div>' +
                    '<i class="fas fa-check-circle text-success"></i>' +
                    '</div></div>'
                );
            }).join('');

            // Entry level option
            const entryDataJson = this._escapeHtml(JSON.stringify({ id: entry.id, isEntryLevel: true }));
            const entryLevelOption = (
                '<div class="sense-option-item list-group-item list-group-item-action p-3" ' +
                `data-sense-id="${entry.id}" ` +
                `data-sense-data='${entryDataJson}' ` +
                'style="cursor: pointer;">' +
                '<div class="d-flex justify-content-between align-items-start">' +
                '<div>' +
                '<div class="fw-bold text-primary"><i class="fas fa-book me-2"></i>Use Entry Level</div>' +
                '<div class="text-muted small">Link to the entire entry (all senses)</div>' +
                '</div>' +
                '<i class="fas fa-arrow-right text-primary"></i>' +
                '</div></div>'
            );

            // Add new sense later option
            const newSenseDataJson = this._escapeHtml(JSON.stringify({ id: '__new_sense__', isNewSense: true }));
            const newSenseOption = (
                '<div class="sense-option-item list-group-item list-group-item-action p-3 border-top" ' +
                `data-sense-id="__new_sense__" ` +
                `data-sense-data='${newSenseDataJson}' ` +
                'style="cursor: pointer;">' +
                '<div class="d-flex justify-content-between align-items-start">' +
                '<div>' +
                '<div class="fw-bold text-success"><i class="fas fa-plus-circle me-2"></i>Add New Sense Later</div>' +
                '<div class="text-muted small">Save entry without linking, add sense after editing</div>' +
                '</div>' +
                '<i class="fas fa-arrow-right text-success"></i>' +
                '</div></div>'
            );

            return (
                '<div class="modal fade" id="sense-selection-modal" tabindex="-1" ' +
                'aria-labelledby="sense-selection-modal-label" aria-hidden="true">' +
                '<div class="modal-dialog modal-dialog-centered">' +
                '<div class="modal-content">' +
                '<div class="modal-header bg-primary text-white">' +
                '<h5 class="modal-title" id="sense-selection-modal-label">' +
                '<i class="fas fa-list-ul me-2"></i>Select Sense</h5>' +
                '<button type="button" class="btn-close btn-close-white" ' +
                'data-bs-dismiss="modal" aria-label="Close"></button>' +
                '</div>' +
                '<div class="modal-body">' +
                '<div class="alert alert-info mb-3">' +
                '<i class="fas fa-info-circle me-2"></i> ' +
                `Entry "<strong>${escapedHeadword}</strong>" was created. ` +
                'Please select which sense to link to, or create a new sense later.' +
                '</div>' +
                '<div class="list-group">' +
                entryLevelOption + sensesHtml + newSenseOption +
                '</div></div>' +
                '<div class="modal-footer">' +
                '<button type="button" class="btn btn-secondary" id="sense-modal-cancel">Cancel</button>' +
                '</div></div></div></div>'
            );
        }

        /**
         * Handle sense selection
         * @private
         */
        _selectSense(senseId, entryId, senseData, context) {
            console.log(`[EntryCreationManager] Selected sense "${senseId}" for entry "${entryId}"`);

            // Check for circular reference
            if (this.detectCircularReference(senseId)) {
                alert('Cannot create relation to an entry within the same entry (circular reference detected)');
                return;
            }

            // Dispatch custom event for other components
            document.dispatchEvent(new CustomEvent('entryCreationManager:senseSelected', {
                bubbles: true,
                detail: {
                    senseId,
                    entryId,
                    senseData,
                    context,
                    timestamp: Date.now()
                }
            }));

            // Call callback if provided
            if (this.options.onSenseSelected) {
                this.options.onSenseSelected(senseId, entryId, context);
            }
        }

        /**
         * Handle case where entry has no senses
         * @private
         */
        _handleNoSensesCase(entry, context) {
            // Use entry-level reference
            this._selectSense(entry.id, entry.id, { isEntryLevel: true }, context);
        }

        /**
         * Handle cancel action
         * @private
         */
        _handleCancel(entryId, context) {
            console.log(`[EntryCreationManager] Canceled sense selection for entry "${entryId}"`);
        }

        /**
         * Show loading state in the calling component
         * @private
         */
        _showLoading(context) {
            const targetId = this._getTargetId(context);
            const target = targetId ? document.getElementById(targetId) : null;

            if (target) {
                const input = target.closest('.card-body')?.querySelector('input[type="text"]');
                if (input) {
                    input.dataset.loading = 'true';
                    input.classList.add('loading');
                }
            }
        }

        /**
         * Hide loading state
         * @private
         */
        _hideLoading(context) {
            const targetId = this._getTargetId(context);
            const target = targetId ? document.getElementById(targetId) : null;

            if (target) {
                const input = target.closest('.card-body')?.querySelector('input[type="text"]');
                if (input) {
                    input.dataset.loading = 'false';
                    input.classList.remove('loading');
                }
            }
        }

        /**
         * Show error to user
         * @private
         */
        _showError(error, context) {
            if (this.options.onError) {
                this.options.onError(error);
            } else {
                alert(`Failed to create entry: ${error.message}`);
            }
        }

        /**
         * Hide the modal
         * @private
         */
        _hideModal() {
            const modal = document.getElementById('sense-selection-modal');
            if (modal) {
                if (typeof bootstrap !== 'undefined' && bootstrap.Modal && this._modalInstance) {
                    this._modalInstance.hide();
                } else {
                    modal.style.display = 'none';
                    modal.classList.remove('show');
                }
                this._removeModal();
            }
        }

        /**
         * Remove modal from DOM
         * @private
         */
        _removeModal() {
            const existingModal = document.getElementById('sense-selection-modal');
            if (existingModal) {
                existingModal.remove();
            }
            this._modalInstance = null;
        }

        /**
         * Get target element ID from context
         * @private
         */
        _getTargetId(context) {
            if (context.relationIndex !== undefined) {
                return `search-results-${context.relationIndex}`;
            }
            if (context.variantIndex !== undefined) {
                return `variant-search-results-${context.variantIndex}`;
            }
            if (context.senseIndex !== undefined && context.relationIndex !== undefined) {
                return `sense-search-results-${context.senseIndex}-${context.relationIndex}`;
            }
            return null;
        }

        /**
         * Check for circular reference
         * @param {string} targetId - Target entry/sense ID
         * @returns {boolean} True if circular reference detected
         */
        detectCircularReference(targetId) {
            if (!this._currentEntryId || !targetId) return false;

            // If target starts with current entry ID, it's a circular reference
            if (targetId.startsWith(this._currentEntryId)) {
                console.warn(`[EntryCreationManager] Circular reference detected: ${targetId} is within ${this._currentEntryId}`);
                return true;
            }

            return false;
        }

        /**
         * Get headword display text from entry
         * @private
         */
        _getEntryHeadword(entry) {
            if (entry.lexical_unit) {
                if (typeof entry.lexical_unit === 'string') {
                    return entry.lexical_unit;
                }
                if (typeof entry.lexical_unit === 'object') {
                    const lang = this.options.sourceLanguage;
                    return entry.lexical_unit[lang] || entry.lexical_unit.en ||
                           Object.values(entry.lexical_unit)[0] || 'Unknown';
                }
            }
            return entry.headword || entry.id || 'Unknown Entry';
        }

        /**
         * Get gloss text from sense
         * @private
         */
        _getSenseGloss(sense) {
            if (!sense.gloss) return null;
            if (typeof sense.gloss === 'string') return sense.gloss;
            if (typeof sense.gloss === 'object') {
                return sense.gloss.en || sense.gloss.pl || Object.values(sense.gloss)[0] || null;
            }
            return null;
        }

        /**
         * Get definition text from sense
         * @private
         */
        _getSenseDefinition(sense) {
            if (!sense.definition) return null;
            if (typeof sense.definition === 'string') return sense.definition;
            if (typeof sense.definition === 'object') {
                return sense.definition.en || sense.definition.pl ||
                       Object.values(sense.definition)[0] || null;
            }
            return null;
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
         * Get CSRF token from page
         * @private
         */
        _getCsrfToken() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) return meta.content;

            const input = document.querySelector('input[name="csrf_token"]');
            if (input) return input.value;

            return '';
        }

        /**
         * Destroy the manager and cleanup
         */
        destroy() {
            this._removeModal();
            this._boundMethods.clear();
        }
    }

    // Export globally
    window.EntryCreationManager = EntryCreationManager;

})();
