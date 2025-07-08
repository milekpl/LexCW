/**
 * Multilingual Sense Fields Manager
 * 
 * Handles the multilingual definition and gloss fields in the entry form.
 * Provides functionality to add and remove language-specific inputs.
 */

class MultilingualSenseFieldsManager {
    constructor() {
        this.initEventListeners();
    }

    /**
     * Initialize event listeners for multilingual field controls
     */
    initEventListeners() {
        // Use event delegation for dynamically added elements
        document.addEventListener('click', (event) => {
            // Add definition language button
            if (event.target.closest('.add-definition-language-btn')) {
                const button = event.target.closest('.add-definition-language-btn');
                const senseIndex = button.dataset.senseIndex;
                const container = button.closest('.mb-3').querySelector('.multilingual-forms');
                this.addLanguageField(container, senseIndex, 'definition');
            }
            
            // Add gloss language button
            if (event.target.closest('.add-gloss-language-btn')) {
                const button = event.target.closest('.add-gloss-language-btn');
                const senseIndex = button.dataset.senseIndex;
                const container = button.closest('.mb-3').querySelector('.multilingual-forms');
                this.addLanguageField(container, senseIndex, 'gloss');
            }
            
            // Remove definition language button
            if (event.target.closest('.remove-definition-language-btn')) {
                const button = event.target.closest('.remove-definition-language-btn');
                const languageForm = button.closest('.language-form');
                this.removeLanguageField(languageForm);
            }
            
            // Remove gloss language button
            if (event.target.closest('.remove-gloss-language-btn')) {
                const button = event.target.closest('.remove-gloss-language-btn');
                const languageForm = button.closest('.language-form');
                this.removeLanguageField(languageForm);
            }
        });
    }

    /**
     * Add a new language field to a multilingual container
     * @param {HTMLElement} container - The container element
     * @param {string} senseIndex - The index of the sense
     * @param {string} fieldType - The type of field ('definition' or 'gloss')
     */
    addLanguageField(container, senseIndex, fieldType) {
        // Get all existing language codes in this container
        const existingLanguages = Array.from(container.querySelectorAll('.language-form'))
            .map(form => form.dataset.language);
        
        // Get all available language options
        const languageOptions = Array.from(container.querySelector('select.language-select').options)
            .map(option => ({
                code: option.value,
                label: option.textContent
            }))
            .filter(lang => !existingLanguages.includes(lang.code));
        
        // If no more languages available, show a message
        if (languageOptions.length === 0) {
            alert('All available languages have already been added.');
            return;
        }
        
        // Select the first available language
        const newLang = languageOptions[0];
        
        // Create the new language form
        const newForm = document.createElement('div');
        newForm.className = 'mb-3 language-form';
        newForm.dataset.language = newLang.code;
        
        // Different HTML structure based on field type
        if (fieldType === 'definition') {
            newForm.innerHTML = `
                <div class="row">
                    <div class="col-md-3">
                        <label class="form-label">Language</label>
                        <select class="form-select language-select" 
                                name="senses[${senseIndex}].definition[${newLang.code}].lang">
                            ${this.generateLanguageOptions(languageOptions, newLang.code)}
                        </select>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Definition Text</label>
                        <textarea class="form-control definition-text" 
                                  name="senses[${senseIndex}].definition[${newLang.code}].text"
                                  rows="2" 
                                  placeholder="Enter definition in ${newLang.code}"></textarea>
                    </div>
                    <div class="col-md-1 d-flex align-items-end">
                        <button type="button" class="btn btn-sm btn-outline-danger remove-definition-language-btn" 
                                title="Remove language">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            `;
        } else if (fieldType === 'gloss') {
            newForm.innerHTML = `
                <div class="row">
                    <div class="col-md-3">
                        <label class="form-label">Language</label>
                        <select class="form-select language-select" 
                                name="senses[${senseIndex}].gloss[${newLang.code}].lang">
                            ${this.generateLanguageOptions(languageOptions, newLang.code)}
                        </select>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Gloss Text</label>
                        <input type="text" class="form-control gloss-text" 
                               name="senses[${senseIndex}].gloss[${newLang.code}].text"
                               value=""
                               placeholder="Enter gloss in ${newLang.code}">
                    </div>
                    <div class="col-md-1 d-flex align-items-end">
                        <button type="button" class="btn btn-sm btn-outline-danger remove-gloss-language-btn" 
                                title="Remove language">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            `;
        }
        
        // Add the new form to the container
        container.appendChild(newForm);
        
        // Initialize any Select2 elements if needed
        if (window.$ && $.fn.select2) {
            $(newForm).find('select').select2({
                theme: 'bootstrap-5'
            });
        }
    }

    /**
     * Remove a language field
     * @param {HTMLElement} languageForm - The language form element to remove
     */
    removeLanguageField(languageForm) {
        if (confirm('Are you sure you want to remove this language?')) {
            languageForm.remove();
        }
    }

    /**
     * Generate HTML options for language select
     * @param {Array} languages - Array of language objects with code and label
     * @param {string} selectedCode - The code of the selected language
     * @returns {string} HTML options string
     */
    generateLanguageOptions(languages, selectedCode) {
        return languages.map(lang => 
            `<option value="${lang.code}" ${lang.code === selectedCode ? 'selected' : ''}>${lang.label}</option>`
        ).join('');
    }

    /**
     * Update field names when sense indices change
     * @param {number} oldIndex - The old sense index
     * @param {number} newIndex - The new sense index
     */
    updateSenseIndices(oldIndex, newIndex) {
        // Update definition field names
        document.querySelectorAll(`.definition-forms[data-sense-index="${oldIndex}"] .language-form`).forEach(form => {
            const lang = form.dataset.language;
            const select = form.querySelector('select');
            const textarea = form.querySelector('textarea');
            
            if (select) {
                select.name = select.name.replace(`senses[${oldIndex}]`, `senses[${newIndex}]`);
            }
            
            if (textarea) {
                textarea.name = textarea.name.replace(`senses[${oldIndex}]`, `senses[${newIndex}]`);
            }
        });
        
        // Update gloss field names
        document.querySelectorAll(`.gloss-forms[data-sense-index="${oldIndex}"] .language-form`).forEach(form => {
            const lang = form.dataset.language;
            const select = form.querySelector('select');
            const input = form.querySelector('input');
            
            if (select) {
                select.name = select.name.replace(`senses[${oldIndex}]`, `senses[${newIndex}]`);
            }
            
            if (input) {
                input.name = input.name.replace(`senses[${oldIndex}]`, `senses[${newIndex}]`);
            }
        });
        
        // Update add buttons
        document.querySelectorAll(`.add-definition-language-btn[data-sense-index="${oldIndex}"]`).forEach(btn => {
            btn.dataset.senseIndex = newIndex;
        });
        
        document.querySelectorAll(`.add-gloss-language-btn[data-sense-index="${oldIndex}"]`).forEach(btn => {
            btn.dataset.senseIndex = newIndex;
        });
    }
}

// Initialize the manager when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.multilingualSenseFieldsManager = new MultilingualSenseFieldsManager();
});