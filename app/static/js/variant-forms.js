/**
 * Variant Forms Manager
 * 
 * JavaScript component for managing LIFT variant forms in the entry editor.
 * Provides dynamic add/remove functionality and Form object editing.
 */

class VariantFormsManager {
    constructor(containerId, rangesApiUrl = '/api/ranges/variant-types') {
        this.container = document.getElementById(containerId);
        this.rangesApiUrl = rangesApiUrl;
        this.variantTypes = [];
        this.languageCodes = [
            'en', 'en-US', 'en-GB', 'en-CA', 'en-AU',
            'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh',
            'ja', 'ko', 'ar', 'hi', 'seh-fonipa'
        ];
        
        this.init();
    }
    
    async init() {
        await this.loadVariantTypes();
        this.setupEventListeners();
        this.renderExistingVariants();
    }
    
    async loadVariantTypes() {
        try {
            const response = await fetch(this.rangesApiUrl);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data && result.data.values) {
                    this.variantTypes = result.data.values;
                }
            }
        } catch (error) {
            console.warn('Failed to load variant types from ranges:', error);
            // Fallback to basic types
            this.variantTypes = [
                { id: 'dialectal', value: 'dialectal', abbrev: 'dial', description: { en: 'Dialectal variant' } },
                { id: 'spelling', value: 'spelling', abbrev: 'sp', description: { en: 'Spelling variant' } },
                { id: 'morphological', value: 'morphological', abbrev: 'morph', description: { en: 'Morphological variant' } }
            ];
        }
    }
    
    setupEventListeners() {
        // Add variant button
        const addButton = document.getElementById('add-variant-btn');
        if (addButton) {
            addButton.addEventListener('click', () => this.addVariant());
        }
        
        // Delegate removal events
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-variant-btn')) {
                const index = parseInt(e.target.dataset.index);
                this.removeVariant(index);
            }
        });
    }
    
    renderExistingVariants() {
        // Find existing variant data in the form
        const existingVariants = this.getExistingVariantsFromForm();
        
        // Clear container
        this.container.innerHTML = '';
        
        // Render each existing variant
        existingVariants.forEach((variant, index) => {
            this.renderVariant(variant, index);
        });
        
        // If no variants exist, show empty state
        if (existingVariants.length === 0) {
            this.showEmptyState();
        }
    }
    
    getExistingVariantsFromForm() {
        // Extract variant data from existing form inputs
        const variants = [];
        const formData = new FormData(document.getElementById('entry-form'));
        
        // Look for variant form inputs
        for (let [key, value] of formData.entries()) {
            const match = key.match(/variants\[(\d+)\]\.form\.(lang|text)/);
            if (match) {
                const index = parseInt(match[1]);
                const field = match[2];
                
                if (!variants[index]) {
                    variants[index] = { form: {} };
                }
                
                variants[index].form[field] = value;
            }
        }
        
        return variants.filter(v => v && v.form && v.form.lang && v.form.text);
    }
    
    addVariant() {
        const variants = this.getExistingVariantsFromForm();
        const newIndex = variants.length;
        
        const newVariant = {
            form: {
                lang: '',
                text: ''
            }
        };
        
        this.renderVariant(newVariant, newIndex);
        this.hideEmptyState();
    }
    
    removeVariant(index) {
        const variantElement = document.querySelector(`[data-variant-index="${index}"]`);
        if (variantElement) {
            variantElement.remove();
            this.reindexVariants();
            
            // Show empty state if no variants remain
            if (this.container.children.length === 0) {
                this.showEmptyState();
            }
        }
    }
    
    renderVariant(variant, index) {
        const variantHtml = this.createVariantHtml(variant, index);
        this.container.insertAdjacentHTML('beforeend', variantHtml);
        
        // Initialize Select2 for language dropdown
        this.initializeLanguageDropdown(index);
    }
    
    createVariantHtml(variant, index) {
        const languageOptions = this.languageCodes.map(code => 
            `<option value="${code}" ${variant.form.lang === code ? 'selected' : ''}>${code}</option>`
        ).join('');
        
        return `
            <div class="variant-item card mb-3" data-variant-index="${index}">
                <div class="card-header bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="fas fa-exchange-alt text-success me-2"></i>
                            Variant ${index + 1}
                        </h6>
                        <button type="button" class="btn btn-sm btn-outline-danger remove-variant-btn" 
                                data-index="${index}">
                            <i class="fas fa-trash"></i> Remove
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <label class="form-label">Language Code</label>
                            <select class="form-select variant-language-select" 
                                    name="variants[${index}].form.lang" 
                                    data-index="${index}" required>
                                <option value="">Select language</option>
                                ${languageOptions}
                            </select>
                            <div class="form-text">ISO 639 language code</div>
                        </div>
                        <div class="col-md-8">
                            <label class="form-label">Variant Text</label>
                            <input type="text" class="form-control" 
                                   name="variants[${index}].form.text"
                                   value="${variant.form.text || ''}" 
                                   placeholder="Enter variant form" required>
                            <div class="form-text">The variant spelling or form</div>
                        </div>
                    </div>
                    
                    <div class="row mt-3">
                        <div class="col-md-6">
                            <label class="form-label">Variant Type</label>
                            <select class="form-select" name="variants[${index}].type">
                                <option value="">Select type</option>
                                ${this.createVariantTypeOptions(variant.type)}
                            </select>
                            <div class="form-text">Type of variant (optional)</div>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Note</label>
                            <input type="text" class="form-control" 
                                   name="variants[${index}].note"
                                   value="${variant.note || ''}" 
                                   placeholder="Optional note about this variant">
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    createVariantTypeOptions(selectedType) {
        return this.variantTypes.map(type => 
            `<option value="${type.value}" ${selectedType === type.value ? 'selected' : ''}>
                ${type.description.en || type.value} (${type.abbrev})
             </option>`
        ).join('');
    }
    
    initializeLanguageDropdown(index) {
        const selector = `select[data-index="${index}"]`;
        const selectElement = document.querySelector(selector);
        
        if (selectElement && window.$ && window.$.fn.select2) {
            $(selectElement).select2({
                placeholder: 'Select or type language code',
                allowClear: true,
                tags: true,
                width: '100%'
            });
        }
    }
    
    reindexVariants() {
        const variantElements = this.container.querySelectorAll('.variant-item');
        
        variantElements.forEach((element, newIndex) => {
            // Update data attribute
            element.setAttribute('data-variant-index', newIndex);
            
            // Update header number
            const header = element.querySelector('.card-header h6');
            if (header) {
                header.innerHTML = `
                    <i class="fas fa-exchange-alt text-success me-2"></i>
                    Variant ${newIndex + 1}
                `;
            }
            
            // Update all input names and IDs
            const inputs = element.querySelectorAll('input, select');
            inputs.forEach(input => {
                const name = input.getAttribute('name');
                if (name) {
                    const newName = name.replace(/variants\[\d+\]/, `variants[${newIndex}]`);
                    input.setAttribute('name', newName);
                }
                
                const dataIndex = input.getAttribute('data-index');
                if (dataIndex !== null) {
                    input.setAttribute('data-index', newIndex);
                }
            });
            
            // Update remove button
            const removeBtn = element.querySelector('.remove-variant-btn');
            if (removeBtn) {
                removeBtn.setAttribute('data-index', newIndex);
            }
        });
    }
    
    showEmptyState() {
        this.container.innerHTML = `
            <div class="empty-state text-center py-4">
                <i class="fas fa-exchange-alt fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Variant Forms</h5>
                <p class="text-muted">Add variant forms to represent different spellings or dialectal forms.</p>
            </div>
        `;
    }
    
    hideEmptyState() {
        const emptyState = this.container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
    }
    
    // Validation helper
    validateVariants() {
        const variants = this.getExistingVariantsFromForm();
        const errors = [];
        
        variants.forEach((variant, index) => {
            if (!variant.form.lang) {
                errors.push(`Variant ${index + 1}: Language code is required`);
            }
            
            if (!variant.form.text) {
                errors.push(`Variant ${index + 1}: Variant text is required`);
            }
            
            // Check for duplicate language codes
            const duplicates = variants.filter(v => v.form.lang === variant.form.lang);
            if (duplicates.length > 1) {
                errors.push(`Variant ${index + 1}: Duplicate language code "${variant.form.lang}"`);
            }
        });
        
        return errors;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('variants-container')) {
        window.variantFormsManager = new VariantFormsManager('variants-container');
    }
});
