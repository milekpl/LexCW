/**
 * Etymology Forms Management Component
 * 
 * Provides dynamic etymology editing functionality for entry forms.
 * Supports LIFT-compliant etymology editing with Form/Gloss multilingual objects.
 * Integrates with LIFT ranges for etymology types.
 *
 * Data model (matches Python Etymology model):
 *   { type: 'borrowing', source: 'Latin',
 *     form: { 'la': 'cattus' },          // {lang: text} dict
 *     gloss: { 'en': 'cat' } }            // {lang: text} dict
 */

class EtymologyFormsManager {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.etymologies = this._normalizeEtymologies(options.etymologies || []);
        this.rangeId = options.rangeId || 'etymology';
        this.ranges = null;
        this.options = {
            allowAdd: options.allowAdd !== false,
            allowRemove: options.allowRemove !== false,
            ...options
        };
        
        this.init();
    }
    
    /**
     * Normalize incoming etymology data to ensure form/gloss are {lang: text} dicts.
     * Handles both the new dict format and legacy {lang:'', text:''} format.
     */
    _normalizeEtymologies(raw) {
        return raw.map(etym => {
            const e = { ...etym };
            // Normalize form: convert {lang:'', text:''} → {lang: text}
            if (e.form && typeof e.form === 'object' && !Array.isArray(e.form)) {
                if (e.form.text !== undefined) {
                    // Legacy format: {lang: 'la', text: 'cattus'} → {'la': 'cattus'}
                    const lang = e.form.lang || '';
                    const text = e.form.text || '';
                    e.form = lang ? { [lang]: text } : {};
                }
                // If already {lang: text} dict, leave as-is
            } else {
                e.form = {};
            }
            // Normalize gloss similarly
            if (e.gloss && typeof e.gloss === 'object' && !Array.isArray(e.gloss)) {
                if (e.gloss.text !== undefined) {
                    const lang = e.gloss.lang || 'en';
                    const text = e.gloss.text || '';
                    e.gloss = lang ? { [lang]: text } : {};
                }
            } else {
                e.gloss = {};
            }
            return e;
        });
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
            if (window.rangesLoader) {
                const rangeData = await window.rangesLoader.loadRange(this.rangeId);
                if (rangeData && rangeData.values) {
                    this.ranges = rangeData.values;
                    return;
                }
            }
            
            const response = await fetch(`/api/ranges-editor/${this.rangeId}`);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data && result.data.values) {
                    this.ranges = result.data.values;
                    return;
                }
            }
            this.ranges = this.getDefaultEtymologyTypes();
        } catch (error) {
            console.error(`Error loading etymology types:`, error);
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
        const listHtml = this.etymologies.length === 0
            ? `<div class="no-etymologies-message text-muted"><em>No etymologies added yet.</em></div>`
            : this.etymologies.map((etymology, index) => this.renderEtymologyForm(etymology, index)).join('');
        
        this.container.innerHTML = `
            <div class="etymology-forms-wrapper">
                <div class="etymology-forms-list">${listHtml}</div>
            </div>
        `;
        
        // Populate type dropdowns after DOM is rendered
        this.etymologies.forEach((etymology, index) => {
            this._populateTypeDropdown(index, etymology.type);
        });
    }
    
    _populateTypeDropdown(index, selectedValue) {
        const selectEl = this.container.querySelector(`.etymology-type-select[data-index="${index}"]`);
        if (!selectEl) return;
        
        // Clear existing options except the first (placeholder)
        while (selectEl.options.length > 1) {
            selectEl.remove(1);
        }
        
        if (window.rangesLoader && this.ranges) {
            window.rangesLoader.populateSelect(selectEl, this.rangeId, {
                selectedValue: selectedValue || '',
                hierarchical: true,
                searchable: true
            });
        } else if (this.ranges) {
            this.ranges.forEach(type => {
                const option = document.createElement('option');
                option.value = type.value;
                option.textContent = type.value;
                if (selectedValue === type.value) option.selected = true;
                selectEl.appendChild(option);
            });
        }
    }
    
    renderEtymologyForm(etymology, index) {
        const type = etymology.type || '';
        const source = etymology.source || '';
        const formEntries = etymology.form ? Object.entries(etymology.form) : [];
        const glossEntries = etymology.gloss ? Object.entries(etymology.gloss) : [];
        
        // Render form language variants
        const formFields = formEntries.length === 0
            ? this._renderFormField(index, '', '', 'form')
            : formEntries.map(([lang, text]) => this._renderFormField(index, lang, text, 'form')).join('');
        
        // Render gloss language variants
        const glossFields = glossEntries.length === 0
            ? this._renderFormField(index, 'en', '', 'gloss')
            : glossEntries.map(([lang, text]) => this._renderFormField(index, lang, text, 'gloss')).join('');
        
        return `
            <div class="etymology-form-item card mb-3" data-index="${index}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span class="etymology-type-label fw-bold">${type || 'New Etymology'}</span>
                    <div>
                        <button type="button" class="btn btn-sm btn-secondary move-up-btn" data-item-type="etymology" title="Move Up">↑</button>
                        <button type="button" class="btn btn-sm btn-secondary move-down-btn" data-item-type="etymology" title="Move Down">↓</button>
                        ${this.options.allowRemove ? `
                            <button type="button" class="btn btn-sm btn-outline-danger remove-etymology-btn" title="Remove">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label class="form-label">Etymology Type</label>
                                <select class="form-control etymology-type-select" 
                                        name="etymologies[${index}][type]" 
                                        data-index="${index}" required>
                                    <option value="">Select type...</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label class="form-label">Source Language</label>
                                <input type="text" class="form-control etymology-source-input" 
                                       name="etymologies[${index}][source]" 
                                       value="${this._escapeAttr(source)}" 
                                       placeholder="e.g., Latin, Proto-Germanic" required>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Etymological Form (multilingual) -->
                    <div class="etymology-form-section mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <label class="form-label mb-0">Etymological Form</label>
                            <button type="button" class="btn btn-sm btn-outline-secondary add-etymology-lang-btn" 
                                    data-index="${index}" data-field="form" title="Add form in another language">
                                <i class="fas fa-plus"></i> Add Language
                            </button>
                        </div>
                        <div class="etymology-form-langs" data-index="${index}" data-field="form">
                            ${formFields}
                        </div>
                        <small class="form-text text-muted">The etymon (ancestor word form)</small>
                    </div>
                    
                    <!-- Gloss (multilingual) -->
                    <div class="etymology-gloss-section mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <label class="form-label mb-0">Gloss / Meaning</label>
                            <button type="button" class="btn btn-sm btn-outline-secondary add-etymology-lang-btn" 
                                    data-index="${index}" data-field="gloss" title="Add gloss in another language">
                                <i class="fas fa-plus"></i> Add Language
                            </button>
                        </div>
                        <div class="etymology-gloss-langs" data-index="${index}" data-field="gloss">
                            ${glossFields}
                        </div>
                        <small class="form-text text-muted">Translation or meaning of the etymon</small>
                    </div>
                </div>
            </div>
        `;
    }
    
    _renderFormField(index, lang, text, field) {
        const safeLang = this._escapeAttr(lang);
        const safeText = this._escapeAttr(text);
        return `
            <div class="input-group mb-2 etymology-${field}-lang-row">
                <input type="text" class="form-control etymology-${field}-lang-input" 
                       name="etymologies[${index}][${field}][${safeLang}]"
                       value="${safeLang}" placeholder="Lang"
                       style="max-width: 90px;" title="Language code">
                <input type="text" class="form-control etymology-${field}-text-input" 
                       name="etymologies[${index}][${field}][${safeLang}]"
                       value="${safeText}" placeholder="${field === 'form' ? 'Etymological form' : 'Meaning/gloss'}">
                <button type="button" class="btn btn-outline-danger remove-etymology-lang-btn" 
                        title="Remove this language">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
    }
    
    _escapeAttr(str) {
        return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
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
                    const item = e.target.closest('.etymology-form-item');
                    this.removeEtymology(parseInt(item.dataset.index));
                }
            });
        }
        
        // Add language variant buttons
        this.container.addEventListener('click', (e) => {
            const btn = e.target.closest('.add-etymology-lang-btn');
            if (btn) {
                const index = parseInt(btn.dataset.index);
                const field = btn.dataset.field; // 'form' or 'gloss'
                this._addLanguageVariant(index, field);
            }
        });
        
        // Remove language variant buttons
        this.container.addEventListener('click', (e) => {
            const btn = e.target.closest('.remove-etymology-lang-btn');
            if (btn) {
                const row = btn.closest('.etymology-form-lang-row, .etymology-gloss-lang-row') ||
                            btn.closest('[class*="etymology-"][class*="-lang-row"]');
                if (row) row.remove();
                this._syncFromDOM();
            }
        });
        
        // Type change
        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('etymology-type-select')) {
                const item = e.target.closest('.etymology-form-item');
                const index = parseInt(item.dataset.index);
                const label = item.querySelector('.etymology-type-label');
                if (label) label.textContent = e.target.value || 'New Etymology';
                this._syncFromDOM();
            }
        });
        
        // Text input changes
        this.container.addEventListener('input', (e) => {
            if (e.target.closest('.etymology-form-item')) {
                this._syncFromDOM();
            }
        });
    }
    
    _addLanguageVariant(index, field) {
        const container = this.container.querySelector(
            `.etymology-${field}-langs[data-index="${index}"]`
        );
        if (!container) return;
        
        const row = document.createElement('div');
        row.className = `input-group mb-2 etymology-${field}-lang-row`;
        row.innerHTML = `
            <input type="text" class="form-control etymology-${field}-lang-input" 
                   placeholder="Lang" style="max-width: 90px;" title="Language code">
            <input type="text" class="form-control etymology-${field}-text-input" 
                   placeholder="${field === 'form' ? 'Etymological form' : 'Meaning/gloss'}">
            <button type="button" class="btn btn-outline-danger remove-etymology-lang-btn" title="Remove">
                <i class="fas fa-times"></i>
            </button>
        `;
        container.appendChild(row);
        row.querySelector('input').focus();
    }
    
    /**
     * Read all etymology data from the DOM into this.etymologies.
     * Called after any form change to keep the model in sync.
     */
    _syncFromDOM() {
        const items = this.container.querySelectorAll('.etymology-form-item');
        this.etymologies = Array.from(items).map(item => {
            const index = parseInt(item.dataset.index);
            const typeSelect = item.querySelector('.etymology-type-select');
            const sourceInput = item.querySelector('.etymology-source-input');
            
            // Read form dict: {lang: text} from lang+text input pairs
            const form = {};
            const formRows = item.querySelectorAll('.etymology-form-lang-row');
            formRows.forEach(row => {
                const langInput = row.querySelector('.etymology-form-lang-input');
                const textInput = row.querySelector('.etymology-form-text-input');
                if (langInput && textInput) {
                    const lang = langInput.value.trim();
                    const text = textInput.value.trim();
                    if (lang && text) form[lang] = text;
                }
            });
            
            // Read gloss dict similarly
            const gloss = {};
            const glossRows = item.querySelectorAll('.etymology-gloss-lang-row');
            glossRows.forEach(row => {
                const langInput = row.querySelector('.etymology-gloss-lang-input');
                const textInput = row.querySelector('.etymology-gloss-text-input');
                if (langInput && textInput) {
                    const lang = langInput.value.trim();
                    const text = textInput.value.trim();
                    if (lang && text) gloss[lang] = text;
                }
            });
            
            return {
                type: typeSelect ? typeSelect.value : '',
                source: sourceInput ? sourceInput.value.trim() : '',
                form: form,
                gloss: gloss
            };
        });
    }
    
    addEtymology() {
        this.etymologies.push({
            type: '',
            source: '',
            form: {},
            gloss: { 'en': '' }
        });
        this.render();
        this.attachEventListeners();
        this._populateTypeDropdown(this.etymologies.length - 1, '');
    }
    
    removeEtymology(index) {
        if (index >= 0 && index < this.etymologies.length) {
            this.etymologies.splice(index, 1);
            this.render();
            this.attachEventListeners();
        }
    }
    
    getEtymologies() {
        this._syncFromDOM();
        return this.etymologies;
    }
    
    setEtymologies(etymologies) {
        this.etymologies = this._normalizeEtymologies(etymologies || []);
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

window.EtymologyFormsManager = EtymologyFormsManager;
