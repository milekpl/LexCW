/**
 * Pronunciation Forms Manager
 * 
 * JavaScript component for managing LIFT pronunciation forms in the entry editor.
 * Provides dynamic add/remove functionality for IPA transcriptions.
 * Only supports seh-fonipa language code as per project requirements.
 */

class PronunciationFormsManager {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.pronunciations = options.pronunciations || [];
        this.languageCode = 'seh-fonipa';

        // Defer initialization to ensure DOM is ready
        setTimeout(() => this.init(), 0);
    }

    /**
     * Get CSRF token from meta tag
     */
    getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    /**
     * Get fetch headers with CSRF token
     */
    getHeaders() {
        return {
            'X-CSRF-TOKEN': this.getCsrfToken()
        };
    }

    init() {
        this.setupEventListeners();
        this.renderExistingPronunciations();
    }

    setupEventListeners() {
        // Add pronunciation button
        const addButton = document.getElementById('add-pronunciation-btn');
        if (addButton) {
            addButton.addEventListener('click', () => this.addPronunciation());
        }
        
        // Delegate removal events
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.remove-pronunciation-btn')) {
                const index = parseInt(e.target.closest('.remove-pronunciation-btn').dataset.index);
                this.removePronunciation(index);
            }
        });
        
        // Audio generation events
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.generate-audio-btn')) {
                const index = parseInt(e.target.closest('.generate-audio-btn').dataset.index);
                this.generateAudio(index);
            }
        });
        
        // LIFT 0.13: CV Pattern and Tone (Day 40)
        // Add cv-pattern language button
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.add-cv-pattern-language-btn')) {
                const button = e.target.closest('.add-cv-pattern-language-btn');
                const pronIndex = button.dataset.pronIndex;
                const container = button.closest('.mt-3').querySelector('.cv-pattern-forms');
                this.addPronunciationCustomFieldLanguage(container, pronIndex, 'cv_pattern');
            }
        });
        
        // Remove cv-pattern language button
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.remove-cv-pattern-language-btn')) {
                const languageForm = e.target.closest('.language-form-group');
                this.removePronunciationCustomFieldLanguage(languageForm);
            }
        });
        
        // Add tone language button
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.add-tone-language-btn')) {
                const button = e.target.closest('.add-tone-language-btn');
                const pronIndex = button.dataset.pronIndex;
                const container = button.closest('.mt-3').querySelector('.tone-forms');
                this.addPronunciationCustomFieldLanguage(container, pronIndex, 'tone');
            }
        });
        
        // Remove tone language button
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.remove-tone-language-btn')) {
                const languageForm = e.target.closest('.language-form-group');
                this.removePronunciationCustomFieldLanguage(languageForm);
            }
        });
    }
    
    renderExistingPronunciations() {
        // Check if pronunciation fields are already rendered server-side
        const existingItems = this.container.querySelectorAll('.pronunciation-item');
        
        if (existingItems.length > 0) {
            // Server-side rendered fields exist - attach event handlers
            console.log('[DEBUG] Found', existingItems.length, 'server-side rendered pronunciation fields');
            this.attachEventHandlersToExisting();
            return;
        }
        
        // No server-side fields - use JavaScript rendering
        this.container.innerHTML = '';
        
        // If no pronunciations exist, add an empty one
        if (!this.pronunciations || this.pronunciations.length === 0) {
            this.addPronunciation();            
            return;
        } 
        
        // Render each existing pronunciation
        this.pronunciations.forEach((pron, index) => {
            this.renderPronunciation(pron, index);
        });
    }
    
    attachEventHandlersToExisting() {
        // Attach event handlers to existing remove audio buttons
        const existingRemoveButtons = this.container.querySelectorAll('.remove-audio-btn');
        existingRemoveButtons.forEach(button => {
            button.addEventListener('click', async (e) => {
                const audioPreview = e.target.closest('.audio-preview');
                const pronunciationItem = e.target.closest('.pronunciation-item');
                
                if (audioPreview && pronunciationItem) {
                    const audioInput = pronunciationItem.querySelector('input[name$=".audio_path"]');
                    const filename = audioInput.value;
                    
                    if (filename) {
                        try {
                            // Delete the file from server
                            const response = await fetch(`/api/pronunciation/delete/${filename}`, {
                                method: 'DELETE',
                                headers: this.getHeaders()
                            });
                            
                            if (response.ok) {
                                console.log('Audio file deleted from server');
                            } else {
                                // Try JSON first, then fall back to text for HTML error bodies
                                try {
                                    const err = await response.json();
                                    console.warn('Failed to delete audio file from server', err);
                                } catch (parseErr) {
                                    const txt = await response.text();
                                    console.warn('Failed to delete audio file from server:', txt || response.statusText);
                                }
                            }
                        } catch (error) {
                            console.warn('Error deleting audio file:', error);
                        }
                    }
                    
                    // Clear the audio input value
                    audioInput.value = '';
                    
                    // Remove the preview
                    audioPreview.remove();
                    
                    // Show feedback
                    this.showMessage('Audio file removed', 'info');
                }
            });
        });
    }
    
    addPronunciation() {
        const index = this.getNextIndex();
        const newPronunciation = {
            value: '',
            type: this.languageCode,
            audio_path: '',
            is_default: index === 0 // First pronunciation is default
        };
        
        this.renderPronunciation(newPronunciation, index);
    }
    
    removePronunciation(index) {
        const pronunciationItem = this.container.querySelector(`.pronunciation-item[data-index="${index}"]`);
        if (pronunciationItem) {
            pronunciationItem.remove();
            this.reindexPronunciations();
        }
    }
    
    renderPronunciation(pronunciation, index) {
        const isDefault = pronunciation.is_default || index === 0;
        
        // SAFETY FIX: Only escape quotes, preserve Unicode characters
        const value = pronunciation.value || '';
        const safeValue = value.replace(/"/g, '&quot;');

        
        // UNICODE FIX: Render IPA characters properly
        const html = `
            <div class="pronunciation-item mb-3 border-bottom pb-3" data-index="${index}">
                <div class="row">
                    <div class="col-12">
                        <label class="form-label">IPA</label>
                        <input type="text" class="form-control ipa-input" 
                               name="pronunciations[${index}].value" 
                               value="${safeValue}" 
                               placeholder="IPA transcription">
                        <input type="hidden" name="pronunciations[${index}].type" value="${this.languageCode}">
                        <div class="form-text">International Phonetic Alphabet (IPA)</div>
                    </div>
                </div>
                
                <div class="mt-2 mb-2">
                    <label class="form-label">Audio File</label>
                    <div class="input-group">
                        <input type="text" class="form-control" name="pronunciations[${index}].audio_path" 
                               value="${pronunciation.audio_path || ''}" readonly 
                               title="Audio file path" placeholder="No audio file">
                        <button class="btn btn-outline-secondary generate-audio-btn" type="button" 
                                data-index="${index}" title="Generate audio">
                            <i class="fas fa-microphone"></i> Generate
                        </button>
                    </div>
                </div>
                
                <!-- LIFT 0.13: CV Pattern (Day 40) -->
                <div class="mt-3 mb-2">
                    <label class="form-label">
                        CV Pattern
                        <i class="fas fa-info-circle ms-1 form-tooltip" 
                           data-bs-toggle="tooltip" 
                           data-bs-placement="top"
                           data-bs-html="true"
                           title="<strong>About CV Pattern:</strong><br>Consonant-Vowel syllable structure pattern (e.g., CV, CVC, CVCC). Useful for phonological analysis."></i>
                    </label>
                    <div class="multilingual-forms cv-pattern-forms" data-pron-index="${index}">
                        <!-- CV pattern languages will be added here -->
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-primary add-cv-pattern-language-btn" 
                            data-pron-index="${index}"
                            title="Add CV pattern in another language">
                        <i class="fas fa-plus"></i> Add Language
                    </button>
                    <div class="form-text small">Syllable structure pattern (Consonant-Vowel notation).</div>
                </div>
                
                <!-- LIFT 0.13: Tone (Day 40) -->
                <div class="mt-3 mb-2">
                    <label class="form-label">
                        Tone
                        <i class="fas fa-info-circle ms-1 form-tooltip" 
                           data-bs-toggle="tooltip" 
                           data-bs-placement="top"
                           data-bs-html="true"
                           title="<strong>About Tone:</strong><br>Tone information for tone languages (e.g., High, Low, Rising, Falling, or numeric notation like 35, 51)."></i>
                    </label>
                    <div class="multilingual-forms tone-forms" data-pron-index="${index}">
                        <!-- Tone languages will be added here -->
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-primary add-tone-language-btn" 
                            data-pron-index="${index}"
                            title="Add tone in another language">
                        <i class="fas fa-plus"></i> Add Language
                    </button>
                    <div class="form-text small">Tone marking for tone languages.</div>
                </div>
                
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" value="1" 
                           id="pron-default-${index}" name="pronunciations[${index}].is_default"
                           ${isDefault ? 'checked' : ''}>
                    <label class="form-check-label" for="pron-default-${index}">
                        Default pronunciation
                    </label>
                </div>
                
                ${index > 0 ? `
                <div class="mt-2">
                    <button type="button" class="btn btn-sm btn-outline-danger remove-pronunciation-btn" 
                            data-index="${index}" title="Remove pronunciation">
                        <i class="fas fa-trash"></i> Remove
                    </button>
                </div>
                ` : ''}
            </div>
        `;
        
        // UNICODE FIX: Use textContent instead of innerHTML
        const wrapper = document.createElement('div');
        wrapper.innerHTML = html;
        this.container.appendChild(wrapper.firstElementChild);
        
        // SAFETY FIX: Set value directly to preserve Unicode
        const input = this.container.querySelector(`.pronunciation-item[data-index="${index}"] .ipa-input`);
        if (input) {
            input.value = value;
        }
    
    }
    
    getNextIndex() {
        const items = this.container.querySelectorAll('.pronunciation-item');
        return items.length;
    }
    
    reindexPronunciations() {
        const items = this.container.querySelectorAll('.pronunciation-item');
        
        items.forEach((item, newIndex) => {
            // Update data-index attribute
            item.setAttribute('data-index', newIndex);
            
            // Update input names
            const inputs = item.querySelectorAll('input');
            inputs.forEach(input => {
                const name = input.getAttribute('name');
                if (name) {
                    const newName = name.replace(/pronunciations\[\d+\]/, `pronunciations[${newIndex}]`);
                    input.setAttribute('name', newName);
                }
                
                // Update ID for checkbox
                if (input.id && input.id.startsWith('pron-default-')) {
                    input.id = `pron-default-${newIndex}`;
                    const label = item.querySelector(`label[for^="pron-default-"]`);
                    if (label) {
                        label.setAttribute('for', `pron-default-${newIndex}`);
                    }
                }
            });
            
            // Update button data-index attributes
            const buttons = item.querySelectorAll('button[data-index]');
            buttons.forEach(button => {
                button.setAttribute('data-index', newIndex);
            });
            
            // First item should be default if no other is selected
            if (newIndex === 0) {
                const defaultCheckbox = item.querySelector('input[name$=".is_default"]');
                const anyChecked = this.container.querySelector('input[name$=".is_default"]:checked');
                if (!anyChecked && defaultCheckbox) {
                    defaultCheckbox.checked = true;
                }
            }
        });
    }
    
    generateAudio(index) {
        // Get the IPA value
        const item = this.container.querySelector(`.pronunciation-item[data-index="${index}"]`);
        if (!item) return;
        
        const ipaInput = item.querySelector('input[name$=".value"]');
        const audioInput = item.querySelector('input[name$=".audio_path"]');
        const generateBtn = item.querySelector('.generate-audio-btn');
        
        if (!ipaInput || !ipaInput.value.trim()) {
            alert('Please enter an IPA transcription first.');
            return;
        }
        
        // Create a file input for audio upload
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'audio/*,.mp3,.wav,.ogg';
        fileInput.style.display = 'none';
        
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            // Validate file type
            if (!file.type.startsWith('audio/') && !file.name.match(/\.(mp3|wav|ogg)$/i)) {
                alert('Please select a valid audio file (MP3, WAV, or OGG).');
                return;
            }
            
            // Validate file size (limit to 10MB)
            const maxSize = 10 * 1024 * 1024; // 10MB
            if (file.size > maxSize) {
                alert('Audio file is too large. Please choose a file smaller than 10MB.');
                return;
            }
            
            // Store original button state
            const originalText = generateBtn.innerHTML;
            
            try {
                // Create FormData for upload
                const formData = new FormData();
                formData.append('audio_file', file); // API expects 'audio_file' as form field name
                formData.append('ipa_value', ipaInput.value);
                formData.append('index', index);
                
                // Show loading state
                generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
                generateBtn.disabled = true;
                
                // Upload the file
                const response = await fetch('/api/pronunciation/upload', {
                    method: 'POST',
                    headers: this.getHeaders(),
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok && result.success) {
                    // Update the hidden input with the filename
                    audioInput.value = result.filename;
                    
                    // Add audio preview
                    this.addAudioPreview(item, result.filename);
                    
                    // Show success message
                    this.showMessage('Audio uploaded successfully!', 'success');
                    
                    // Update button text to indicate upload complete
                    generateBtn.innerHTML = '<i class="fas fa-check"></i> Uploaded';
                    
                    // Reset button after 2 seconds
                    setTimeout(() => {
                        generateBtn.innerHTML = originalText;
                        generateBtn.disabled = false;
                    }, 2000);
                } else {
                    throw new Error(result.message || 'Upload failed');
                }
            } catch (error) {
                console.error('Audio upload error:', error);
                this.showMessage('Failed to upload audio: ' + error.message, 'error');
                
                // Restore button state immediately on error
                generateBtn.innerHTML = originalText;
                generateBtn.disabled = false;
            }
            
            // Clean up file input
            if (document.body.contains(fileInput)) {
                document.body.removeChild(fileInput);
            }
        });
        
        // Trigger file selection
        document.body.appendChild(fileInput);
        fileInput.click();
    }
    
    addAudioPreview(item, filename) {
        // Remove existing preview
        const existingPreview = item.querySelector('.audio-preview');
        if (existingPreview) {
            existingPreview.remove();
        }
        
        // Determine the audio file extension for proper MIME type
        const fileExtension = filename.split('.').pop().toLowerCase();
        let mimeType = 'audio/mpeg'; // default
        
        if (fileExtension === 'wav') {
            mimeType = 'audio/wav';
        } else if (fileExtension === 'ogg') {
            mimeType = 'audio/ogg';
        } else if (fileExtension === 'm4a') {
            mimeType = 'audio/mp4';
        }
        
        // Create audio preview element
        const audioPreview = document.createElement('div');
        audioPreview.className = 'audio-preview mt-2';
        audioPreview.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="flex-grow-1">
                    <small class="text-muted d-block">Audio file: ${filename}</small>
                    <audio controls class="w-100 mt-1" preload="metadata">
                        <source src="/static/audio/${filename}" type="${mimeType}">
                        <source src="/static/audio/${filename}">
                        Your browser does not support the audio element.
                    </audio>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger ms-2 remove-audio-btn" 
                        title="Remove audio file">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        // Add event listener for audio removal
        const removeBtn = audioPreview.querySelector('.remove-audio-btn');
        removeBtn.addEventListener('click', async () => {
            try {
                // Optional: Delete the file from server
                const response = await fetch(`/api/pronunciation/delete/${filename}`, {
                    method: 'DELETE',
                    headers: this.getHeaders()
                });
                
                if (response.ok) {
                    console.log('Audio file deleted from server');
                } else {
                    try {
                        const err = await response.json();
                        console.warn('Failed to delete audio file from server', err);
                    } catch (parseErr) {
                        const txt = await response.text();
                        console.warn('Failed to delete audio file from server:', txt || response.statusText);
                    }
            
            // Clear the audio input value
            const audioInput = item.querySelector('input[name$=".audio_path"]');
            audioInput.value = '';
            
            // Remove the preview
            audioPreview.remove();
            
            // Show feedback
            this.showMessage('Audio file removed', 'info');
        });
        
        // Insert preview after the audio file input group
        const audioInputGroup = item.querySelector('.input-group');
        if (audioInputGroup && audioInputGroup.parentNode) {
            audioInputGroup.parentNode.insertBefore(audioPreview, audioInputGroup.nextSibling);
        }
        
        // Add error handling for audio element
        const audioElement = audioPreview.querySelector('audio');
        audioElement.addEventListener('error', (e) => {
            console.error('Audio playback error:', e);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'text-danger small mt-1';
            errorDiv.textContent = 'Audio file could not be loaded';
            audioElement.parentNode.appendChild(errorDiv);
        });
        
        audioElement.addEventListener('loadedmetadata', () => {
            console.log('Audio loaded successfully:', filename);
        });
    }
    
    /**
     * Add a language form to a pronunciation custom field (cv_pattern or tone)
     * @param {HTMLElement} container - Container for language forms
     * @param {number} pronIndex - Pronunciation index
     * @param {string} fieldName - Field name ('cv_pattern' or 'tone')
     */
    addPronunciationCustomFieldLanguage(container, pronIndex, fieldName) {
        // Get available languages from a select element if present, or use defaults
        const selectElement = document.querySelector('select.language-selector');
        let availableLanguages = ['en', 'fr', 'pt', 'es'];
        if (selectElement) {
            availableLanguages = Array.from(selectElement.options)
                .map(opt => opt.value)
                .filter(Boolean); // Remove empty values
        }
        
        const existingLangs = new Set(Array.from(container.querySelectorAll('.language-form-group'))
            .map(form => form.dataset.lang));
        const availableLang = availableLanguages.find(lang => !existingLangs.has(lang)) || availableLanguages[0];
        
        const displayName = fieldName === 'cv_pattern' ? 'CV Pattern' : 'Tone';
        const placeholder = fieldName === 'cv_pattern' ? 'e.g., CVCC, CV-CVC' : 'e.g., High, 35, Rising';
        
        const languageFormHtml = `
            <div class="language-form-group mb-2 border rounded p-2" data-lang="${availableLang}">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <label class="form-label small">Language</label>
                        <select class="form-select form-select-sm language-selector" 
                                name="pronunciations[${pronIndex}].${fieldName}.${availableLang}.lang"
                                data-field-name="pronunciations[${pronIndex}].${fieldName}.${availableLang}">
                            <option value="">Select language</option>
                            ${availableLanguages.map(lang => 
                                `<option value="${lang}" ${lang === availableLang ? 'selected' : ''}>${lang}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="col-md-9">
                        <div class="d-flex align-items-start">
                            <div class="flex-grow-1">
                                <label class="form-label small">${displayName}</label>
                                <input type="text" class="form-control form-control-sm ${fieldName}-text" 
                                       name="pronunciations[${pronIndex}].${fieldName}.${availableLang}.text" 
                                       placeholder="${placeholder}">
                            </div>
                            <button type="button" class="btn btn-sm btn-outline-danger remove-${fieldName}-language-btn ms-2 mt-4" 
                                    data-pron-index="${pronIndex}"
                                    title="Remove this language">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', languageFormHtml);
        
        // Attach language change handler
        const newForm = container.lastElementChild;
        const select = newForm.querySelector('.language-selector');
        select.addEventListener('change', (e) => this.handlePronunciationCustomFieldLanguageChange(e, pronIndex, fieldName));
    }
    
    /**
     * Remove a language form from a pronunciation custom field
     * @param {HTMLElement} languageForm - Language form element to remove
     */
    removePronunciationCustomFieldLanguage(languageForm) {
        if (languageForm) {
            languageForm.remove();
        }
    }
    
    /**
     * Handle language change for pronunciation custom fields
     * @param {Event} event - Change event
     * @param {number} pronIndex - Pronunciation index
     * @param {string} fieldName - Field name ('cv_pattern' or 'tone')
     */
    handlePronunciationCustomFieldLanguageChange(event, pronIndex, fieldName) {
        const select = event.target;
        const newLang = select.value;
        const languageForm = select.closest('.language-form-group');
        const oldLang = languageForm.dataset.lang;
        
        if (!newLang || newLang === oldLang) return;
        
        // Update data-lang attribute
        languageForm.dataset.lang = newLang;
        
        // Update all inputs/selects within this form
        const inputs = languageForm.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            const name = input.getAttribute('name');
            if (name) {
                const newName = name.replace(
                    `pronunciations[${pronIndex}].${fieldName}.${oldLang}`,
                    `pronunciations[${pronIndex}].${fieldName}.${newLang}`
                );
                input.setAttribute('name', newName);
            }
            
            // Update data-field-name for language selector
            if (input.classList.contains('language-selector')) {
                const fieldName = input.dataset.fieldName;
                if (fieldName) {
                    input.dataset.fieldName = fieldName.replace(
                        `pronunciations[${pronIndex}].${fieldName}.${oldLang}`,
                        `pronunciations[${pronIndex}].${fieldName}.${newLang}`
                    );
                }
            }
        });
    }
    
    showMessage(message, type = 'info') {
        // Create a toast-like message
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        messageDiv.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
        messageDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(messageDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 5000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('pronunciation-container')) {
        // Get pronunciations data from the page, if available
        let pronunciations = [];
        
        try {
            if (typeof entryPronunciations !== 'undefined') {
                pronunciations = entryPronunciations;
            }
        } catch (e) {
            console.warn('No pronunciations data found, starting with empty state');
        }
        
        window.pronunciationFormsManager = new PronunciationFormsManager('pronunciation-container', {
            pronunciations: pronunciations
        });
    }
});
