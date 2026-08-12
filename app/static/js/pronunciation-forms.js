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

    /**
     * Escape a string for safe interpolation into HTML.
     */
    escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    init() {
        // Stage 2.3: Alpine now owns pronunciation rendering (x-for, addItem/removeItem).
        // The legacy manager is neutered to audio-only.  Do NOT render HTML, do NOT
        // bind add/remove/CV/tone handlers — those are Alpine's responsibility.
        this.setupAudioListeners();
        this.attachAudioHandlersToExisting();
    }

    /**
     * Only bind audio-related listeners.  Alpine owns add/remove/reorder/CV/tone.
     */
    setupAudioListeners() {
        // Audio generation button (delegated inside the container)
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.generate-audio-btn')) {
                var index = parseInt(e.target.closest('.generate-audio-btn').dataset.index);
                this.generateTTSAudio(index);
            }
            // Audio upload button
            if (e.target.closest('.upload-audio-btn')) {
                var idx = parseInt(e.target.closest('.upload-audio-btn').dataset.index);
                this.uploadAudio(idx);
            }
        });
    }
    
    /**
     * Attach audio-delete handlers to existing (server-side rendered) audio previews.
     * Alpine owns rendering; the legacy manager only manages audio lifecycle.
     */
    attachAudioHandlersToExisting() {
        var self = this;
        var existingRemoveButtons = this.container.querySelectorAll('.remove-audio-btn');
        existingRemoveButtons.forEach(function (button) {
            button.addEventListener('click', async function (e) {
                var audioPreview = e.target.closest('.audio-preview');
                var pronunciationItem = e.target.closest('.pronunciation-item');
                
                if (audioPreview && pronunciationItem) {
                    var audioInput = pronunciationItem.querySelector('input[x-model="item.audioPath"]');
                    if (!audioInput) {
                        // Fall back to legacy name= selector for entries that haven't been re-saved
                        audioInput = pronunciationItem.querySelector('input[name$=".audio_path"]');
                    }
                    var filename = audioInput ? (audioInput.value || '') : '';
                    
                    if (filename) {
                        try {
                            var response = await fetch('/api/pronunciation/delete/' + filename, {
                                method: 'DELETE',
                                headers: self.getHeaders()
                            });
                            if (response.ok) {
                                console.log('Audio file deleted from server');
                            }
                        } catch (error) {
                            console.warn('Error deleting audio file:', error);
                        }
                    }
                    
                    // Clear the audio input value
                    if (audioInput) audioInput.value = '';
                    
                    // Remove the preview
                    audioPreview.remove();
                    
                    self.showMessage('Audio file removed', 'info');
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
    
    /**
     * Set the audio files on a pronunciation item.
     *
     * In the entry form Alpine owns the item state, so we write
     * ``items[index].audioPath``/``audioPaths`` through the Alpine scope (which
     * makes the ``x-text`` label reactive and persists the value on save). The
     * legacy non-Alpine path falls back to writing the hidden input.
     *
     * @param {number} index - Pronunciation index.
     * @param {string[]} hrefs - Audio filenames, in order (first = primary).
     */
    setAudioPaths(index, hrefs) {
        var itemEl = this.container.querySelector('.pronunciation-item[data-index="' + index + '"]');
        if (!itemEl) return;

        hrefs = (hrefs || []).filter(Boolean);
        var primary = hrefs[0] || '';

        if (window.Alpine && typeof window.Alpine.$data === 'function') {
            var alpineData = window.Alpine.$data(itemEl);
            if (alpineData && alpineData.items && alpineData.items[index]) {
                alpineData.items[index].audioPaths = hrefs;
                alpineData.items[index].audioPath = primary;
                return;
            }
        }

        var audioInput = itemEl.querySelector('input[x-model="item.audioPath"]');
        if (!audioInput) audioInput = itemEl.querySelector('input[name$=".audio_path"]');
        if (audioInput) audioInput.value = primary;
    }

    /**
     * Set a single audio file on a pronunciation item (upload replaces all).
     */
    setAudioPath(index, filename) {
        this.setAudioPaths(index, filename ? [filename] : []);
    }

    /**
     * Generate pronunciation audio via the configured TTS engine.
     * Calls POST /api/pronunciation/generate with {word, ipa}. Comma-delimited
     * IPA lists are expanded server-side; one audio file per variant is
     * generated and all of them are attached to the item.
     */
    generateTTSAudio(index) {
        var item = this.container.querySelector('.pronunciation-item[data-index="' + index + '"]');
        if (!item) return;

        var ipaInput = item.querySelector('input.ipa-input');
        if (!ipaInput) ipaInput = item.querySelector('input[name$=".value"]'); // legacy fallback

        var lexicalUnitInput = document.querySelector('.lexical-unit-text');
        var word = lexicalUnitInput ? lexicalUnitInput.value.trim() : '';
        if (!word && window.__entryData && window.__entryData.lexical_unit) {
            var lu = window.__entryData.lexical_unit;
            word = lu.en || Object.values(lu)[0] || '';
        }
        var ipa = ipaInput ? ipaInput.value.trim() : '';

        if (!word && !ipa) {
            alert('Please enter a headword or an IPA transcription first.');
            return;
        }

        var generateBtn = item.querySelector('.generate-audio-btn');
        var originalText = generateBtn.innerHTML;
        generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        generateBtn.disabled = true;

        fetch('/api/pronunciation/generate', {
            method: 'POST',
            headers: Object.assign({}, this.getHeaders(), { 'Content-Type': 'application/json' }),
            body: JSON.stringify({ word: word, ipa: ipa })
        })
        .then(async function (r) {
            var data = await r.json().catch(function () { return {}; });
            if (!r.ok) {
                throw new Error(data.message || 'Audio generation failed (HTTP ' + r.status + ')');
            }
            return data;
        })
        .then(function (data) {
            var results = (data.results && data.results.length)
                ? data.results
                : (data.filename ? [{ ipa: ipa, filename: data.filename }] : []);
            if (!results.length) {
                throw new Error('API response did not include audio files.');
            }

            // Attach every generated variant (first = primary) to the item.
            var hrefs = results.map(function (r) { return r.filename; });
            this.setAudioPaths(index, hrefs);

            // Preview each variant; label them when there is more than one.
            var multi = results.length > 1;
            var self = this;
            results.forEach(function (r) {
                self.addAudioPreview(item, r.filename, multi ? (r.ipa || '') : '');
            });

            this.showMessage(
                multi ? 'Audio generated for ' + results.length + ' pronunciations' : 'Audio generated successfully!',
                'success'
            );
            generateBtn.innerHTML = '<i class="fas fa-check"></i> Generated';
            setTimeout(function () {
                generateBtn.innerHTML = originalText;
                generateBtn.disabled = false;
            }, 2000);
        }.bind(this))
        .catch(function (error) {
            var message = (error && error.message) ? error.message : String(error);
            console.error('[Pronunciation] Audio generation failed: ' + message, error);
            this.showMessage('Failed to generate audio: ' + message, 'error');
            generateBtn.innerHTML = originalText;
            generateBtn.disabled = false;
        }.bind(this));
    }

    uploadAudio(index) {
        // Get the IPA value from the Alpine-managed input
        var item = this.container.querySelector('.pronunciation-item[data-index="' + index + '"]');
        if (!item) return;
        
        var ipaInput = item.querySelector('input.ipa-input');  // Alpine-rendered
        if (!ipaInput) ipaInput = item.querySelector('input[name$=".value"]'); // legacy fallback
        var generateBtn = item.querySelector('.generate-audio-btn');
        
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
                    // Record the filename on the item (Alpine state or legacy input)
                    this.setAudioPath(index, result.filename);
                    
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
                var message = (error && error.message) ? error.message : String(error);
                console.error('[Pronunciation] Audio upload failed: ' + message, error);
                this.showMessage('Failed to upload audio: ' + message, 'error');
                
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
    
    /**
     * Remove all audio preview blocks from a pronunciation item.
     */
    clearAudioPreviews(item) {
        const existing = item.querySelectorAll('.audio-preview');
        existing.forEach(function (preview) {
            preview.remove();
        });
    }

    addAudioPreview(item, filename, label) {
        // Remove an existing single preview when replacing with exactly one file
        if (!label) {
            this.clearAudioPreviews(item);
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
        const labelHtml = label
            ? '<small class="text-muted d-block"><strong>' + this.escapeHtml(label) + '</strong></small>'
            : '';
        audioPreview.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="flex-grow-1">
                    ${labelHtml}
                    <small class="text-muted d-block">Audio file: ${filename}</small>
                    <audio controls class="w-100 mt-1" preload="metadata">
                        <source src="/audio/${filename}" type="${mimeType}">
                        <source src="/audio/${filename}">
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
                }
            } catch (e) {
                console.warn('Failed to delete audio file:', e);
            }

            // Drop this file from the Alpine state (or legacy input), keeping the rest.
            var itemEl = item;
            var removed = false;
            if (window.Alpine && typeof window.Alpine.$data === 'function') {
                var ad = window.Alpine.$data(itemEl);
                var idx = parseInt(itemEl.dataset.index, 10);
                if (ad && ad.items && !isNaN(idx) && ad.items[idx]) {
                    ad.items[idx].audioPaths = (ad.items[idx].audioPaths || [])
                        .filter(function (h) { return h !== filename; });
                    ad.items[idx].audioPath = ad.items[idx].audioPaths[0] || '';
                    removed = true;
                }
            }
            if (!removed) {
                var audioInput = item.querySelector('input[x-model="item.audioPath"]');
                if (!audioInput) audioInput = item.querySelector('input[name$=".audio_path"]');
                if (audioInput) audioInput.value = '';
            }
            
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
        // Create a toast-like message. Errors persist until dismissed (so the
        // user can read and copy the text) and are also logged to the console;
        // info/success toasts auto-dismiss.
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        messageDiv.style.cssText =
            'top: 20px; right: 20px; z-index: 1050; min-width: 340px; max-width: 520px;' +
            ' user-select: text; white-space: pre-wrap; word-break: break-word;';
        messageDiv.setAttribute('role', type === 'error' ? 'alert' : 'status');

        const isError = type === 'error';
        const copyBtn = isError
            ? '<button type="button" class="btn btn-sm btn-outline-secondary ms-2" title="Copy error message" style="flex-shrink:0">Copy</button>'
            : '';
        messageDiv.innerHTML = `
            <div class="d-flex align-items-start justify-content-between gap-2">
                <span class="flex-grow-1">${this.escapeHtml(message)}</span>
                ${copyBtn}
                <button type="button" class="btn-close" data-bs-dismiss="alert" style="flex-shrink:0"></button>
            </div>
        `;

        if (isError) {
            const copy = messageDiv.querySelector('button[title="Copy error message"]');
            if (copy) {
                copy.addEventListener('click', () => {
                    const textEl = messageDiv.querySelector('span');
                    const text = textEl ? textEl.textContent : '';
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(text).then(() => {
                            copy.textContent = 'Copied!';
                            setTimeout(() => { copy.textContent = 'Copy'; }, 1500);
                        }).catch(() => { /* clipboard may be blocked; fall through */ });
                    } else {
                        // Fallback: select the message text for manual copy
                        const range = document.createRange();
                        range.selectNodeContents(textEl);
                        const sel = window.getSelection();
                        sel.removeAllRanges();
                        sel.addRange(range);
                    }
                });
            }
        }

        document.body.appendChild(messageDiv);

        if (!isError) {
            // Auto-remove info/success after 5 seconds; errors stay until dismissed.
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.remove();
                }
            }, 5000);
        }
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
