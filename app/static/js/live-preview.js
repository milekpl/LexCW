/**
 * Live Preview functionality for entry form
 * 
 * Provides real-time preview updates as users edit the form
 */

class LivePreviewManager {
    constructor(formSelector, previewContainerSelector, debounceDelay = 500) {
        console.log('LivePreviewManager constructor called');
        
        this.form = document.querySelector(formSelector);
        this.previewContainer = document.querySelector(previewContainerSelector);
        this.debounceDelay = debounceDelay;
        this.debounceTimer = null;
        this.isUpdating = false;
        
        // Check if elements exist
        if (!this.form) {
            console.error('LivePreviewManager: Form element not found', formSelector);
            alert('DEBUG: Form element not found: ' + formSelector);
            return;
        }
        if (!this.previewContainer) {
            console.error('LivePreviewManager: Preview container not found', previewContainerSelector);
            alert('DEBUG: Preview container not found: ' + previewContainerSelector);
            return;
        }
        
        console.log('LivePreviewManager initialized', {
            form: this.form.id,
            previewContainer: this.previewContainer.id,
            debounceDelay: this.debounceDelay
        });
        
        // Store original content for fallback
        this.originalContent = this.previewContainer.innerHTML;
        
        // Initialize event listeners
        this._initializeEventListeners();
        
        // Show loading state initially
        this._showLoadingState();
        
        // Generate initial preview with a small delay to ensure everything is loaded
        setTimeout(() => {
            console.log('Generating initial preview...');
            this.updatePreview().catch(error => {
                console.error('Initial preview failed:', error);
                this._showErrorState('Failed to generate initial preview. Click refresh to try again.');
            });
        }, 500);  // Increased delay to ensure all form components are ready
    }
    
    _initializeEventListeners() {
        console.log('Initializing event listeners...');
        
        // Listen for input events on the form
        this.form.addEventListener('input', (e) => {
            this._handleFormChange(e);
        });
        
        // Listen for change events (for selects, checkboxes, etc.)
        this.form.addEventListener('change', (e) => {
            this._handleFormChange(e);
        });
        
        // Listen for keyup events as well (more reliable for some inputs)
        this.form.addEventListener('keyup', (e) => {
            this._handleFormChange(e);
        });
        
        // Listen for paste events
        this.form.addEventListener('paste', (e) => {
            this._handleFormChange(e);
        });
        
        // Listen for custom events that indicate structural changes
        // (like adding/removing senses, examples, etc.)
        document.addEventListener('formStructureChanged', () => {
            console.log('Form structure changed event received');
            this._handleFormChange(null, true);
        });
        
        // Also listen for the existing updateXmlPreview function calls
        // that are used by other parts of the system
        if (window.updateXmlPreview) {
            const originalUpdateXmlPreview = window.updateXmlPreview;
            window.updateXmlPreview = () => {
                originalUpdateXmlPreview();
                // Also trigger live preview update
                this._handleFormChange(null, true);
            };
        }
        
        console.log('Event listeners initialized');
    }
    
    _handleFormChange(event, forceUpdate = false) {
        console.log('Form change detected', {
            eventType: event ? event.type : 'custom',
            target: event ? (event.target ? event.target.id || event.target.tagName : 'unknown') : 'custom event',
            forceUpdate: forceUpdate
        });
        
        // Clear existing debounce timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Set new debounce timer
        this.debounceTimer = setTimeout(() => {
            console.log('Triggering preview update after debounce');
            this.updatePreview(forceUpdate);
        }, this.debounceDelay);
    }
    
    _showLoadingState() {
        if (this.isUpdating) return;
        
        this.isUpdating = true;
        this.previewContainer.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <small class="text-muted ms-2">Generating preview...</small>
            </div>
        `;
    }
    
    _showErrorState(errorMessage) {
        this.isUpdating = false;
        this.previewContainer.innerHTML = `
            <div class="alert alert-warning mb-0">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Preview Error:</strong> ${errorMessage}
                <button type="button" class="btn btn-sm btn-outline-secondary mt-2" onclick="window.livePreviewManager.retryPreview()">
                    <i class="fas fa-redo"></i> Retry
                </button>
            </div>
        `;
    }
    
    async updatePreview(forceUpdate = false) {
        // Skip if already updating and not forced
        if (this.isUpdating && !forceUpdate) return;
        
        try {
            console.log('updatePreview called', {forceUpdate});
            this._showLoadingState();
            
            // Serialize form data
            const formData = this._serializeFormData();
            console.log('Form data for preview:', formData);
            
            if (!formData) {
                console.error('No form data available');
                this._showErrorState('No form data available for preview.');
                this.isUpdating = false;
                return;
            }
            
            // Check if we have at least a lexical unit
            const lexicalUnit = formData.lexical_unit || {};
            if (!lexicalUnit || Object.keys(lexicalUnit).length === 0) {
                console.warn('No lexical unit found in form data');
                this.previewContainer.innerHTML = `
                    <div class="alert alert-info mb-0">
                        <i class="fas fa-info-circle"></i>
                        Please enter a lexical unit (word/phrase) to see the preview.
                    </div>
                `;
                this.isUpdating = false;
                return;
            }
            
            // Send to server for preview generation
            const response = await this._fetchPreview(formData);
            
            if (response.success && response.html) {
                this.previewContainer.innerHTML = response.html;
                this.isUpdating = false;
            } else {
                const errorMsg = response.error || 'Unknown error generating preview';
                this._showErrorState(errorMsg);
            }
            
        } catch (error) {
            console.error('Live preview error:', error);
            this._showErrorState(error.message || 'Failed to generate preview');
        }
    }
    
    _serializeFormData() {
        try {
            console.log('Serializing form data...');
            
            // Use the existing form serializer if available
            if (window.FormSerializer && window.FormSerializer.serializeFormToJSON) {
                const formData = window.FormSerializer.serializeFormToJSON(this.form, {
                    includeEmpty: true
                });
                console.log('Form data serialized:', formData);
                
                // Ensure we have the basic required fields
                if (!formData.lexical_unit) {
                    console.warn('No lexical_unit in form data, adding fallback');
                    formData.lexical_unit = {'en': 'test'};
                }
                
                return formData;
            }
            
            // Fallback to simple serialization
            console.log('Using fallback form serialization');
            const formData = new FormData(this.form);
            const result = {};
            
            for (let [key, value] of formData.entries()) {
                // Simple key-value mapping
                if (value) {
                    result[key] = value;
                }
            }
            
            console.log('Fallback form data:', result);
            return result;
            
        } catch (error) {
            console.error('Form serialization error:', error);
            return null;
        }
    }
    
    async _fetchPreview(formData) {
        try {
            console.log('Sending preview request to server...');
            console.log('Form data being sent:', formData);
            
            // Add timeout to prevent hanging
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            const response = await fetch('/api/live-preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(formData),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            console.log('Server response received:', response.status, response.statusText);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Server error details:', errorText);
                throw new Error(`Server error: ${response.status} ${response.statusText} - ${errorText}`);
            }
            
            const result = await response.json();
            console.log('Preview response:', result);
            
            if (!result.success) {
                console.error('Preview generation failed:', result.error);
                throw new Error(result.error || 'Preview generation failed');
            }
            
            return result;
            
        } catch (error) {
            console.error('Preview fetch error:', error);
            this._showErrorState(`Failed to generate preview: ${error.message}`);
            throw error;
        }
    }
    
    retryPreview() {
        this.updatePreview(true);
    }
    
    destroy() {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        this.isUpdating = false;
    }
}

// Debounced function utility
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}

// Make it available in the global scope for browser environments
if (typeof window !== 'undefined') {
    window.LivePreviewManager = LivePreviewManager;
}

// Simple test to verify this file is being executed
console.log('Live Preview JS file loaded and executed!');
window.livePreviewLoaded = true;