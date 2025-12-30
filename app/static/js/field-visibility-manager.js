/**
 * FieldVisibilityManager - Handles field visibility settings for forms
 *
 * Uses event-driven architecture for component communication.
 * Settings are persisted to localStorage and broadcast via CustomEvents.
 */
class FieldVisibilityManager {
    /**
     * Create a new FieldVisibilityManager instance
     * @param {Object} options - Configuration options
     * @param {string} options.storageKey - localStorage key prefix (default: 'fieldVisibilitySettings')
     * @param {Object} options.defaultSettings - Default visibility settings
     * @param {Function} options.onChange - Callback when visibility changes
     * @param {boolean} options.autoApply - Apply settings on init (default: true)
     */
    constructor(options = {}) {
        this.options = {
            storageKey: 'fieldVisibilitySettings',
            defaultSettings: {
                'basic-info': true,
                'custom-fields': true,
                'notes': true,
                'pronunciation': true,
                'variants': true,
                'direct-variants': true,
                'relations': true,
                'senses': true
            },
            onChange: null,
            autoApply: true,
            ...options
        };

        this.settings = this._loadSettings();
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
     * Load settings from localStorage or use defaults
     * @private
     */
    _loadSettings() {
        try {
            const stored = localStorage.getItem(this.options.storageKey);
            if (stored) {
                return { ...this.options.defaultSettings, ...JSON.parse(stored) };
            }
        } catch (e) {
            console.warn('[FieldVisibilityManager] Failed to load settings:', e);
        }
        return { ...this.options.defaultSettings };
    }

    /**
     * Save settings to localStorage
     * @private
     */
    _saveSettings() {
        try {
            localStorage.setItem(this.options.storageKey, JSON.stringify(this.settings));
        } catch (e) {
            console.warn('[FieldVisibilityManager] Failed to save settings:', e);
        }
    }

    /**
     * Set up event listeners using event delegation
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
        });
    }

    /**
     * Handle checkbox toggle change
     * @private
     */
    _handleToggleChange(event) {
        // Stop event propagation to prevent triggering form validation/auto-save
        // Visibility toggles are UI preferences, not form data
        event.stopPropagation();
        event.preventDefault();

        const checkbox = event.target;
        const sectionId = checkbox.dataset.sectionId;
        const isVisible = checkbox.checked;

        if (sectionId) {
            this.setSectionVisibility(sectionId, isVisible);
        }
    }

    /**
     * Handle button clicks (reset, hide empty, show all)
     * @private
     */
    _handleButtonClick(event) {
        // Check if this is a visibility control button
        const isVisibilityBtn =
            event.target.classList.contains('reset-field-visibility-btn') ||
            event.target.classList.contains('hide-empty-sections-btn') ||
            event.target.classList.contains('show-all-sections-btn') ||
            event.target.closest('.reset-field-visibility-btn') ||
            event.target.closest('.hide-empty-sections-btn') ||
            event.target.closest('.show-all-sections-btn');

        if (isVisibilityBtn) {
            // Stop event propagation for visibility control buttons
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
        if (!(sectionId in this.options.defaultSettings)) {
            console.warn(`[FieldVisibilityManager] Unknown section: ${sectionId}`);
            return;
        }

        this.settings[sectionId] = visible;
        this._saveSettings();

        // Update all checkboxes with this section ID
        const checkboxes = document.querySelectorAll(`[data-section-id="${sectionId}"]`);
        checkboxes.forEach(checkbox => {
            checkbox.checked = visible;
        });

        // Apply visibility to target elements
        if (checkboxes.length > 0) {
            const targetSelector = checkboxes[0].dataset.target;
            if (targetSelector) {
                const targetElements = document.querySelectorAll(targetSelector);
                targetElements.forEach(el => {
                    el.style.display = visible ? '' : 'none';
                });
            }
        }

        // Emit change event for other components
        this._emitChangeEvent(sectionId, visible);

        // Call onChange callback
        if (typeof this.options.onChange === 'function') {
            this.options.onChange(sectionId, visible, this.settings);
        }
    }

    /**
     * Apply all settings to the DOM
     * @private
     */
    _applySettings() {
        Object.entries(this.settings).forEach(([sectionId, isVisible]) => {
            this.setSectionVisibility(sectionId, isVisible);
        });
    }

    /**
     * Reset all settings to defaults
     */
    resetToDefaults() {
        this.settings = { ...this.options.defaultSettings };
        this._saveSettings();
        this._applySettings();
        this._emitChangeEvent('reset', true);
    }

    /**
     * Hide sections that have no content
     * @private
     */
    _hideEmptySections() {
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
                if (sectionId && this.settings[sectionId]) {
                    this.setSectionVisibility(sectionId, false);
                }
            }
        });
    }

    /**
     * Find section ID for a DOM element based on class names
     * @private
     */
    _findSectionIdForElement(element) {
        const classList = Array.from(element.classList);
        for (const [sectionId, target] of Object.entries(this.options.defaultSettings)) {
            if (target.startsWith('.')) {
                const targetClass = target.slice(1);
                if (classList.includes(targetClass)) {
                    return sectionId;
                }
            }
        }
        return null;
    }

    /**
     * Show all sections
     */
    showAllSections() {
        Object.keys(this.settings).forEach(sectionId => {
            this.setSectionVisibility(sectionId, true);
        });
        this._emitChangeEvent('showAll', true);
    }

    /**
     * Emit CustomEvent for other components
     * @private
     */
    _emitChangeEvent(sectionId, isVisible) {
        const event = new CustomEvent('fieldVisibilityChanged', {
            bubbles: false,  // Don't bubble to prevent triggering form validation
            detail: {
                sectionId,
                isVisible,
                allSettings: { ...this.settings },
                timestamp: Date.now()
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * Get current settings
     * @returns {Object} Copy of current settings
     */
    getSettings() {
        return { ...this.settings };
    }

    /**
     * Update settings programmatically
     * @param {Object} newSettings - Settings to merge
     */
    updateSettings(newSettings) {
        this.settings = { ...this.settings, ...newSettings };
        this._saveSettings();
        this._applySettings();
    }

    /**
     * Check if a section is visible
     * @param {string} sectionId - Section identifier
     * @returns {boolean}
     */
    isVisible(sectionId) {
        return !!this.settings[sectionId];
    }

    /**
     * Toggle a section's visibility
     * @param {string} sectionId - Section identifier
     * @returns {boolean} New visibility state
     */
    toggle(sectionId) {
        const newVisibility = !this.settings[sectionId];
        this.setSectionVisibility(sectionId, newVisibility);
        return newVisibility;
    }
}

// Export for use in other modules
window.FieldVisibilityManager = FieldVisibilityManager;
