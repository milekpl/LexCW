/**
 * FieldVisibilityManager - Handles field visibility settings for forms
 *
 * Supports both section-level and per-field visibility control.
 * Uses event-driven architecture for component communication.
 * Settings are persisted to localStorage and broadcast via CustomEvents.
 */
class FieldVisibilityManager {
    /**
     * Create a new FieldVisibilityManager instance
     * @param {Object} options - Configuration options
     * @param {string} options.storageKey - localStorage key (default: 'fieldVisibilitySettings')
     * @param {Object} options.defaultSectionSettings - Default section visibility
     * @param {Object} options.defaultFieldSettings - Default field visibility per section
     * @param {Function} options.onChange - Callback when visibility changes
     * @param {boolean} options.autoApply - Apply settings on init (default: true)
     */
    constructor(options = {}) {
        this.options = {
            storageKey: 'fieldVisibilitySettings',
            // Section-level defaults
            defaultSectionSettings: {
                'basic-info': true,
                'custom-fields': true,
                'notes': true,
                'pronunciation': true,
                'variants': true,
                'direct-variants': true,
                'relations': true,
                'annotations': true,
                'senses': true
            },
            // Per-field defaults within each section
            defaultFieldSettings: {
                'basic-info': {
                    'lexical-unit': true,
                    'pronunciation': true,
                    'variants': true
                },
                'custom-fields': {
                    'custom-fields-all': true
                },
                'notes': {
                    'notes-all': true
                },
                'pronunciation': {
                    'pronunciation-all': true
                },
                'variants': {
                    'variants-all': true
                },
                'direct-variants': {
                    'direct-variants-all': true
                },
                'relations': {
                    'relations-all': true
                },
                'annotations': {
                    'annotations-all': true
                },
                'senses': {
                    'sense-definition': true,
                    'sense-gloss': true,
                    'sense-grammatical': true,
                    'sense-domain': true,
                    'sense-examples': true,
                    'sense-illustrations': true,
                    'sense-relations': true,
                    'sense-variants': true,
                    'sense-reversals': false,
                    'sense-annotations': false
                }
            },
            // Mapping from section IDs to form section class names
            sectionClassMap: {
                'basic-info': '.basic-info-section',
                'custom-fields': '.custom-fields-section',
                'notes': '.notes-section',
                'pronunciation': '.pronunciation-section',
                'variants': '.variants-section',
                'direct-variants': '.direct-variants-section',
                'relations': '.relations-section',
                'annotations': '.annotations-section-entry',
                'senses': '.senses-section'
            },
            onChange: null,
            autoApply: true,
            ...options
        };

        this.sectionSettings = this._loadSectionSettings();
        this.fieldSettings = this._loadFieldSettings();
        this._boundMethods = new WeakMap();

        this._setupEventListeners();

        if (this.options.autoApply) {
            this._applySettings();
        }
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
     * Load section settings from localStorage
     * @private
     */
    _loadSectionSettings() {
        try {
            const stored = localStorage.getItem(`${this.options.storageKey}_sections`);
            if (stored) {
                return { ...this.options.defaultSectionSettings, ...JSON.parse(stored) };
            }
        } catch (e) {
            console.warn('[FieldVisibilityManager] Failed to load section settings:', e);
        }
        return { ...this.options.defaultSectionSettings };
    }

    /**
     * Load field settings from localStorage
     * @private
     */
    _loadFieldSettings() {
        try {
            const stored = localStorage.getItem(`${this.options.storageKey}_fields`);
            if (stored) {
                // Merge with defaults for new fields
                const parsed = JSON.parse(stored);
                const merged = { ...this.options.defaultFieldSettings };
                Object.keys(parsed).forEach(sectionId => {
                    merged[sectionId] = { ...merged[sectionId], ...parsed[sectionId] };
                });
                return merged;
            }
        } catch (e) {
            console.warn('[FieldVisibilityManager] Failed to load field settings:', e);
        }
        return JSON.parse(JSON.stringify(this.options.defaultFieldSettings));
    }

    /**
     * Save all settings to localStorage
     * @private
     */
    _saveSettings() {
        try {
            localStorage.setItem(`${this.options.storageKey}_sections`, JSON.stringify(this.sectionSettings));
            localStorage.setItem(`${this.options.storageKey}_fields`, JSON.stringify(this.fieldSettings));
        } catch (e) {
            console.warn('[FieldVisibilityManager] Failed to save settings:', e);
        }
    }

    /**
     * Set up event listeners
     * @private
     */
    _setupEventListeners() {
        const handleChange = this._bind(this._handleToggleChange);
        const handleClick = this._bind(this._handleButtonClick);

        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('field-visibility-toggle')) {
                handleChange(e);
            }
        });

        document.addEventListener('click', (e) => {
            handleClick(e);

            // Handle view toggle
            if (e.target.id === 'view-fields' || e.target.closest('#view-fields')) {
                this._switchToFieldsView();
            } else if (e.target.id === 'view-sections' || e.target.closest('#view-sections')) {
                this._switchToSectionsView();
            }
        });
    }

    /**
     * Switch to fields view
     * @private
     */
    _switchToFieldsView() {
        document.getElementById('sections-view').style.display = 'none';
        document.getElementById('fields-view').style.display = 'block';
        document.getElementById('view-fields').checked = true;
    }

    /**
     * Switch to sections view
     * @private
     */
    _switchToSectionsView() {
        document.getElementById('sections-view').style.display = 'block';
        document.getElementById('fields-view').style.display = 'none';
        document.getElementById('view-sections').checked = true;
    }

    /**
     * Handle checkbox toggle change
     * @private
     */
    _handleToggleChange(event) {
        event.stopPropagation();
        event.preventDefault();

        const checkbox = event.target;
        const sectionId = checkbox.dataset.sectionId;
        const fieldId = checkbox.dataset.fieldId;
        const isVisible = checkbox.checked;

        if (fieldId) {
            // Field-level toggle
            this.setFieldVisibility(sectionId, fieldId, isVisible);
        } else if (sectionId) {
            // Section-level toggle
            this.setSectionVisibility(sectionId, isVisible);
        }
    }

    /**
     * Handle button clicks
     * @private
     */
    _handleButtonClick(event) {
        const isVisibilityBtn =
            event.target.classList.contains('reset-field-visibility-btn') ||
            event.target.classList.contains('hide-empty-sections-btn') ||
            event.target.classList.contains('show-all-sections-btn') ||
            event.target.closest('.reset-field-visibility-btn') ||
            event.target.closest('.hide-empty-sections-btn') ||
            event.target.closest('.show-all-sections-btn');

        if (isVisibilityBtn) {
            event.stopPropagation();
            event.preventDefault();
        }

        if (event.target.classList.contains('reset-field-visibility-btn') ||
            event.target.closest('.reset-field-visibility-btn')) {
            this._resetToDefaults();
        } else if (event.target.classList.contains('hide-empty-sections-btn') ||
                   event.target.closest('.hide-empty-sections-btn')) {
            this._hideEmptySections();
        } else if (event.target.classList.contains('show-all-sections-btn') ||
                   event.target.closest('.show-all-sections-btn')) {
            this._showAllSections();
        }
    }

    /**
     * Set visibility for a specific section
     * @param {string} sectionId - Section identifier
     * @param {boolean} visible - Whether the section should be visible
     */
    setSectionVisibility(sectionId, visible) {
        if (!(sectionId in this.options.defaultSectionSettings)) {
            console.warn(`[FieldVisibilityManager] Unknown section: ${sectionId}`);
            return;
        }

        this.sectionSettings[sectionId] = visible;
        this._saveSettings();

        // Update all section-level checkboxes
        const checkboxes = document.querySelectorAll(`[data-section-id="${sectionId}"]:not([data-field-id])`);
        checkboxes.forEach(checkbox => {
            checkbox.checked = visible;
        });

        // Apply visibility to section elements
        this._applySectionVisibility(sectionId, visible);

        // Also set all fields in this section to match
        if (this.fieldSettings[sectionId]) {
            Object.keys(this.fieldSettings[sectionId]).forEach(fieldId => {
                this.fieldSettings[sectionId][fieldId] = visible;
            });
            this._saveSettings();
            this._updateFieldCheckboxes(sectionId);
        }

        this._emitChangeEvent(sectionId, visible, null);
    }

    /**
     * Set visibility for a specific field
     * @param {string} sectionId - Section identifier
     * @param {string} fieldId - Field identifier
     * @param {boolean} visible - Whether the field should be visible
     */
    setFieldVisibility(sectionId, fieldId, visible) {
        if (!this.fieldSettings[sectionId]) {
            this.fieldSettings[sectionId] = {};
        }

        // If setting field to visible, ensure section is also visible
        if (visible) {
            this.sectionSettings[sectionId] = true;
            const sectionCheckboxes = document.querySelectorAll(`[data-section-id="${sectionId}"]:not([data-field-id])`);
            sectionCheckboxes.forEach(checkbox => checkbox.checked = true);
        }

        this.fieldSettings[sectionId][fieldId] = visible;
        this._saveSettings();

        // Update field checkboxes
        const checkboxes = document.querySelectorAll(`[data-section-id="${sectionId}"][data-field-id="${fieldId}"]`);
        checkboxes.forEach(checkbox => {
            checkbox.checked = visible;
        });

        // Apply visibility to field elements
        this._applyFieldVisibility(sectionId, fieldId, visible);

        // Update section checkbox state based on field states
        this._updateSectionCheckboxFromFields(sectionId);

        // Emit change event
        this._emitChangeEvent(sectionId, visible, fieldId);
    }

    /**
     * Update section checkbox based on field states
     * @private
     */
    _updateSectionCheckboxFromFields(sectionId) {
        const fields = this.fieldSettings[sectionId];
        if (!fields) return;

        const allVisible = Object.values(fields).every(v => v);
        const anyVisible = Object.values(fields).some(v => v);

        // Update section checkboxes
        const checkboxes = document.querySelectorAll(`[data-section-id="${sectionId}"]:not([data-field-id])`);
        checkboxes.forEach(checkbox => {
            // Check if this is a field-view section toggle (in accordion header)
            if (checkbox.classList.contains('section-field-toggle')) {
                checkbox.checked = anyVisible;
            } else {
                checkbox.checked = allVisible;
            }
        });

        // Update section visibility based on fields
        if (anyVisible) {
            this.sectionSettings[sectionId] = anyVisible;
            this._applySectionVisibility(sectionId, anyVisible);
        }
    }

    /**
     * Update all field checkboxes for a section
     * @private
     */
    _updateFieldCheckboxes(sectionId) {
        const fields = this.fieldSettings[sectionId];
        if (!fields) return;

        Object.entries(fields).forEach(([fieldId, isVisible]) => {
            const checkboxes = document.querySelectorAll(`[data-section-id="${sectionId}"][data-field-id="${fieldId}"]`);
            checkboxes.forEach(checkbox => {
                checkbox.checked = isVisible;
            });
            this._applyFieldVisibility(sectionId, fieldId, isVisible);
        });
    }

    /**
     * Apply section visibility to DOM
     * @private
     */
    _applySectionVisibility(sectionId, visible) {
        const targetClass = this.options.sectionClassMap[sectionId];
        if (!targetClass) {
            console.warn(`[FieldVisibilityManager] No class mapping for section: ${sectionId}`);
            return;
        }

        const targetElements = document.querySelectorAll(targetClass);
        targetElements.forEach(el => {
            el.style.display = visible ? '' : 'none';
        });
    }

    /**
     * Apply field visibility to DOM
     * @private
     */
    _applyFieldVisibility(sectionId, fieldId, visible) {
        // Find the actual form field element, NOT the modal checkbox
        // Field elements have data-field-id but NOT class="field-visibility-toggle"
        const fieldElements = document.querySelectorAll(
            `[data-section-id="${sectionId}"][data-field-id="${fieldId}"]:not(.field-visibility-toggle)`
        );
        fieldElements.forEach(el => {
            el.style.display = visible ? '' : 'none';
        });
    }

    /**
     * Apply all settings to the DOM
     * @private
     */
    _applySettings() {
        // Apply section settings
        Object.entries(this.sectionSettings).forEach(([sectionId, isVisible]) => {
            this._applySectionVisibility(sectionId, isVisible);
        });

        // Apply field settings
        Object.entries(this.fieldSettings).forEach(([sectionId, fields]) => {
            Object.entries(fields).forEach(([fieldId, isVisible]) => {
                this._applyFieldVisibility(sectionId, fieldId, isVisible);
            });
        });
    }

    /**
     * Reset all settings to defaults
     */
    resetToDefaults() {
        this.sectionSettings = { ...this.options.defaultSectionSettings };
        this.fieldSettings = JSON.parse(JSON.stringify(this.options.defaultFieldSettings));
        this._saveSettings();

        // Reset all checkboxes
        document.querySelectorAll('.field-visibility-toggle').forEach(checkbox => {
            const sectionId = checkbox.dataset.sectionId;
            const fieldId = checkbox.dataset.fieldId;
            const defaultVisible = checkbox.dataset.defaultVisible !== 'false';

            if (fieldId) {
                checkbox.checked = this.fieldSettings[sectionId]?.[fieldId] ?? defaultVisible;
            } else if (sectionId) {
                checkbox.checked = this.sectionSettings[sectionId];
            }
        });

        this._applySettings();
        this._emitChangeEvent('reset', true, null);
    }

    /**
     * Hide sections and individual fields that have no content
     * @private
     */
    _hideEmptySections() {
        // First, hide individual fields that are empty
        const fieldElements = document.querySelectorAll('[data-section-id][data-field-id]');

        fieldElements.forEach(fieldElement => {
            const sectionId = fieldElement.dataset.sectionId;
            const fieldId = fieldElement.dataset.fieldId;

            // Only hide if field is supposed to be visible in settings
            const settingsKey = `${sectionId}-${fieldId}`;
            if (this.fieldSettings[sectionId]?.[fieldId] === false) {
                return; // Already hidden by user preference
            }

            // Check if field is empty
            const inputs = fieldElement.querySelectorAll('input, textarea, select');
            const isEmpty = inputs.length === 0 ||
                           Array.from(inputs).every(input => {
                               const value = input.value?.trim();
                               if (input.type === 'checkbox' || input.type === 'radio') {
                                   return !input.checked;
                               }
                               return !value;
                           });

            if (isEmpty) {
                // Hide the field element directly
                fieldElement.style.display = 'none';
                // Also update field settings to reflect hidden state
                this.setFieldVisibility(sectionId, fieldId, false);
            }
        });

        // Then, hide sections that are completely empty (no visible content)
        const sections = document.querySelectorAll('[class*="-section"]');

        sections.forEach(section => {
            const inputs = section.querySelectorAll('input, textarea, select');
            const isEmpty = inputs.length === 0 ||
                           Array.from(inputs).every(input => {
                               const value = input.value?.trim();
                               if (input.type === 'checkbox' || input.type === 'radio') {
                                   return !input.checked;
                               }
                               return !value;
                           });

            if (isEmpty) {
                const sectionId = this._findSectionIdForElement(section);
                if (sectionId && this.sectionSettings[sectionId]) {
                    this.setSectionVisibility(sectionId, false);
                }
            }
        });
    }

    /**
     * Find section ID for a DOM element
     * @private
     */
    _findSectionIdForElement(element) {
        const classList = Array.from(element.classList);

        // Invert sectionClassMap to get {className: sectionId} mapping
        const classToSectionMap = {};
        Object.entries(this.options.sectionClassMap).forEach(([sectionId, classSelector]) => {
            // Remove the leading '.' from '.basic-info-section' -> 'basic-info-section'
            const baseClass = classSelector.replace(/^\./, '');
            classToSectionMap[baseClass] = sectionId;
        });

        // Check if any of the section classes are in the element's classList
        for (const [baseClass, sectionId] of Object.entries(classToSectionMap)) {
            if (classList.includes(baseClass)) {
                return sectionId;
            }
        }

        return null;
    }

    /**
     * Show all sections and fields
     */
    showAllSections() {
        Object.keys(this.sectionSettings).forEach(sectionId => {
            this.setSectionVisibility(sectionId, true);
        });
        Object.keys(this.fieldSettings).forEach(sectionId => {
            Object.keys(this.fieldSettings[sectionId]).forEach(fieldId => {
                this.setFieldVisibility(sectionId, fieldId, true);
            });
        });
        this._emitChangeEvent('showAll', true, null);
    }

    /**
     * Emit CustomEvent
     * @private
     */
    _emitChangeEvent(sectionId, isVisible, fieldId) {
        const event = new CustomEvent('fieldVisibilityChanged', {
            bubbles: false,
            detail: {
                sectionId,
                fieldId,
                isVisible,
                sectionSettings: { ...this.sectionSettings },
                fieldSettings: JSON.parse(JSON.stringify(this.fieldSettings)),
                timestamp: Date.now()
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * Get current settings
     * @returns {Object} Current settings
     */
    getSettings() {
        return {
            sections: { ...this.sectionSettings },
            fields: JSON.parse(JSON.stringify(this.fieldSettings))
        };
    }

    /**
     * Check if a section is visible
     * @param {string} sectionId - Section identifier
     * @returns {boolean}
     */
    isSectionVisible(sectionId) {
        return !!this.sectionSettings[sectionId];
    }

    /**
     * Check if a field is visible
     * @param {string} sectionId - Section identifier
     * @param {string} fieldId - Field identifier
     * @returns {boolean}
     */
    isFieldVisible(sectionId, fieldId) {
        return !!this.fieldSettings[sectionId]?.[fieldId];
    }

    /**
     * Toggle a section's visibility
     * @param {string} sectionId - Section identifier
     * @returns {boolean} New visibility state
     */
    toggleSection(sectionId) {
        const newVisibility = !this.sectionSettings[sectionId];
        this.setSectionVisibility(sectionId, newVisibility);
        return newVisibility;
    }

    // ===== Backward Compatibility Aliases =====

    /**
     * @deprecated Use isSectionVisible() instead
     */
    isVisible(sectionId) {
        return this.isSectionVisible(sectionId);
    }

    /**
     * @deprecated Use toggleSection() instead
     */
    toggle(sectionId) {
        return this.toggleSection(sectionId);
    }

    /**
     * @deprecated Use setSectionVisibility() and setFieldVisibility() instead
     */
    updateSettings(newSettings) {
        if (newSettings.sections) {
            Object.keys(newSettings.sections).forEach(sectionId => {
                this.setSectionVisibility(sectionId, newSettings.sections[sectionId]);
            });
        }
        if (newSettings.fields) {
            Object.keys(newSettings.fields).forEach(sectionId => {
                Object.keys(newSettings.fields[sectionId]).forEach(fieldId => {
                    this.setFieldVisibility(sectionId, fieldId, newSettings.fields[sectionId][fieldId]);
                });
            });
        }
    }
}

// Export for use in other modules
window.FieldVisibilityManager = FieldVisibilityManager;
