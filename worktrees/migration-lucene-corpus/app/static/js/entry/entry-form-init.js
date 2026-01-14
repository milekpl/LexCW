/**
 * Entry Form Initialization
 *
 * Initializes all managers and functionality after DOM is ready.
 * This file is loaded via script tag with defer, after all other modules.
 *
 * NOTE: DictionaryApp namespace must be initialized BEFORE this file runs.
 * The inline script in entry_form.html handles that.
 */

(function() {
    'use strict';

    /**
     * Initialize all entry form managers and functionality
     * @param {Object} options - Configuration options
     * @param {Object} options.variantRelations - Variant relations data
     * @param {string} options.entriesUrl - URL for entries list
     */
    function initEntryForm(options = {}) {
        const entriesUrl = options.entriesUrl || '{{ url_for("main.entries") }}';

        // Initialize Bootstrap tooltips
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

        // Initialize pronunciation manager (if it exists)
        if (window.PronunciationFormsManager && document.getElementById('pronunciation-container')) {
            window.pronunciationFormsManager = new PronunciationFormsManager('pronunciation-container');
        }

        // Initialize variant forms manager
        if (window.VariantFormsManager && document.getElementById('variants-container')) {
            window.variantFormsManager = new VariantFormsManager('variants-container', {
                variantRelations: options.variantRelations || []
            });
        }

        // Initialize relations manager
        if (window.RelationsManager && document.getElementById('relations-container')) {
            window.relationsManager = new RelationsManager('relations-container');
        }

        // Initialize etymology forms manager
        if (window.EtymologyFormsManager && document.getElementById('etymology-container')) {
            window.etymologyFormsManager = new EtymologyFormsManager('etymology-container', {
                rangeId: 'etymology'
            });
        }

        // Initialize multilingual notes manager
        if (window.MultilingualNotesManager && document.getElementById('notes-container')) {
            window.multilingualNotesManager = new MultilingualNotesManager('notes-container');
        }

        // Initialize SortableJS for senses
        const sensesContainer = document.getElementById('senses-container');
        if (sensesContainer && typeof Sortable !== 'undefined') {
            new Sortable(sensesContainer, {
                animation: 150,
                handle: '.drag-handle',
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen',
                dragClass: 'sortable-drag',
                onStart: function(evt) {
                    document.body.style.cursor = 'grabbing';
                },
                onEnd: function (evt) {
                    document.body.style.cursor = '';
                    if (typeof reindexSenses === 'function') {
                        reindexSenses();
                    }
                }
            });
        }

        // Initialize live preview manager
        const previewContainer = document.getElementById('live-preview-container');
        if (typeof LivePreviewManager !== 'undefined' && previewContainer) {
            window.livePreviewManager = new LivePreviewManager('#entry-form', '#live-preview-container', 500);

            const refreshBtn = document.getElementById('refresh-preview-btn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => {
                    if (window.livePreviewManager) {
                        window.livePreviewManager.updatePreview(true);
                    }
                });
            }

            const toggleXmlBtn = document.getElementById('toggle-xml-preview-btn');
            if (toggleXmlBtn) {
                toggleXmlBtn.addEventListener('click', () => {
                    setTimeout(() => {
                        if (window.livePreviewManager) {
                            window.livePreviewManager.updatePreview(true);
                        }
                    }, 100);
                });
            }
        }

        // Initialize Field Visibility Manager
        if (typeof FieldVisibilityManager !== 'undefined') {
            window.fieldVisibilityManager = new FieldVisibilityManager({
                storageKey: 'entryFormFieldVisibility'
            });
        }

        // Initialize DELETE button with two-step confirmation
        initDeleteButton(entriesUrl);
    }

    /**
     * Initialize DELETE button functionality
     * @param {string} entriesUrl - URL to redirect after deletion
     */
    function initDeleteButton(entriesUrl) {
        const deleteBtn = document.getElementById('delete-entry-btn');
        const deleteWarning = document.getElementById('delete-warning');

        if (!deleteBtn) return;

        deleteBtn.addEventListener('click', function() {
            if (!deleteWarning.classList.contains('visible')) {
                // First click: show warning
                deleteWarning.classList.add('visible');
                deleteBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> CONFIRM DELETE';
                deleteBtn.classList.remove('btn-outline-danger');
                deleteBtn.classList.add('btn-danger');
            } else {
                // Second click: proceed with deletion
                if (confirm('Are you sure you want to permanently delete this entry? This action cannot be undone.')) {
                    const entryId = DictionaryApp?.config?.entryId;
                    const csrfToken = DictionaryApp?.config?.csrfToken;

                    if (entryId) {
                        const headers = { 'Content-Type': 'application/json' };
                        if (csrfToken) {
                            headers['X-CSRF-TOKEN'] = csrfToken;
                        }

                        fetch(`/api/entries/${entryId}`, {
                            method: 'DELETE',
                            headers: headers
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                window.location.href = entriesUrl;
                            } else {
                                alert('Error deleting entry: ' + (data.error || 'Unknown error'));
                            }
                        })
                        .catch(error => {
                            Logger.error('Error deleting entry:', error);
                            alert('Error deleting entry. Please try again.');
                        });
                    }
                } else {
                    // Cancel: reset button state
                    deleteWarning.classList.remove('visible');
                    deleteBtn.innerHTML = '<i class="fas fa-trash-alt"></i> DELETE ENTRY';
                    deleteBtn.classList.remove('btn-danger');
                    deleteBtn.classList.add('btn-outline-danger');
                }
            }
        });
    }

    // Export for module systems
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { initEntryForm, initDeleteButton };
    }

    // Make available globally
    window.initEntryForm = initEntryForm;
    window.initDeleteButton = initDeleteButton;

})();
