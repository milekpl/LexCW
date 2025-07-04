/**
 * Variant Forms Manager
 * 
 * JavaScript component for managing LIFT relation-based variants in the entry editor.
 * Displays variants from relations with variant-type traits, as per project specification.
 */

class VariantFormsManager {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.variantRelations = [];
        
        // Accept variant relations from options (passed during initialization)
        if (options.variantRelations && Array.isArray(options.variantRelations)) {
            console.log('[VARIANT DEBUG] Received variant relations via options:', options.variantRelations);
            this.variantRelations = options.variantRelations;
        }
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        
        // Delay rendering to ensure data is available
        setTimeout(() => {
            this.renderExistingVariants();
        }, 50);
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
        
        // Update header when variant type changes
        this.container.addEventListener('change', (e) => {
            if (e.target.name && e.target.name.includes('variant_type')) {
                const variantItem = e.target.closest('.variant-item');
                if (variantItem) {
                    const index = parseInt(variantItem.dataset.variantIndex);
                    const header = variantItem.querySelector('.card-header h6');
                    if (header) {
                        header.innerHTML = `
                            <i class="fas fa-code-branch me-2"></i>
                            Variant Relation ${index + 1}: ${e.target.value || 'Unknown Type'}
                        `;
                    }
                }
            }
        });
    }
    
    renderExistingVariants() {
        // Get variant data from the entry's variant_relations
        const existingVariants = this.getExistingVariantRelationsFromEntry();
        
        console.log('[VARIANT DEBUG] renderExistingVariants() called');
        console.log('[VARIANT DEBUG] Existing variants:', existingVariants);
        console.log('[VARIANT DEBUG] Variant count:', existingVariants.length);
        
        // Clear container
        this.container.innerHTML = '';
        
        // Render each existing variant relation
        existingVariants.forEach((variantRelation, index) => {
            console.log('[VARIANT DEBUG] Rendering variant', index, ':', variantRelation);
            this.renderVariantRelation(variantRelation, index);
        });
        
        // If no variants exist, show empty state
        if (existingVariants.length === 0) {
            console.log('[VARIANT DEBUG] No variants found, showing empty state');
            this.showEmptyState();
        } else {
            console.log('[VARIANT DEBUG] Rendered', existingVariants.length, 'variants');
        }
    }
    
    getExistingVariantRelationsFromEntry() {
        // Extract variant relations from the global entry data if available
        const variants = [];
        
        console.log('[VARIANT DEBUG] Starting getExistingVariantRelationsFromEntry()');
        
        try {
            // Check if variant relations are available in the window
            if (typeof window.variantRelations !== 'undefined' && Array.isArray(window.variantRelations)) {
                console.log('[VARIANT DEBUG] Found window.variantRelations:', window.variantRelations);
                console.log('[VARIANT DEBUG] Length:', window.variantRelations.length);
                return window.variantRelations;
            }
            
            // Fallback: look for entryData with variant_relations
            if (typeof entryData !== 'undefined' && entryData.variant_relations) {
                console.log('[VARIANT DEBUG] Found variant relations in entryData:', entryData.variant_relations);
                return entryData.variant_relations;
            }
            
            // Additional fallback: check window.entry
            if (typeof window.entry !== 'undefined' && window.entry.variant_relations) {
                console.log('[VARIANT DEBUG] Found variant relations in window.entry:', window.entry.variant_relations);
                return window.entry.variant_relations;
            }
            
            console.log('[VARIANT DEBUG] No variant relations found in global scope');
            console.log('[VARIANT DEBUG] Available window properties:', Object.keys(window).filter(k => k.includes('variant') || k.includes('entry')));
        } catch (e) {
            console.warn('[VARIANT DEBUG] Error accessing variant relations data:', e);
        }
        
        return variants;
    }
    
    addVariant() {
        // Get current variants to determine next index
        const existingVariants = this.getExistingVariantRelationsFromEntry();
        const currentVariantElements = this.container.querySelectorAll('.variant-item');
        const newIndex = Math.max(existingVariants.length, currentVariantElements.length);
        
        // Create a new variant relation template
        const newVariantRelation = {
            ref: '',
            variant_type: 'Unspecified Variant',
            type: '_component-lexeme',
            order: newIndex
        };
        
        // Render the new variant
        this.renderVariantRelation(newVariantRelation, newIndex);
        this.hideEmptyState();
        
        // Scroll to the new variant and focus on the ref input
        const newVariantElement = this.container.querySelector(`[data-variant-index="${newIndex}"]`);
        if (newVariantElement) {
            newVariantElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            
            // Focus on the ref input after a short delay
            setTimeout(() => {
                const refInput = newVariantElement.querySelector('input[name*="ref"]');
                if (refInput) {
                    refInput.focus();
                }
            }, 300);
        }
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
    
    renderVariantRelation(variantRelation, index) {
        const variantHtml = this.createVariantRelationHtml(variantRelation, index);
        this.container.insertAdjacentHTML('beforeend', variantHtml);
    }
    
    createVariantRelationHtml(variantRelation, index) {
        return `
            <div class="variant-item card mb-3" data-variant-index="${index}">
                <div class="card-header bg-success text-white">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="fas fa-code-branch me-2"></i>
                            Variant Relation ${index + 1}: ${variantRelation.variant_type || 'Unknown Type'}
                        </h6>
                        <button type="button" class="btn btn-sm btn-light remove-variant-btn" 
                                data-index="${index}" title="Remove variant">
                            <i class="fas fa-trash text-danger"></i>
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <label class="form-label fw-bold">Target Entry Reference</label>
                            <input type="text" class="form-control" 
                                   name="variant_relations[${index}][ref]"
                                   value="${variantRelation.ref || ''}" 
                                   placeholder="Entry ID that this entry is a variant of"
                                   required>
                            <div class="form-text">LIFT entry ID or GUID of the main/canonical entry</div>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Variant Type</label>
                            <select class="form-control" 
                                    name="variant_relations[${index}][variant_type]" required>
                                <option value="">Select variant type</option>
                                <option value="Spelling Variant" ${variantRelation.variant_type === 'Spelling Variant' ? 'selected' : ''}>Spelling Variant</option>
                                <option value="Dialectal Variant" ${variantRelation.variant_type === 'Dialectal Variant' ? 'selected' : ''}>Dialectal Variant</option>
                                <option value="Unspecified Variant" ${variantRelation.variant_type === 'Unspecified Variant' ? 'selected' : ''}>Unspecified Variant</option>
                                <option value="Stopień najwyższy" ${variantRelation.variant_type === 'Stopień najwyższy' ? 'selected' : ''}>Stopień najwyższy</option>
                                <option value="Plural Form" ${variantRelation.variant_type === 'Plural Form' ? 'selected' : ''}>Plural Form</option>
                                <option value="Past Tense" ${variantRelation.variant_type === 'Past Tense' ? 'selected' : ''}>Past Tense</option>
                            </select>
                            <div class="form-text">Type of variant relationship</div>
                        </div>
                    </div>
                    
                    <div class="row mt-3">
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Relation Type</label>
                            <input type="text" class="form-control" 
                                   name="variant_relations[${index}][type]"
                                   value="${variantRelation.type || '_component-lexeme'}" 
                                   readonly>
                            <div class="form-text">LIFT relation type (typically "_component-lexeme")</div>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Order</label>
                            <input type="number" class="form-control" 
                                   name="variant_relations[${index}][order]"
                                   value="${variantRelation.order || index}" 
                                   placeholder="0" min="0">
                            <div class="form-text">Order of the relation</div>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Status</label>
                            <div class="mt-2">
                                <span class="badge bg-success fs-6">
                                    <i class="fas fa-check-circle me-1"></i>Active Variant
                                </span>
                                <div class="form-text">This variant will be saved to the LIFT file</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="alert alert-info mt-3">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>Variant Relationship:</strong> This entry is a variant of the target entry 
                        (<code>${variantRelation.ref || 'target entry'}</code>). 
                        In LIFT format, this creates a relation with a variant-type trait.
                    </div>
                </div>
            </div>
        `;
    }
    
    reindexVariants() {
        const variantElements = this.container.querySelectorAll('.variant-item');
        
        variantElements.forEach((element, newIndex) => {
            // Update data attribute
            element.setAttribute('data-variant-index', newIndex);
            
            // Update header number and variant type display
            const header = element.querySelector('.card-header h6');
            if (header) {
                const variantTypeSelect = element.querySelector('select[name*="variant_type"]');
                const currentVariantType = variantTypeSelect ? variantTypeSelect.value : 'Unknown Type';
                header.innerHTML = `
                    <i class="fas fa-code-branch me-2"></i>
                    Variant Relation ${newIndex + 1}: ${currentVariantType}
                `;
            }
            
            // Update all input names and IDs
            const inputs = element.querySelectorAll('input, select');
            inputs.forEach(input => {
                const name = input.getAttribute('name');
                if (name && name.includes('variant_relations')) {
                    const newName = name.replace(/variant_relations\[\d+\]/, `variant_relations[${newIndex}]`);
                    input.setAttribute('name', newName);
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
            <div class="empty-state text-center py-5">
                <i class="fas fa-code-branch fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Variants Found</h5>
                <p class="text-muted">
                    This entry does not have any variant relations defined.
                </p>
                <p class="text-muted">
                    <strong>What are variants?</strong> Variants are different forms or spellings of the same lexical item, 
                    such as "protestor" vs "protester", or "Protestant ethic" vs "Protestant work ethic".
                </p>
                <p class="text-muted">
                    <strong>How variants work:</strong> Variants are stored as LIFT relations with variant-type traits. 
                    When you create a relation with a variant-type trait, it will appear here as a variant.
                </p>
                <div class="mt-3">
                    <button type="button" class="btn btn-success" onclick="window.variantFormsManager.addVariant()">
                        <i class="fas fa-plus me-2"></i>Add New Variant
                    </button>
                </div>
            </div>
        `;
    }
    
    hideEmptyState() {
        const emptyState = this.container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
    }
    
    /**
     * Force re-render of variants - useful when called from template after data is loaded
     */
    forceRender() {
        console.log('[VARIANT DEBUG] forceRender() called');
        this.renderExistingVariants();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('[VARIANT DEBUG] DOMContentLoaded event fired');
    if (document.getElementById('variants-container')) {
        console.log('[VARIANT DEBUG] variants-container found, creating VariantFormsManager');
        window.variantFormsManager = new VariantFormsManager('variants-container');
    } else {
        console.log('[VARIANT DEBUG] variants-container not found in DOM');
    }
});

// Also make the class available immediately
console.log('[VARIANT DEBUG] VariantFormsManager class defined');
