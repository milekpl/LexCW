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
            const response = await fetch('/api/ranges/etymology-types');
            if (response.ok) {
                const data = await response.json();
                this.ranges = data.values || [];
            } else {
                console.warn('Failed to load etymology types, using defaults');
                this.ranges = this.getDefaultEtymologyTypes();
            }
        } catch (error) {
            console.error('Error loading etymology types:', error);
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
                <div class="etymology-forms-header">
                    <h4>Etymology</h4>
                    ${this.options.allowAdd ? `
                        <button type="button" class="btn btn-sm btn-success add-etymology-btn">
                            <i class="fas fa-plus"></i> Add Etymology
                        </button>
                    ` : ''}
                </div>
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
    }
    
    renderEtymologyForm(etymology, index) {
        const etymologyTypes = this.ranges.map(type => 
            `<option value="${type.value}" ${etymology.type === type.value ? 'selected' : ''}>${type.value}</option>`
        ).join('');
        
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
                                <select class="form-control etymology-type-select" 
                                        name="etymologies[${index}][type]" required>
                                    <option value="">Select type...</option>
                                    ${etymologyTypes}
                                </select>
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
            const addButton = this.container.querySelector('.add-etymology-btn');
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
