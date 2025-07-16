# Entry Form Fix Plan

## Issues Identified

1. **Multilingual Field Support**:
   - Definition and gloss fields don't support multilingual content
   - API expects definitions and glosses as objects with language codes as keys
   - Current template uses simple text fields instead of language-specific inputs

2. **Form Serialization Issues**:
   - The form serializer may be failing to properly handle complex nested data
   - Potential memory leaks or infinite recursion in the serialization process
   - Lack of proper error handling during serialization

3. **Form Submission Problems**:
   - Form may be freezing during submission due to large data structures
   - Lack of proper validation for multilingual fields
   - Potential race conditions in the async submission process

## Step-by-Step Fix Plan

### 1. Fix Multilingual Field Support

1. **Update Sense Definition Fields**:
   - Replace single textarea with language-specific inputs
   - Use the same pattern as already implemented for notes
   - Add language selection dropdown for each definition
   - Ensure proper naming convention for form fields: `senses[index].definition[lang_code]`

2. **Update Sense Gloss Fields**:
   - Replace single input with language-specific inputs
   - Add language selection dropdown for each gloss
   - Ensure proper naming convention: `senses[index].gloss[lang_code]`

3. **Update Template Logic**:
   - Modify the template to handle definition/gloss as objects with language keys
   - Add UI controls to add/remove languages for each field
   - Ensure default language is always present

### 2. Fix Form Serialization

1. **Improve Form Serializer**:
   - Add memory usage monitoring to detect potential memory leaks
   - Implement size limits for serialized data
   - Add proper error handling for circular references
   - Optimize the serialization algorithm for large forms

2. **Add Debugging Tools**:
   - Implement logging for serialization process
   - Add performance metrics to identify bottlenecks
   - Create a fallback serialization method for complex forms

3. **Implement Progressive Serialization**:
   - Break down serialization into smaller chunks
   - Add progress indicators during serialization
   - Implement cancellation mechanism for long-running operations

### 3. Fix Form Submission

1. **Improve Error Handling**:
   - Add more detailed error reporting
   - Implement recovery mechanisms for failed submissions
   - Add client-side validation for all multilingual fields

2. **Optimize Submission Process**:
   - Implement debouncing for form submission
   - Add request timeout handling
   - Implement retry logic for failed submissions

3. **Add Auto-Save Functionality**:
   - Implement periodic auto-saving of form data
   - Add draft saving functionality
   - Ensure auto-save doesn't interfere with manual saves

## Implementation Details

### Multilingual Definition/Gloss Template Changes

Replace the current definition field:

```html
<div class="mb-3">
    <label class="form-label">Definition <span class="text-danger">*</span></label>
    <textarea class="form-control" name="senses[{{ loop.index0 }}].definition" 
              rows="2" required>{{ sense.definition }}</textarea>
</div>
```

With multilingual version:

```html
<div class="mb-3">
    <label class="form-label">Definition <span class="text-danger">*</span></label>
    <div class="multilingual-forms definition-forms">
        {% if sense.definition is mapping %}
            {% for lang, text in sense.definition.items() %}
            <div class="mb-3 language-form" data-language="{{ lang }}">
                <div class="row">
                    <div class="col-md-3">
                        <label class="form-label">Language</label>
                        <select class="form-select language-select" 
                                name="senses[{{ loop.index0 }}].definition[{{ lang }}].lang">
                            {% for code, label in project_languages %}
                                <option value="{{ code }}" {% if lang == code %}selected{% endif %}>{{ label|safe }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Definition Text</label>
                        <textarea class="form-control definition-text" 
                                  name="senses[{{ loop.index0 }}].definition[{{ lang }}].text" 
                                  rows="2" 
                                  {% if loop.first %}required{% endif %}
                                  placeholder="Enter definition in {{ lang }}">{{ text }}</textarea>
                    </div>
                    <div class="col-md-1 d-flex align-items-end">
                        {% if not loop.first %}
                        <button type="button" class="btn btn-sm btn-outline-danger remove-language-btn" 
                                title="Remove language">
                            <i class="fas fa-times"></i>
                        </button>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
        {% else %}
            {# Default to source language if definition is a simple string #}
            {% set default_lang_code = current_app.config.PROJECT_SETTINGS.source_language.code if current_app and current_app.config.PROJECT_SETTINGS else 'en' %}
            <div class="mb-3 language-form" data-language="{{ default_lang_code }}">
                <div class="row">
                    <div class="col-md-3">
                        <label class="form-label">Language</label>
                        <select class="form-select language-select" 
                                name="senses[{{ loop.index0 }}].definition[{{ default_lang_code }}].lang">
                            {% for code, label in project_languages %}
                                <option value="{{ code }}" {% if code == default_lang_code %}selected{% endif %}>{{ label|safe }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Definition Text</label>
                        <textarea class="form-control definition-text" 
                                  name="senses[{{ loop.index0 }}].definition[{{ default_lang_code }}].text"
                                  rows="2" 
                                  required
                                  placeholder="Enter definition in {{ default_lang_code }}">{{ sense.definition }}</textarea>
                    </div>
                    <div class="col-md-1">
                        <!-- No remove button for primary language -->
                    </div>
                </div>
            </div>
        {% endif %}
    </div>
    <div class="mt-2">
        <button type="button" class="btn btn-sm btn-outline-primary add-definition-language-btn" 
                data-sense-index="{{ loop.index0 }}"
                title="Add another language">
            <i class="fas fa-plus"></i> Add Language
        </button>
    </div>
</div>
```

Apply similar changes to the gloss field.

### Form Serializer Improvements

Add memory monitoring and chunking to form-serializer.js:

```javascript
/**
 * Serializes a form to a structured JSON object with memory monitoring
 * @param {HTMLFormElement|FormData} input - Form element or FormData object
 * @param {Object} options - Configuration options
 * @returns {Promise<Object>} Structured JSON object
 */
function serializeFormToJSONSafe(input, options = {}) {
    return new Promise((resolve, reject) => {
        // Set a reasonable timeout
        const timeout = setTimeout(() => {
            reject(new Error('Form serialization timed out. The form may be too complex.'));
        }, options.timeout || 10000);
        
        try {
            // Use a worker if available to prevent UI freezing
            if (window.Worker) {
                const worker = new Worker('/static/js/form-serializer-worker.js');
                
                worker.onmessage = function(e) {
                    clearTimeout(timeout);
                    if (e.data.error) {
                        reject(new Error(e.data.error));
                    } else {
                        resolve(e.data.result);
                    }
                    worker.terminate();
                };
                
                worker.onerror = function(error) {
                    clearTimeout(timeout);
                    reject(new Error(`Worker error: ${error.message}`));
                    worker.terminate();
                };
                
                // Convert form to serializable format
                const formData = input instanceof HTMLFormElement ? 
                    Array.from(new FormData(input).entries()) : 
                    Array.from(input.entries());
                
                worker.postMessage({
                    formData: formData,
                    options: options
                });
            } else {
                // Fallback to synchronous processing
                const result = serializeFormToJSON(input, options);
                clearTimeout(timeout);
                resolve(result);
            }
        } catch (error) {
            clearTimeout(timeout);
            reject(error);
        }
    });
}
```

### Form Submission Improvements

Update the submitForm function in entry-form.js:

```javascript
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
        
        // Use the safe serialization method
        const jsonData = await window.FormSerializer.serializeFormToJSONSafe(form, {
            includeEmpty: false,
            timeout: 30000, // 30 seconds timeout
            transform: (value) => (typeof value === 'string' ? value.trim() : value)
        });
        
        // Update progress
        progressBar.style.width = '30%';
        progressBar.textContent = 'Data prepared, sending...';
        
        const entryId = form.querySelector('input[name="id"]')?.value.trim();
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
```

## Testing Plan

1. **Unit Tests**:
   - Test multilingual field serialization
   - Test form serializer with large datasets
   - Test error handling in submission process

2. **Integration Tests**:
   - Test end-to-end form submission with multilingual data
   - Test performance with large entries
   - Test error recovery scenarios

3. **Manual Testing**:
   - Test form with various language combinations
   - Test with extremely large entries
   - Test with slow network conditions