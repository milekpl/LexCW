/**
 * Dictionary Writing System - Entry Form JavaScript
 * 
 * This file contains the functionality for the entry edit/add form.
 */

document.addEventListener('DOMContentLoaded', function() {
    window.rangesLoader = new RangesLoader();

    // Function to initialize dynamic selects
    function initializeDynamicSelects(container) {
        const dynamicSelects = container.querySelectorAll('.dynamic-grammatical-info');
        dynamicSelects.forEach(select => {
            const rangeId = select.dataset.rangeId;
            const selectedValue = select.dataset.selected;
            if (rangeId) {
                window.rangesLoader.populateSelect(select, rangeId, { 
                    selectedValue: selectedValue,
                    emptyOption: 'Select part of speech' 
                });
            }
        });
    }

    // Initial load for selects already on the page
    initializeDynamicSelects(document.body);

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
    if (!partOfSpeech) {
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
    const form = document.getElementById('entry-form');
    if (!form) return;
    
    // Convert form data to structured object
    const formData = new FormData(form);
    const jsonData = {};
    
    formData.forEach((value, key) => {
        // Handle bracket notation for nested objects
        const keys = key.split(/[\[\]]/).filter(k => k !== '');
        let current = jsonData;
        
        for (let i = 0; i < keys.length; i++) {
            const keyPart = keys[i];
            const isLast = i === keys.length - 1;
            
            if (isLast) {
                current[keyPart] = value;
            } else {
                // Handle numeric array indices
                const nextKey = keys[i + 1];
                const useArray = !isNaN(parseInt(nextKey));
                
                if (!current[keyPart]) {
                    current[keyPart] = useArray ? [] : {};
                }
                
                // Move into nested object/array
                current = current[keyPart];
            }
        }
    });
    
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
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        window.location.href = `/entries/${data.id}`;
    })
    .catch(error => {
        console.error('Error:', error);
        // Reset button
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
        alert('Error saving entry. Please try again.');
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
        }
    }
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
        
        // Available languages
        this.languages = [
            { value: 'en', label: 'English' },
            { value: 'pt', label: 'Portuguese' },
            { value: 'seh', label: 'Sena' },
            { value: 'fr', label: 'French' },
            { value: 'es', label: 'Spanish' }
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

// Make MultilingualNotesManager globally available
window.MultilingualNotesManager = MultilingualNotesManager;