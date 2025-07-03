// Modified pronunciation-forms.js with debugging for troubleshooting
/**
 * Pronunciation Forms Manager
 * 
 * JavaScript component for managing LIFT pronunciation forms in the entry editor.
 * Provides dynamic add/remove functionality for IPA transcriptions.
 * Only supports seh-fonipa language code as per project requirements.
 */

class PronunciationFormsManager {
    constructor(containerId, options = {}) {
        console.log('PronunciationFormsManager constructor called with options:', JSON.stringify(options));
        this.container = document.getElementById(containerId);
        this.pronunciations = options.pronunciations || [];
        this.languageCode = 'seh-fonipa'; // Fixed language code as per project requirements
        
        this.init();
    }
    
    init() {
        console.log('Initializing PronunciationFormsManager');
        console.log('Container:', this.container);
        console.log('Pronunciations:', JSON.stringify(this.pronunciations));
        
        this.setupEventListeners();
        this.renderExistingPronunciations();
    }
    
    setupEventListeners() {
        // Add pronunciation button
        const addButton = document.getElementById('add-pronunciation-btn');
        if (addButton) {
            console.log('Add pronunciation button found');
            addButton.addEventListener('click', () => this.addPronunciation());
        } else {
            console.error('Add pronunciation button not found');
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
        console.log('Rendering existing pronunciations');
        // Clear container
        this.container.innerHTML = '';
        
        // If no pronunciations exist, add an empty one
        if (!this.pronunciations || this.pronunciations.length === 0) {
            console.log('No existing pronunciations, adding empty one');
            this.addPronunciation();
            return;
        }
        
        // Render each existing pronunciation
        console.log(`Rendering ${this.pronunciations.length} pronunciations`);
        this.pronunciations.forEach((pron, index) => {
            console.log(`Rendering pronunciation ${index}:`, JSON.stringify(pron));
            this.renderPronunciation(pron, index);
        });
    }
    
    addPronunciation() {
        console.log('Adding new pronunciation');
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
        console.log(`Removing pronunciation at index ${index}`);
        const pronunciationItem = this.container.querySelector(`.pronunciation-item[data-index="${index}"]`);
        if (pronunciationItem) {
            pronunciationItem.remove();
            this.reindexPronunciations();
        }
    }
    
    renderPronunciation(pronunciation, index) {
        console.log(`Rendering pronunciation ${index} with value:`, pronunciation.value);
        
        const isDefault = pronunciation.is_default || index === 0;
        const htmlValue = (pronunciation.value || '').replace(/"/g, '&quot;');
        
        console.log(`HTML-escaped value: "${htmlValue}"`);
        
        const html = `
            <div class="pronunciation-item mb-3 border-bottom pb-3" data-index="${index}">
                <div class="row">
                    <div class="col-12">
                        <label class="form-label">IPA</label>
                        <input type="text" class="form-control" name="pronunciations[${index}].value" 
                               value="${htmlValue}" placeholder="IPA transcription">
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
        
        console.log('Generated HTML for pronunciation item');
        
        this.container.insertAdjacentHTML('beforeend', html);
        
        // Verify the input was created correctly
        setTimeout(() => {
            const input = this.container.querySelector(`input[name="pronunciations[${index}].value"]`);
            if (input) {
                console.log(`Input field created successfully with value: "${input.value}"`);
            } else {
                console.error('Input field was not created');
            }
        }, 0);
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
