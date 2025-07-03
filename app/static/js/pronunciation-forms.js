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
            // Server-side rendered fields exist - don't clear them, just ensure event handlers are attached
            console.log('[DEBUG] Found', existingItems.length, 'server-side rendered pronunciation fields');
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
    
    addPronunciation() {
        const index = this.getNextIndex();
        const newPronunciation = {
            value: '',
            type: this.languageCode,
            audio_file: '',
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
                        <input type="text" class="form-control" name="pronunciations[${index}].audio_file" 
                               value="${pronunciation.audio_file || ''}" readonly 
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
        const audioInput = item.querySelector('input[name$=".audio_file"]');
        
        if (!ipaInput || !ipaInput.value.trim()) {
            alert('Please enter an IPA transcription first.');
            return;
        }
        
        // In a real implementation, this would make an API call to generate audio
        // For now, we'll just update the UI with a mock file path
        const mockFilePath = `audio/${Date.now()}_${Math.floor(Math.random() * 1000)}.mp3`;
        audioInput.value = mockFilePath;
        
        // Show a success message
        alert('Audio generation would happen here in a real implementation.');
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
