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
                                method: 'DELETE'
                            });
                            
                            if (response.ok) {
                                console.log('Audio file deleted from server');
                            } else {
                                console.warn('Failed to delete audio file from server');
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
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    console.log('Audio file deleted from server');
                } else {
                    console.warn('Failed to delete audio file from server');
                }
            } catch (error) {
                console.warn('Error deleting audio file:', error);
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
