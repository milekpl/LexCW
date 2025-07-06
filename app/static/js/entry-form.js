/**
 * Dictionary Writing System - Entry Form JavaScript
 * 
 * This file contains the functionality for the entry edit/add form.
 */

document.addEventListener('DOMContentLoaded', function() {
    window.rangesLoader = new RangesLoader();

    // Function to initialize dynamic selects
    async function initializeDynamicSelects(container) {
        const dynamicSelects = container.querySelectorAll('.dynamic-grammatical-info');
        
        // Load all ranges first
        const promises = Array.from(dynamicSelects).map(async select => {
            const rangeId = select.dataset.rangeId;
            const selectedValue = select.dataset.selected;
            if (rangeId) {
                await window.rangesLoader.populateSelect(select, rangeId, { 
                    selectedValue: selectedValue,
                    emptyOption: 'Select part of speech' 
                });
            }
        });
        
        // Wait for all ranges to load
        await Promise.all(promises);
        
        // Then trigger inheritance logic if it's available
        if (typeof updateGrammaticalCategoryInheritance === 'function') {
            // Add a small delay to ensure all DOM updates are complete
            setTimeout(() => {
                updateGrammaticalCategoryInheritance();
            }, 100);
        }
    }

    // Initial load for selects already on the page
    initializeDynamicSelects(document.body).then(() => {
        // Morph-type is now handled server-side, no client-side auto-classification needed
        console.log('Dynamic selects initialized, morph-type handled by backend');
    });

    /**
     * Grammatical Category Inheritance Logic
     * Automatically derives entry-level grammatical category from senses
     * and validates for discrepancies as specified in section 7.2.1
     */
    async function updateGrammaticalCategoryInheritance() {
        const entryPartOfSpeechSelect = document.getElementById('part-of-speech');
        const requiredIndicator = document.getElementById('pos-required-indicator');
        if (!entryPartOfSpeechSelect) return;

        // Get all sense grammatical categories
        const senseGrammaticalSelects = document.querySelectorAll('#senses-container .dynamic-grammatical-info');
        const senseCategories = Array.from(senseGrammaticalSelects)
            .map(select => select.value)
            .filter(value => value && value.trim()); // Only non-empty values

        // Clear any existing error styling
        entryPartOfSpeechSelect.classList.remove('is-invalid', 'is-valid');
        const existingFeedback = entryPartOfSpeechSelect.parentElement.querySelector('.invalid-feedback, .valid-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }

        if (senseCategories.length === 0) {
            // No senses with grammatical categories
            // Check if entry already has a POS value - if so, it might be inherited
            if (entryPartOfSpeechSelect.value && entryPartOfSpeechSelect.value.trim() !== '') {
                // Entry has POS but no sense POS loaded yet - field is optional
                entryPartOfSpeechSelect.required = false;
                if (requiredIndicator) requiredIndicator.style.display = 'none';
                return;
            } else {
                // No entry POS and no sense POS - field is optional per specification
                entryPartOfSpeechSelect.required = false;
                if (requiredIndicator) requiredIndicator.style.display = 'none';
                return;
            }
        }

        // Check for consistency among sense categories
        const uniqueCategories = [...new Set(senseCategories)];
        
        if (uniqueCategories.length === 1) {
            // All senses have the same grammatical category - auto-inherit, field not required
            const commonCategory = uniqueCategories[0];
            const currentValue = entryPartOfSpeechSelect.value;
            
            // Check if entry POS already matches the common category
            if (currentValue === commonCategory) {
                // Already correctly inherited - field not required
                entryPartOfSpeechSelect.required = false;
                if (requiredIndicator) {
                    requiredIndicator.style.display = 'none';
                }
                
                // Add success feedback
                entryPartOfSpeechSelect.classList.add('is-valid');
                const feedback = document.createElement('div');
                feedback.className = 'valid-feedback';
                feedback.textContent = 'Automatically inherited from senses';
                entryPartOfSpeechSelect.parentElement.appendChild(feedback);
            } else {
                // Entry POS doesn't match - update it
                entryPartOfSpeechSelect.value = commonCategory;
                entryPartOfSpeechSelect.required = false;
                if (requiredIndicator) {
                    requiredIndicator.style.display = 'none';
                }
                
                // Add success feedback
                entryPartOfSpeechSelect.classList.add('is-valid');
                const feedback = document.createElement('div');
                feedback.className = 'valid-feedback';
                feedback.textContent = 'Automatically inherited from senses';
                entryPartOfSpeechSelect.parentElement.appendChild(feedback);
            }
        } else {
            // Discrepancy detected - field is required, show error
            entryPartOfSpeechSelect.required = true;
            if (requiredIndicator) requiredIndicator.style.display = 'inline';
            entryPartOfSpeechSelect.classList.add('is-invalid');
            const feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            feedback.innerHTML = `
                <strong>Grammatical category discrepancy detected!</strong><br>
                Senses have different categories: ${uniqueCategories.join(', ')}<br>
                Please manually select the appropriate entry-level category.
            `;
            entryPartOfSpeechSelect.parentElement.appendChild(feedback);
        }
    }

    /**
     * Grammatical Category Inheritance Logic  
     * Automatically derives entry-level grammatical category from senses
     * and validates for discrepancies as specified in section 7.2.1
     */
    // Set up event listeners for grammatical category inheritance
    function setupGrammaticalInheritanceListeners() {
        // Listen for changes in sense grammatical categories
        document.addEventListener('change', function(e) {
            if (e.target.matches('#senses-container .dynamic-grammatical-info')) {
                updateGrammaticalCategoryInheritance();
            }
        });

        // Listen for addition/removal of senses
        const sensesContainer = document.querySelector('#senses-container');
        if (sensesContainer) {
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                        updateGrammaticalCategoryInheritance();
                    }
                });
            });
            observer.observe(sensesContainer, { childList: true, subtree: true });
        }
    }

    // Initialize inheritance logic
    setupGrammaticalInheritanceListeners();
    
    // Run initial updates after ranges are loaded
    setTimeout(async () => {
        await updateGrammaticalCategoryInheritance();
    }, 500);

    // Expose functions to global scope for use by other components
    window.updateGrammaticalCategoryInheritance = updateGrammaticalCategoryInheritance;

    // Initialize Select2 for tag inputs
    $('.select2-tags').select2({
        theme: 'bootstrap-5',
        tags: true,
        tokenSeparators: [',', ' '],
        placeholder: 'Enter or select values...'
    });
    
    // Handle form submission
    const entryForm = document.getElementById('entry-form');
    if (entryForm) {
        entryForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (validateForm()) {
                submitForm();
            }
        });
    }
    
    // Validate button handler
    const validateBtn = document.getElementById('validate-btn');
    if (validateBtn) {
        validateBtn.addEventListener('click', function() {
            validateForm(true);
        });
    }
    
    // Cancel button handler
    const cancelBtn = document.getElementById('cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
                window.location.href = '/entries';
            }
        });
    }
    
    // Add pronunciation button handler
    const addPronunciationBtn = document.getElementById('add-pronunciation-btn');
    if (addPronunciationBtn) {
        addPronunciationBtn.addEventListener('click', addPronunciation);
    }
    
    // Add sense button handler
    const addSenseBtn = document.getElementById('add-sense-btn');
    if (addSenseBtn) {
        addSenseBtn.addEventListener('click', addSense);
    }
    
    // Add first sense button handler (for when no senses exist)
    const addFirstSenseBtn = document.getElementById('add-first-sense-btn');
    if (addFirstSenseBtn) {
        addFirstSenseBtn.addEventListener('click', function() {
            const noSensesMessage = document.getElementById('no-senses-message');
            if (noSensesMessage) {
                noSensesMessage.style.display = 'none';
            }
            addSense();
        });
    }
    
    // Handle pronunciation section events (delegated)
    const pronunciationContainer = document.getElementById('pronunciation-container');
    if (pronunciationContainer) {
        pronunciationContainer.addEventListener('click', function(e) {
            // Remove pronunciation button
            const removeBtn = e.target.closest('.remove-pronunciation-btn');
            if (removeBtn) {
                const pronunciationItem = removeBtn.closest('.pronunciation-item');
                if (pronunciationItem && confirm('Are you sure you want to remove this pronunciation?')) {
                    pronunciationItem.remove();
                    return;
                }
            }
            
            // Generate audio button
            const generateBtn = e.target.closest('.generate-audio-btn');
            if (generateBtn) {
                const index = generateBtn.dataset.index;
                const pronunciationItem = generateBtn.closest('.pronunciation-item');
                const ipaInput = pronunciationItem.querySelector(`input[name="pronunciations[${index}].value"]`);
                const lexicalUnit = document.getElementById('lexical-unit').value;
                
                generateAudio(lexicalUnit, ipaInput.value, index);
            }
        });
    }
    
    // Handle senses container events (delegated)
    const sensesContainer = document.getElementById('senses-container');
    if (sensesContainer) {
        sensesContainer.addEventListener('click', function(e) {
            // Remove sense button
            const removeSenseBtn = e.target.closest('.remove-sense-btn');
            if (removeSenseBtn) {
                const senseItem = removeSenseBtn.closest('.sense-item');
                if (senseItem && confirm('Are you sure you want to remove this sense and all its examples?')) {
                    senseItem.remove();
                    reindexSenses();
                    
                    // Trigger grammatical category inheritance update after removal
                    setTimeout(() => {
                        if (typeof updateGrammaticalCategoryInheritance === 'function') {
                            updateGrammaticalCategoryInheritance();
                        }
                    }, 10);
                    return;
                }
            }
            
            // Add example button
            const addExampleBtn = e.target.closest('.add-example-btn');
            if (addExampleBtn) {
                const senseIndex = addExampleBtn.dataset.senseIndex;
                const senseItem = document.querySelector(`.sense-item[data-sense-index="${senseIndex}"]`);
                if (senseItem) {
                    const examplesContainer = senseItem.querySelector('.examples-container');
                    const noExamples = examplesContainer.querySelector('.no-examples');
                    if (noExamples) {
                        noExamples.remove();
                    }
                    addExample(senseIndex);
                }
                return;
            }
            
            // Remove example button
            const removeExampleBtn = e.target.closest('.remove-example-btn');
            if (removeExampleBtn) {
                const exampleItem = removeExampleBtn.closest('.example-item');
                const senseIndex = removeExampleBtn.dataset.senseIndex;
                const senseItem = document.querySelector(`.sense-item[data-sense-index="${senseIndex}"]`);
                if (senseItem && exampleItem && confirm('Are you sure you want to remove this example?')) {
                    const examplesContainer = senseItem.querySelector('.examples-container');
                    exampleItem.remove();
                    
                    // Check if any examples remain
                    const examples = examplesContainer.querySelectorAll('.example-item');
                    if (examples.length === 0) {
                        // Show "no examples" message
                        const noExamples = document.createElement('div');
                        noExamples.className = 'no-examples text-center text-muted py-3 border rounded';
                        noExamples.innerHTML = `
                            <p>No examples added yet</p>
                            <button type="button" class="btn btn-sm btn-outline-primary add-example-btn" 
                                    data-sense-index="${senseIndex}">
                                <i class="fas fa-plus"></i> Add Example
                            </button>
                        `;
                        examplesContainer.appendChild(noExamples);
                    } else {
                        reindexExamples(senseIndex);
                    }
                }
            }
        });
    }
    
    // Audio preview modal
    const audioPreviewModalEl = document.getElementById('audioPreviewModal');
    let audioPreviewModal = null;
    if (audioPreviewModalEl) {
        audioPreviewModal = new bootstrap.Modal(audioPreviewModalEl);
    }
    
    // Save audio button
    const saveAudioBtn = document.getElementById('save-audio-btn');
    if (saveAudioBtn) {
        saveAudioBtn.addEventListener('click', function() {
            const audioPlayer = document.getElementById('audio-preview-player');
            const audioSrc = audioPlayer.src;
            const currentPronunciationIndex = audioPlayer.dataset.pronunciationIndex;
            
            // Save the audio file path to the input
            const audioFileInput = document.querySelector(`input[name="pronunciations[${currentPronunciationIndex}].audio_file"]`);
            if (audioFileInput) {
                audioFileInput.value = audioSrc.split('/').pop();
            }
            
            // Close the modal
            if (audioPreviewModal) {
                audioPreviewModal.hide();
            }
        });
    }
});

/**
 * Validate the form before submission
 * 
 * @param {boolean} showValidationModal - Whether to show the validation modal
 * @returns {boolean} Whether the form is valid
 */
function validateForm(showValidationModal = false) {
    const errors = [];
    let isValid = true;
    
    // Basic validation
    const lexicalUnit = document.getElementById('lexical-unit')?.value.trim();
    if (!lexicalUnit) {
        errors.push('Lexical Unit is required');
        isValid = false;
    }
    
    const partOfSpeech = document.getElementById('part-of-speech')?.value;
    const partOfSpeechElement = document.getElementById('part-of-speech');
    // Only require PoS if the field is marked as required (determined by inheritance logic)
    if (partOfSpeechElement && partOfSpeechElement.required && !partOfSpeech) {
        errors.push('Part of Speech is required');
        isValid = false;
    }
    
    // Sense validation
    const senses = document.querySelectorAll('.sense-item');
    if (senses.length === 0) {
        errors.push('At least one sense is required');
        isValid = false;
    } else {
        senses.forEach((sense, index) => {
            const definition = sense.querySelector(`textarea[name="senses[${index}].definition"]`)?.value.trim();
            if (!definition) {
                errors.push(`Sense ${index + 1}: Definition is required`);
                isValid = false;
            }
            
            // Validate examples if present
            const examples = sense.querySelectorAll('.example-item');
            examples.forEach((example, exIndex) => {
                const exampleText = example.querySelector(`textarea[name="senses[${index}].examples[${exIndex}].text"]`)?.value.trim();
                if (!exampleText) {
                    errors.push(`Sense ${index + 1}, Example ${exIndex + 1}: Example text is required`);
                    isValid = false;
                }
            });
        });
    }
    
    // Show validation errors
    if (errors.length > 0 && showValidationModal) {
        const errorsList = document.getElementById('validation-errors-list');
        if (errorsList) {
            errorsList.innerHTML = '';
            errors.forEach(error => {
                const li = document.createElement('li');
                li.className = 'text-danger';
                li.textContent = error;
                errorsList.appendChild(li);
            });
            
            const validationModal = new bootstrap.Modal(document.getElementById('validationModal'));
            validationModal.show();
        }
    }
    
    return isValid;
}

/**
 * Submit the form via AJAX
 */
function submitForm() {
    console.log('submitForm() called');
    const form = document.getElementById('entry-form');
    if (!form) {
        console.error('Form not found');
        return;
    }
    
    console.log('Form found, starting submission');
    
    // Use the robust form serializer
    let jsonData;
    try {
        if (typeof window.FormSerializer === 'undefined') {
            throw new Error('FormSerializer not loaded. Please ensure form-serializer.js is included.');
        }
        
        // Validate form structure before serialization
        const validation = window.FormSerializer.validateFormForSerialization(form);
        if (!validation.success) {
            console.error('Form validation errors:', validation.errors);
            throw new Error('Form structure validation failed: ' + validation.errors.join(', '));
        }
        
        if (validation.warnings.length > 0) {
            console.warn('Form validation warnings:', validation.warnings);
        }
        
        // Serialize form to JSON
        jsonData = window.FormSerializer.serializeFormToJSON(form, {
            includeEmpty: false, // Don't include empty fields
            transform: (value, key) => {
                // Trim string values
                return typeof value === 'string' ? value.trim() : value;
            }
        });
        
        console.log('Final JSON data to be sent:', JSON.stringify(jsonData, null, 2));
        
    } catch (error) {
        console.error('Form serialization error:', error);
        alert(`Form serialization failed: ${error.message}`);
        return;
    }
    
    // Show loading state
    const saveBtn = document.getElementById('save-btn');
    if (!saveBtn) return;
    
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    saveBtn.disabled = true;
    
    // Send request
    fetch(form.action, {
        method: form.method || 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(jsonData)
    })
    .then(async response => {
        let data;
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            // Not JSON, likely an HTML error page
            const text = await response.text();
            throw new Error('Server returned an unexpected response.\n' + text.substring(0, 500));
        }
        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        return data;
    })
    .then(data => {
        if (data.id) {
            window.location.href = `/entries/${data.id}`;
        } else {
            throw new Error('No entry ID returned from server');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Reset button
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
        // Show error in a user-friendly way
        let errorDiv = document.getElementById('form-error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'form-error-message';
            errorDiv.className = 'alert alert-danger mt-3';
            form.prepend(errorDiv);
        }
        errorDiv.textContent = error.message;
        // Optionally, also alert
        // alert(`Error saving entry: ${error.message}`);
    });
}

/**
 * Add a new pronunciation field
 */
function addPronunciation() {
    const container = document.getElementById('pronunciation-container');
    if (!container) return;
    
    const pronunciationItems = container.querySelectorAll('.pronunciation-item');
    const newIndex = pronunciationItems.length;    

    // Get and prepare template
    const templateEl = document.getElementById('pronunciation-template');
    if (!templateEl) return;
    
    let template = templateEl.innerHTML.replace(/INDEX/g, newIndex);
    const temp = document.createElement('div');
    temp.innerHTML = template;
    
    // Append the new pronunciation item
    container.appendChild(temp.firstElementChild);
}

/**
 * Add a new sense
 */
async function addSense() {
    const container = document.getElementById('senses-container');
    if (!container) return;
    
    const senseItems = container.querySelectorAll('.sense-item');
    const newIndex = senseItems.length;
    const newNumber = newIndex + 1;
    
    // Get and prepare template
    const templateEl = document.getElementById('sense-template');
    if (!templateEl) return;
    
    let template = templateEl.innerHTML
        .replace(/INDEX/g, newIndex)
        .replace(/NUMBER/g, newNumber);
    
    const temp = document.createElement('div');
    temp.innerHTML = template;
    
    // Append the new sense item
    const newSenseElement = temp.firstElementChild;
    container.appendChild(newSenseElement);
    
    // Initialize Select2 for the new sense
    $(newSenseElement).find('.select2-tags').select2({
        theme: 'bootstrap-5',
        tags: true,
        tokenSeparators: [',', ' '],
        placeholder: 'Enter or select values...'
    });
    
    // Load grammatical info options for the new sense
    if (window.rangesLoader) {
        const grammaticalSelect = newSenseElement.querySelector('.dynamic-grammatical-info');
        if (grammaticalSelect) {
            await window.rangesLoader.populateSelectWithFallback(
                grammaticalSelect, 
                'grammatical-info', 
                {
                    emptyOption: 'Select part of speech',
                    valueField: 'value',
                    labelField: 'value'
                }
            );
            
            // Add change listener for grammatical category inheritance
            grammaticalSelect.addEventListener('change', function() {
                if (typeof updateGrammaticalCategoryInheritance === 'function') {
                    updateGrammaticalCategoryInheritance();
                }
            });
        }
    }
    
    // Trigger inheritance update after adding the sense
    setTimeout(() => {
        if (typeof updateGrammaticalCategoryInheritance === 'function') {
            updateGrammaticalCategoryInheritance();
        }
    }, 100);
}

/**
 * Add a new example to a sense
 * 
 * @param {number} senseIndex - Index of the sense to add the example to
 */
function addExample(senseIndex) {
    const senseItem = document.querySelector(`.sense-item[data-sense-index="${senseIndex}"]`);
    if (!senseItem) return;
    
    const examplesContainer = senseItem.querySelector('.examples-container');
    if (!examplesContainer) return;
    
    const exampleItems = examplesContainer.querySelectorAll('.example-item');
    const newIndex = exampleItems.length;
    const newNumber = newIndex + 1;
    
    // Get and prepare template
    const templateEl = document.getElementById('example-template');
    if (!templateEl) return;
    
    let template = templateEl.innerHTML
        .replace(/SENSE_INDEX/g, senseIndex)
        .replace(/EXAMPLE_INDEX/g, newIndex)
        .replace(/NUMBER/g, newNumber);
    
    const temp = document.createElement('div');
    temp.innerHTML = template;
    
    // Append the new example item
    examplesContainer.appendChild(temp.firstElementChild);
}

/**
 * Reindex senses after removal
 */
function reindexSenses() {
    const senseItems = document.querySelectorAll('.sense-item');
    
    senseItems.forEach((sense, index) => {
        // Update sense number
        const header = sense.querySelector('h6');
        if (header) {
            header.textContent = `Sense ${index + 1}`;
        }
        
        // Update sense index attribute
        sense.dataset.senseIndex = index;
        
        // Update remove button
        const removeBtn = sense.querySelector('.remove-sense-btn');
        if (removeBtn) {
            removeBtn.dataset.senseIndex = index;
        }
        
        // Update add example button
        const addExampleBtn = sense.querySelector('.add-example-btn');
        if (addExampleBtn) {
            addExampleBtn.dataset.senseIndex = index;
        }
        
        // Update field names
        sense.querySelectorAll('[name^="senses["]').forEach(field => {
            const name = field.getAttribute('name');
            const newName = name.replace(/senses\[\d+\]/, `senses[${index}]`);
            field.setAttribute('name', newName);
        });
        
        // Reindex examples in this sense
        reindexExamples(index);
    });
}

/**
 * Reindex examples within a sense after removal
 * 
 * @param {number} senseIndex - Index of the sense containing the examples
 */
function reindexExamples(senseIndex) {
    const senseItem = document.querySelector(`.sense-item[data-sense-index="${senseIndex}"]`);
    if (!senseItem) return;
    
    const exampleItems = senseItem.querySelectorAll('.example-item');
    
    exampleItems.forEach((example, index) => {
        // Update example number
        const label = example.querySelector('small');
        if (label) {
            label.textContent = `Example ${index + 1}`;
        }
        
        // Update remove button attributes
        const removeBtn = example.querySelector('.remove-example-btn');
        if (removeBtn) {
            removeBtn.dataset.senseIndex = senseIndex;
            removeBtn.dataset.exampleIndex = index;
        }
        
        // Update field names
        example.querySelectorAll('[name^="senses["]').forEach(field => {
            const name = field.getAttribute('name');
            const newName = name.replace(/examples\[\d+\]/, `examples[${index}]`);
            field.setAttribute('name', newName);
        });
    });
}

/**
 * Generate audio for a pronunciation
 * 
 * @param {string} word - The word to generate audio for
 * @param {string} ipa - The IPA pronunciation
 * @param {number} index - The index of the pronunciation item
 */
function generateAudio(word, ipa, index) {
    const btn = document.querySelector(`.generate-audio-btn[data-index="${index}"]`);
    if (!btn) return;
    
    // Show loading state
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
    btn.disabled = true;
    
    // Make API request to generate audio
    fetch('/api/pronunciations/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word, ipa })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Audio generation failed: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
        
        // Show audio preview
        const audioPlayer = document.getElementById('audio-preview-player');
        if (audioPlayer) {
            audioPlayer.src = data.audio_url;
            audioPlayer.dataset.pronunciationIndex = index;
            
            const audioPreviewModal = new bootstrap.Modal(
                document.getElementById('audioPreviewModal')
            );
            audioPreviewModal.show();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
        alert('Error generating audio. Please try again.');
    });
}

/**
 * Multilingual Notes Manager
 * Handles dynamic creation and management of multilingual note forms
 */
class MultilingualNotesManager {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = options;
        this.noteCounter = 0;
        this.languageCounter = 0;
        
        // Available note types
        this.noteTypes = [
            { value: 'general', label: 'General' },
            { value: 'usage', label: 'Usage' },
            { value: 'semantic', label: 'Semantic' },
            { value: 'etymology', label: 'Etymology' },
            { value: 'cultural', label: 'Cultural' },
            { value: 'anthropology', label: 'Anthropology' },
            { value: 'discourse', label: 'Discourse' },
            { value: 'phonology', label: 'Phonology' },
            { value: 'sociolinguistics', label: 'Sociolinguistics' },
            { value: 'bibliography', label: 'Bibliography' }
        ];
        
        // Available languages - comprehensive list including commonly used codes
        this.languages = [
            { value: 'en', label: 'English' },
            { value: 'pt', label: 'Portuguese' },
            { value: 'seh', label: 'Sena' },
            { value: 'seh-fonipa', label: 'Sena (IPA)' },
            { value: 'fr', label: 'French' },
            { value: 'es', label: 'Spanish' },
            { value: 'de', label: 'German' },
            { value: 'it', label: 'Italian' }
        ];
        
        this.init();
    }
    
    init() {
        if (!this.container) {
            console.error('Multilingual notes container not found');
            return;
        }
        // Initialize existing note items
        this.container.querySelectorAll('.note-item').forEach((item, index) => {
            this.attachNoteEventListeners(item, index);
        });
        
        // Attach event listener to add note button
        const addNoteBtn = document.getElementById('add-note-btn');
        if (addNoteBtn) {
            addNoteBtn.addEventListener('click', () => this.addNote());
        }
        
        // Hide "no notes" message if notes exist
        this.updateNoNotesMessage();
    }
    
    attachNoteEventListeners(noteItem, index) {
        // Remove note button
        const removeNoteBtn = noteItem.querySelector('.remove-note-btn');
        if (removeNoteBtn) {
            removeNoteBtn.addEventListener('click', () => this.removeNote(noteItem));
        }
        
        // Add language button
        const addLanguageBtn = noteItem.querySelector('.add-language-btn');
        if (addLanguageBtn) {
            addLanguageBtn.addEventListener('click', () => this.addLanguageToNote(noteItem));
        }
        
        // Remove language buttons
        noteItem.querySelectorAll('.remove-language-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const languageForm = e.target.closest('.language-form');
                this.removeLanguageFromNote(languageForm);
            });
        });
        
        // Note type change
        const noteTypeSelect = noteItem.querySelector('.note-type-select');
        if (noteTypeSelect) {
            noteTypeSelect.addEventListener('change', () => {
                this.updateNoteType(noteItem, noteTypeSelect.value);
            });
        }
    }
    
    addNote() {
        const noteType = 'general';
        const language = 'en';
        
        const noteHtml = this.generateNoteHtml(noteType, language);
        
        // Hide "no notes" message
        const noNotesMessage = document.getElementById('no-notes-message');
        if (noNotesMessage) {
            noNotesMessage.style.display = 'none';
        }
        
        // Insert before the add button
        const addNoteBtn = document.getElementById('add-note-btn');
        addNoteBtn.insertAdjacentHTML('beforebegin', noteHtml);
        
        // Get the newly added note item and attach event listeners
        const newNoteItems = this.container.querySelectorAll('.note-item');
        const newNoteItem = newNoteItems[newNoteItems.length - 1];
        
        this.attachNoteEventListeners(newNoteItem, this.noteCounter);
        this.noteCounter++;
        
        // Focus on the note text textarea
        const textArea = newNoteItem.querySelector('.note-text');
        if (textArea) {
            textArea.focus();
        }
    }
    
    removeNote(noteItem) {
        if (confirm('Are you sure you want to remove this note?')) {
            noteItem.remove();
            this.updateNoNotesMessage();
        }
    }
    
    addLanguageToNote(noteItem) {
        const noteType = noteItem.dataset.noteType;
        const existingLanguages = Array.from(noteItem.querySelectorAll('.language-select'))
            .map(select => select.value);
        
        // Find first available language
        const availableLanguage = this.languages.find(lang => 
            !existingLanguages.includes(lang.value)
        );
        
        if (!availableLanguage) {
            alert('All supported languages have been added to this note.');
            return;
        }
        
        const languageHtml = this.generateLanguageFormHtml(noteType, availableLanguage.value);
        
        const multilingualForms = noteItem.querySelector('.multilingual-forms');
        multilingualForms.insertAdjacentHTML('beforeend', languageHtml);
        
        // Attach event listeners to the new language form
        const newLanguageForms = multilingualForms.querySelectorAll('.language-form');
        const newLanguageForm = newLanguageForms[newLanguageForms.length - 1];
        
        const removeBtn = newLanguageForm.querySelector('.remove-language-btn');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                this.removeLanguageFromNote(newLanguageForm);
            });
        }
        
        // Focus on the text area
        const textArea = newLanguageForm.querySelector('.note-text');
        if (textArea) {
            textArea.focus();
        }
    }
    
    removeLanguageFromNote(languageForm) {
        const noteItem = languageForm.closest('.note-item');
        const remainingForms = noteItem.querySelectorAll('.language-form');
        
        if (remainingForms.length <= 1) {
            alert('A note must have at least one language.');
            return;
        }
        
        if (confirm('Are you sure you want to remove this language?')) {
            languageForm.remove();
        }
    }
    
    updateNoteType(noteItem, newNoteType) {
        noteItem.dataset.noteType = newNoteType;
        
        // Update all name attributes within this note
        const inputs = noteItem.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            if (input.name && input.name.includes('notes[')) {
                // Replace the note type in the name attribute
                input.name = input.name.replace(/notes\[[^\]]+\]/, `notes[${newNoteType}]`);
            }
        });
    }
    
    updateNoNotesMessage() {
        const noNotesMessage = document.getElementById('no-notes-message');
        const noteItems = this.container.querySelectorAll('.note-item');
        
        if (noNotesMessage) {
            noNotesMessage.style.display = noteItems.length === 0 ? 'block' : 'none';
        }
    }
    
    generateNoteHtml(noteType, language) {
        const noteTypeOptions = this.noteTypes.map(type => 
            `<option value="${type.value}" ${type.value === noteType ? 'selected' : ''}>${type.label}</option>`
        ).join('');
        
        return `
            <div class="note-item mb-4 border rounded p-3" data-note-type="${noteType}">
                <div class="row align-items-center mb-2">
                    <div class="col-md-6">
                        <label class="form-label fw-bold">Note Type</label>
                        <select class="form-select note-type-select" name="notes[${noteType}][type]" title="Select note type">
                            ${noteTypeOptions}
                        </select>
                    </div>
                    <div class="col-md-6 text-end">
                        <button type="button" class="btn btn-sm btn-outline-danger remove-note-btn" 
                                title="Remove note">
                            <i class="fas fa-trash"></i> Remove Note
                        </button>
                    </div>
                </div>
                
                <div class="multilingual-forms">
                    ${this.generateLanguageFormHtml(noteType, language)}
                </div>
                
                <div class="mt-3">
                    <button type="button" class="btn btn-sm btn-outline-primary add-language-btn" 
                            title="Add another language">
                        <i class="fas fa-plus"></i> Add Language
                    </button>
                </div>
            </div>
        `;
    }
    
    generateLanguageFormHtml(noteType, language) {
        const languageOptions = this.languages.map(lang => 
            `<option value="${lang.value}" ${lang.value === language ? 'selected' : ''}>${lang.label}</option>`
        ).join('');
        
        return `
            <div class="mb-3 language-form" data-language="${language}">
                <div class="row">
                    <div class="col-md-3">
                        <label class="form-label">Language</label>
                        <select class="form-select language-select" 
                                name="notes[${noteType}][${language}][lang]" 
                                title="Select language">
                            ${languageOptions}
                        </select>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Note Text</label>
                        <textarea class="form-control note-text" 
                                  name="notes[${noteType}][${language}][text]" 
                                  rows="2" 
                                  placeholder="Enter note text in ${this.getLanguageLabel(language)}"></textarea>
                    </div>
                    <div class="col-md-1 d-flex align-items-end">
                        <button type="button" class="btn btn-sm btn-outline-danger remove-language-btn" 
                                title="Remove language">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    getLanguageLabel(languageCode) {
        const language = this.languages.find(lang => lang.value === languageCode);
        return language ? language.label : languageCode;
    }
}

/**
 * IPA Validation Module
 * Implements real-time validation against admissible IPA characters and sequences
 * as specified in Section 15.3 of the specification
 */
class IPAValidator {
    constructor() {
        // Primary IPA symbols as defined in Section 15.3.1
        this.vowels = 'ɑæɒəɜɪiʊuʌeɛoɔ';
        this.consonants = 'bdfghjklmnprstwvzðθŋʃʒ';
        this.lengthMarkers = 'ː';
        this.stressMarkers = 'ˈˌ';
        this.specialSymbols = 'ᵻ';
        this.diphthongs = ['eɪ', 'aɪ', 'ɔɪ', 'əʊ', 'aʊ', 'ɪə', 'eə', 'ʊə', 'oʊ'];
        this.complexConsonants = ['tʃ', 'dʒ'];
        
        // Build complete valid character set
        this.validChars = this.vowels + this.consonants + this.lengthMarkers + 
                         this.stressMarkers + this.specialSymbols + ' .';
        
        // Invalid sequences as defined in Section 15.3.3
        this.invalidSequences = [
            'ˈˈ', 'ˌˌ', 'ˈˌ', 'ˌˈ', // Double stress markers
            'ːː', // Double length markers
        ];
    }
    
    /**
     * Validate IPA text and return validation result
     * @param {string} ipaText - The IPA text to validate
     * @returns {Object} Validation result with isValid, errors, and positions
     */
    validate(ipaText) {
        const result = {
            isValid: true,
            errors: [],
            invalidPositions: []
        };
        
        if (!ipaText || ipaText.trim() === '') {
            return result; // Empty is valid
        }
        
        // Check for invalid characters
        for (let i = 0; i < ipaText.length; i++) {
            const char = ipaText[i];
            if (!this.validChars.includes(char)) {
                result.isValid = false;
                result.errors.push(`Invalid IPA character: '${char}' at position ${i + 1}`);
                result.invalidPositions.push(i);
            }
        }
        
        // Check for invalid sequences
        this.invalidSequences.forEach(sequence => {
            let index = ipaText.indexOf(sequence);
            while (index !== -1) {
                result.isValid = false;
                result.errors.push(`Invalid sequence: '${sequence}' at position ${index + 1}`);
                for (let j = index; j < index + sequence.length; j++) {
                    if (!result.invalidPositions.includes(j)) {
                        result.invalidPositions.push(j);
                    }
                }
                index = ipaText.indexOf(sequence, index + 1);
            }
        });
        
        return result;
    }
    
    /**
     * Apply visual feedback to an input field based on validation result
     * @param {HTMLInputElement} inputField - The input field to style
     * @param {Object} validationResult - Result from validate() method
     */
    applyVisualFeedback(inputField, validationResult) {
        // Remove existing validation classes
        inputField.classList.remove('is-invalid', 'is-valid', 'ipa-invalid');
        
        // Remove existing feedback elements
        const existingFeedback = inputField.parentElement.querySelector('.invalid-feedback, .valid-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
        
        if (inputField.value.trim() === '') {
            return; // No validation for empty fields
        }
        
        if (validationResult.isValid) {
            inputField.classList.add('is-valid');
            
            // Add success feedback
            const feedback = document.createElement('div');
            feedback.className = 'valid-feedback';
            feedback.textContent = 'Valid IPA transcription';
            inputField.parentElement.appendChild(feedback);
        } else {
            inputField.classList.add('is-invalid', 'ipa-invalid');
            
            // Add error feedback
            const feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            feedback.innerHTML = '<strong>IPA Validation Errors:</strong><br>' + 
                               validationResult.errors.join('<br>');
            inputField.parentElement.appendChild(feedback);
            
            // Apply underline styling to invalid characters
            this.highlightInvalidCharacters(inputField, validationResult.invalidPositions);
        }
    }
    
    /**
     * Highlight invalid characters with red underline
     * @param {HTMLInputElement} inputField - The input field
     * @param {Array} invalidPositions - Array of invalid character positions
     */
    highlightInvalidCharacters(inputField, invalidPositions) {
        // This would be complex to implement with input fields directly
        // For now, we rely on the Bootstrap validation classes and feedback
        // A future enhancement could use a contenteditable div for more granular highlighting
    }
}

/**
 * Initialize IPA validation for all pronunciation input fields
 */
function initializeIPAValidation() {
    const validator = new IPAValidator();
    
    function validateIPAField(inputField) {
        const validationResult = validator.validate(inputField.value);
        validator.applyVisualFeedback(inputField, validationResult);
    }
    
    // Apply validation to existing IPA input fields
    document.querySelectorAll('.ipa-input').forEach(inputField => {
        // Real-time validation on input
        inputField.addEventListener('input', function() {
            validateIPAField(this);
        });
        
        // Validation on blur for better UX
        inputField.addEventListener('blur', function() {
            validateIPAField(this);
        });
        
        // Initial validation if field has content
        if (inputField.value.trim()) {
            validateIPAField(inputField);
        }
    });
    
    // Add validation CSS if not already present
    if (!document.querySelector('#ipa-validation-styles')) {
        const style = document.createElement('style');
        style.id = 'ipa-validation-styles';
        style.textContent = `
            .ipa-invalid {
                border-color: #dc3545 !important;
                box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25) !important;
            }
            
            .ipa-invalid:focus {
                border-color: #dc3545 !important;
                box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25) !important;
            }
            
            .ipa-input.is-valid {
                border-color: #198754 !important;
            }
            
            .ipa-input.is-valid:focus {
                border-color: #198754 !important;
                box-shadow: 0 0 0 0.2rem rgba(25, 135, 84, 0.25) !important;
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * Field Visibility Management
 * Implements user-configurable field visibility as specified in Section 7.2.1
 */
class FieldVisibilityManager {
    constructor() {
        this.storageKey = 'entryFormFieldVisibility';
        this.defaultSettings = {
            'basic-info-section': true,
            'custom-fields-section': true,
            'notes-section': true,
            'pronunciation-section': true,
            'variants-section': true,
            'relations-section': true,
            'senses-section': true
        };
        this.currentSettings = this.loadSettings();
        this.initializeControls();
        this.applySettings();
    }
    
    /**
     * Load settings from localStorage
     */
    loadSettings() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            return stored ? { ...this.defaultSettings, ...JSON.parse(stored) } : { ...this.defaultSettings };
        } catch (error) {
            console.warn('Failed to load field visibility settings:', error);
            return { ...this.defaultSettings };
        }
    }
    
    /**
     * Save settings to localStorage
     */
    saveSettings() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.currentSettings));
        } catch (error) {
            console.warn('Failed to save field visibility settings:', error);
        }
    }
    
    /**
     * Initialize event listeners for visibility controls
     */
    initializeControls() {
        // Individual section toggles
        document.querySelectorAll('.field-visibility-toggle').forEach(checkbox => {
            const sectionClass = checkbox.dataset.target?.replace('.', '');
            if (sectionClass) {
                // Set initial state from settings
                checkbox.checked = this.currentSettings[sectionClass];
                
                // Add change listener
                checkbox.addEventListener('change', () => {
                    this.currentSettings[sectionClass] = checkbox.checked;
                    this.saveSettings();
                    this.applySectionVisibility(sectionClass, checkbox.checked);
                });
            }
        });
        
        // Reset to defaults button
        const resetBtn = document.getElementById('reset-field-visibility');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetToDefaults();
            });
        }
        
        // Hide empty sections button
        const hideEmptyBtn = document.getElementById('hide-empty-sections');
        if (hideEmptyBtn) {
            hideEmptyBtn.addEventListener('click', () => {
                this.hideEmptySections();
            });
        }
        
        // Show all sections button
        const showAllBtn = document.getElementById('show-all-sections');
        if (showAllBtn) {
            showAllBtn.addEventListener('click', () => {
                this.showAllSections();
            });
        }
    }
    
    /**
     * Apply all current visibility settings
     */
    applySettings() {
        Object.entries(this.currentSettings).forEach(([sectionClass, isVisible]) => {
            this.applySectionVisibility(sectionClass, isVisible);
        });
    }
    
    /**
     * Apply visibility to a specific section
     */
    applySectionVisibility(sectionClass, isVisible) {
        const elements = document.querySelectorAll(`.${sectionClass}`);
        elements.forEach(element => {
            if (isVisible) {
                element.style.display = '';
                element.classList.remove('field-hidden');
            } else {
                element.style.display = 'none';
                element.classList.add('field-hidden');
            }
        });
    }
    
    /**
     * Reset all settings to defaults
     */
    resetToDefaults() {
        this.currentSettings = { ...this.defaultSettings };
        this.saveSettings();
        
        // Update checkboxes
        document.querySelectorAll('.field-visibility-toggle').forEach(checkbox => {
            const sectionClass = checkbox.dataset.target?.replace('.', '');
            if (sectionClass) {
                checkbox.checked = this.currentSettings[sectionClass];
            }
        });
        
        // Apply settings
        this.applySettings();
        
        // Show feedback
        this.showFeedback('Field visibility reset to defaults', 'success');
    }
    
    /**
     * Hide sections that appear to be empty
     */
    hideEmptySections() {
        Object.keys(this.currentSettings).forEach(sectionClass => {
            const sections = document.querySelectorAll(`.${sectionClass}`);
            sections.forEach(section => {
                if (this.isSectionEmpty(section)) {
                    this.currentSettings[sectionClass] = false;
                    this.applySectionVisibility(sectionClass, false);
                    
                    // Update corresponding checkbox
                    const checkbox = document.querySelector(`[data-target=".${sectionClass}"]`);
                    if (checkbox) {
                        checkbox.checked = false;
                    }
                }
            });
        });
        
        this.saveSettings();
        this.showFeedback('Empty sections hidden', 'info');
    }
    
    /**
     * Show all sections
     */
    showAllSections() {
        Object.keys(this.currentSettings).forEach(sectionClass => {
            this.currentSettings[sectionClass] = true;
            this.applySectionVisibility(sectionClass, true);
            
            // Update corresponding checkbox
            const checkbox = document.querySelector(`[data-target=".${sectionClass}"]`);
            if (checkbox) {
                checkbox.checked = true;
            }
        });
        
        this.saveSettings();
        this.showFeedback('All sections shown', 'success');
    }
    
    /**
     * Check if a section appears to be empty
     */
    isSectionEmpty(section) {
        // For custom fields section
        if (section.classList.contains('custom-fields-section')) {
            const customFieldItems = section.querySelectorAll('.custom-field-item');
            return customFieldItems.length === 0;
        }
        
        // For notes section
        if (section.classList.contains('notes-section')) {
            const noteItems = section.querySelectorAll('.note-item');
            return noteItems.length === 0;
        }
        
        // For pronunciation section
        if (section.classList.contains('pronunciation-section')) {
            const pronunciationItems = section.querySelectorAll('.pronunciation-item');
            return pronunciationItems.length === 0;
        }
        
        // For variants section
        if (section.classList.contains('variants-section')) {
            const variantItems = section.querySelectorAll('.variant-item');
            return variantItems.length === 0;
        }
        
        // For relations section
        if (section.classList.contains('relations-section')) {
            const relationItems = section.querySelectorAll('.relation-item');
            return relationItems.length === 0;
        }
        
        // For senses section - never hide as it's required
        if (section.classList.contains('senses-section')) {
            return false;
        }
        
        // Default: check for input/textarea/select elements with values
        const inputs = section.querySelectorAll('input[type="text"], textarea, select');
        const hasContent = Array.from(inputs).some(input => 
            input.value && input.value.trim() !== ''
        );
        
        return !hasContent;
    }
    
    /**
     * Show feedback message to user
     */
    showFeedback(message, type = 'info') {
        // Create a temporary toast-like notification
        const feedback = document.createElement('div');
        feedback.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        feedback.style.cssText = `
            top: 20px; 
            right: 20px; 
            z-index: 9999; 
            min-width: 300px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        `;
        feedback.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(feedback);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (feedback.parentNode) {
                feedback.remove();
            }
        }, 3000);
    }
}

// Initialize field visibility management
document.addEventListener('DOMContentLoaded', function() {
    // Small delay to ensure modal is ready
    setTimeout(() => {
        window.fieldVisibilityManager = new FieldVisibilityManager();
        
        // Initialize Phase 3: Auto-Save & Conflict Resolution
        initializeAutoSaveSystem();
    }, 200);
});

/**
 * Phase 3: Auto-Save & Conflict Resolution Initialization
 * Integrates the AutoSaveManager with the form state management and validation systems
 */
function initializeAutoSaveSystem() {
    try {
        // Check if required components are available
        if (typeof FormStateManager === 'undefined') {
            console.warn('FormStateManager not available, auto-save disabled');
            return;
        }
        
        if (typeof ClientValidationEngine === 'undefined') {
            console.warn('ClientValidationEngine not available, auto-save disabled');
            return;
        }
        
        if (typeof AutoSaveManager === 'undefined') {
            console.warn('AutoSaveManager not available, auto-save disabled');
            return;
        }
        
        // Initialize form state manager
        window.formStateManager = new FormStateManager();
        
        // Initialize client validation engine
        window.validationEngine = new ClientValidationEngine();
        
        // Initialize auto-save manager
        window.autoSaveManager = new AutoSaveManager(
            window.formStateManager, 
            window.validationEngine
        );
        
        // Check if we're editing an existing entry
        const entryIdField = document.querySelector('[name="id"]');
        const entryId = entryIdField ? entryIdField.value : null;
        
        if (entryId) {
            // Get initial version if available
            const versionField = document.querySelector('[name="version"]');
            const version = versionField ? versionField.value : Date.now().toString();
            
            // Start auto-save for existing entry
            window.autoSaveManager.start();
            
            console.log(`Auto-save enabled for entry: ${entryId}`);
        } else {
            console.log('Auto-save disabled for new entry (no ID yet)');
        }
        
        // Add Ctrl+S shortcut for manual save
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                if (window.autoSaveManager && window.autoSaveManager.isActive) {
                    window.autoSaveManager.forceSave().then(result => {
                        if (result.success) {
                            showToast('Entry saved manually', 'success');
                        } else {
                            showToast(`Save failed: ${result.reason}`, 'error');
                        }
                    });
                }
            }
        });
        
        // Integration with form submission
        const form = document.querySelector('form');
        if (form) {
            form.addEventListener('submit', function(e) {
                // Stop auto-save during manual submission
                if (window.autoSaveManager) {
                    window.autoSaveManager.stop();
                }
            });
        }
        
        console.log('Phase 3: Auto-Save & Conflict Resolution initialized successfully');
        
    } catch (error) {
        console.error('Failed to initialize auto-save system:', error);
    }
}

/**
 * Show toast notification for auto-save feedback
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible position-fixed`;
    toast.style.cssText = `
        top: 20px; 
        right: 20px; 
        z-index: 9999; 
        min-width: 300px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 3000);
}