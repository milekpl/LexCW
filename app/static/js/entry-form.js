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


document.addEventListener('DOMContentLoaded', function() {
    // REFACTOR: Define frequently used elements once to avoid repeated DOM queries.
    const sensesContainer = document.getElementById('senses-container');
    const entryForm = document.getElementById('entry-form');

    // Initialize external components if they exist
    window.rangesLoader = window.rangesLoader || new RangesLoader();

    /**
     * Function to initialize dynamic selects.
     * Populates select elements with options from a given range.
     */
    async function initializeDynamicSelects(container) {
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

        await Promise.all(promises);
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

    // Initialize Select2 for any tag inputs.
    $('.select2-tags').select2({
        theme: 'bootstrap-5',
        tags: true,
        tokenSeparators: [',', ' '],
        placeholder: 'Enter or select values...'
    });

    // --- Main Event Handlers ---

    if (entryForm) {
        entryForm.addEventListener('submit', function(e) {
            e.preventDefault();
            // First, run all client-side validations.
            if (validateForm(true)) { // Pass true to show modal on failure
                submitForm();
            } else {
                console.log('Form submission halted due to validation errors.');
            }
        });
    }

    document.getElementById('validate-btn')?.addEventListener('click', () => validateForm(true));

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

    // --- Event Delegation for Dynamic Elements ---

    document.getElementById('pronunciation-container')?.addEventListener('click', function(e) {
        const removeBtn = e.target.closest('.remove-pronunciation-btn');
        if (removeBtn) {
            if (confirm('Are you sure you want to remove this pronunciation?')) {
                removeBtn.closest('.pronunciation-item')?.remove();
            }
            return;
        }

        const generateBtn = e.target.closest('.generate-audio-btn');
        if (generateBtn) {
            const pronunciationItem = generateBtn.closest('.pronunciation-item');
            const ipaInput = pronunciationItem.querySelector('.ipa-input');
            const lexicalUnit = document.getElementById('lexical-unit').value;
            generateAudio(lexicalUnit, ipaInput.value, generateBtn.dataset.index);
        }
    });

    if (sensesContainer) {
        sensesContainer.addEventListener('click', function(e) {
            const removeSenseBtn = e.target.closest('.remove-sense-btn');
            if (removeSenseBtn) {
                const senseItem = removeSenseBtn.closest('.sense-item');
                if (senseItem && confirm('Are you sure you want to remove this sense and all its examples?')) {
                    senseItem.remove();
                    reindexSenses();
                    // The MutationObserver will automatically trigger updateGrammaticalCategoryInheritance.
                }
                return;
            }
            
            // Handle move sense up button
            const moveSenseUpBtn = e.target.closest('.move-sense-up-btn');
            if (moveSenseUpBtn) {
                const senseItem = moveSenseUpBtn.closest('.sense-item');
                const prevSenseItem = senseItem.previousElementSibling;
                if (prevSenseItem && prevSenseItem.classList.contains('sense-item')) {
                    sensesContainer.insertBefore(senseItem, prevSenseItem);
                    reindexSenses();
                }
                return;
            }
            
            // Handle move sense down button
            const moveSenseDownBtn = e.target.closest('.move-sense-down-btn');
            if (moveSenseDownBtn) {
                const senseItem = moveSenseDownBtn.closest('.sense-item');
                const nextSenseItem = senseItem.nextElementSibling;
                if (nextSenseItem && nextSenseItem.classList.contains('sense-item')) {
                    sensesContainer.insertBefore(nextSenseItem, senseItem);
                    reindexSenses();
                }
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

    // Validate Lexical Unit
    const lexicalUnitEl = document.getElementById('lexical-unit');
    if (!lexicalUnitEl.value.trim()) {
        invalidate(lexicalUnitEl, 'Lexical Unit is required.');
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
                definitionForms.forEach(form => {
                    const textareaEl = form.querySelector('.definition-text');
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

    // Show summary modal if requested and there are errors
    if (!isValid && showSummaryModal) {
        const errorsList = document.getElementById('validation-errors-list');
        if (errorsList) {
            errorsList.innerHTML = errors.map(error => `<li class="text-danger">${error}</li>`).join('');
            const validationModal = new bootstrap.Modal(document.getElementById('validationModal'));
            validationModal.show();
        }
    }

    return isValid;
}


/**
 * Serializes and submits the form data via AJAX with improved error handling.
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

        // Check if we have the safe serialization method
        if (typeof window.FormSerializer === 'undefined' || typeof window.FormSerializer.serializeFormToJSONSafe !== 'function') {
            throw new Error('FormSerializer library is not loaded or does not support safe serialization.');
        }

        // Use the safe, async serialization method (web worker fallback)
        const jsonData = await window.FormSerializer.serializeFormToJSONSafe(form, {
            includeEmpty: false,
            transform: (value) => (typeof value === 'string' ? value.trim() : value)
        });
        
        // Update progress
        progressBar.style.width = '30%';
        progressBar.textContent = 'Data prepared, sending...';
        
        const entryId = form.querySelector('input[name="id"]')?.value?.trim();
        const apiUrl = entryId ? `/api/entries/${entryId}` : '/api/entries/';
        const apiMethod = entryId ? 'PUT' : 'POST';
        
        console.log(`Submitting to URL: ${apiUrl}, Method: ${apiMethod}`);
        
        // Set a timeout for the fetch request
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
        
        // Update progress
        progressBar.style.width = '50%';
        progressBar.textContent = 'Sending to server...';
        
        const response = await fetch(apiUrl, {
            method: apiMethod,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(jsonData),
            signal: controller.signal
        });
        
        // Clear the timeout
        clearTimeout(timeoutId);
        
        // Update progress
        progressBar.style.width = '80%';
        progressBar.textContent = 'Processing response...';
        
        const responseData = await response.json();
        
        if (!response.ok) {
            // Extract a more detailed error message if available
            const errorMessage = responseData.error || responseData.message || `HTTP error! Status: ${response.status}`;
            throw new Error(errorMessage);
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
        
        // Show detailed error message
        showToast(`Error saving entry: ${error.message}`, 'error');
        
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

    const newIndex = container.querySelectorAll('.sense-item').length;
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
                ipa
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

