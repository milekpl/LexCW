/**
 * Lexicographic Curation Workbench - Entry Form JavaScript
 *
 * This file contains the functionality for the entry edit/add form.
 *
 * Refactored and bug-fixed version.
 */

// REFACTOR: Create a single, reusable utility for showing toast notifications.
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    const alertClass = type === 'error' ? 'alert-danger' : `alert-${type}`;
    toast.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
    toast.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 1056; /* Ensure it's above modals */
        min-width: 300px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    document.body.appendChild(toast);

    // Auto-remove after 3.5 seconds
    setTimeout(() => {
        // Use bootstrap's API to gracefully fade out the alert
        const bsAlert = bootstrap.Alert.getOrCreateInstance(toast);
        if (bsAlert) {
            bsAlert.close();
        } else if (toast.parentNode) {
            toast.remove();
        }
    }, 3500);
}

// Helper to normalize numeric-keyed objects to arrays (used by serializers)
const normalizeIndexedArray = window.normalizeIndexedArray || function(value) {
    if (value === undefined || value === null) {
        return [];
    }

    if (Array.isArray(value)) {
        return value;
    }

    if (typeof value === 'object') {
        const entries = Object.entries(value)
            .filter(([key]) => key !== '__proto__' && key !== 'constructor' && key !== 'prototype' && !Number.isNaN(Number(key)))
            .sort((a, b) => Number(a[0]) - Number(b[0]));

        return entries.map(([, val]) => val);
    }

    return [];
};

if (!window.normalizeIndexedArray) {
    window.normalizeIndexedArray = normalizeIndexedArray;
}

// Helper to apply sense relations from current DOM to formData, clearing stale values
const applySenseRelationsFromDom = window.applySenseRelationsFromDom || function(form, formData, normalizeFn) {
    const normalize = typeof normalizeFn === 'function' ? normalizeFn : normalizeIndexedArray;
    const result = formData || {};
    result.senses = normalize(result.senses);

    // CRITICAL: Exclude the default-sense-template to avoid adding ghost senses
    // The template should never be included in the actual data being submitted
    const senseItems = form ? form.querySelectorAll('#senses-container .sense-item:not(#default-sense-template):not(.default-sense-template)') : [];
    senseItems.forEach((senseEl, fallbackIndex) => {
        const senseIndex = senseEl.dataset.senseIndex;
        const idx = Number.isNaN(Number(senseIndex)) ? fallbackIndex : Number(senseIndex);

        if (!result.senses[idx]) {
            result.senses[idx] = {};
        }

        const relations = [];
        senseEl.querySelectorAll('.sense-relation-item').forEach((relEl, relIdx) => {
            const typeEl = relEl.querySelector('.sense-lexical-relation-select');
            const refEl = relEl.querySelector('.sense-relation-ref-hidden');
            const type = typeEl ? (typeEl.value || '').trim() : '';
            const ref = refEl ? (refEl.value || '').trim() : '';
            if (type || ref) {
                relations.push({ type, ref, order: relIdx });
            }
        });

        // Always set relations to the current DOM state to avoid stale data
        result.senses[idx].relations = relations;
    });

    return result;
};

if (!window.applySenseRelationsFromDom) {
    window.applySenseRelationsFromDom = applySenseRelationsFromDom;
}


document.addEventListener('DOMContentLoaded', function() {
    // REFACTOR: Define frequently used elements once to avoid repeated DOM queries.
    const sensesContainer = document.getElementById('senses-container');
    const entryForm = document.getElementById('entry-form');

    // Initialize external components if they exist
    window.rangesLoader = window.rangesLoader || new RangesLoader();
    
    // Initialize LIFT XML Serializer
    if (typeof LIFTXMLSerializer !== 'undefined') {
        window.xmlSerializer = new LIFTXMLSerializer();
        console.log('[Entry Form] LIFT XML Serializer initialized');
    } else {
        console.warn('[Entry Form] LIFT XML Serializer not available');
    }
    
    // XML Preview Toggle Handler
    const xmlPreviewPanel = document.getElementById('xml-preview-panel');
    const toggleXmlPreviewBtn = document.getElementById('toggle-xml-preview-btn');
    const copyXmlBtn = document.getElementById('copy-xml-btn');
    const xmlPreviewContent = document.getElementById('xml-preview-content');
    
    if (toggleXmlPreviewBtn && xmlPreviewPanel) {
        toggleXmlPreviewBtn.addEventListener('click', function() {
            if (xmlPreviewPanel.style.display === 'none') {
                // Show panel and generate XML
                xmlPreviewPanel.style.display = 'block';
                updateXmlPreview();
                toggleXmlPreviewBtn.innerHTML = '<i class="fas fa-code-slash"></i> Hide XML';
            } else {
                // Hide panel
                xmlPreviewPanel.style.display = 'none';
                toggleXmlPreviewBtn.innerHTML = '<i class="fas fa-code"></i> XML Preview';
            }
        });
    }
    
    // Copy XML to clipboard
    if (copyXmlBtn && xmlPreviewContent) {
        copyXmlBtn.addEventListener('click', function() {
            const xmlText = xmlPreviewContent.textContent;
            navigator.clipboard.writeText(xmlText).then(() => {
                showToast('XML copied to clipboard', 'success');
            }).catch(err => {
                console.error('Failed to copy XML:', err);
                showToast('Failed to copy XML', 'error');
            });
        });
    }
    
    /**
     * Update XML Preview with current form data
     */
    function updateXmlPreview() {
        if (!window.xmlSerializer || !xmlPreviewContent) return;
        
        try {
            // Serialize form to JSON first (includeEmpty: true to ensure we get all fields)
            const formData = window.FormSerializer.serializeFormToJSON(entryForm, {
                includeEmpty: true
            });

            // Normalize senses and refresh relations directly from DOM to avoid stale values
            formData.senses = normalizeIndexedArray(formData.senses);
            applySenseRelationsFromDom(entryForm, formData, normalizeIndexedArray);
            
            console.log('[XML Preview] Form data:', formData);
            console.log('[XML Preview] lexical_unit:', formData.lexical_unit);
            
            // Generate XML directly from form data (serializer now handles snake_case)
            const xmlString = window.xmlSerializer.serializeEntry(formData);
            
            // Display in preview panel
            xmlPreviewContent.textContent = xmlString;
            
            // Highlight syntax (optional - could add a lightweight highlighter later)
        } catch (error) {
            console.error('[XML Preview] Error generating XML:', error);
            console.error('[XML Preview] Error stack:', error.stack);
            xmlPreviewContent.textContent = `Error generating XML: ${error.message}\n\nCheck browser console (F12) for details.`;
        }
    }

    // Expose for other modules (relations search, etc.) to trigger refresh
    window.updateXmlPreview = updateXmlPreview;

    /**
     * Function to initialize dynamic selects.
     * Populates select elements with options from a given range.
     */
    async function initializeDynamicSelects(container) {
        // Initialize grammatical-info selects
        const dynamicSelects = container.querySelectorAll('.dynamic-grammatical-info');

        const promises = Array.from(dynamicSelects).map(select => {
            const rangeId = select.dataset.rangeId;
            const selectedValue = select.dataset.selected;
            if (rangeId) {
                // Assuming populateSelect is an async function that returns a promise
                return window.rangesLoader.populateSelect(select, rangeId, {
                    selectedValue: selectedValue,
                    emptyOption: 'Select part of speech'
                });
            }
            return Promise.resolve(); // Return a resolved promise for selects without a rangeId
        });

        // Initialize ALL dynamic-lift-range selects (semantic-domain, usage-type, etc.)
        const allDynamicRanges = container.querySelectorAll('.dynamic-lift-range');
        
        const rangePromises = Array.from(allDynamicRanges).map(select => {
            const rangeId = select.dataset.rangeId;
            const selectedValue = select.dataset.selected;
            const hierarchical = select.dataset.hierarchical === 'true';
            const searchable = select.dataset.searchable === 'true';
            
            if (rangeId && window.rangesLoader) {
                console.log(`[Entry Form] Initializing range dropdown: ${rangeId}`);
                return window.rangesLoader.populateSelect(select, rangeId, {
                    selectedValue: selectedValue,
                    emptyOption: select.querySelector('option[value=""]')?.textContent || 'Select option',
                    hierarchical: hierarchical,
                    searchable: searchable
                }).catch(err => {
                    console.error(`[Entry Form] Failed to populate ${rangeId}:`, err);
                });
            }
            return Promise.resolve();
        });

        await Promise.all([...promises, ...rangePromises]);
    }

    /**
     * Grammatical Category Inheritance Logic.
     * Automatically derives and validates the entry-level grammatical category
     * based on the categories of its senses, as per specification 7.2.1.
     */
    async function updateGrammaticalCategoryInheritance() {
        const entryPartOfSpeechSelect = document.getElementById('part-of-speech');
        const requiredIndicator = document.getElementById('pos-required-indicator');
        if (!entryPartOfSpeechSelect) return;

        // Get all sense grammatical categories that have a selected value
        const senseGrammaticalSelects = document.querySelectorAll('#senses-container .dynamic-grammatical-info');
        const senseCategories = Array.from(senseGrammaticalSelects)
            .map(select => select.value)
            .filter(value => value && value.trim()); // Only consider non-empty values

        // REFACTOR: Clear existing validation state more robustly.
        entryPartOfSpeechSelect.classList.remove('is-invalid', 'is-valid');
        const feedbackElement = entryPartOfSpeechSelect.parentElement.querySelector('.invalid-feedback, .valid-feedback');
        if (feedbackElement) {
            feedbackElement.remove();
        }

        if (senseCategories.length === 0) {
            // No senses have a part of speech selected. The entry-level field is optional.
            entryPartOfSpeechSelect.required = false;
            if (requiredIndicator) requiredIndicator.style.display = 'none';
            return;
        }

        const uniqueCategories = [...new Set(senseCategories)];

        if (uniqueCategories.length === 1) {
            // All senses agree. Auto-inherit the category.
            const commonCategory = uniqueCategories[0];
            entryPartOfSpeechSelect.value = commonCategory;
            entryPartOfSpeechSelect.required = false;
            if (requiredIndicator) requiredIndicator.style.display = 'none';

            entryPartOfSpeechSelect.classList.add('is-valid');
            const feedback = document.createElement('div');
            feedback.className = 'valid-feedback';
            feedback.textContent = 'Automatically inherited from senses.';
            entryPartOfSpeechSelect.parentElement.appendChild(feedback);
        } else {
            // Discrepancy detected. Field is required, show an error.
            entryPartOfSpeechSelect.required = true;
            if (requiredIndicator) requiredIndicator.style.display = 'inline';
            entryPartOfSpeechSelect.classList.add('is-invalid');
            const feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            feedback.innerHTML = `
                <strong>Grammatical category discrepancy detected!</strong><br>
                Senses have different categories: ${uniqueCategories.join(', ')}.<br>
                Please manually select the correct entry-level category.
            `;
            entryPartOfSpeechSelect.parentElement.appendChild(feedback);
        }
    }

    /**
     * Sets up event listeners for the grammatical category inheritance logic.
     */
    function setupGrammaticalInheritanceListeners() {
        // Listen for changes in any sense's grammatical category select.
        // Using event delegation on the form for efficiency.
        if (entryForm) {
            entryForm.addEventListener('change', function(e) {
                if (e.target.matches('#senses-container .dynamic-grammatical-info')) {
                    updateGrammaticalCategoryInheritance();
                }
            });
        }

        // Use a MutationObserver to detect when senses are added or removed.
        if (sensesContainer) {
            // REFACTOR: The observer is simplified. Explicit calls after add/remove
            // are more reliable, but this observer catches all list changes.
            // We only need to observe direct children additions/removals.
            const observer = new MutationObserver(() => {
                updateGrammaticalCategoryInheritance();
            });
            observer.observe(sensesContainer, {
                childList: true
            });
        }
    }

    // --- Initialization Sequence ---

    function initializeMergeSplitButtons() {
        document.getElementById('merge-senses-btn')?.addEventListener('click', function(e) {
            e.preventDefault();
            const entryId = document.querySelector('input[name="id"]')?.value;
            openMergeSensesDialog(entryId);
        });

        document.getElementById('senses-container')?.addEventListener('click', function(e) {
            const splitBtn = e.target.closest('.split-sense-btn');
            if (splitBtn) {
                e.preventDefault();
                const senseId = splitBtn.dataset.senseId;
                const entryId = document.querySelector('input[name="id"]')?.value;
                openSplitEntryDialog(entryId, [senseId]);
            }
        });
    }

    function openMergeSensesDialog(entryId) {
        const mergeSensesModalEl = document.getElementById('mergeSensesModal');
        const mergeSensesModal = new bootstrap.Modal(mergeSensesModalEl);
        const targetSenseSelect = mergeSensesModalEl.querySelector('#targetSenseSelect');
        const sourceSensesList = mergeSensesModalEl.querySelector('#sourceSensesList');
        
        targetSenseSelect.innerHTML = '<option value="">Select target sense...</option>';
        sourceSensesList.innerHTML = '';

        const senseItems = document.querySelectorAll('#senses-container .sense-item');
        const senses = Array.from(senseItems).map(item => {
            const id = item.querySelector('input[name*=".id"]')?.value;
            const gloss = item.querySelector('textarea[name*=".definition."]')?.value; // using definition as a stand-in for gloss
            return { id, gloss: gloss ? gloss.substring(0, 50) + '...' : `Sense ${id}` };
        });

        if (senses.length < 2) {
            alert('You need at least two senses to merge.');
            return;
        }

        senses.forEach(sense => {
            const option = document.createElement('option');
            option.value = sense.id;
            option.textContent = sense.gloss;
            targetSenseSelect.appendChild(option);
        });

        targetSenseSelect.addEventListener('change', () => {
            const targetId = targetSenseSelect.value;
            sourceSensesList.innerHTML = '';
            senses.forEach(sense => {
                if (sense.id !== targetId) {
                    const item = document.createElement('div');
                    item.className = 'list-group-item';
                    item.innerHTML = `
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="${sense.id}" id="merge-source-sense-${sense.id}">
                            <label class="form-check-label" for="merge-source-sense-${sense.id}">
                                ${sense.gloss}
                            </label>
                        </div>
                    `;
                    sourceSensesList.appendChild(item);
                }
            });
        });

        mergeSensesModal.show();
    }

    const confirmMergeSensesBtn = document.getElementById('confirmMergeSenses');
    if (confirmMergeSensesBtn) {
        confirmMergeSensesBtn.addEventListener('click', () => {
            const mergeSensesModalEl = document.getElementById('mergeSensesModal');
            const entryId = document.querySelector('input[name="id"]').value;
            const targetSenseId = mergeSensesModalEl.querySelector('#targetSenseSelect').value;
            const sourceSenseIds = Array.from(mergeSensesModalEl.querySelectorAll('#sourceSensesList input:checked')).map(input => input.value);
            const mergeStrategy = mergeSensesModalEl.querySelector('input[name="mergeStrategy"]:checked').value;

            if (!targetSenseId) {
                alert('Please select a target sense.');
                return;
            }
            if (sourceSenseIds.length === 0) {
                alert('Please select at least one source sense.');
                return;
            }

            const payload = {
                source_sense_ids: sourceSenseIds,
                merge_strategy: mergeStrategy
            };

            fetch(`/api/merge-split/entries/${entryId}/senses/${targetSenseId}/merge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Senses merged successfully!', 'success');
                    const mergeSensesModal = bootstrap.Modal.getInstance(mergeSensesModalEl);
                    mergeSensesModal.hide();
                    location.reload(); // Easiest way to show the result
                } else {
                    alert(`Error merging senses: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Error merging senses:', error);
                alert('An error occurred while merging senses.');
            });
        });
    }

    function openSplitEntryDialog(entryId, senseIds) {
        console.log(`Opening Split Entry Dialog for entry: ${entryId} with senses: ${senseIds}`);
        const splitEntryModal = new bootstrap.Modal(document.getElementById('splitEntryModal'));
        splitEntryModal.show();
        document.getElementById('splitSourceEntry').textContent = entryId;
    }

    // Expose the update function globally for other components that might add senses.
    window.updateGrammaticalCategoryInheritance = updateGrammaticalCategoryInheritance;

    // 1. Initialize all dynamic select elements on the page.
    initializeDynamicSelects(document.body).then(() => {
        console.log('Dynamic selects initialized.');

        // 2. After selects are populated, set up the inheritance logic.
        setupGrammaticalInheritanceListeners();

        // 3. Run an initial check on the grammatical inheritance.
        // REFACTOR: Removed unreliable setTimeout. This now runs after selects are ready.
        updateGrammaticalCategoryInheritance();
    });

    initializeMergeSplitButtons();

    // Initialize Select2 for any tag inputs.
    $('.select2-tags').select2({
        theme: 'bootstrap-5',
        tags: true,
        tokenSeparators: [',', ' '],
        placeholder: 'Enter or select values...'
    });

    // --- Main Event Handlers ---

    // --- Main Event Handlers ---

    if (entryForm) {
        entryForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Check if user wants to skip validation
            const skipValidationCheckbox = document.getElementById('skip-validation-checkbox');
            const shouldSkipValidation = skipValidationCheckbox && skipValidationCheckbox.checked;
            
            if (shouldSkipValidation) {
                // Skip validation and submit directly
                console.log('Skipping validation as requested by user');
                submitForm();
            } else {
                // Submit form - validation will happen server-side
                console.log('Submitting form - server will validate');
                submitForm();
            }
        });
    }

    const validateBtn = document.getElementById('validate-btn');
    if (validateBtn) {
        validateBtn.addEventListener('click', () => {
            console.log('[Entry Form] Validate button clicked');
            validateForm(true);
        });
        console.log('[Entry Form] Validate button event listener attached');
    } else {
        console.warn('[Entry Form] Validate button not found');
    }

    document.getElementById('cancel-btn')?.addEventListener('click', () => {
        if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
            window.location.href = '/entries';
        }
    });

    document.getElementById('add-pronunciation-btn')?.addEventListener('click', addPronunciation);
    document.getElementById('add-sense-btn')?.addEventListener('click', addSense);
    document.getElementById('add-first-sense-btn')?.addEventListener('click', function() {
        document.getElementById('no-senses-message')?.remove();
        addSense();
    });

    // Handle adding/removing lexical unit language forms
    document.querySelector('.add-lexical-unit-language-btn')?.addEventListener('click', function() {
        const container = document.querySelector('.lexical-unit-forms');
        if (!container) return;
        
        // Get existing languages
        const existingLangs = Array.from(container.querySelectorAll('.language-form'))
            .map(form => form.dataset.language);
        
        // Get available languages from the first select
        const firstSelect = container.querySelector('select.language-select');
        if (!firstSelect) return;
        
        const availableLangs = Array.from(firstSelect.options)
            .map(opt => ({ code: opt.value, label: opt.textContent }))
            .filter(lang => !existingLangs.includes(lang.code));
        
        if (availableLangs.length === 0) {
            alert('All available languages have already been added.');
            return;
        }
        
        const newLang = availableLangs[0];
        
        // Create new language form
        const newForm = document.createElement('div');
        newForm.className = 'mb-2 language-form';
        newForm.dataset.language = newLang.code;
        newForm.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <label class="form-label">Language</label>
                    <select class="form-select language-select" 
                            name="lexical_unit_lang.${newLang.code}"
                            data-current-lang="${newLang.code}">
                        ${Array.from(firstSelect.options).map(opt => 
                            `<option value="${opt.value}" ${opt.value === newLang.code ? 'selected' : ''}>${opt.textContent}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="col-md-8">
                    <label class="form-label">Headword Text</label>
                    <input type="text" class="form-control lexical-unit-text" 
                           name="lexical_unit.${newLang.code}"
                           placeholder="Enter headword in ${newLang.code}">
                </div>
                <div class="col-md-1 d-flex align-items-end">
                    <button type="button" class="btn btn-sm btn-outline-danger remove-lexical-unit-language-btn" 
                            title="Remove language">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
        
        container.appendChild(newForm);
    });

    document.querySelector('.lexical-unit-forms')?.addEventListener('click', function(e) {
        const removeBtn = e.target.closest('.remove-lexical-unit-language-btn');
        if (removeBtn) {
            const languageForm = removeBtn.closest('.language-form');
            if (languageForm && confirm('Remove this language variant?')) {
                languageForm.remove();
            }
        }
    });

    // --- Event Delegation for Dynamic Elements ---

    document.getElementById('pronunciation-container')?.addEventListener('click', function(e) {
        const removeBtn = e.target.closest('.remove-pronunciation-btn');
        if (removeBtn) {
            if (confirm('Are you sure you want to remove this pronunciation?')) {
                removeBtn.closest('.pronunciation-item')?.remove();
            }
            return;
        }

        const uploadBtn = e.target.closest('.upload-audio-btn');
        if (uploadBtn) {
            const index = uploadBtn.dataset.index;
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = 'audio/*';
            
            fileInput.onchange = (event) => {
                const file = event.target.files[0];
                if (!file) return;
                
                // For now, just set the filename (in production, upload to server)
                // TODO: Implement actual server-side upload
                const audioPath = `audio/${file.name}`;
                const pronunciationItem = uploadBtn.closest('.pronunciation-item');
                const audioPathInput = pronunciationItem.querySelector('input[name*="audio_path"]');
                audioPathInput.value = audioPath;
                
                console.log('Selected audio file:', file.name, 'Size:', file.size, 'bytes');
                // TODO: Upload file to server and get actual path/URL
            };
            
            fileInput.click();
            return;
        }

        const generateBtn = e.target.closest('.generate-audio-btn');
        if (generateBtn) {
            const pronunciationItem = generateBtn.closest('.pronunciation-item');
            const ipaInput = pronunciationItem.querySelector('.ipa-input');
            const lexicalUnit = document.getElementById('lexical-unit').value;
            
            // Allow generation even without IPA - will use word text for TTS
            const ipaValue = ipaInput ? ipaInput.value.trim() : '';
            generateAudio(lexicalUnit, ipaValue, generateBtn.dataset.index);
        }
    });

    // --- Entry-Level Annotation Handlers (document-level, outside senses container) ---
    document.addEventListener('click', function(e) {
        // Only handle entry-level annotation buttons (not sense-level, which are in sensesContainer)
        const target = e.target.closest('.add-annotation-btn, .remove-annotation-btn, .add-annotation-language-btn');
        if (!target) return;
        
        // Check if this is an entry-level annotation (not inside senses-container)
        if (target.closest('#senses-container')) {
            // Let the sensesContainer handler deal with it
            return;
        }
        
        // Handle Add Annotation for entry
        if (target.classList.contains('add-annotation-btn')) {
            const containerType = target.dataset.containerType;
            const index = target.dataset.index;
            addAnnotation(containerType, index);
            return;
        }
        
        // Handle Remove Annotation for entry
        if (target.classList.contains('remove-annotation-btn')) {
            const annotationItem = target.closest('.annotation-item');
            const containerType = target.dataset.containerType;
            const index = target.dataset.index;
            if (annotationItem && confirm('Are you sure you want to remove this annotation?')) {
                removeAnnotation(annotationItem, containerType, index);
            }
            return;
        }
        
        // Handle Add Language for entry annotations
        if (target.classList.contains('add-annotation-language-btn')) {
            addAnnotationLanguage(target);
            return;
        }
    });

    if (sensesContainer) {
        sensesContainer.addEventListener('click', function(e) {
            const removeSenseBtn = e.target.closest('.remove-sense-btn');
            if (removeSenseBtn) {
                const senseItem = removeSenseBtn.closest('.sense-item');
                if (senseItem && confirm('Are you sure you want to remove this sense and all its examples?')) {
                    const senseId = senseItem.querySelector('[name*=".id"]')?.value || 'unknown';
                    console.log('[SENSE DELETION] Removing sense:', senseId);
                    console.log('[SENSE DELETION] Sense count before removal:', document.querySelectorAll('.sense-item').length);
                    
                    senseItem.remove();
                    
                    console.log('[SENSE DELETION] Sense count after removal:', document.querySelectorAll('.sense-item').length);
                    console.log('[SENSE DELETION] Remaining sense IDs:', 
                        Array.from(document.querySelectorAll('[name*="senses["][name*=".id"]'))
                            .map(input => input.value));
                    
                    reindexSenses();
                    // The MutationObserver will automatically trigger updateGrammaticalCategoryInheritance.
                }
                return;
            }
            
            // Handle move sense up button
            const moveSenseUpBtn = e.target.closest('.move-sense-up');
            if (moveSenseUpBtn) {
                const senseItem = moveSenseUpBtn.closest('.sense-item');
                const prevSenseItem = senseItem.previousElementSibling;
                if (prevSenseItem && prevSenseItem.classList.contains('sense-item')) {
                    sensesContainer.insertBefore(senseItem, prevSenseItem);
                    reindexSenses();
                    showToast('Sense moved up successfully', 'success');
                }
                return;
            }
            
            // Handle move sense down button
            const moveSenseDownBtn = e.target.closest('.move-sense-down');
            if (moveSenseDownBtn) {
                const senseItem = moveSenseDownBtn.closest('.sense-item');
                const nextSenseItem = senseItem.nextElementSibling;
                if (nextSenseItem && nextSenseItem.classList.contains('sense-item')) {
                    sensesContainer.insertBefore(nextSenseItem, senseItem);
                    reindexSenses();
                    showToast('Sense moved down successfully', 'success');
                }
                return;
            }

            // --- Illustration Handlers (Add / Upload / Labels) ---
            const addIllustrationBtn = e.target.closest('.add-illustration-btn');
            if (addIllustrationBtn) {
                const senseIndex = addIllustrationBtn.dataset.senseIndex;
                const container = addIllustrationBtn.closest('.sense-item')?.querySelector('.illustrations-container');
                if (!container) return;

                const illustrationIndex = container.querySelectorAll('.illustration-item').length;
                const card = document.createElement('div');
                card.className = 'illustration-item card mb-3';
                card.dataset.illustrationIndex = illustrationIndex;
                card.innerHTML = `
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="mb-0"><i class="fas fa-image"></i> Illustration ${illustrationIndex + 1}</h6>
                            <button type="button" class="btn btn-sm btn-outline-danger remove-illustration-btn" title="Remove illustration">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Image Path/URL</label>
                            <div class="input-group">
                                <input type="text" class="form-control illustration-href" name="senses[${senseIndex}].illustrations[${illustrationIndex}].href" placeholder="images/photo.jpg or https://example.com/image.jpg" readonly>
                                <button class="btn btn-outline-secondary upload-illustration-btn" type="button" data-sense-index="${senseIndex}" data-illustration-index="${illustrationIndex}" title="Upload image file">
                                    <i class="fas fa-upload"></i> Upload Image
                                </button>
                            </div>
                            <div class="form-text">Relative path (e.g., images/photo.jpg) or absolute URL</div>
                        </div>
                        <div class="mb-3 image-preview-container" style="display:none;"></div>
                        <div class="illustration-labels">
                            <label class="form-label">Labels/Captions (Multilingual)</label>
                            <div class="multilingual-forms illustration-label-forms"></div>
                            <button type="button" class="btn btn-sm btn-outline-primary add-illustration-label-language-btn mt-1" data-sense-index="${senseIndex}" data-illustration-index="${illustrationIndex}" title="Add caption in another language">
                                <i class="fas fa-plus"></i> Add Caption Language
                            </button>
                        </div>
                    </div>
                `;

                const placeholder = container.querySelector('.no-illustrations');
                if (placeholder) placeholder.remove();

                container.appendChild(card);
                return;
            }

            const uploadIllustrationBtn = e.target.closest('.upload-illustration-btn');
            if (uploadIllustrationBtn) {
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.accept = 'image/*';

                fileInput.onchange = async (ev) => {
                    const file = ev.target.files[0];
                    if (!file) return;
                    const senseIndex = uploadIllustrationBtn.dataset.senseIndex;
                    const illustrationIndex = uploadIllustrationBtn.dataset.illustrationIndex;

                    const senseItem = uploadIllustrationBtn.closest('.sense-item');
                    const hrefInput = senseItem.querySelector(`.illustration-item[data-illustration-index="${illustrationIndex}"] .illustration-href`);
                    const previewContainer = senseItem.querySelector(`.illustration-item[data-illustration-index="${illustrationIndex}"] .image-preview-container`);

                    // Upload image to server
                    try {
                        const form = new FormData();
                        form.append('image_file', file);

                        const resp = await fetch('/api/illustration/upload', {
                            method: 'POST',
                            body: form
                        });

                        const data = await resp.json();
                        if (!resp.ok || !data.success) {
                            showToast('Image upload failed: ' + (data.message || resp.statusText), 'error');
                            return;
                        }

                        const filename = data.filename;
                        const path = `images/${filename}`;

                        if (hrefInput) hrefInput.value = path;

                        if (previewContainer) {
                            previewContainer.style.display = 'block';
                            previewContainer.innerHTML = `<img src="/static/${path}" class="img-thumbnail illustration-preview" style="max-width:300px;max-height:200px;" alt="Illustration preview" onerror="this.style.display='none';">`;
                        }

                    } catch (err) {
                        console.error('Image upload failed', err);
                        showToast('Image upload failed', 'error');
                    }
                };

                fileInput.click();
                return;
            }

            const addIllustrationLabelBtn = e.target.closest('.add-illustration-label-language-btn');
            if (addIllustrationLabelBtn) {
                const senseIndex = addIllustrationLabelBtn.dataset.senseIndex;
                const illustrationIndex = addIllustrationLabelBtn.dataset.illustrationIndex;
                const container = addIllustrationLabelBtn.closest('.illustration-item')?.querySelector('.illustration-label-forms');
                if (!container) return;

                const languageOptions = Array.from(document.querySelectorAll('select.language-select option')).map(o => ({code: o.value, label: o.textContent}));
                const existing = Array.from(container.querySelectorAll('.language-form-group')).map(g => g.dataset.lang);
                const available = languageOptions.filter(l => !existing.includes(l.code));
                const newLang = available.length ? available[0].code : 'en';

                const div = document.createElement('div');
                div.className = 'language-form-group mb-2 border rounded p-2';
                div.dataset.lang = newLang;
                div.innerHTML = `
                    <div class="row align-items-center">
                        <div class="col-md-3"><span class="badge bg-secondary">${newLang}</span></div>
                        <div class="col-md-9">
                            <div class="d-flex align-items-center">
                                <input type="text" class="form-control form-control-sm illustration-label-text" name="senses[${senseIndex}].illustrations[${illustrationIndex}].label.${newLang}" placeholder="Caption in ${newLang}">
                                <button type="button" class="btn btn-sm btn-outline-danger remove-illustration-label-language-btn ms-2" title="Remove this language"><i class="fas fa-times"></i></button>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(div);
                return;
            }

            const removeIllustrationLabelBtn = e.target.closest('.remove-illustration-label-language-btn');
            if (removeIllustrationLabelBtn) {
                const form = removeIllustrationLabelBtn.closest('.language-form-group');
                if (form && confirm('Remove this caption language?')) form.remove();
                return;
            }
            
            const addExampleBtn = e.target.closest('.add-example-btn');
            if (addExampleBtn) {
                const senseIndex = addExampleBtn.dataset.senseIndex;
                addExample(senseIndex);
                addExampleBtn.closest('.no-examples')?.remove(); // Remove the placeholder if it exists.
                return;
            }

            const removeExampleBtn = e.target.closest('.remove-example-btn');
            if (removeExampleBtn) {
                const exampleItem = removeExampleBtn.closest('.example-item');
                const senseIndex = removeExampleBtn.dataset.senseIndex;
                if (exampleItem && confirm('Are you sure you want to remove this example?')) {
                    const examplesContainer = exampleItem.parentElement;
                    exampleItem.remove();
                    reindexExamples(senseIndex);

                    if (examplesContainer.children.length === 0) {
                        examplesContainer.innerHTML = `
                            <div class="no-examples text-center text-muted py-3 border rounded">
                                <p>No examples added yet</p>
                                <button type="button" class="btn btn-sm btn-outline-primary add-example-btn" data-sense-index="${senseIndex}">
                                    <i class="fas fa-plus"></i> Add Example
                                </button>
                            </div>`;
                    }
                }
            }

            // --- Subsense Handlers (LIFT 0.13 - Day 22) ---
            const addSubsenseBtn = e.target.closest('.add-subsense-btn');
            if (addSubsenseBtn) {
                const senseIndex = addSubsenseBtn.dataset.senseIndex;
                addSubsense(senseIndex);
                // Remove placeholder if exists
                const subsensesContainer = document.querySelector(`.subsenses-container[data-sense-index="${senseIndex}"]`);
                subsensesContainer?.querySelector('.no-subsenses')?.remove();
                return;
            }

            const removeSubsenseBtn = e.target.closest('.remove-subsense-btn');
            if (removeSubsenseBtn) {
                const subsenseItem = removeSubsenseBtn.closest('.subsense-item');
                const senseIndex = removeSubsenseBtn.dataset.senseIndex;
                if (subsenseItem && confirm('Are you sure you want to remove this subsense?')) {
                    const subsensesContainer = subsenseItem.parentElement;
                    subsenseItem.remove();
                    reindexSubsenses(senseIndex);

                    // Show placeholder if no subsenses remain
                    if (subsensesContainer.children.length === 0) {
                        subsensesContainer.innerHTML = `
                            <div class="no-subsenses text-center text-muted py-2 border border-success border-opacity-25 rounded">
                                <p class="mb-2"><small>No subsenses yet. Add subsenses to create more specific meanings under this sense.</small></p>
                            </div>`;
                    }
                }
                return;
            }

            const addNestedSubsenseBtn = e.target.closest('.add-nested-subsense-btn');
            if (addNestedSubsenseBtn) {
                const senseIndex = addNestedSubsenseBtn.dataset.senseIndex;
                const parentSubsenseIndex = addNestedSubsenseBtn.dataset.subsenseIndex;
                addNestedSubsense(senseIndex, parentSubsenseIndex);
                return;
            }

            // --- LIFT 0.13: Reversal Handlers (Day 24-25) ---
            const addReversalBtn = e.target.closest('.add-reversal-btn');
            if (addReversalBtn) {
                const senseIndex = addReversalBtn.dataset.senseIndex;
                addReversal(senseIndex);
                return;
            }

            const removeReversalBtn = e.target.closest('.remove-reversal-btn');
            if (removeReversalBtn) {
                const reversalItem = removeReversalBtn.closest('.reversal-item');
                const senseIndex = removeReversalBtn.dataset.senseIndex;
                if (reversalItem && confirm('Are you sure you want to remove this reversal?')) {
                    removeReversal(reversalItem, senseIndex);
                }
                return;
            }
            
            // --- LIFT 0.13: Annotation Handlers (Day 26-27) ---
            const addAnnotationBtn = e.target.closest('.add-annotation-btn');
            if (addAnnotationBtn) {
                const containerType = addAnnotationBtn.dataset.containerType; // "entry" or "sense"
                const index = addAnnotationBtn.dataset.index;
                addAnnotation(containerType, index);
                return;
            }
            
            const removeAnnotationBtn = e.target.closest('.remove-annotation-btn');
            if (removeAnnotationBtn) {
                const annotationItem = removeAnnotationBtn.closest('.annotation-item');
                const containerType = removeAnnotationBtn.dataset.containerType;
                const index = removeAnnotationBtn.dataset.index;
                if (annotationItem && confirm('Are you sure you want to remove this annotation?')) {
                    removeAnnotation(annotationItem, containerType, index);
                }
                return;
            }
            
            // --- Annotation Add Language Button ---
            const addAnnotationLanguageBtn = e.target.closest('.add-annotation-language-btn');
            if (addAnnotationLanguageBtn) {
                addAnnotationLanguage(addAnnotationLanguageBtn);
                return;
            }
            
            // --- Literal Meaning Add Language Button ---
            const addLiteralMeaningBtn = e.target.closest('.add-literal-meaning-language-btn');
            if (addLiteralMeaningBtn) {
                addCustomFieldLanguage(addLiteralMeaningBtn, 'literal-meaning');
                return;
            }
            
            // --- Exemplar Add Language Button ---
            const addExemplarBtn = e.target.closest('.add-exemplar-language-btn');
            if (addExemplarBtn) {
                addCustomFieldLanguage(addExemplarBtn, 'exemplar');
                return;
            }
            
            // --- Scientific Name Add Language Button ---
            const addScientificNameBtn = e.target.closest('.add-scientific-name-language-btn');
            if (addScientificNameBtn) {
                addCustomFieldLanguage(addScientificNameBtn, 'scientific-name');
                return;
            }

            // --- Sense Relations Handlers ---
            const addSenseRelationBtn = e.target.closest('.add-sense-relation-btn');
            if (addSenseRelationBtn) {
                const senseIndex = addSenseRelationBtn.dataset.senseIndex;
                addSenseRelation(senseIndex);
                // Remove placeholder if exists
                const relationsContainer = document.querySelector(`.sense-relations-container[data-sense-index="${senseIndex}"]`);
                relationsContainer?.querySelector('.no-sense-relations')?.remove();
                return;
            }

            const removeSenseRelationBtn = e.target.closest('.remove-sense-relation-btn');
            if (removeSenseRelationBtn) {
                const relationItem = removeSenseRelationBtn.closest('.sense-relation-item');
                const senseIndex = removeSenseRelationBtn.dataset.senseIndex;
                const relationIndex = removeSenseRelationBtn.dataset.relationIndex;
                if (relationItem && confirm('Are you sure you want to remove this sense relation?')) {
                    const relationsContainer = relationItem.parentElement;
                    relationItem.remove();
                    reindexSenseRelations(senseIndex);

                    // Show placeholder if no relations remain
                    if (relationsContainer.children.length === 0) {
                        relationsContainer.innerHTML = `
                            <div class="no-sense-relations text-center text-muted py-2 border border-warning border-opacity-25 rounded">
                                <p class="mb-2"><small>No sense relations yet. Add relations to link this sense to related meanings.</small></p>
                            </div>`;
                    }
                }
                return;
            }
        });
    }

    // --- Audio Modal Handling ---
    const audioPreviewModalEl = document.getElementById('audioPreviewModal');
    const audioPreviewModal = audioPreviewModalEl ? new bootstrap.Modal(audioPreviewModalEl) : null;

    document.getElementById('save-audio-btn')?.addEventListener('click', function() {
        const audioPlayer = document.getElementById('audio-preview-player');
        const audioSrc = audioPlayer.src;
        const index = audioPlayer.dataset.pronunciationIndex;
        const audioFileInput = document.querySelector(`input[name="pronunciations[${index}].audio_file"]`);

        if (audioFileInput) {
            // Assuming the URL path contains the filename we want to save.
            audioFileInput.value = audioSrc.split('/').pop();
        }
        audioPreviewModal?.hide();
    });
});


/**
 * Validates the entire form, highlighting errors and optionally showing a summary modal.
 * @param {boolean} showSummaryModal - If true, displays a modal with a list of validation errors.
 * @returns {boolean} - True if the form is valid, false otherwise.
 */
function validateForm(showSummaryModal = false) {
    console.log('[validateForm] Called with showSummaryModal:', showSummaryModal);
    const errors = [];
    let isValid = true;

    // Helper to invalidate a field and add an error message
    const invalidate = (element, message) => {
        if (element) {
            element.classList.add('is-invalid');
            const feedback = element.parentElement.querySelector('.invalid-feedback') || document.createElement('div');
            feedback.className = 'invalid-feedback';
            feedback.textContent = message;
            if (!feedback.parentElement) {
                element.parentElement.appendChild(feedback);
            }
        }
        errors.push(message);
        isValid = false;
    };

    // Clear previous validation
    document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

    // Validate Lexical Unit (check all language inputs, at least one must have a value)
    const lexicalUnitInputs = document.querySelectorAll('.lexical-unit-text');
    const hasLexicalUnit = Array.from(lexicalUnitInputs).some(input => input.value.trim());
    if (!hasLexicalUnit && lexicalUnitInputs.length > 0) {
        // Mark the first input as invalid
        invalidate(lexicalUnitInputs[0], 'Lexical Unit is required in at least one language.');
    }

    // Validate Part of Speech (only if required by inheritance logic)
    const partOfSpeechEl = document.getElementById('part-of-speech');
    if (partOfSpeechEl && partOfSpeechEl.required && !partOfSpeechEl.value) {
        invalidate(partOfSpeechEl, 'Part of Speech is required due to sense discrepancies.');
    }

    // Validate Senses
    const senses = document.querySelectorAll('.sense-item');
    if (senses.length === 0) {
        errors.push('At least one sense is required.');
        isValid = false;
        // Visually indicate the error on the senses container or a related element
        document.getElementById('senses-section-header')?.classList.add('text-danger');
    } else {
        document.getElementById('senses-section-header')?.classList.remove('text-danger');
        
        senses.forEach((sense, index) => {
            // Check for multilingual definition fields
            const definitionForms = sense.querySelectorAll('.definition-forms .language-form');
            let hasValidDefinition = false;
            
            if (definitionForms.length > 0) {
                // Check each language form for a valid definition
                // IMPORTANT: Source language definitions are COMPLETELY OPTIONAL!
                // We just need ANY language with content
                definitionForms.forEach(form => {
                    const textareaEl = form.querySelector('.definition-text');
                    
                    // Check if ANY language has content (source or target)
                    if (textareaEl && textareaEl.value.trim()) {
                        hasValidDefinition = true;
                    }
                });
                
                // If no valid definition found, mark the first textarea as invalid
                if (!hasValidDefinition) {
                    const firstTextarea = sense.querySelector('.definition-forms .language-form:first-child .definition-text');
                    if (firstTextarea) {
                        invalidate(firstTextarea, `Sense ${index + 1}: Definition is required in at least one language.`);
                    } else {
                        errors.push(`Sense ${index + 1}: Definition is required in at least one language.`);
                        isValid = false;
                    }
                }
            } else {
                // Fallback to old structure (should not happen with updated template)
                const definitionEl = sense.querySelector(`textarea[name="senses[${index}].definition"]`);
                if (definitionEl && !definitionEl.value.trim()) {
                    invalidate(definitionEl, `Sense ${index + 1}: Definition is required.`);
                } else if (!definitionEl) {
                    errors.push(`Sense ${index + 1}: Definition field not found.`);
                    isValid = false;
                }
            }

            // Validate Examples
            sense.querySelectorAll('.example-item').forEach((example, exIndex) => {
                const exampleTextEl = example.querySelector(`textarea[name*="examples"][name*="text"]`);
                if (exampleTextEl && !exampleTextEl.value.trim()) {
                    invalidate(exampleTextEl, `Sense ${index + 1}, Example ${exIndex + 1}: Example text is required.`);
                }
            });
        });
    }

    // Show summary if requested
    if (showSummaryModal) {
        console.log('[validateForm] Showing feedback, isValid:', isValid, 'errors:', errors);
        
        if (!isValid) {
            // Form has errors - show them in modal for detailed review
            const errorsList = document.getElementById('validation-errors-list');
            const validationModalEl = document.getElementById('validationModal');
            
            if (!validationModalEl) {
                console.error('[validateForm] validationModal element not found');
                showToast(`Form has ${errors.length} validation error(s). Check the form for details.`, 'error');
                return isValid;
            }
            
            if (errorsList) {
                errorsList.innerHTML = errors.map(error => `<li class="text-danger">${error}</li>`).join('');
                const modalHeader = validationModalEl.querySelector('.modal-header');
                const modalTitle = validationModalEl.querySelector('.modal-title');
                if (modalHeader) modalHeader.className = 'modal-header bg-danger text-white';
                if (modalTitle) modalTitle.textContent = 'Validation Errors';
                const validationModal = new bootstrap.Modal(validationModalEl);
                validationModal.show();
            } else {
                console.error('[validateForm] validation-errors-list element not found');
                showToast(`Form has ${errors.length} validation error(s). Check the form for details.`, 'error');
            }
        } else {
            // Form is valid - show unobtrusive success toast
            showToast('✓ Form validation passed! No errors found.', 'success');
        }
    } else {
        console.log('[validateForm] isValid:', isValid, 'showSummaryModal:', showSummaryModal);
    }

    return isValid;
}


/**
 * Serializes and submits the form data via AJAX with improved error handling.
 * Now uses LIFT XML serialization instead of JSON.
 */
async function submitForm() {
    const form = document.getElementById('entry-form');
    if (!form) {
        console.error('Form not found');
        return;
    }

    const saveBtn = document.getElementById('save-btn');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    saveBtn.disabled = true;
    
    // Add a progress indicator
    const progressContainer = document.createElement('div');
    progressContainer.className = 'progress mt-2';
    progressContainer.innerHTML = '<div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>';
    saveBtn.parentNode.appendChild(progressContainer);
    const progressBar = progressContainer.querySelector('.progress-bar');
    
    try {
        // Update progress
        progressBar.style.width = '10%';
        progressBar.textContent = 'Preparing data...';

        // Check if XML serializer is available
        if (!window.xmlSerializer) {
            throw new Error('LIFT XML Serializer is not loaded.');
        }

        // Serialize form to JSON first
        const formData = await window.FormSerializer.serializeFormToJSONSafe(form, {
            includeEmpty: false
        });

        // Normalize senses and refresh relations directly from DOM to avoid stale values before XML generation
        formData.senses = normalizeIndexedArray(formData.senses);
        applySenseRelationsFromDom(form, formData, normalizeIndexedArray);
        
        console.log('[FORM SUBMIT] Form data serialized to JSON');
        
        // Update progress
        progressBar.style.width = '30%';
        progressBar.textContent = 'Generating LIFT XML...';
        
        // Ensure formData has an id so older/cached serializers don't throw
        if (!formData.id) {
            let tempId;
            if (window.xmlSerializer && typeof window.xmlSerializer.generateEntryId === 'function') {
                try {
                    tempId = window.xmlSerializer.generateEntryId();
                } catch (e) {
                    tempId = null;
                }
            }
            if (!tempId) {
                tempId = `temp-${Date.now()}-${Math.floor(Math.random()*10000)}`;
            }
            formData.id = tempId;
            console.warn(`[FORM SUBMIT] No entry id in formData; assigned temporary id: ${formData.id}`);
        }

        // Generate LIFT XML directly from form data (serializer now handles snake_case)
        let xmlString;
        try {
            console.debug('[FORM SUBMIT] Before serializeEntry - formData.id =', formData.id, 'xmlSerializer.generateEntryId =', typeof (window.xmlSerializer && window.xmlSerializer.generateEntryId));
            xmlString = window.xmlSerializer.serializeEntry(formData);
            console.log('[FORM SUBMIT] LIFT XML generated successfully');
            console.log('[FORM SUBMIT] XML Preview:', xmlString.substring(0, 500) + '...');
        } catch (xmlError) {
            throw new Error(`XML generation failed: ${xmlError.message}`);
        }
        
        // Validate XML if needed
        const skipValidationCheckbox = document.getElementById('skip-validation-checkbox');
        const skipValidation = skipValidationCheckbox && skipValidationCheckbox.checked;
        
        // Update progress
        progressBar.style.width = '50%';
        progressBar.textContent = 'Sending to server...';
        
        const entryId = form.querySelector('input[name="id"]')?.value?.trim();
        const apiUrl = entryId ? `/api/xml/entries/${entryId}` : '/api/xml/entries';
        const apiMethod = entryId ? 'PUT' : 'POST';
        
        // Debug: Log sense count in XML being sent
        const senseMatchesBefore = xmlString.match(/<sense\s+/g);
        const senseCountBefore = senseMatchesBefore ? senseMatchesBefore.length : 0;
        console.log(`[FORM SUBMIT] About to send XML to ${apiUrl} with ${senseCountBefore} senses`);
        
        console.log(`Submitting XML to URL: ${apiUrl}, Method: ${apiMethod}`);
        
        // Set a timeout for the fetch request
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
        
        const response = await fetch(apiUrl, {
            method: apiMethod,
            headers: {
                'Content-Type': 'application/xml',
                'Accept': 'application/json'
            },
            body: xmlString,
            signal: controller.signal
        });
        
        // Clear the timeout
        clearTimeout(timeoutId);
        
        // Update progress
        progressBar.style.width = '80%';
        progressBar.textContent = 'Processing response...';
        
        const responseData = await response.json();
        
        if (!response.ok) {
            // Handle validation errors from server
            if (responseData.validation_errors && Array.isArray(responseData.validation_errors)) {
                // Display structured validation errors
                const errorList = responseData.validation_errors.map(err => `• ${err}`).join('\n');
                throw new Error(`Validation failed:\n${errorList}`);
            } else {
                // Extract a more detailed error message if available
                const errorMessage = responseData.error || responseData.message || `HTTP error! Status: ${response.status}`;
                throw new Error(errorMessage);
            }
        }
        
        // Update progress
        progressBar.style.width = '100%';
        progressBar.textContent = 'Complete!';
        
        // Redirect after successful save
        const idForRedirect = responseData.entry_id || entryId;
        if (idForRedirect) {
            window.location.href = `/entries/${idForRedirect}?status=saved`;
        } else {
            console.warn("No entry ID found for redirect. Redirecting to entries list.");
            window.location.href = '/entries';
        }
        
    } catch (error) {
        console.error('Submission Error:', error);
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
        
        // Update progress to show error
        progressBar.style.width = '100%';
        progressBar.className = 'progress-bar bg-danger';
        progressBar.textContent = 'Error!';
        
        // Show detailed error message (preserve newlines in toast)
        const errorDiv = document.createElement('div');
        errorDiv.style.whiteSpace = 'pre-wrap';
        errorDiv.textContent = error.message;
        showToast(errorDiv.innerHTML || `Error saving entry: ${error.message}`, 'error');
        
        // Remove progress bar after delay
        setTimeout(() => {
            progressContainer.remove();
        }, 5000);
    }
}

// --- Dynamic Element Creation Functions ---

/**
 * Adds a new pronunciation field group to the form.
 */
function addPronunciation() {
    const container = document.getElementById('pronunciation-container');
    const templateEl = document.getElementById('pronunciation-template');
    if (!container || !templateEl) return;

    const newIndex = container.querySelectorAll('.pronunciation-item').length;
    const template = templateEl.innerHTML.replace(/INDEX/g, newIndex);

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = template;
    const newItem = tempDiv.firstElementChild;

    container.appendChild(newItem);

    // Initialize IPA validation on the new input field
    const ipaInput = newItem.querySelector('.ipa-input');
    if (ipaInput && typeof initializeIPAValidation === 'function') {
        // Assuming initializeIPAValidation can be called to set up a single element or re-scan
        initializeIPAValidation(); // Re-run to catch new inputs
    }
}

/**
 * Adds a new sense field group to the form.
 */
async function addSense() {
    const container = document.getElementById('senses-container');
    const templateEl = document.getElementById('sense-template');
    if (!container || !templateEl) return;

    // Count only real senses, excluding the default template
    const newIndex = container.querySelectorAll('.sense-item:not(#default-sense-template):not(.default-sense-template)').length;
    const newNumber = newIndex + 1;

    let template = templateEl.innerHTML
        .replace(/INDEX/g, newIndex)
        .replace(/NUMBER/g, newNumber);

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = template;
    const newSenseElement = tempDiv.firstElementChild;
    container.appendChild(newSenseElement);

    // Initialize any Select2 elements within the new sense
    $(newSenseElement).find('.select2-tags').select2({
        theme: 'bootstrap-5',
        tags: true,
        tokenSeparators: [',', ' '],
        placeholder: 'Enter or select values...'
    });

    // Populate the grammatical info select for the new sense
    const grammaticalSelect = newSenseElement.querySelector('.dynamic-grammatical-info');
    if (grammaticalSelect && window.rangesLoader) {
        await window.rangesLoader.populateSelect(grammaticalSelect, 'grammatical-info', {
            emptyOption: 'Select part of speech'
        });
        // The event listener for 'change' is handled by delegation on the form, so no need to add one here.
    }
    
    // Populate semantic domain select for the new sense (sense-level)
    const semanticDomainSelect = newSenseElement.querySelector('select[name*=".domain_type"]');
    if (semanticDomainSelect && window.rangesLoader) {
        await window.rangesLoader.populateSelect(semanticDomainSelect, 'semantic-domain-ddp4', {
            emptyOption: 'Select semantic domain(s)'
        });
    }
    
    // Populate usage type select for the new sense (sense-level)
    const usageTypeSelect = newSenseElement.querySelector('select[name*=".usage_type"]');
    if (usageTypeSelect && window.rangesLoader) {
        await window.rangesLoader.populateSelect(usageTypeSelect, 'usage-type', {
            emptyOption: 'Select usage type(s)'
        });
    }
    
    // The MutationObserver will handle calling updateGrammaticalCategoryInheritance.
}


/**
 * Adds a new example field group to a specific sense.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function addExample(senseIndex) {
    const examplesContainer = document.querySelector(`.sense-item[data-sense-index="${senseIndex}"] .examples-container`);
    const templateEl = document.getElementById('example-template');
    if (!examplesContainer || !templateEl) return;

    const newIndex = examplesContainer.querySelectorAll('.example-item').length;
    const newNumber = newIndex + 1;

    let template = templateEl.innerHTML
        .replace(/SENSE_INDEX/g, senseIndex)
        .replace(/EXAMPLE_INDEX/g, newIndex)
        .replace(/NUMBER/g, newNumber);

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = template;
    examplesContainer.appendChild(tempDiv.firstElementChild);
}

/**
 * Adds a new sense relation field group to a specific sense.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function addSenseRelation(senseIndex) {
    const relationsContainer = document.querySelector(`.sense-relations-container[data-sense-index="${senseIndex}"]`);
    if (!relationsContainer) return;

    const newIndex = relationsContainer.querySelectorAll('.sense-relation-item').length;
    const newNumber = newIndex + 1;

    // Create new sense relation HTML dynamically since there's no template
    const newRelationHTML = `
        <div class="sense-relation-item card mb-3 border-warning" data-relation-index="${newIndex}">
            <div class="card-header bg-warning bg-opacity-10">
                <div class="d-flex justify-content-between align-items-center">
                    <span><i class="fas fa-link"></i> Relation ${newNumber}</span>
                    <button type="button" class="btn btn-sm btn-outline-danger remove-sense-relation-btn"
                            data-sense-index="${senseIndex}" data-relation-index="${newIndex}">
                        <i class="fas fa-trash"></i> Remove
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <label class="form-label">Relation Type</label>
                        <select class="form-control sense-lexical-relation-select dynamic-lift-range"
                                name="senses[${senseIndex}].relations[${newIndex}].type"
                                data-range-id="lexical-relation"
                                data-hierarchical="true"
                                data-searchable="true"
                                required>
                            <option value="">Select type</option>
                        </select>
                        <div class="form-text">Type of semantic relation</div>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Target Sense</label>
                        <div class="alert alert-light mb-2">
                            <i class="fas fa-project-diagram me-2"></i>
                            <strong>No target selected</strong>
                        </div>
                        <input type="hidden"
                               class="sense-relation-ref-hidden"
                               name="senses[${senseIndex}].relations[${newIndex}].ref"
                               value="">
                        <div class="input-group">
                            <input type="text"
                                   class="form-control sense-relation-search-input"
                                   placeholder="Search to change target..."
                                   data-sense-index="${senseIndex}"
                                   data-relation-index="${newIndex}"
                                   autocomplete="off">
                            <button type="button"
                                    class="btn btn-outline-secondary sense-relation-search-btn"
                                    data-sense-index="${senseIndex}"
                                    data-relation-index="${newIndex}">
                                <i class="fas fa-search"></i> Search
                            </button>
                        </div>
                        <div class="form-text">Search by headword to change target entry/sense</div>
                        <div class="sense-relation-search-results"
                             id="sense-search-results-${senseIndex}-${newIndex}"
                             style="display: none; position: relative; z-index: 1000;">
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    relationsContainer.insertAdjacentHTML('beforeend', newRelationHTML);

    // Initialize the new relation's dropdown with range data
    const newSelect = relationsContainer.querySelector(`.sense-relation-item[data-relation-index="${newIndex}"] .sense-lexical-relation-select`);
    if (newSelect && window.rangesLoader) {
        // Use rangesLoader to populate the select with proper range values
        window.rangesLoader.populateSelect(newSelect, 'lexical-relation', {
            emptyOption: 'Select type',
            hierarchical: true,
            searchable: true
        }).catch(err => {
            console.error(`[addSenseRelation] Failed to populate select via rangesLoader:`, err);
        });
    }

    // Initialize the search functionality for the new relation if the sense-relation-search handler exists
    if (window.senseRelationSearchHandler) {
        // The event listeners are already in place to handle the new elements
        console.log(`[addSenseRelation] New relation ${newIndex} added to sense ${senseIndex}`);
    }
}

/**
 * Re-indexes all sense relations for a specific sense after removal.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function reindexSenseRelations(senseIndex) {
    const relationsContainer = document.querySelector(`.sense-relations-container[data-sense-index="${senseIndex}"]`);
    if (!relationsContainer) return;

    const relationItems = relationsContainer.querySelectorAll('.sense-relation-item');
    relationItems.forEach((relation, newIndex) => {
        const oldIndex = relation.dataset.relationIndex;
        if (oldIndex === newIndex.toString()) return;

        // Update visual elements
        relation.querySelector('.card-header span').innerHTML = `<i class="fas fa-link"></i> Relation ${newIndex + 1}`;

        // Update data attribute
        relation.dataset.relationIndex = newIndex;

        // Update all name attributes
        relation.querySelectorAll('[name]').forEach(input => {
            const name = input.getAttribute('name');
            const newName = name.replace(
                new RegExp(`senses\\[${senseIndex}\\]\\.relations\\[${oldIndex}\\]`, 'g'),
                `senses[${senseIndex}].relations[${newIndex}]`
            );
            input.setAttribute('name', newName);
        });

        // Update data-relation-index and other data attributes on buttons and other elements
        relation.querySelectorAll('[data-relation-index]').forEach(btn => {
            btn.dataset.relationIndex = newIndex;
        });

        // Update search input data attributes
        relation.querySelectorAll('.sense-relation-search-input, .sense-relation-search-btn').forEach(el => {
            el.dataset.relationIndex = newIndex;
        });

        // Update search results container ID
        const oldResultsId = `sense-search-results-${senseIndex}-${oldIndex}`;
        const newResultsId = `sense-search-results-${senseIndex}-${newIndex}`;
        const resultsContainer = document.getElementById(oldResultsId);
        if (resultsContainer) {
            resultsContainer.id = newResultsId;
        }
    });
}

/**
 * Adds a new subsense field group to a specific sense (LIFT 0.13 - Day 22).
 * @param {number|string} senseIndex - The index of the parent sense.
 */
async function addSubsense(senseIndex) {
    const subsensesContainer = document.querySelector(`.subsenses-container[data-sense-index="${senseIndex}"]`);
    const templateEl = document.getElementById('subsense-template');
    if (!subsensesContainer || !templateEl) return;

    const newIndex = subsensesContainer.querySelectorAll('.subsense-item').length;
    const newNumber = newIndex + 1;

    let template = templateEl.innerHTML
        .replace(/SENSE_INDEX/g, senseIndex)
        .replace(/SUBSENSE_INDEX/g, newIndex)
        .replace(/NUMBER/g, newNumber);

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = template;
    const newSubsenseElement = tempDiv.firstElementChild;
    subsensesContainer.appendChild(newSubsenseElement);

    // Populate grammatical info select for the new subsense
    const grammaticalSelect = newSubsenseElement.querySelector('.dynamic-grammatical-info');
    if (grammaticalSelect && window.rangesLoader) {
        await window.rangesLoader.populateSelect(grammaticalSelect, 'grammatical-info', {
            emptyOption: 'Select part of speech'
        });
    }
}

/**
 * Adds a nested subsense (subsense within subsense) - recursive support.
 * @param {number|string} senseIndex - The index of the parent sense.
 * @param {number|string} parentSubsenseIndex - The index of the parent subsense.
 */
async function addNestedSubsense(senseIndex, parentSubsenseIndex) {
    const nestedContainer = document.querySelector(
        `.subsense-item[data-subsense-index="${parentSubsenseIndex}"] .nested-subsenses-container`
    );
    const templateEl = document.getElementById('subsense-template');
    if (!nestedContainer || !templateEl) return;

    const newIndex = nestedContainer.querySelectorAll('.subsense-item').length;
    const newNumber = newIndex + 1;

    // For nested subsenses, use a compound index
    const nestedIndexPath = `${parentSubsenseIndex}_${newIndex}`;

    let template = templateEl.innerHTML
        .replace(/SENSE_INDEX/g, senseIndex)
        .replace(/SUBSENSE_INDEX/g, nestedIndexPath)
        .replace(/NUMBER/g, newNumber);

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = template;
    const newSubsenseElement = tempDiv.firstElementChild;
    
    // Clear placeholder text if exists
    if (nestedContainer.textContent.includes('No nested subsenses yet')) {
        nestedContainer.innerHTML = '';
    }
    
    nestedContainer.appendChild(newSubsenseElement);

    // Populate grammatical info select
    const grammaticalSelect = newSubsenseElement.querySelector('.dynamic-grammatical-info');
    if (grammaticalSelect && window.rangesLoader) {
        await window.rangesLoader.populateSelect(grammaticalSelect, 'grammatical-info', {
            emptyOption: 'Select part of speech'
        });
    }
}

/**
 * Re-indexes all subsenses for a specific sense.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function reindexSubsenses(senseIndex) {
    const subsensesContainer = document.querySelector(`.subsenses-container[data-sense-index="${senseIndex}"]`);
    if (!subsensesContainer) return;

    const subsenseItems = subsensesContainer.querySelectorAll(':scope > .subsense-item');
    subsenseItems.forEach((subsense, newIndex) => {
        const oldIndex = subsense.dataset.subsenseIndex;
        if (oldIndex === newIndex.toString()) return;

        // Update visual elements
        subsense.querySelectorAll('small').forEach(small => {
            if (small.textContent.includes('Subsense')) {
                small.innerHTML = `<i class="fas fa-level-down-alt"></i> Subsense ${newIndex + 1}`;
            }
        });

        // Update data attribute
        subsense.dataset.subsenseIndex = newIndex;

        // Update all name attributes
        subsense.querySelectorAll('[name]').forEach(input => {
            const name = input.getAttribute('name');
            const newName = name.replace(
                new RegExp(`senses\\[${senseIndex}\\]\\.subsenses\\[${oldIndex}\\]`),
                `senses[${senseIndex}].subsenses[${newIndex}]`
            );
            input.setAttribute('name', newName);
        });

        // Update data-subsense-index on buttons
        subsense.querySelectorAll('[data-subsense-index]').forEach(btn => {
            btn.dataset.subsenseIndex = newIndex;
        });
    });
}

// --- LIFT 0.13: Reversal Functions (Day 24-25) ---

/**
 * Adds a new reversal to a specific sense.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
async function addReversal(senseIndex) {
    const reversalsContainer = document.querySelector(`.reversals-container[data-sense-index="${senseIndex}"]`);
    const templateEl = document.getElementById('reversal-template');
    if (!reversalsContainer || !templateEl) return;

    const newIndex = reversalsContainer.querySelectorAll('.reversal-item').length;
    const newNumber = newIndex + 1;

    let template = templateEl.innerHTML
        .replace(/SENSE_INDEX/g, senseIndex)
        .replace(/REVERSAL_INDEX/g, newIndex)
        .replace(/NUMBER/g, newNumber);

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = template;
    const newReversalElement = tempDiv.firstElementChild;
    
    // Remove "no reversals" placeholder if exists
    const noReversalsPlaceholder = reversalsContainer.querySelector('.no-reversals');
    if (noReversalsPlaceholder) {
        noReversalsPlaceholder.remove();
    }
    
    reversalsContainer.appendChild(newReversalElement);

    // Populate reversal type select
    const typeSelect = newReversalElement.querySelector('.reversal-type-select');
    if (typeSelect && window.rangesLoader) {
        await window.rangesLoader.populateSelect(typeSelect, 'reversal-type', {
            emptyOption: '-- Select Language --'
        });
    }

    // Populate grammatical info selects
    const grammaticalSelects = newReversalElement.querySelectorAll('.dynamic-grammatical-info');
    grammaticalSelects.forEach(async select => {
        if (window.rangesLoader) {
            await window.rangesLoader.populateSelect(select, 'grammatical-info', {
                emptyOption: '-- Select --'
            });
        }
    });
}

/**
 * Removes a reversal from a specific sense.
 * @param {Element} reversalItem - The reversal item element to remove.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function removeReversal(reversalItem, senseIndex) {
    if (!reversalItem) return;

    const reversalsContainer = reversalItem.closest('.reversals-container');
    reversalItem.remove();

    // If no more reversals, show placeholder
    const remainingReversals = reversalsContainer.querySelectorAll('.reversal-item');
    if (remainingReversals.length === 0) {
        const placeholder = document.createElement('div');
        placeholder.className = 'no-reversals text-center text-muted py-2 border border-info border-opacity-25 rounded';
        placeholder.innerHTML = '<p class="mb-2"><small>No reversals yet. Add reversals for bilingual dictionary support.</small></p>';
        reversalsContainer.appendChild(placeholder);
    } else {
        // Re-index remaining reversals
        reindexReversals(senseIndex);
    }
}

/**
 * Re-indexes all reversals for a specific sense after removal.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function reindexReversals(senseIndex) {
    const reversalsContainer = document.querySelector(`.reversals-container[data-sense-index="${senseIndex}"]`);
    if (!reversalsContainer) return;

    const reversalItems = reversalsContainer.querySelectorAll('.reversal-item');
    reversalItems.forEach((reversal, newIndex) => {
        const oldIndex = reversal.dataset.reversalIndex;
        if (oldIndex === newIndex.toString()) return;

        // Update visual elements
        reversal.querySelector('.card-header span').innerHTML = `<i class="fas fa-language"></i> Reversal ${newIndex + 1}`;

        // Update data attribute
        reversal.dataset.reversalIndex = newIndex;

        // Update all name attributes
        reversal.querySelectorAll('[name]').forEach(input => {
            const name = input.getAttribute('name');
            const newName = name.replace(
                new RegExp(`senses\\[${senseIndex}\\]\\.reversals\\[${oldIndex}\\]`),
                `senses[${senseIndex}].reversals[${newIndex}]`
            );
            input.setAttribute('name', newName);
        });

        // Update data-reversal-index on buttons
        reversal.querySelectorAll('[data-reversal-index]').forEach(btn => {
            btn.dataset.reversalIndex = newIndex;
        });

        // Update collapse target IDs for main element
        const toggleBtn = reversal.querySelector('.toggle-main-btn');
        const collapseDiv = reversal.querySelector('.collapse');
        if (toggleBtn && collapseDiv) {
            const newId = `reversal-main-${senseIndex}-${newIndex}`;
            toggleBtn.setAttribute('data-bs-target', `#${newId}`);
            collapseDiv.id = newId;
        }
    });
}

// --- Re-indexing Functions ---

/**
 * Re-indexes all sense fields after a sense is removed to ensure continuous indices.
 */
function reindexSenses() {
    const senseItems = document.querySelectorAll('#senses-container > .sense-item');
    senseItems.forEach((sense, newIndex) => {
        const oldIndex = sense.dataset.senseIndex;
        if (oldIndex === newIndex.toString()) return; // No change needed

        // Update visual elements - find all headers that contain the sense number
        sense.querySelectorAll('h6').forEach(header => {
            if (header.textContent.includes('Sense')) {
                header.textContent = `Sense ${newIndex + 1}`;
            }
        });
        
        // Also update span elements that contain "Sense" text
        sense.querySelectorAll('span').forEach(span => {
            if (span.textContent.includes('Sense')) {
                span.textContent = `Sense ${newIndex + 1}`;
            }
        });
        
        // Update data attribute
        sense.dataset.senseIndex = newIndex;

        // Update buttons that rely on the index
        sense.querySelectorAll('[data-sense-index]').forEach(btn => {
            btn.dataset.senseIndex = newIndex;
        });

        // Update field names with a more robust approach
        sense.querySelectorAll('[name^="senses["]').forEach(field => {
            const name = field.getAttribute('name');
            field.setAttribute('name', name.replace(new RegExp(`senses\\[${oldIndex}\\]`, 'g'), `senses[${newIndex}]`));
        });
        
        // Update multilingual field indices if the manager exists
        if (window.multilingualSenseFieldsManager) {
            window.multilingualSenseFieldsManager.updateSenseIndices(oldIndex, newIndex);
        }
        
        // Update example buttons and headers
        sense.querySelectorAll('.add-example-btn').forEach(btn => {
            btn.dataset.senseIndex = newIndex;
        });
        
        // Reindex examples within this sense
        reindexExamples(newIndex);
    });
    
    // After reindexing, check if we need to update grammatical inheritance
    if (typeof updateGrammaticalCategoryInheritance === 'function') {
        updateGrammaticalCategoryInheritance();
    }
}

/**
 * Re-indexes example fields within a sense after one is removed.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function reindexExamples(senseIndex) {
    const exampleItems = document.querySelectorAll(`.sense-item[data-sense-index="${senseIndex}"] .example-item`);
    exampleItems.forEach((example, newIndex) => {
        const oldIndexMatch = RegExp(/\[examples\]\[(\d+)\]/).exec(example.querySelector('[name*="[examples]["]')
                                     ?.getAttribute('name'));
        const oldIndex = oldIndexMatch ? oldIndexMatch[1] : null;

        if (oldIndex === null || oldIndex === newIndex.toString()) return;

        // Update visual elements
        example.querySelector('small').textContent = `Example ${newIndex + 1}`;

        // Update remove button
        const removeBtn = example.querySelector('.remove-example-btn');
        if (removeBtn) removeBtn.dataset.exampleIndex = newIndex;

        // FIX: Update field names with a more robust regex.
        // This correctly targets the `examples[<number>]` part of the name.
        example.querySelectorAll('[name*="[examples]["]').forEach(field => {
            const name = field.getAttribute('name');
            field.setAttribute('name', name.replace(`[examples][${oldIndex}]`, `[examples][${newIndex}]`));
        });
    });
}


/**
 * Calls the backend API to generate audio for a pronunciation.
 * @param {string} word - The lexical unit.
 * @param {string} ipa - The IPA transcription.
 * @param {number|string} index - The index of the pronunciation item.
 */
function generateAudio(word, ipa, index) {
    const btn = document.querySelector(`.generate-audio-btn[data-index="${index}"]`);
    if (!btn) return;

    // Check if we have either word or IPA to generate from
    if (!word || word.trim() === '') {
        showToast('Please enter a lexical unit (word) to generate audio', 'warning');
        return;
    }

    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Generating...';
    btn.disabled = true;

    fetch('/api/pronunciations/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                word,
                ipa  // Can be empty - backend will use word text for TTS
            })
        })
        .then(async response => {
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.message || `Audio generation failed with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data.audio_url) {
                throw new Error("API response did not include an audio URL.");
            }
            const audioPlayer = document.getElementById('audio-preview-player');
            audioPlayer.src = data.audio_url;
            audioPlayer.dataset.pronunciationIndex = index;

            const audioPreviewModal = bootstrap.Modal.getOrCreateInstance('#audioPreviewModal');
            audioPreviewModal.show();
        })
        .catch(error => {
            console.error('Error generating audio:', error);
            showToast(`Error generating audio: ${error.message}`, 'error');
        })
        .finally(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        });
}

// =====================
// LIFT 0.13: Annotation Management (Day 26-27)
// =====================

/**
 * Adds a new annotation to entry or sense.
 * @param {string} containerType - "entry" or "sense"
 * @param {number|string} index - The index (0 for entry, sense index for sense)
 */
function addAnnotation(containerType, index) {
    const selector = containerType === 'entry' 
        ? '.annotations-container[data-container-type="entry"]'
        : `.annotations-container[data-container-type="sense"][data-index="${index}"]`;
    
    const annotationsContainer = document.querySelector(selector);
    if (!annotationsContainer) return;

    const newIndex = annotationsContainer.querySelectorAll('.annotation-item').length;
    const newNumber = newIndex + 1;

    // Build name prefix
    const namePrefix = containerType === 'entry' 
        ? `annotations[${newIndex}]`
        : `senses[${index}].annotations[${newIndex}]`;
    
    // Build collapse ID
    const collapseId = containerType === 'entry'
        ? `annotation-content-entry-${newIndex}`
        : `annotation-content-${index}-${newIndex}`;

    // Create new annotation HTML
    const newAnnotationHTML = `
        <div class="annotation-item card mb-3 border-warning" data-annotation-index="${newIndex}">
            <div class="card-header bg-warning bg-opacity-10">
                <div class="d-flex justify-content-between align-items-center">
                    <span><i class="fas fa-tag"></i> Annotation ${newNumber}</span>
                    <button type="button" class="btn btn-sm btn-outline-danger remove-annotation-btn"
                            data-container-type="${containerType}" data-index="${index}" data-annotation-index="${newIndex}">
                        <i class="fas fa-trash"></i> Remove
                    </button>
                </div>
            </div>
            <div class="card-body">
                <!-- Annotation Name (required) -->
                <div class="mb-3">
                    <label class="form-label">Name <span class="text-danger">*</span></label>
                    <input type="text" class="form-control annotation-name-input" 
                           name="${namePrefix}.name"
                           placeholder="e.g., review-status, comment, flagged"
                           required>
                    <small class="form-text text-muted">
                        Common names: review-status, comment, reviewer-comment, approval-status, flagged, priority, needs-revision
                    </small>
                </div>
                
                <!-- Annotation Value (optional) -->
                <div class="mb-3">
                    <label class="form-label">Value</label>
                    <input type="text" class="form-control" 
                           name="${namePrefix}.value"
                           placeholder="e.g., approved, pending, rejected">
                </div>
                
                <!-- Annotation Who (optional) -->
                <div class="mb-3">
                    <label class="form-label">Who</label>
                    <input type="text" class="form-control" 
                           name="${namePrefix}.who"
                           placeholder="e.g., editor@example.com, John Doe">
                    <small class="form-text text-muted">Person or email who created this annotation (will be auto-filled with username when user management is implemented)</small>
                </div>
                
                <!-- Annotation When (auto-populated) -->
                <div class="mb-3">
                    <label class="form-label">When</label>
                    <input type="datetime-local" class="form-control" 
                           name="${namePrefix}.when"
                           value="${new Date().toISOString().slice(0, 16)}"
                           readonly>
                    <small class="form-text text-muted">Timestamp when this annotation was created (auto-generated)</small>
                </div>
                
                <!-- Annotation Content (collapsible) -->
                <div class="annotation-content-section">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <label class="form-label mb-0">Content</label>
                        <button type="button" class="btn btn-sm btn-outline-secondary toggle-content-btn"
                                data-bs-toggle="collapse" 
                                data-bs-target="#${collapseId}">
                            <i class="fas fa-chevron-down"></i>
                        </button>
                    </div>
                    <div class="collapse" id="${collapseId}">
                        <div class="card bg-light">
                            <div class="card-body">
                                <div class="annotation-content-forms">
                                    <div class="input-group mb-2">
                                        <span class="input-group-text">en</span>
                                        <textarea class="form-control" 
                                               name="${namePrefix}.content.en"
                                               data-lang="en"
                                               rows="2"
                                               placeholder="Enter comment or description in English"></textarea>
                                    </div>
                                </div>
                                <button type="button" class="btn btn-sm btn-outline-primary mt-2 add-annotation-language-btn">
                                    <i class="fas fa-plus"></i> Add Language
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = newAnnotationHTML.trim();
    const newAnnotationElement = tempDiv.firstElementChild;
    
    // Remove "no annotations" placeholder if exists
    const noAnnotationsPlaceholder = annotationsContainer.querySelector('.no-annotations');
    if (noAnnotationsPlaceholder) {
        noAnnotationsPlaceholder.remove();
    }
    
    annotationsContainer.appendChild(newAnnotationElement);
}

/**
 * Removes an annotation from entry or sense.
 * @param {Element} annotationItem - The annotation item element to remove.
 * @param {string} containerType - "entry" or "sense"
 * @param {number|string} index - The index (0 for entry, sense index for sense)
 */
function removeAnnotation(annotationItem, containerType, index) {
    if (!annotationItem) return;

    const annotationsContainer = annotationItem.closest('.annotations-container');
    annotationItem.remove();

    // If no more annotations, show placeholder
    const remainingAnnotations = annotationsContainer.querySelectorAll('.annotation-item');
    if (remainingAnnotations.length === 0) {
        const placeholder = document.createElement('div');
        placeholder.className = 'no-annotations text-center text-muted py-3 border border-warning border-opacity-25 rounded';
        const placeholderText = containerType === 'entry'
            ? 'No entry-level annotations yet. Add annotations for editorial workflow (review status, comments, etc.).'
            : 'No annotations yet. Add annotations for editorial workflow (review status, comments, etc.).';
        placeholder.innerHTML = `<p class="mb-2"><small>${placeholderText}</small></p>`;
        annotationsContainer.appendChild(placeholder);
    } else {
        // Re-index remaining annotations
        reindexAnnotations(containerType, index);
    }
}

/**
 * Re-indexes all annotations for entry or sense after removal.
 * @param {string} containerType - "entry" or "sense"
 * @param {number|string} index - The index (0 for entry, sense index for sense)
 */
function reindexAnnotations(containerType, index) {
    const selector = containerType === 'entry' 
        ? '.annotations-container[data-container-type="entry"]'
        : `.annotations-container[data-container-type="sense"][data-index="${index}"]`;
    
    const annotationsContainer = document.querySelector(selector);
    if (!annotationsContainer) return;

    const annotationItems = annotationsContainer.querySelectorAll('.annotation-item');
    annotationItems.forEach((annotation, newIndex) => {
        const oldIndex = annotation.dataset.annotationIndex;
        if (oldIndex === newIndex.toString()) return;

        // Update visual elements
        annotation.querySelector('.card-header span').innerHTML = `<i class="fas fa-tag"></i> Annotation ${newIndex + 1}`;

        // Update data attribute
        annotation.dataset.annotationIndex = newIndex;

        // Build name prefix for replacement
        const oldNamePrefix = containerType === 'entry'
            ? `annotations[${oldIndex}]`
            : `senses[${index}].annotations[${oldIndex}]`;
        
        const newNamePrefix = containerType === 'entry'
            ? `annotations[${newIndex}]`
            : `senses[${index}].annotations[${newIndex}]`;

        // Update all name attributes
        annotation.querySelectorAll('[name]').forEach(input => {
            const name = input.getAttribute('name');
            const newName = name.replace(oldNamePrefix, newNamePrefix);
            input.setAttribute('name', newName);
        });

        // Update data-annotation-index on buttons
        annotation.querySelectorAll('[data-annotation-index]').forEach(btn => {
            btn.dataset.annotationIndex = newIndex;
        });

        // Update collapse target IDs
        const toggleBtn = annotation.querySelector('.toggle-content-btn');
        const collapseDiv = annotation.querySelector('.collapse');
        if (toggleBtn && collapseDiv) {
            const oldCollapseId = collapseDiv.id;
            const newCollapseId = containerType === 'entry'
                ? `annotation-content-entry-${newIndex}`
                : `annotation-content-${index}-${newIndex}`;
            
            collapseDiv.id = newCollapseId;
            toggleBtn.setAttribute('data-bs-target', `#${newCollapseId}`);
        }
    });
}

/**
 * Adds a new language field to an annotation's content section.
 * @param {Element} button - The "Add Language" button element.
 */
function addAnnotationLanguage(button) {
    const contentBody = button.closest('.card-body');
    const formsContainer = contentBody.querySelector('.annotation-content-forms');
    
    if (!formsContainer) return;
    
    // Prompt for language code
    const langCode = prompt('Enter language code (e.g., fr, es, de):');
    if (!langCode || !langCode.trim()) return;
    
    const sanitizedLang = langCode.trim().toLowerCase();
    
    // Check if language already exists
    const existingLangs = Array.from(formsContainer.querySelectorAll('.input-group-text')).map(span => span.textContent.trim());
    if (existingLangs.includes(sanitizedLang)) {
        alert(`Language "${sanitizedLang}" already exists.`);
        return;
    }
    
    // Get the name prefix from an existing textarea
    const existingTextarea = formsContainer.querySelector('textarea');
    if (!existingTextarea) return;
    
    const existingName = existingTextarea.getAttribute('name');
    const nameBase = existingName.substring(0, existingName.lastIndexOf('.') + 1);
    
    // Create new language input
    const newLangHTML = `
        <div class="input-group mb-2">
            <span class="input-group-text">${sanitizedLang}</span>
            <textarea class="form-control" 
                   name="${nameBase}${sanitizedLang}"
                   data-lang="${sanitizedLang}"
                   rows="2"
                   placeholder="Enter comment or description in ${sanitizedLang}"></textarea>
            <button type="button" class="btn btn-outline-danger remove-annotation-language-btn" title="Remove this language">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    formsContainer.insertAdjacentHTML('beforeend', newLangHTML);
}

// Event listener for removing language fields from annotations
document.addEventListener('click', (e) => {
    const removeLanguageBtn = e.target.closest('.remove-annotation-language-btn');
    if (removeLanguageBtn) {
        const inputGroup = removeLanguageBtn.closest('.input-group');
        if (inputGroup && confirm('Remove this language?')) {
            inputGroup.remove();
        }
    }
});

/**
 * Add a language field to a custom field (literal-meaning, exemplar, scientific-name).
 * @param {Element} button - The "Add Language" button element.
 * @param {string} fieldType - The type of custom field ('literal-meaning', 'exemplar', 'scientific-name')
 */
function addCustomFieldLanguage(button, fieldType) {
    // Find the container for this field type
    const formsContainer = button.closest('.mb-3, .card-body').querySelector(`.${fieldType}-forms`);
    
    if (!formsContainer) {
        console.error(`Could not find .${fieldType}-forms container`);
        return;
    }
    
    // Prompt for language code
    const langCode = prompt('Enter language code (e.g., en, fr, es):');
    if (!langCode || !langCode.trim()) return;
    
    const sanitizedLang = langCode.trim().toLowerCase();
    
    // Check if language already exists
    const existingLangSelects = formsContainer.querySelectorAll('select.language-selector');
    for (const select of existingLangSelects) {
        if (select.value === sanitizedLang) {
            alert(`Language "${sanitizedLang}" already exists.`);
            return;
        }
    }
    
    // Determine name prefix based on field type and context (entry or sense)
    let namePrefix = '';
    const senseCard = button.closest('.sense-card');
    
    if (senseCard) {
        // This is a sense-level field
        const senseIndex = senseCard.dataset.senseIndex;
        if (fieldType === 'exemplar') {
            namePrefix = `senses[${senseIndex}].exemplar.`;
        } else if (fieldType === 'scientific-name') {
            namePrefix = `senses[${senseIndex}].scientific-name.`;
        }
    } else {
        // This is an entry-level field
        if (fieldType === 'literal-meaning') {
            namePrefix = `literal-meaning.`;
        }
    }
    
    // Get available languages for the selector
    const languagesJson = document.getElementById('project-languages-data')?.textContent;
    let languageOptions = [];
    if (languagesJson) {
        try {
            const languages = JSON.parse(languagesJson);
            languageOptions = languages.map(([code, label]) => 
                `<option value="${code}" ${code === sanitizedLang ? 'selected' : ''}>${label}</option>`
            ).join('');
        } catch (e) {
            console.error('Failed to parse project languages:', e);
        }
    }
    
    // Create new language form group
    const removeButtonClass = `remove-${fieldType}-language-btn`;
    const textareaClass = `${fieldType}-text`;
    
    const newLangHTML = `
        <div class="language-form-group mb-2">
            <div class="row">
                <div class="col-md-3">
                    <select class="form-select language-selector" 
                            name="${namePrefix}${sanitizedLang}_lang">
                        ${languageOptions}
                    </select>
                </div>
                <div class="col-md-8">
                    <textarea class="form-control ${textareaClass}" 
                           name="${namePrefix}${sanitizedLang}"
                           rows="2"
                           placeholder="Enter ${fieldType} in ${sanitizedLang}"></textarea>
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn btn-outline-danger ${removeButtonClass}" 
                            title="Remove this language">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    formsContainer.insertAdjacentHTML('beforeend', newLangHTML);
}

// Event listeners for removing custom field language forms
document.addEventListener('click', (e) => {
    // Literal meaning remove button
    const removeLiteralMeaningBtn = e.target.closest('.remove-literal-meaning-language-btn');
    if (removeLiteralMeaningBtn) {
        const formGroup = removeLiteralMeaningBtn.closest('.language-form-group');
        if (formGroup && confirm('Remove this language?')) {
            formGroup.remove();
        }
        return;
    }
    
    // Exemplar remove button
    const removeExemplarBtn = e.target.closest('.remove-exemplar-language-btn');
    if (removeExemplarBtn) {
        const formGroup = removeExemplarBtn.closest('.language-form-group');
        if (formGroup && confirm('Remove this language?')) {
            formGroup.remove();
        }
        return;
    }
    
    // Scientific name remove button
    const removeScientificNameBtn = e.target.closest('.remove-scientific-name-language-btn');
    if (removeScientificNameBtn) {
        const formGroup = removeScientificNameBtn.closest('.language-form-group');
        if (formGroup && confirm('Remove this language?')) {
            formGroup.remove();
        }
        return;
    }
});



