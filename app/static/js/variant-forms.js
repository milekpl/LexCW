/**
 * Variant Forms Manager
 * 
 * JavaScript component for managing LIFT variant forms in the entry editor.
 * Provides dynamic add/remove functionality and Form object editing.
 */

class VariantFormsManager {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.rangeId = options.rangeId || 'variant-types-from-traits'; // Use traits-based variant types
        this.variantTypes = [];
        this.languageCodes = []; // Will be dynamically loaded from API
        
        this.init();
    }
    
    async init() {
        await Promise.all([
            this.loadVariantTypes(),
            this.loadLanguageCodes()
        ]);
        this.setupEventListeners();
        this.renderExistingVariants();
    }
    
    async loadVariantTypes() {
        try {
            // Use the global rangesLoader if available
            if (window.rangesLoader) {
                const rangeData = await window.rangesLoader.loadRange(this.rangeId);
                if (rangeData && rangeData.values) {
                    this.variantTypes = rangeData.values;
                    return;
                }
            }
            
            // Fallback to direct API call if rangesLoader isn't available
            const response = await fetch(`/api/ranges/${this.rangeId}`);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data && result.data.values) {
                    this.variantTypes = result.data.values;
                    return;
                }
            }
        } catch (error) {
            console.warn(`Failed to load variant types from range '${this.rangeId}':`, error);
        }
        
        // Fallback to basic types if loading fails
        this.variantTypes = [
            { id: 'dialectal', value: 'dialectal', abbrev: 'dial', description: { en: 'Dialectal variant' } },
            { id: 'spelling', value: 'spelling', abbrev: 'sp', description: { en: 'Spelling variant' } },
            { id: 'morphological', value: 'morphological', abbrev: 'morph', description: { en: 'Morphological variant' } }
        ];
    }
    
    async loadLanguageCodes() {
        try {
            // Load language codes from API
            const response = await fetch('/api/ranges/language-codes');
            if (response.ok) {
                const result = await response.json();
                if (result.success && Array.isArray(result.data)) {
                    this.languageCodes = result.data;
                    return;
                }
            }
        } catch (error) {
            console.warn('Failed to load language codes:', error);
        }
        
        // Fallback to basic codes if loading fails
        this.languageCodes = [
            'en', 'seh-fonipa'
        ];
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
        
        // Initialize the variant type dropdown using the ranges loader
        if (window.rangesLoader) {
            const typeSelect = this.container.querySelector(`.variant-item[data-variant-index="${index}"] .variant-type-select`);
            if (typeSelect) {
                window.rangesLoader.populateSelect(typeSelect, this.rangeId, {
                    selectedValue: variant.type || '',
                    hierarchical: true,
                    searchable: true
                });
            }
        }
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
                            <label class="form-label">Morphological Type</label>
                            <select class="form-select variant-type-select" 
                                   name="variants[${index}].type"
                                   data-range-id="${this.rangeId}" 
                                   data-selected="${variant.type || ''}">
                                <option value="">Select type</option>
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
        // Get variants data from the page if available
        let variants = [];
        try {
            if (typeof entryVariants !== 'undefined') {
                variants = entryVariants;
            }
        } catch (e) {
            console.warn('No variants data found, starting with empty state');
        }
        
        window.variantFormsManager = new VariantFormsManager('variants-container', {
            rangeId: 'variant-types-from-traits', // Use traits-based variant types instead of morph-type
            variants: variants
        });
    }
});
