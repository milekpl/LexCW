/**
 * Direct Variants (Allomorphs) Management
 *
 * Handles adding, removing, and managing direct variant forms.
 * Extracted from inline script in entry_form.html for better maintainability.
 */

class DirectVariantsManager {
    constructor(containerSelector) {
        this.container = document.querySelector(containerSelector);
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

        this.container.addEventListener('click', handleClick);
        this.container.addEventListener('change', handleChange);
    }

    /**
     * Handle click events
     * @private
     */
    _handleClick(event) {
        // Add direct variant button
        if (event.target.classList.contains('add-direct-variant-btn') ||
            event.target.closest('.add-direct-variant-btn')) {
            this.add();
        }

        // Remove direct variant button
        if (event.target.classList.contains('remove-direct-variant-btn')) {
            const index = parseInt(event.target.dataset.index, 10);
            this.remove(index);
        }

        // Add variant language button
        if (event.target.classList.contains('add-variant-language-btn')) {
            const variantItem = event.target.closest('.direct-variant-item');
            if (variantItem) {
                const index = parseInt(variantItem.dataset.variantIndex, 10);
                this.addLanguage(index);
            }
        }

        // Add variant trait button
        if (event.target.classList.contains('add-variant-trait-btn')) {
            const variantItem = event.target.closest('.direct-variant-item');
            if (variantItem) {
                const index = parseInt(variantItem.dataset.variantIndex, 10);
                this.addTrait(index);
            }
        }

        // Add grammatical trait button
        if (event.target.classList.contains('add-grammatical-trait-btn')) {
            const variantItem = event.target.closest('.direct-variant-item');
            if (variantItem) {
                const index = parseInt(variantItem.dataset.variantIndex, 10);
                this.addGrammaticalTrait(index);
            }
        }
    }

    /**
     * Handle change events
     * @private
     */
    _handleChange(event) {
        // Language code input change
        if (event.target.classList.contains('lang-code-input')) {
            const variantItem = event.target.closest('.direct-variant-item');
            const inputGroup = event.target.closest('.input-group');
            if (variantItem && inputGroup) {
                const variantIndex = parseInt(variantItem.dataset.variantIndex, 10);
                const textInput = inputGroup.querySelector('input[type="text"]:not(.lang-code-input)');
                if (textInput) {
                    this._updateLanguageInputName(textInput, variantIndex, event.target.value);
                }
            }
        }
    }

    /**
     * Update the name attribute when language code is entered
     * @private
     */
    _updateLanguageInputName(input, variantIndex, langCode) {
        const name = input.getAttribute('name');
        if (name && name.includes('.form.NEW_LANG')) {
            const newName = name.replace('.form.NEW_LANG', `.form.${langCode.trim()}`);
            input.setAttribute('name', newName);
        }
    }

    /**
     * Add a new direct variant
     */
    add() {
        const variantItems = this.container.querySelectorAll('.direct-variant-item');
        const newIndex = variantItems.length;

        // Remove empty state if present
        const emptyState = this.container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        // Create new variant HTML
        const variantHtml = this._createVariantHtml(newIndex);
        this.container.insertAdjacentHTML('beforeend', variantHtml);

        // Emit event for other components
        this._emitEvent('added', { index: newIndex });
    }

    /**
     * Create HTML for a new variant
     * @private
     */
    _createVariantHtml(index) {
        return `
            <div class="direct-variant-item card mb-3" data-variant-index="${index}">
                <div class="card-header bg-warning text-dark">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="fas fa-copy me-2"></i>
                            Direct Variant ${index + 1}
                        </h6>
                        <button type="button" class="btn btn-sm btn-light remove-direct-variant-btn"
                                data-index="${index}" title="Remove direct variant">
                            <i class="fas fa-trash text-danger"></i>
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <div class="mb-3">
                                <label class="form-label fw-bold">Variant Form</label>
                                <div class="variant-form-languages">
                                    <div class="input-group mb-2">
                                        <span class="input-group-text">en</span>
                                        <input type="text" class="form-control"
                                               name="variants[${index}].form.en"
                                               value=""
                                               placeholder="Variant form in English">
                                    </div>
                                </div>
                                <button type="button" class="btn btn-sm btn-outline-secondary add-variant-language-btn">
                                    <i class="fas fa-plus"></i> Add Language
                                </button>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label class="form-label fw-bold">Variant Traits</label>
                                <div class="variant-traits">
                                </div>
                                <button type="button" class="btn btn-sm btn-outline-secondary add-variant-trait-btn">
                                    <i class="fas fa-plus"></i> Add Trait
                                </button>
                            </div>
                        </div>
                    </div>

                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Grammatical Info</label>
                                <input type="text" class="form-control"
                                       name="variants[${index}].grammatical_info"
                                       value=""
                                       placeholder="Grammatical information">
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Grammatical Traits</label>
                                <div class="variant-grammatical-traits">
                                </div>
                                <button type="button" class="btn btn-sm btn-outline-secondary add-grammatical-trait-btn">
                                    <i class="fas fa-plus"></i> Add Grammatical Trait
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Remove a direct variant
     * @param {number} index - Index of variant to remove
     */
    remove(index) {
        const variantElement = this.container.querySelector(`[data-variant-index="${index}"]`);
        if (variantElement) {
            variantElement.remove();
            this.reindex();
            this._emitEvent('removed', { index });
        }
    }

    /**
     * Reindex all variants after removal
     */
    reindex() {
        const variantElements = this.container.querySelectorAll('.direct-variant-item');

        variantElements.forEach((element, newIndex) => {
            // Update data attribute
            element.setAttribute('data-variant-index', newIndex);

            // Update header number
            const header = element.querySelector('.card-header h6');
            if (header) {
                header.innerHTML = `<i class="fas fa-copy me-2"></i> Direct Variant ${newIndex + 1}`;
            }

            // Update remove button
            const removeBtn = element.querySelector('.remove-direct-variant-btn');
            if (removeBtn) {
                removeBtn.setAttribute('data-index', newIndex);
            }

            // Update all input names
            const inputs = element.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                const name = input.getAttribute('name');
                if (name && name.includes('variants[')) {
                    const newName = name.replace(/variants\[\d+\]/, `variants[${newIndex}]`);
                    input.setAttribute('name', newName);
                }
            });
        });
    }

    /**
     * Add a new language input to a variant
     * @param {number} variantIndex - Index of variant
     */
    addLanguage(variantIndex) {
        const variantElement = this.container.querySelector(`[data-variant-index="${variantIndex}"]`);
        const languagesContainer = variantElement?.querySelector('.variant-form-languages');

        if (!languagesContainer) return;

        const newInput = document.createElement('div');
        newInput.className = 'input-group mb-2';
        newInput.innerHTML = `
            <span class="input-group-text">
                <input type="text" class="form-control form-control-sm lang-code-input"
                       style="width: 60px;" placeholder="xx" maxlength="10">
            </span>
            <input type="text" class="form-control"
                   name="variants[${variantIndex}].form.NEW_LANG"
                   value="" placeholder="Variant form in new language">
            <button type="button" class="btn btn-outline-danger remove-variant-language-btn"
                    title="Remove this language">
                <i class="fas fa-times"></i>
            </button>
        `;

        languagesContainer.appendChild(newInput);

        // Add remove handler
        const removeBtn = newInput.querySelector('.remove-variant-language-btn');
        removeBtn.addEventListener('click', () => newInput.remove());
    }

    /**
     * Add a new trait to a variant
     * @param {number} variantIndex - Index of variant
     */
    addTrait(variantIndex) {
        const variantElement = this.container.querySelector(`[data-variant-index="${variantIndex}"]`);
        const traitsContainer = variantElement?.querySelector('.variant-traits');

        if (!traitsContainer) return;

        const newInput = document.createElement('div');
        newInput.className = 'input-group mb-2';
        newInput.innerHTML = `
            <input type="text" class="form-control trait-name-input"
                   placeholder="trait-name" style="width: 40%;">
            <input type="text" class="form-control trait-value-input"
                   placeholder="trait-value" style="width: 60%;">
            <button type="button" class="btn btn-outline-danger remove-variant-trait-btn"
                    title="Remove this trait">
                <i class="fas fa-times"></i>
            </button>
            <input type="hidden" class="trait-hidden-input"
                   name="variants[${variantIndex}].traits.NEW_TRAIT" value="">
        `;

        traitsContainer.appendChild(newInput);

        // Set up name/value synchronization
        const traitNameInput = newInput.querySelector('.trait-name-input');
        const traitValueInput = newInput.querySelector('.trait-value-input');
        const hiddenInput = newInput.querySelector('.trait-hidden-input');

        const updateHiddenInput = () => {
            const traitName = traitNameInput.value.trim();
            const traitValue = traitValueInput.value.trim();
            if (traitName && traitValue) {
                const currentName = hiddenInput.getAttribute('name');
                const newName = currentName.replace('.traits.NEW_TRAIT', `.traits.${traitName}`);
                hiddenInput.setAttribute('name', newName);
                hiddenInput.value = traitValue;
            }
        };

        traitNameInput.addEventListener('change', updateHiddenInput);
        traitValueInput.addEventListener('input', updateHiddenInput);

        // Add remove handler
        const removeBtn = newInput.querySelector('.remove-variant-trait-btn');
        removeBtn.addEventListener('click', () => newInput.remove());
    }

    /**
     * Add a new grammatical trait to a variant
     * @param {number} variantIndex - Index of variant
     */
    addGrammaticalTrait(variantIndex) {
        const variantElement = this.container.querySelector(`[data-variant-index="${variantIndex}"]`);
        const traitsContainer = variantElement?.querySelector('.variant-grammatical-traits');

        if (!traitsContainer) return;

        const newInput = document.createElement('div');
        newInput.className = 'input-group mb-2';
        newInput.innerHTML = `
            <input type="text" class="form-control grammatical-trait-name-input"
                   placeholder="trait-name" style="width: 40%;">
            <input type="text" class="form-control grammatical-trait-value-input"
                   placeholder="trait-value" style="width: 60%;">
            <button type="button" class="btn btn-outline-danger remove-grammatical-trait-btn"
                    title="Remove this trait">
                <i class="fas fa-times"></i>
            </button>
            <input type="hidden" class="grammatical-trait-hidden-input"
                   name="variants[${variantIndex}].grammatical_traits.NEW_TRAIT" value="">
        `;

        traitsContainer.appendChild(newInput);

        // Set up name/value synchronization
        const traitNameInput = newInput.querySelector('.grammatical-trait-name-input');
        const traitValueInput = newInput.querySelector('.grammatical-trait-value-input');
        const hiddenInput = newInput.querySelector('.grammatical-trait-hidden-input');

        const updateHiddenInput = () => {
            const traitName = traitNameInput.value.trim();
            const traitValue = traitValueInput.value.trim();
            if (traitName && traitValue) {
                const currentName = hiddenInput.getAttribute('name');
                const newName = currentName.replace('.grammatical_traits.NEW_TRAIT', `.grammatical_traits.${traitName}`);
                hiddenInput.setAttribute('name', newName);
                hiddenInput.value = traitValue;
            }
        };

        traitNameInput.addEventListener('change', updateHiddenInput);
        traitValueInput.addEventListener('input', updateHiddenInput);

        // Add remove handler
        const removeBtn = newInput.querySelector('.remove-grammatical-trait-btn');
        removeBtn.addEventListener('click', () => newInput.remove());
    }

    /**
     * Emit an event for other components
     * @private
     */
    _emitEvent(eventType, data) {
        const event = new CustomEvent(`directVariants:${eventType}`, {
            bubbles: true,
            detail: data
        });
        document.dispatchEvent(event);
    }

    /**
     * Get the count of variants
     * @returns {number}
     */
    getCount() {
        return this.container.querySelectorAll('.direct-variant-item').length;
    }
}

// Export
window.DirectVariantsManager = DirectVariantsManager;
