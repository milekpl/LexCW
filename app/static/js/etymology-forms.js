/**
 * Etymology Forms Management Component
 * 
 * Provides dynamic etymology editing functionality for entry forms.
 * Supports LIFT-compliant etymology editing with Form/Gloss objects.
 * Integrates with LIFT ranges for etymology types.
 */

class EtymologyFormsManager {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.etymologies = options.etymologies || [];
        this.rangeId = options.rangeId || 'etymology'; // Default to using 'etymology' range
        this.ranges = null;
        this.options = {
            allowAdd: options.allowAdd !== false,
            allowRemove: options.allowRemove !== false,
            ...options
        };
        
        this.init();
    }
    
    async init() {
        if (!this.container) {
            console.error('Etymology forms container not found');
            return;
        }
        
        await this.loadRanges();
        this.render();
        this.attachEventListeners();
    }
    
    async loadRanges() {
        try {
            // Use the global rangesLoader if available
            if (window.rangesLoader) {
                const rangeData = await window.rangesLoader.loadRange(this.rangeId);
                if (rangeData && rangeData.values) {
                    this.ranges = rangeData.values;
                    return;
                }
            }
            
            // Fallback to direct API call if rangesLoader isn't available
            const response = await fetch(`/api/ranges/${this.rangeId}`);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data && result.data.values) {
                    this.ranges = result.data.values;
                    return;
                }
            } else {
                console.warn(`Failed to load etymology types from range '${this.rangeId}', using defaults`);
                this.ranges = this.getDefaultEtymologyTypes();
            }
        } catch (error) {
            console.error(`Error loading etymology types from range '${this.rangeId}':`, error);
            this.ranges = this.getDefaultEtymologyTypes();
        }
    }
    
    getDefaultEtymologyTypes() {
        return [
            { id: 'inheritance', value: 'inheritance', abbrev: 'inh', description: { en: 'Inherited word' } },
            { id: 'borrowing', value: 'borrowing', abbrev: 'bor', description: { en: 'Borrowed word' } },
            { id: 'compound', value: 'compound', abbrev: 'comp', description: { en: 'Compound word' } },
            { id: 'derivation', value: 'derivation', abbrev: 'der', description: { en: 'Derived word' } },
            { id: 'calque', value: 'calque', abbrev: 'calq', description: { en: 'Calque/loan translation' } },
            { id: 'semantic', value: 'semantic', abbrev: 'sem', description: { en: 'Semantic change' } },
            { id: 'onomatopoeia', value: 'onomatopoeia', abbrev: 'onom', description: { en: 'Onomatopoeia' } }
        ];
    }
    
    render() {
        this.container.innerHTML = `
            <div class="etymology-forms-wrapper">
                <div class="etymology-forms-list">
                    ${this.etymologies.length === 0 ? `
                        <div class="no-etymologies-message text-muted">
                            <em>No etymologies added yet.</em>
                        </div>
                    ` : ''}
                    ${this.etymologies.map((etymology, index) => this.renderEtymologyForm(etymology, index)).join('')}
                </div>
            </div>
        `;
        
        // Replace select placeholders with actual select elements
        this.etymologies.forEach((etymology, index) => {
            const placeholder = this.container.querySelector(`.etymology-type-select-placeholder[data-index="${index}"]`);
            if (placeholder) {
                // Create a new select element
                const selectElement = document.createElement('select');
                selectElement.className = 'form-control etymology-type-select';
                selectElement.name = `etymologies[${index}][type]`;
                selectElement.required = true;
                selectElement.dataset.index = index;
                
                // Replace the placeholder with the select
                placeholder.parentNode.replaceChild(selectElement, placeholder);
                
                // Populate the select with rangesLoader
                if (window.rangesLoader) {
                    window.rangesLoader.populateSelect(selectElement, this.rangeId, {
                        selectedValue: etymology.type || '',
                        hierarchical: true,
                        searchable: true
                    });
                } else {
                    // Fallback if rangesLoader isn't available
                    const emptyOption = document.createElement('option');
                    emptyOption.value = '';
                    emptyOption.textContent = 'Select type...';
                    selectElement.appendChild(emptyOption);
                    
                    this.ranges.forEach(type => {
                        const option = document.createElement('option');
                        option.value = type.value;
                        option.textContent = type.value;
                        if (etymology.type === type.value) {
                            option.selected = true;
                        }
                        selectElement.appendChild(option);
                    });
                }
            }
        });
    }
    
    renderEtymologyForm(etymology, index) {
        // Create select element for etymology types with support for hierarchy
        const selectElement = document.createElement('select');
        selectElement.className = 'form-control etymology-type-select';
        selectElement.name = `etymologies[${index}][type]`;
        selectElement.required = true;
        selectElement.dataset.index = index;
        
        // Add empty option
        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = 'Select type...';
        selectElement.appendChild(emptyOption);
        
        // Populate the select element
        if (window.rangesLoader) {
            // Defer this to post-rendering to ensure the element is in the DOM
            setTimeout(() => {
                window.rangesLoader.populateSelect(selectElement, this.rangeId, {
                    selectedValue: etymology.type || '',
                    hierarchical: true,
                    searchable: true
                });
            }, 0);
        } else {
            // Fallback to direct rendering if rangesLoader isn't available
            this.ranges.forEach(type => {
                const option = document.createElement('option');
                option.value = type.value;
                option.textContent = type.value;
                if (etymology.type === type.value) {
                    option.selected = true;
                }
                selectElement.appendChild(option);
            });
        }
        
        // Create the HTML for the select - we'll replace it with the actual element after rendering
        const selectPlaceholder = `<div class="etymology-type-select-placeholder" data-index="${index}"></div>`;
        
        return `
            <div class="etymology-form-item card mb-3" data-index="${index}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span class="etymology-type-label">${etymology.type || 'Etymology'}</span>
                    ${this.options.allowRemove ? `
                        <button type="button" class="btn btn-sm btn-outline-danger remove-etymology-btn">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : ''}
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label class="form-label">Etymology Type</label>
                                ${selectPlaceholder}
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label class="form-label">Source</label>
                                <input type="text" class="form-control etymology-source-input" 
                                       name="etymologies[${index}][source]" 
                                       value="${etymology.source || ''}" 
                                       placeholder="e.g., Latin, Proto-Germanic" required>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label class="form-label">Etymological Form</label>
                                <div class="input-group">
                                    <input type="text" class="form-control etymology-form-lang-input" 
                                           name="etymologies[${index}][form][lang]" 
                                           value="${etymology.form?.lang || ''}" 
                                           placeholder="Language code" 
                                           style="max-width: 100px;">
                                    <input type="text" class="form-control etymology-form-text-input" 
                                           name="etymologies[${index}][form][text]" 
                                           value="${etymology.form?.text || ''}" 
                                           placeholder="Etymological form">
                                </div>
                                <small class="form-text text-muted">Language code (e.g., la, ang, gem-pro) and form</small>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label class="form-label">Gloss/Meaning</label>
                                <div class="input-group">
                                    <input type="text" class="form-control etymology-gloss-lang-input" 
                                           name="etymologies[${index}][gloss][lang]" 
                                           value="${etymology.gloss?.lang || 'en'}" 
                                           placeholder="Language" 
                                           style="max-width: 100px;">
                                    <input type="text" class="form-control etymology-gloss-text-input" 
                                           name="etymologies[${index}][gloss][text]" 
                                           value="${etymology.gloss?.text || ''}" 
                                           placeholder="Meaning/gloss">
                                </div>
                                <small class="form-text text-muted">Language code and meaning</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    attachEventListeners() {
        // Add etymology button
        if (this.options.allowAdd) {
            const addButton = document.getElementById('add-etymology-btn');
            if (addButton) {
                addButton.addEventListener('click', () => this.addEtymology());
            }
        }
        
        // Remove etymology buttons
        if (this.options.allowRemove) {
            this.container.addEventListener('click', (e) => {
                if (e.target.closest('.remove-etymology-btn')) {
                    const etymologyItem = e.target.closest('.etymology-form-item');
                    const index = parseInt(etymologyItem.dataset.index);
                    this.removeEtymology(index);
                }
            });
        }
        
        // Etymology type change handlers
        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('etymology-type-select')) {
                const etymologyItem = e.target.closest('.etymology-form-item');
                const index = parseInt(etymologyItem.dataset.index);
                this.etymologies[index].type = e.target.value;
                
                // Update label
                const label = etymologyItem.querySelector('.etymology-type-label');
                if (label) {
                    label.textContent = e.target.value || 'Etymology';
                }
            }
        });
        
        // Form field change handlers
        this.container.addEventListener('input', (e) => {
            const etymologyItem = e.target.closest('.etymology-form-item');
            if (!etymologyItem) return;
            
            const index = parseInt(etymologyItem.dataset.index);
            if (!this.etymologies[index]) return;
            
            if (e.target.classList.contains('etymology-source-input')) {
                this.etymologies[index].source = e.target.value;
            } else if (e.target.classList.contains('etymology-form-lang-input')) {
                if (!this.etymologies[index].form) this.etymologies[index].form = {};
                this.etymologies[index].form.lang = e.target.value;
            } else if (e.target.classList.contains('etymology-form-text-input')) {
                if (!this.etymologies[index].form) this.etymologies[index].form = {};
                this.etymologies[index].form.text = e.target.value;
            } else if (e.target.classList.contains('etymology-gloss-lang-input')) {
                if (!this.etymologies[index].gloss) this.etymologies[index].gloss = {};
                this.etymologies[index].gloss.lang = e.target.value;
            } else if (e.target.classList.contains('etymology-gloss-text-input')) {
                if (!this.etymologies[index].gloss) this.etymologies[index].gloss = {};
                this.etymologies[index].gloss.text = e.target.value;
            }
        });
    }
    
    addEtymology() {
        const newEtymology = {
            type: '',
            source: '',
            form: { lang: '', text: '' },
            gloss: { lang: 'en', text: '' }
        };
        
        this.etymologies.push(newEtymology);
        this.render();
        this.attachEventListeners();
        
        // Focus on the new etymology type field
        const newEtymologyForm = this.container.querySelector('.etymology-form-item:last-child .etymology-type-select');
        if (newEtymologyForm) {
            newEtymologyForm.focus();
        }
    }
    
    removeEtymology(index) {
        if (index >= 0 && index < this.etymologies.length) {
            this.etymologies.splice(index, 1);
            this.render();
            this.attachEventListeners();
        }
    }
    
    getEtymologies() {
        return this.etymologies;
    }
    
    setEtymologies(etymologies) {
        this.etymologies = etymologies || [];
        this.render();
        this.attachEventListeners();
    }
    
    validate() {
        let isValid = true;
        const errors = [];
        
        this.etymologies.forEach((etymology, index) => {
            if (!etymology.type) {
                isValid = false;
                errors.push(`Etymology ${index + 1}: Type is required`);
            }
            if (!etymology.source) {
                isValid = false;
                errors.push(`Etymology ${index + 1}: Source is required`);
            }
        });
        
        return { isValid, errors };
    }
}

// Export for use in other modules
window.EtymologyFormsManager = EtymologyFormsManager;
