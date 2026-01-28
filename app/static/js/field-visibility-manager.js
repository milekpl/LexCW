/**
 * FieldVisibilityManager - Handles field visibility settings for forms
 *
 * Supports both section-level and per-field visibility control.
 * Uses event-driven architecture for component communication.
 * Settings are persisted via API to user preferences in database.
 */
class FieldVisibilityManager {
    /**
     * Create a new FieldVisibilityManager instance
     * @param {Object} options - Configuration options
     * @param {string} options.apiBaseUrl - Base URL for API calls (required)
     * @param {number} options.userId - User ID for API authentication (required)
     * @param {number} options.projectId - Project ID for project defaults (optional)
     * @param {Object} options.defaultSectionSettings - Default section visibility
     * @param {Object} options.defaultFieldSettings - Default field visibility per section
     * @param {Function} options.onChange - Callback when visibility changes
     * @param {boolean} options.autoApply - Apply settings on init (default: true)
     * @param {Function} options.onLoad - Callback when settings are loaded from API
     */
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: '',
            userId: null,
            projectId: null,
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
            onLoad: null,
            autoApply: true,
            ...options
        };

        this.sectionSettings = { ...this.options.defaultSectionSettings };
        this.fieldSettings = JSON.parse(JSON.stringify(this.options.defaultFieldSettings));
        this._boundMethods = new WeakMap();
        this._loaded = false;

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
     * Load settings from API
     * @returns {Promise<Object>} Settings object with sections and fields
     */
    async loadFromAPI() {
        if (!this.options.apiBaseUrl || !this.options.userId) {
            console.warn('[FieldVisibilityManager] API base URL and user ID are required');
            return this._getDefaults();
        }

        try {
            const url = new URL(`/api/users/${this.options.userId}/preferences/field-visibility`, window.location.origin);
            url.searchParams.set('project_id', this.options.projectId || '');

            const response = await fetch(url.toString(), {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`API returned ${response.status}`);
            }

            const data = await response.json();
            const visibility = data.fieldVisibility || {};

            // Apply settings from API
            if (visibility.sections) {
                this.sectionSettings = { ...this.options.defaultSectionSettings, ...visibility.sections };
            }
            if (visibility.fields) {
                this.fieldSettings = this._mergeFieldSettings(visibility.fields);
            }

            this._loaded = true;

            // Call onLoad callback if provided
            if (this.options.onLoad) {
                this.options.onLoad(this.getSettings());
            }

            if (this.options.autoApply) {
                this._applySettings();
            }

            return this.getSettings();
        } catch (e) {
            console.warn('[FieldVisibilityManager] Failed to load settings from API:', e);
            this._loaded = false;
            return this._getDefaults();
        }
    }

    /**
     * Save settings to API
     * @returns {Promise<boolean>} Success status
     */
    async saveToAPI() {
        if (!this.options.apiBaseUrl || !this.options.userId) {
            console.warn('[FieldVisibilityManager] API base URL and user ID are required');
            return false;
        }

        try {
            const url = new URL(`/api/users/${this.options.userId}/preferences/field-visibility`, window.location.origin);

            const response = await fetch(url.toString(), {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    project_id: this.options.projectId,
                    sections: this.sectionSettings,
                    fields: this.fieldSettings
                })
            });

            if (!response.ok) {
                throw new Error(`API returned ${response.status}`);
            }

            return true;
        } catch (e) {
            console.warn('[FieldVisibilityManager] Failed to save settings to API:', e);
            return false;
        }
    }

    /**
     * Get default settings (hardcoded or from project)
     * @returns {Object} Default settings
     * @private
     */
    _getDefaults() {
        return {
            sections: { ...this.options.defaultSectionSettings },
            fields: JSON.parse(JSON.stringify(this.options.defaultFieldSettings))
        };
    }

    /**
     * Merge field settings with defaults for new fields
     * @private
     */
    _mergeFieldSettings(storedFields) {
        const merged = { ...this.options.defaultFieldSettings };
        Object.keys(storedFields).forEach(sectionId => {
            merged[sectionId] = { ...merged[sectionId], ...storedFields[sectionId] };
        });
        return merged;
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
    async _handleToggleChange(event) {
        event.stopPropagation();
        event.preventDefault();

        const checkbox = event.target;
        const sectionId = checkbox.dataset.sectionId;
        const fieldId = checkbox.dataset.fieldId;
        const isVisible = checkbox.checked;

        if (fieldId) {
            // Field-level toggle
            await this.setFieldVisibility(sectionId, fieldId, isVisible);
        } else if (sectionId) {
            // Section-level toggle
            await this.setSectionVisibility(sectionId, isVisible);
        }
    }

    /**
     * Handle button clicks
     * @private
     */
    async _handleButtonClick(event) {
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
            await this.resetToDefaults();
        } else if (event.target.classList.contains('hide-empty-sections-btn') ||
                   event.target.closest('.hide-empty-sections-btn')) {
            await this._hideEmptySections();
        } else if (event.target.classList.contains('show-all-sections-btn') ||
                   event.target.closest('.show-all-sections-btn')) {
            await this.showAllSections();
        }
    }

    /**
     * Set visibility for a specific section
     * @param {string} sectionId - Section identifier
     * @param {boolean} visible - Whether the section should be visible
     * @param {boolean} save - Whether to save to API (default: true)
     */
    async setSectionVisibility(sectionId, visible, save = true) {
        if (!(sectionId in this.options.defaultSectionSettings)) {
            console.warn(`[FieldVisibilityManager] Unknown section: ${sectionId}`);
            return;
        }

        this.sectionSettings[sectionId] = visible;

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
            this._updateFieldCheckboxes(sectionId);
        }

        // Save to API if requested
        if (save) {
            await this.saveToAPI();
        }

        this._emitChangeEvent(sectionId, visible, null);
    }

    /**
     * Set visibility for a specific field
     * @param {string} sectionId - Section identifier
     * @param {string} fieldId - Field identifier
     * @param {boolean} visible - Whether the field should be visible
     * @param {boolean} save - Whether to save to API (default: true)
     */
    async setFieldVisibility(sectionId, fieldId, visible, save = true) {
        if (!this.fieldSettings[sectionId]) {
            this.fieldSettings[sectionId] = {};
        }

        // If setting field to visible, ensure section is also visible
        if (visible) {
            this.sectionSettings[sectionId] = true;
            const sectionCheckboxes = document.querySelectorAll(`[data-section-id="${sectionId}"]:not([data-field-id])`);
            sectionCheckboxes.forEach(checkbox => checkbox.checked = true);
            this._applySectionVisibility(sectionId, true);
        }

        this.fieldSettings[sectionId][fieldId] = visible;

        // Update field checkboxes
        const checkboxes = document.querySelectorAll(`[data-section-id="${sectionId}"][data-field-id="${fieldId}"]`);
        checkboxes.forEach(checkbox => {
            checkbox.checked = visible;
        });

        // Apply visibility to field elements
        this._applyFieldVisibility(sectionId, fieldId, visible);

        // Update section checkbox state based on field states
        this._updateSectionCheckboxFromFields(sectionId);

        // Save to API if requested
        if (save) {
            await this.saveToAPI();
        }

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
     * Sync all modal checkboxes to match current settings
     * Call this when the modal opens to ensure checkboxes reflect saved settings
     */
    syncModalCheckboxes() {
        this._syncCheckboxesToSettings();
    }

    /**
     * Sync all checkboxes in modal to current settings
     * @private
     */
    _syncCheckboxesToSettings() {
        document.querySelectorAll('.field-visibility-toggle').forEach(checkbox => {
            const sectionId = checkbox.dataset.sectionId;
            const fieldId = checkbox.dataset.fieldId;

            if (fieldId) {
                // Field checkbox
                checkbox.checked = this.fieldSettings[sectionId]?.[fieldId] === true;
            } else if (sectionId) {
                // Section checkbox
                checkbox.checked = this.sectionSettings[sectionId] === true;
            }
        });
    }

    /**
     * Reset all settings to defaults (project defaults or hardcoded defaults)
     * @param {boolean} save - Whether to save to API (default: true)
     */
    async resetToDefaults(save = true) {
        // Reset to hardcoded defaults (will be overridden by project defaults on next load)
        this.sectionSettings = { ...this.options.defaultSectionSettings };
        this.fieldSettings = JSON.parse(JSON.stringify(this.options.defaultFieldSettings));

        // Sync checkboxes to defaults
        this._syncCheckboxesToSettings();

        // Apply to form
        this._applySettings();

        // Call API to clear user preferences (will fall back to project defaults)
        if (save && this.options.apiBaseUrl && this.options.userId) {
            try {
                const url = new URL(`/api/users/${this.options.userId}/preferences/field-visibility/reset`, window.location.origin);
                if (this.options.projectId) {
                    url.searchParams.set('project_id', this.options.projectId);
                }

                await fetch(url.toString(), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin'
                });

                // Reload from API to get actual defaults
                await this.loadFromAPI();
            } catch (e) {
                console.warn('[FieldVisibilityManager] Failed to reset settings via API:', e);
            }
        }

        this._emitChangeEvent('reset', true, null);
    }

    /**
     * Hide sections and individual fields that have no content
     * @private
     */
    async _hideEmptySections() {
        // First, hide individual fields that are empty
        const fieldElements = document.querySelectorAll('[data-section-id][data-field-id]');

        for (const fieldElement of fieldElements) {
            const sectionId = fieldElement.dataset.sectionId;
            const fieldId = fieldElement.dataset.fieldId;

            // Only hide if field is supposed to be visible in settings
            if (this.fieldSettings[sectionId]?.[fieldId] === false) {
                continue; // Already hidden by user preference
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
                // Also update field settings to reflect hidden state (don't save individually)
                await this.setFieldVisibility(sectionId, fieldId, false, false);
            }
        }

        // Then, hide sections that are completely empty (no visible content)
        const sections = document.querySelectorAll('[class*="-section"]');

        for (const section of sections) {
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
                    await this.setSectionVisibility(sectionId, false, false);
                }
            }
        }

        // Save accumulated changes
        await this.saveToAPI();
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
     * @param {boolean} save - Whether to save to API (default: true)
     */
    async showAllSections(save = true) {
        // Show all sections
        Object.keys(this.sectionSettings).forEach(sectionId => {
            this.sectionSettings[sectionId] = true;
        });

        // Show all fields
        Object.keys(this.fieldSettings).forEach(sectionId => {
            Object.keys(this.fieldSettings[sectionId]).forEach(fieldId => {
                this.fieldSettings[sectionId][fieldId] = true;
            });
        });

        // Update all checkboxes
        this._syncCheckboxesToSettings();

        // Apply to form
        this._applySettings();

        // Save to API if requested
        if (save) {
            await this.saveToAPI();
        }

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
