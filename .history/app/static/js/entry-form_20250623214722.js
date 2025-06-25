/**
 * Dictionary Writing System - Entry Form JavaScript
 * 
 * This file contains the functionality for the entry edit/add form.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Select2 for tag inputs
    $('.select2-tags').select2({
        theme: 'bootstrap-5',
        tags: true,
        tokenSeparators: [',', ' '],
        placeholder: 'Enter or select values...'
    });
    
    // Handle form submission
    const entryForm = document.getElementById('entry-form');
    entryForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Perform client-side validation
        if (!validateForm()) {
            return;
        }
        
        // Submit the form
        submitForm();
    });
    
    // Validate button handler
    document.getElementById('validate-btn').addEventListener('click', function() {
        validateForm(true);
    });
    
    // Cancel button handler
    document.getElementById('cancel-btn').addEventListener('click', function() {
        if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
            window.location.href = '/entries';
        }
    });
    
    // Add pronunciation button handler
    document.getElementById('add-pronunciation-btn').addEventListener('click', function() {
        addPronunciation();
    });
    
    // Add sense button handler
    document.getElementById('add-sense-btn').addEventListener('click', function() {
        addSense();
    });
    
    // Add first sense button handler (for when no senses exist)
    const addFirstSenseBtn = document.getElementById('add-first-sense-btn');
    if (addFirstSenseBtn) {
        addFirstSenseBtn.addEventListener('click', function() {
            document.getElementById('no-senses-message').style.display = 'none';
            addSense();
        });
    }
    
    // Handle pronunciation section events (delegated)
    document.getElementById('pronunciation-container').addEventListener('click', function(e) {
        // Remove pronunciation button
        if (e.target.closest('.remove-pronunciation-btn')) {
            const btn = e.target.closest('.remove-pronunciation-btn');
            const pronunciationItem = btn.closest('.pronunciation-item');
            
            if (confirm('Are you sure you want to remove this pronunciation?')) {
                pronunciationItem.remove();
            }
        }
        
        // Generate audio button
        if (e.target.closest('.generate-audio-btn')) {
            const btn = e.target.closest('.generate-audio-btn');
            const index = btn.dataset.index;
            const pronunciationItem = btn.closest('.pronunciation-item');
            const ipaInput = pronunciationItem.querySelector(`input[name="pronunciations[${index}].value"]`);
            const lexicalUnit = document.getElementById('lexical-unit').value;
            
            generateAudio(lexicalUnit, ipaInput.value, index);
        }
    });
    
    // Handle senses container events (delegated)
    document.getElementById('senses-container').addEventListener('click', function(e) {
        // Remove sense button
        if (e.target.closest('.remove-sense-btn')) {
            const btn = e.target.closest('.remove-sense-btn');
            const senseItem = btn.closest('.sense-item');
            const senseIndex = senseItem.dataset.senseIndex;
            
            if (confirm('Are you sure you want to remove this sense and all its examples?')) {
                senseItem.remove();
                reindexSenses();
            }
        }
        
        // Add example button
        if (e.target.closest('.add-example-btn')) {
            const btn = e.target.closest('.add-example-btn');
            const senseIndex = btn.dataset.senseIndex;
            const senseItem = document.querySelector(`.sense-item[data-sense-index="${senseIndex}"]`);
            const examplesContainer = senseItem.querySelector('.examples-container');
            
            // Remove "no examples" message if present
            const noExamples = examplesContainer.querySelector('.no-examples');
            if (noExamples) {
                noExamples.remove();
            }
            
            addExample(senseIndex);
        }
        
        // Remove example button
        if (e.target.closest('.remove-example-btn')) {
            const btn = e.target.closest('.remove-example-btn');
            const exampleItem = btn.closest('.example-item');
            const senseIndex = btn.dataset.senseIndex;
            const senseItem = document.querySelector(`.sense-item[data-sense-index="${senseIndex}"]`);
            const examplesContainer = senseItem.querySelector('.examples-container');
            
            if (confirm('Are you sure you want to remove this example?')) {
                exampleItem.remove();
                
                // Reindex examples
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
    
    // Audio preview modal
    const audioPreviewModal = new bootstrap.Modal(document.getElementById('audioPreviewModal'));
    
    // Save audio button
    document.getElementById('save-audio-btn').addEventListener('click', function() {
        const audioPlayer = document.getElementById('audio-preview-player');
        const audioSrc = audioPlayer.src;
        const currentPronunciationIndex = audioPlayer.dataset.pronunciationIndex;
        
        // Save the audio file path to the input
        const audioFileInput = document.querySelector(`input[name="pronunciations[${currentPronunciationIndex}].audio_file"]`);
        audioFileInput.value = audioSrc.split('/').pop();
        
        // Close the modal
        audioPreviewModal.hide();
    });
});

/**
 * Validate the form before submission
 * 
 * @param {boolean} showValidationModal - Whether to show the validation modal
 * @returns {boolean} Whether the form is valid
 */
function validateForm(showValidationModal = false) {
    const errors = [];
    
    // Basic validation
    const lexicalUnit = document.getElementById('lexical-unit').value.trim();
    if (!lexicalUnit) {
        errors.push('Lexical Unit is required');
    }
    
    const partOfSpeech = document.getElementById('part-of-speech').value;
    if (!partOfSpeech) {
        errors.push('Part of Speech is required');
    }
    
    // Sense validation
    const senses = document.querySelectorAll('.sense-item');
    if (senses.length === 0) {
        errors.push('At least one sense is required');
    } else {
        senses.forEach((sense, index) => {
            const definition = sense.querySelector(`textarea[name="senses[${index}].definition"]`).value.trim();
            if (!definition) {
                errors.push(`Sense ${index + 1}: Definition is required`);
            }
            
            // Validate examples if present
            const examples = sense.querySelectorAll('.example-item');
            examples.forEach((example, exIndex) => {
                const exampleText = example.querySelector(`textarea[name="senses[${index}].examples[${exIndex}].text"]`).value.trim();
                if (!exampleText) {
                    errors.push(`Sense ${index + 1}, Example ${exIndex + 1}: Example text is required`);
                }
            });
        });
    }
    
    // Show validation errors
    if (errors.length > 0) {
        if (showValidationModal) {
            const errorsList = document.getElementById('validation-errors-list');
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
        
        return false;
    }
    
    return true;
}

/**
 * Submit the form via AJAX
 */
function submitForm() {
    const form = document.getElementById('entry-form');
    const formData = new FormData(form);
    
    // Convert form data to JSON
    const jsonData = {};
    
    for (const [key, value] of formData.entries()) {
        // Handle arrays and nested objects
        if (key.includes('[') && key.includes(']')) {
            const parts = key.split('[');
            const mainKey = parts[0];
            const subKey = parts[1].replace(']', '');
            
            if (parts.length === 2) {
                // Simple array or object property
                if (subKey === '') {
                    // Array
                    if (!jsonData[mainKey]) {
                        jsonData[mainKey] = [];
                    }
                    jsonData[mainKey].push(value);
                } else {
                    // Object property
                    if (!jsonData[mainKey]) {
                        jsonData[mainKey] = {};
                    }
                    jsonData[mainKey][subKey] = value;
                }
            } else if (parts.length === 3) {
                // Nested array in object
                const nestedKey = parts[2].replace(']', '');
                
                if (!jsonData[mainKey]) {
                    jsonData[mainKey] = {};
                }
                
                if (!jsonData[mainKey][subKey]) {
                    jsonData[mainKey][subKey] = [];
                }
                
                if (nestedKey === '') {
                    jsonData[mainKey][subKey].push(value);
                } else {
                    if (!jsonData[mainKey][subKey][nestedKey]) {
                        jsonData[mainKey][subKey][nestedKey] = value;
                    }
                }
            } else if (parts.length === 4) {
                // Deeply nested object
                const arrayIndex = parseInt(parts[1].replace(']', ''));
                const objectKey = parts[2].replace(']', '');
                const nestedKey = parts[3].replace(']', '');
                
                if (!jsonData[mainKey]) {
                    jsonData[mainKey] = [];
                }
                
                if (!jsonData[mainKey][arrayIndex]) {
                    jsonData[mainKey][arrayIndex] = {};
                }
                
                if (!jsonData[mainKey][arrayIndex][objectKey]) {
                    jsonData[mainKey][arrayIndex][objectKey] = {};
                }
                
                jsonData[mainKey][arrayIndex][objectKey][nestedKey] = value;
            }
        } else {
            // Simple key-value
            jsonData[key] = value;
        }
    }
    
    // Show loading state
    const saveBtn = document.getElementById('save-btn');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    saveBtn.disabled = true;
    
    // Send request
    fetch(form.action, {
        method: form.method || 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(jsonData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error saving entry');
        }
        return response.json();
    })
    .then(data => {
        // Redirect to the entry view page
        window.location.href = `/entries/${data.id}`;
    })
    .catch(error => {
        console.error('Error:', error);
        
        // Reset button
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
        
        // Show error message
        alert('Error saving entry. Please try again.');
    });
}

/**
 * Add a new pronunciation field
 */
function addPronunciation() {
    const container = document.getElementById('pronunciation-container');
    const pronunciationItems = container.querySelectorAll('.pronunciation-item');
    const newIndex = pronunciationItems.length;
    
    // Get the template and replace the index placeholder
    let template = document.getElementById('pronunciation-template').innerHTML;
    template = template.replace(/INDEX/g, newIndex);
    
    // Create a temporary element to hold the template
    const temp = document.createElement('div');
    temp.innerHTML = template;
    
    // Append the new pronunciation item
    container.appendChild(temp.firstElementChild);
}

/**
 * Add a new sense
 */
function addSense() {
    const container = document.getElementById('senses-container');
    const senseItems = container.querySelectorAll('.sense-item');
    const newIndex = senseItems.length;
    const newNumber = newIndex + 1;
    
    // Get the template and replace the index placeholder
    let template = document.getElementById('sense-template').innerHTML;
    template = template.replace(/INDEX/g, newIndex);
    template = template.replace(/NUMBER/g, newNumber);
    
    // Create a temporary element to hold the template
    const temp = document.createElement('div');
    temp.innerHTML = template;
    
    // Append the new sense item
    container.appendChild(temp.firstElementChild);
    
    // Initialize Select2 for the new sense
    $(`.sense-item[data-sense-index="${newIndex}"] .select2-tags`).select2({
        theme: 'bootstrap-5',
        tags: true,
        tokenSeparators: [',', ' '],
        placeholder: 'Enter or select values...'
    });
}

/**
 * Add a new example to a sense
 * 
 * @param {number} senseIndex - Index of the sense to add the example to
 */
function addExample(senseIndex) {
    const senseItem = document.querySelector(`.sense-item[data-sense-index="${senseIndex}"]`);
    const examplesContainer = senseItem.querySelector('.examples-container');
    const exampleItems = examplesContainer.querySelectorAll('.example-item');
    const newIndex = exampleItems.length;
    const newNumber = newIndex + 1;
    
    // Get the template and replace the placeholders
    let template = document.getElementById('example-template').innerHTML;
    template = template.replace(/SENSE_INDEX/g, senseIndex);
    template = template.replace(/EXAMPLE_INDEX/g, newIndex);
    template = template.replace(/NUMBER/g, newNumber);
    
    // Create a temporary element to hold the template
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
        // Update sense number in header
        sense.querySelector('h6').textContent = `Sense ${index + 1}`;
        
        // Update sense index attribute
        sense.dataset.senseIndex = index;
        
        // Update remove button data attribute
        const removeBtn = sense.querySelector('.remove-sense-btn');
        if (removeBtn) {
            removeBtn.dataset.index = index;
        }
        
        // Update add example button data attribute
        const addExampleBtn = sense.querySelector('.add-example-btn');
        addExampleBtn.dataset.senseIndex = index;
        
        // Update field names
        sense.querySelectorAll('[name^="senses["]').forEach(field => {
            const name = field.getAttribute('name');
            const newName = name.replace(/senses\[\d+\]/, `senses[${index}]`);
            field.setAttribute('name', newName);
        });
        
        // Update example buttons
        sense.querySelectorAll('.remove-example-btn').forEach(btn => {
            btn.dataset.senseIndex = index;
        });
        
        // Reindex examples
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
    const exampleItems = senseItem.querySelectorAll('.example-item');
    
    exampleItems.forEach((example, index) => {
        // Update example number
        example.querySelector('small').textContent = `Example ${index + 1}`;
        
        // Update remove button data attributes
        const removeBtn = example.querySelector('.remove-example-btn');
        removeBtn.dataset.senseIndex = senseIndex;
        removeBtn.dataset.exampleIndex = index;
        
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
    // Show loading state
    const btn = document.querySelector(`.generate-audio-btn[data-index="${index}"]`);
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
    btn.disabled = true;
    
    // Make API request to generate audio
    fetch('/api/pronunciations/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            word: word,
            ipa: ipa
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error generating audio');
        }
        return response.json();
    })
    .then(data => {
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
        
        // Show audio preview
        const audioPlayer = document.getElementById('audio-preview-player');
        audioPlayer.src = data.audio_url;
        audioPlayer.dataset.pronunciationIndex = index;
        
        const audioPreviewModal = new bootstrap.Modal(document.getElementById('audioPreviewModal'));
        audioPreviewModal.show();
    })
    .catch(error => {
        console.error('Error:', error);
        
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
        
        // Show error message
        alert('Error generating audio. Please try again.');
    });
}
