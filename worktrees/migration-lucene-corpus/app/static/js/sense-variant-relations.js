/**
 * SenseVariantRelationsManager - Handles sense-level variant relations
 *
 * Manages adding, editing, and removing variant relations at the sense level.
 * Uses event-driven architecture for component communication.
 */
class SenseVariantRelationsManager {
    /**
     * Create a new SenseVariantRelationsManager instance
     * @param {Object} options - Configuration options
     */
    constructor(options = {}) {
        this.options = {
            containerSelector: '[class*="sense-variant-relations-container"]',
            addButtonClass: 'add-sense-variant-relation-btn',
            removeButtonClass: 'remove-sense-variant-relation-btn',
            variantTypeSelectClass: 'sense-variant-type-select',
            emptyStateClass: 'no-sense-variant-relations',
            eventNamespace: 'senseVariantRelation',
            ...options
        };

        this._boundMethods = new WeakMap();
        this._setupEventListeners();
    }

    /**
     * Bind a method to preserve 'this' context
     * @private
     */
    _bind(method) {
        if (!this._boundMethods.has(method)) {
            this._boundMethods.set(method, method.bind(this));
        }
        return this._boundMethods.get(method);
    }

    /**
     * Set up event listeners using event delegation
     * @private
     */
    _setupEventListeners() {
        const handleClick = this._bind(this._handleClick);
        const handleChange = this._bind(this._handleChange);

        document.addEventListener('click', handleClick);
        document.addEventListener('change', handleChange);
    }

    /**
     * Handle click events
     * @private
     */
    _handleClick(event) {
        // Add variant relation button
        if (event.target.classList.contains(this.options.addButtonClass) ||
            event.target.closest(`.${this.options.addButtonClass}`)) {
            const btn = event.target.classList.contains(this.options.addButtonClass)
                ? event.target
                : event.target.closest(`.${this.options.addButtonClass}`);
            const senseIndex = btn.dataset.senseIndex;
            this.addVariantRelation(senseIndex);
        }

        // Remove variant relation button
        if (event.target.classList.contains(this.options.removeButtonClass) ||
            event.target.closest(`.${this.options.removeButtonClass}`)) {
            const btn = event.target.classList.contains(this.options.removeButtonClass)
                ? event.target
                : event.target.closest(`.${this.options.removeButtonClass}`);
            const senseIndex = btn.dataset.senseIndex;
            const variantIndex = btn.dataset.variantIndex;
            this.removeVariantRelation(senseIndex, variantIndex);
        }

        // Search variant entry button
        if (event.target.classList.contains('search-variant-entry-btn') ||
            event.target.closest('.search-variant-entry-btn')) {
            const btn = event.target.classList.contains('search-variant-entry-btn')
                ? event.target
                : event.target.closest('.search-variant-entry-btn');
            this._searchVariantEntry(btn.dataset.senseIndex, btn.dataset.variantIndex);
        }
    }

    /**
     * Handle change events
     * @private
     */
    _handleChange(event) {
        if (event.target.classList.contains(this.options.variantTypeSelectClass)) {
            // Update the card header with the selected type
            const card = event.target.closest('.sense-variant-relation-item');
            if (card) {
                const headerSpan = card.querySelector('.card-header span');
                if (headerSpan && event.target.options[event.target.selectedIndex]) {
                    const selectedText = event.target.options[event.target.selectedIndex].text;
                    headerSpan.innerHTML = `<i class="fas fa-link"></i> Variant: ${selectedText}`;
                }
            }

            // Emit change event
            this._emitChangeEvent('typeChanged', {
                senseIndex: event.target.name.match(/senses\[(\d+)\]/)?.[1],
                variantIndex: event.target.name.match(/variant_relations\[(\d+)\]/)?.[1],
                type: event.target.value
            });
        }
    }

    /**
     * Add a new variant relation for a sense
     * @param {string} senseIndex - Index of the sense
     */
    addVariantRelation(senseIndex) {
        const container = document.querySelector(
            `.sense-variant-relations-container[data-sense-index="${senseIndex}"]`
        );

        if (!container) {
            console.warn(`[SenseVariantRelationsManager] Container not found for sense ${senseIndex}`);
            return;
        }

        // Get the next variant index
        const existingRelations = container.querySelectorAll('.sense-variant-relation-item');
        const variantIndex = existingRelations.length;

        // Remove empty state if present
        const emptyState = container.querySelector(`.${this.options.emptyStateClass}`);
        if (emptyState) {
            emptyState.remove();
        }

        // Create new variant relation card
        const cardHtml = this._createVariantRelationCard(senseIndex, variantIndex);
        container.insertAdjacentHTML('beforeend', cardHtml);

        // Initialize Select2 and populate ranges on the new variant type select
        this._populateVariantTypeSelect(container, variantIndex);

        // Emit event
        this._emitChangeEvent('added', {
            senseIndex,
            variantIndex
        });
    }

    /**
     * Create HTML for a variant relation card
     * @private
     */
    _createVariantRelationCard(senseIndex, variantIndex) {
        return `
            <div class="sense-variant-relation-item card mb-3 border-secondary" data-variant-index="${variantIndex}">
                <div class="card-header bg-secondary bg-opacity-10">
                    <div class="d-flex justify-content-between align-items-center">
                        <span><i class="fas fa-link"></i> Variant: (select type)</span>
                        <button type="button" class="btn btn-sm btn-outline-danger remove-sense-variant-relation-btn"
                                data-sense-index="${senseIndex}" data-variant-index="${variantIndex}">
                            <i class="fas fa-trash"></i> Remove
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <label class="form-label">Variant Type</label>
                            <select class="form-select dynamic-lift-range sense-variant-type-select"
                                    name="senses[${senseIndex}].variant_relations[${variantIndex}].type"
                                    data-range-id="variant-type">
                                <option value="">Select type</option>
                            </select>
                        </div>
                        <div class="col-md-8">
                            <label class="form-label">Target Entry</label>
                            <div class="input-group">
                                <input type="text" class="form-control sense-variant-target-input"
                                       name="senses[${senseIndex}].variant_relations[${variantIndex}].ref"
                                       value=""
                                       placeholder="Enter entry ID or search">
                                <button type="button" class="btn btn-outline-secondary search-variant-entry-btn"
                                        data-sense-index="${senseIndex}" data-variant-index="${variantIndex}"
                                        title="Search for entry">
                                    <i class="fas fa-search"></i>
                                </button>
                            </div>
                            <div class="form-text">ID of the target entry for this variant relation</div>
                        </div>
                    </div>
                    <div class="row mt-2">
                        <div class="col-md-12">
                            <label class="form-label">Comment (Optional)</label>
                            <textarea class="form-control"
                                      name="senses[${senseIndex}].variant_relations[${variantIndex}].comment"
                                      rows="2"
                                      placeholder="Optional note about this variant"></textarea>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Populate variant type select using ranges-loader (same as entry-level variants)
     * @private
     */
    _populateVariantTypeSelect(container, variantIndex) {
        try {
            const addedElem = container.querySelector(`[data-variant-index="${variantIndex}"]`);
            if (addedElem && window.rangesLoader) {
                const select = addedElem.querySelector('select.dynamic-lift-range');
                if (select) {
                    const rangeId = select.dataset.rangeId;
                    const selectedValue = select.dataset.selected;
                    console.log('[SenseVariantRelationsManager] Populating variant type select', {rangeId, selectedValue, select});
                    window.rangesLoader.populateSelect(select, rangeId, {
                        selectedValue: selectedValue,
                        emptyOption: select.querySelector('option[value=""]')?.textContent || 'Select type'
                    }).then(result => {
                        console.log('[SenseVariantRelationsManager] populateSelect result', {rangeId, result, select});
                    }).catch(err => console.error('[SenseVariantRelationsManager] Failed to populate variant type select:', err));
                }
            }
        } catch (e) {
            console.warn('[SenseVariantRelationsManager] Error populating variant type select:', e);
        }
    }

    /**
     * Remove a variant relation
     * @param {string} senseIndex - Index of the sense
     * @param {string} variantIndex - Index of the variant relation
     */
    removeVariantRelation(senseIndex, variantIndex) {
        const container = document.querySelector(
            `.sense-variant-relations-container[data-sense-index="${senseIndex}"]`
        );

        if (!container) {
            console.warn(`[SenseVariantRelationsManager] Container not found for sense ${senseIndex}`);
            return;
        }

        const card = container.querySelector(
            `.sense-variant-relation-item[data-variant-index="${variantIndex}"]`
        );

        if (card) {
            // Destroy Select2 before removing
            const select = card.querySelector('.sense-variant-type-select');
            if (select && typeof $ !== 'undefined' && $(select).hasClass('select2-hidden-accessible')) {
                $(select).select2('destroy');
            }

            card.remove();

            // Reindex remaining relations
            this._reindexVariantRelations(container, senseIndex);

            // Add empty state if no relations left
            const remaining = container.querySelectorAll('.sense-variant-relation-item');
            if (remaining.length === 0) {
                container.innerHTML = `
                    <div class="no-sense-variant-relations text-center text-muted py-3 border border-secondary border-opacity-25 rounded">
                        <p class="mb-2"><small>No variant relations yet. Add variants to link this sense to alternate forms (e.g., spelling variants, archaic forms).</small></p>
                    </div>
                `;
            }

            // Emit event
            this._emitChangeEvent('removed', {
                senseIndex,
                variantIndex
            });
        }
    }

    /**
     * Reindex variant relations after removal
     * @private
     */
    _reindexVariantRelations(container, senseIndex) {
        const cards = container.querySelectorAll('.sense-variant-relation-item');
        cards.forEach((card, newIndex) => {
            card.dataset.variantIndex = newIndex;

            // Update all form field names
            const fields = card.querySelectorAll('[name]');
            fields.forEach(field => {
                const oldName = field.name;
                const newName = oldName
                    .replace(/senses\[\d+\]\.variant_relations\[\d+\]/g,
                             `senses[${senseIndex}].variant_relations[${newIndex}]`);
                field.name = newName;

                // Update data attributes
                if (field.dataset.variantIndex) {
                    field.dataset.variantIndex = newIndex;
                }
            });

            // Update button data attributes
            const removeBtn = card.querySelector(`.${this.options.removeButtonClass}`);
            if (removeBtn) {
                removeBtn.dataset.variantIndex = newIndex;
            }

            const searchBtn = card.querySelector('.search-variant-entry-btn');
            if (searchBtn) {
                searchBtn.dataset.variantIndex = newIndex;
            }
        });
    }

    /**
     * Search for a variant entry
     * @private
     */
    _searchVariantEntry(senseIndex, variantIndex) {
        // Emit event for other components to handle entry search
        this._emitChangeEvent('searchEntry', {
            senseIndex,
            variantIndex,
            callback: (entryId, entryText) => {
                const input = document.querySelector(
                    `input[name="senses[${senseIndex}].variant_relations[${variantIndex}].ref"]`
                );
                if (input) {
                    input.value = entryId;
                    input.placeholder = entryText || entryId;
                }
            }
        });
    }

    /**
     * Get all variant relations for a sense
     * @param {string} senseIndex - Index of the sense
     * @returns {Array} Array of variant relation objects
     */
    getVariantRelations(senseIndex) {
        const container = document.querySelector(
            `.sense-variant-relations-container[data-sense-index="${senseIndex}"]`
        );

        if (!container) {
            return [];
        }

        const relations = [];
        const cards = container.querySelectorAll('.sense-variant-relation-item');

        cards.forEach(card => {
            const type = card.querySelector('.sense-variant-type-select')?.value || '';
            const ref = card.querySelector('.sense-variant-target-input')?.value || '';
            const comment = card.querySelector('textarea[name*="comment"]')?.value || '';

            if (type || ref) {
                relations.push({ type, ref, comment });
            }
        });

        return relations;
    }

    /**
     * Emit CustomEvent for other components
     * @private
     */
    _emitChangeEvent(eventType, detail) {
        const event = new CustomEvent(`${this.options.eventNamespace}:${eventType}`, {
            bubbles: true,
            detail: {
                ...detail,
                timestamp: Date.now()
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * Clean up event listeners
     */
    destroy() {
        document.removeEventListener('click', this._boundMethods.get(this._handleClick));
        document.removeEventListener('change', this._boundMethods.get(this._handleChange));
        this._boundMethods.clear();
    }
}

// Export for use in other modules
window.SenseVariantRelationsManager = SenseVariantRelationsManager;

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.SenseVariantRelationsManager) {
        const manager = new SenseVariantRelationsManager();
        window.senseVariantRelationsManager = manager;

        // Populate variant type selects for existing relations on page load
        // Wait for ranges-loader to be ready, then populate all existing selects
        const checkRangesLoader = setInterval(() => {
            if (window.rangesLoader && window.rangesLoader.loaded) {
                clearInterval(checkRangesLoader);
                manager._populateAllExistingSelects();
            }
        }, 100);

        // Timeout after 10 seconds to stop trying
        setTimeout(() => clearInterval(checkRangesLoader), 10000);
    }
});

// Also add a method to populate all existing selects
SenseVariantRelationsManager.prototype._populateAllExistingSelects = function() {
    const containers = document.querySelectorAll('[class*="sense-variant-relations-container"]');
    containers.forEach(container => {
        const cards = container.querySelectorAll('.sense-variant-relation-item');
        cards.forEach((card, index) => {
            const select = card.querySelector('select.sense-variant-type-select');
            if (select && window.rangesLoader) {
                const rangeId = select.dataset.rangeId || 'variant-type';
                // Get the currently selected value
                const selectedValue = select.value;
                window.rangesLoader.populateSelect(select, rangeId, {
                    selectedValue: selectedValue,
                    emptyOption: select.querySelector('option[value=""]')?.textContent || 'Select type'
                });
            }
        });
    });
};
