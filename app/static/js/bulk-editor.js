/**
 * Bulk Editor - Comprehensive bulk operations interface
 * Features: ConditionBuilder, PipelineEditor, and execution controls
 */

// Simple notification helper that works without ValidationUI
function showBulkEditorNotification(message, type = 'info') {
    // Try to use ValidationUI if available
    if (typeof window.validationUI !== 'undefined' && window.validationUI) {
        window.validationUI.showToast('Bulk Editor', message, type);
        return;
    }

    // Fallback: use Bootstrap alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        <strong>Bulk Editor:</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);

    // Auto-remove after 3 seconds
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 300);
    }, 3000);
}

/**
 * ConditionBuilder - Visual query builder for entry conditions
 * Supports field conditions, relational conditions, and compound AND/OR
 */
class ConditionBuilder {
    constructor(container, options = {}) {
        this.container = typeof container === 'string'
            ? document.querySelector(container)
            : container;
        this.options = {
            showRelations: true,
            maxDepth: 3,
            ...options
        };
        this.conditions = [];
        this.ranges = null;
        this.init();
    }

    async init() {
        await this.loadRanges();
        this.render();
    }

    async loadRanges() {
        try {
            const response = await fetch('/api/ranges');
            if (response.ok) {
                this.ranges = await response.json();
            }
        } catch (e) {
            console.warn('[ConditionBuilder] Could not load ranges:', e);
            this.ranges = { traits: [], relations: [] };
        }
    }

    getFieldOptions() {
        return [
            { value: 'lexical_unit', label: 'Lexical Unit', type: 'text' },
            { value: 'trait', label: 'Trait', type: 'trait' },
            { value: 'definition', label: 'Definition', type: 'multitext' },
            { value: 'example', label: 'Example', type: 'text' },
            { value: 'pronunciation', label: 'Pronunciation', type: 'text' },
            { value: 'etymology', label: 'Etymology', type: 'text' },
            { value: 'note', label: 'Note', type: 'text' },
            { value: 'relation', label: 'Relation', type: 'relation' }
        ];
    }

    getOperators() {
        return [
            { value: 'equals', label: 'Equals' },
            { value: 'not_equals', label: 'Not Equals' },
            { value: 'contains', label: 'Contains' },
            { value: 'starts_with', label: 'Starts With' },
            { value: 'ends_with', label: 'Ends With' },
            { value: 'is_empty', label: 'Is Empty' },
            { value: 'is_not_empty', label: 'Is Not Empty' },
            { value: 'regex', label: 'Matches Regex' }
        ];
    }

    render() {
        this.container.innerHTML = `
            <div class="condition-builder">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="mb-0">Query Conditions</h6>
                    <button class="btn btn-sm btn-outline-primary" id="add-condition-btn">
                        + Add Condition
                    </button>
                </div>
                <div id="conditions-container"></div>
                ${this.conditions.length > 1 ? `
                    <div class="mt-2">
                        <small class="text-muted">Combine with:</small>
                        <div class="btn-group btn-group-sm ms-2">
                            <button class="btn btn-outline-secondary active" data-combine="and">AND</button>
                            <button class="btn btn-outline-secondary" data-combine="or">OR</button>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;

        this.container.querySelector('#add-condition-btn')
            .addEventListener('click', () => this.addCondition());

        this.renderConditions();

        // Combine buttons
        this.container.querySelectorAll('[data-combine]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.container.querySelectorAll('[data-combine]').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.combineMode = e.target.dataset.combine;
            });
        });
    }

    addCondition() {
        this.conditions.push({
            field: 'lexical_unit',
            operator: 'contains',
            value: ''
        });
        this.renderConditions();
    }

    removeCondition(index) {
        this.conditions.splice(index, 1);
        this.renderConditions();
    }

    updateCondition(index, field, value) {
        this.conditions[index][field] = value;
        this.renderConditions();
    }

    renderConditions() {
        const container = this.container.querySelector('#conditions-container');
        container.innerHTML = '';

        this.conditions.forEach((condition, index) => {
            const row = document.createElement('div');
            row.className = 'condition-row mb-2 p-2 border rounded';
            row.innerHTML = this.renderConditionRow(condition, index);
            container.appendChild(row);
        });
    }

    renderConditionRow(condition, index) {
        const fields = this.getFieldOptions();
        const operators = this.getOperators();

        const fieldOptions = fields.map(f =>
            `<option value="${f.value}" ${condition.field === f.value ? 'selected' : ''}>${f.label}</option>`
        ).join('');

        const operatorOptions = operators.map(op =>
            `<option value="${op.value}" ${condition.operator === op.value ? 'selected' : ''}>${op.label}</option>`
        ).join('');

        let valueInput = '';
        const fieldDef = fields.find(f => f.value === condition.field);

        if (fieldDef?.type === 'trait') {
            // Trait dropdown with values from ranges
            const traitTypes = this.ranges?.traits || [];
            valueInput = `
                <select class="form-select form-select-sm" data-field="type" data-index="${index}">
                    <option value="">Select trait type...</option>
                    ${traitTypes.map(t => `<option value="${t.type}" ${condition.type === t.type ? 'selected' : ''}>${t.type}</option>`).join('')}
                </select>
                <select class="form-select form-select-sm" data-field="value" data-index="${index}">
                    <option value="">Any value</option>
                    ${traitTypes.filter(t => t.type === condition.type).flatMap(t => t.values || []).map(v =>
                        `<option value="${v}" ${condition.value === v ? 'selected' : ''}>${v}</option>`
                    ).join('')}
                </select>
            `;
        } else if (fieldDef?.type === 'relation') {
            // Relation type dropdown
            const relationTypes = this.ranges?.relations || [];
            valueInput = `
                <select class="form-select form-select-sm" data-field="type" data-index="${index}">
                    <option value="">Select relation type...</option>
                    ${relationTypes.map(r =>
                        `<option value="${r.type}" ${condition.type === r.type ? 'selected' : ''}>${r.type}</option>`
                    ).join('')}
                </select>
                <input type="text" class="form-control form-control-sm"
                    placeholder="Target lexical unit..."
                    data-field="target" data-index="${index}"
                    value="${condition.target || ''}">
            `;
        } else if (condition.operator === 'is_empty' || condition.operator === 'is_not_empty') {
            valueInput = '<small class="text-muted">(no value needed)</small>';
        } else {
            valueInput = `
                <input type="text" class="form-control form-control-sm"
                    placeholder="Value..."
                    data-field="value" data-index="${index}"
                    value="${condition.value || ''}">
            `;
        }

        return `
            <div class="row g-2 align-items-center">
                <div class="col-auto">
                    <select class="form-select form-select-sm" data-field="field" data-index="${index}">
                        ${fieldOptions}
                    </select>
                </div>
                <div class="col-auto">
                    <select class="form-select form-select-sm" data-field="operator" data-index="${index}">
                        ${operatorOptions}
                    </select>
                </div>
                <div class="col">
                    ${valueInput}
                </div>
                <div class="col-auto">
                    <button class="btn btn-sm btn-outline-danger remove-condition" data-index="${index}">
                        &times;
                    </button>
                </div>
            </div>
        `;
    }

    getCondition() {
        if (this.conditions.length === 0) return null;

        const combineOp = this.combineMode || (this.conditions.length > 1 ? 'and' : null);

        if (this.conditions.length === 1) {
            return this.conditions[0];
        }

        if (combineOp === 'and') {
            return { and: this.conditions };
        } else {
            return { or: this.conditions };
        }
    }

    setCondition(conditions) {
        if (Array.isArray(conditions)) {
            this.conditions = conditions;
        } else if (conditions.and) {
            this.conditions = conditions.and;
            this.combineMode = 'and';
        } else if (conditions.or) {
            this.conditions = conditions.or;
            this.combineMode = 'or';
        }
        this.renderConditions();
    }
}

/**
 * PipelineEditor - Chain multiple bulk operations
 * Each step can set, clear, append values, or modify relations
 */
class PipelineEditor {
    constructor(container, options = {}) {
        this.container = typeof container === 'string'
            ? document.querySelector(container)
            : container;
        this.options = {
            maxSteps: 10,
            ...options
        };
        this.steps = [];
        this.ranges = null;
        this.init();
    }

    async init() {
        await this.loadRanges();
        this.render();
    }

    async loadRanges() {
        try {
            const response = await fetch('/api/ranges');
            if (response.ok) {
                this.ranges = await response.json();
            }
        } catch (e) {
            console.warn('[PipelineEditor] Could not load ranges:', e);
            this.ranges = { traits: [], relations: [] };
        }
    }

    getActionTypes() {
        return [
            { value: 'set', label: 'Set Value', icon: 'pencil' },
            { value: 'clear', label: 'Clear Field', icon: 'trash' },
            { value: 'append', label: 'Append Text', icon: 'plus' },
            { value: 'prepend', label: 'Prepend Text', icon: 'arrow-up' },
            { value: 'add_relation', label: 'Add Relation', icon: 'link' },
            { value: 'remove_relation', label: 'Remove Relation', icon: 'x-circle' },
            { value: 'replace_relation', label: 'Replace Relation Target', icon: 'refresh' }
        ];
    }

    getFieldOptions() {
        return [
            { value: 'lexical_unit', label: 'Lexical Unit' },
            { value: 'trait', label: 'Trait', subfield: true },
            { value: 'definition', label: 'Definition' },
            { value: 'example', label: 'Example' },
            { value: 'pronunciation', label: 'Pronunciation' },
            { value: 'etymology', label: 'Etymology' },
            { value: 'note', label: 'Note' }
        ];
    }

    render() {
        this.container.innerHTML = `
            <div class="pipeline-editor">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="mb-0">Operation Pipeline</h6>
                    <button class="btn btn-sm btn-outline-primary" id="add-step-btn">
                        + Add Step
                    </button>
                </div>
                <div id="pipeline-steps"></div>
                ${this.steps.length > 0 ? `
                    <div class="mt-3 border-top pt-2">
                        <div class="d-flex gap-2 align-items-center">
                            <input type="checkbox" class="form-check-input" id="preview-mode">
                            <label class="form-check-label" for="preview-mode">Preview only (no changes)</label>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;

        this.container.querySelector('#add-step-btn')
            .addEventListener('click', () => this.addStep());

        this.renderSteps();
    }

    addStep() {
        if (this.steps.length >= this.options.maxSteps) {
            showBulkEditorNotification('Maximum pipeline steps reached', 'warning');
            return;
        }

        this.steps.push({
            type: 'set',
            field: 'lexical_unit',
            value: ''
        });
        this.renderSteps();
    }

    removeStep(index) {
        this.steps.splice(index, 1);
        this.renderSteps();
    }

    updateStep(index, field, value) {
        this.steps[index][field] = value;
        this.renderSteps();
    }

    renderSteps() {
        const container = this.container.querySelector('#pipeline-steps');
        container.innerHTML = '';

        this.steps.forEach((step, index) => {
            const stepEl = document.createElement('div');
            stepEl.className = 'pipeline-step mb-3 p-3 border rounded bg-light';
            stepEl.innerHTML = this.renderStepCard(step, index);
            container.appendChild(stepEl);
        });

        // Attach event listeners
        container.querySelectorAll('.remove-step').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.removeStep(parseInt(e.target.dataset.index));
            });
        });

        container.querySelectorAll('[data-field]').forEach(input => {
            input.addEventListener('change', (e) => {
                const index = parseInt(e.target.dataset.index);
                const field = e.target.dataset.field;
                this.updateStep(index, field, e.target.value);
            });
        });

        // Initialize EntrySearchSelect for relation steps
        this.steps.forEach((step, index) => {
            if (['add_relation', 'remove_relation', 'replace_relation'].includes(step.type)) {
                this.initEntrySearchSelect(index, step.target);
            }
        });
    }

    initEntrySearchSelect(index, selectedValue) {
        const containerId = `relation-target-container-${index}`;
        const container = document.getElementById(containerId);
        if (!container || typeof EntrySearchSelect === 'undefined') return;

        // Store reference for later access
        if (!this.searchSelectors) this.searchSelectors = {};

        this.searchSelectors[index] = new EntrySearchSelect(container, {
            placeholder: 'Search for target entry...',
            onSelect: (entryId, entryData) => {
                this.steps[index].target = entryId;
                // Update hidden input for getPipeline()
                this.updateStep(index, 'target', entryId);
            }
        });

        // If we have an existing target value, try to set it
        if (selectedValue) {
            this.searchSelectors[index].setValue(selectedValue, selectedValue);
        }
    }

    renderStepCard(step, index) {
        const actionTypes = this.getActionTypes();
        const fields = this.getFieldOptions();

        const actionOptions = actionTypes.map(a =>
            `<option value="${a.value}" ${step.type === a.value ? 'selected' : ''}>${a.label}</option>`
        ).join('');

        const fieldOptions = fields.map(f => {
            const hasSubfield = f.subfield ? ' (with type)' : '';
            return `<option value="${f.value}" ${step.field === f.value ? 'selected' : ''}>${f.label}${hasSubfield}</option>`;
        }).join('');

        let valueInput = '';

        switch (step.type) {
            case 'set':
            case 'append':
            case 'prepend':
                if (step.field === 'trait') {
                    const traitTypes = this.ranges?.traits || [];
                    valueInput = `
                        <div class="row g-2">
                            <div class="col-6">
                                <select class="form-select form-select-sm" data-field="trait_type" data-index="${index}">
                                    <option value="">Trait type...</option>
                                    ${traitTypes.map(t =>
                                        `<option value="${t.type}" ${step.trait_type === t.type ? 'selected' : ''}>${t.type}</option>`
                                    ).join('')}
                                </select>
                            </div>
                            <div class="col-6">
                                <input type="text" class="form-control form-control-sm"
                                    placeholder="Value..."
                                    data-field="value" data-index="${index}"
                                    value="${step.value || ''}">
                            </div>
                        </div>
                    `;
                } else {
                    valueInput = `
                        <input type="text" class="form-control form-control-sm"
                            placeholder="Value..."
                            data-field="value" data-index="${index}"
                            value="${step.value || ''}">
                    `;
                }
                break;

            case 'add_relation':
            case 'remove_relation':
            case 'replace_relation':
                const relTypes = this.ranges?.relations || [];
                valueInput = `
                    <div class="row g-2">
                        <div class="col-6">
                            <select class="form-select form-select-sm" data-field="relation_type" data-index="${index}">
                                <option value="">Relation type...</option>
                                ${relTypes.map(r =>
                                    `<option value="${r.type}" ${step.relation_type === r.type ? 'selected' : ''}>${r.type}</option>`
                                ).join('')}
                            </select>
                        </div>
                        <div class="col-6">
                            <div id="relation-target-container-${index}" class="relation-target-selector"></div>
                        </div>
                    </div>
                `;
                break;

            case 'clear':
                valueInput = '<small class="text-mast">Clears the field value</small>';
                break;
        }

        return `
            <div class="d-flex justify-content-between align-items-start">
                <div class="d-flex gap-2 align-items-center">
                    <span class="badge bg-secondary">${index + 1}</span>
                    <select class="form-select form-select-sm" style="width: auto;" data-field="type" data-index="${index}">
                        ${actionOptions}
                    </select>
                    <span class="text-muted">→</span>
                    <select class="form-select form-select-sm" style="width: auto;" data-field="field" data-index="${index}">
                        ${fieldOptions}
                    </select>
                    ${valueInput}
                </div>
                <button class="btn btn-sm btn-outline-danger remove-step" data-index="${index}">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
        `;
    }

    getPipeline() {
        return this.steps.map((step, index) => {
            const pipelineStep = {
                type: step.type,
                order: index + 1
            };

            // Common fields
            if (step.field) pipelineStep.field = step.field;
            if (step.value) pipelineStep.value = step.value;

            // Trait-specific
            if (step.trait_type) {
                pipelineStep.trait_type = step.trait_type;
                pipelineStep.field = 'trait';
            }

            // Relation-specific
            if (step.relation_type) {
                pipelineStep.relation_type = step.relation_type;
                pipelineStep.field = 'relation';
            }
            if (step.target) pipelineStep.target = step.target;

            return pipelineStep;
        });
    }

    setPipeline(steps) {
        this.steps = steps.map(s => ({
            type: s.type || 'set',
            field: s.field || 'lexical_unit',
            value: s.value || '',
            trait_type: s.trait_type || '',
            relation_type: s.relation_type || '',
            target: s.target || ''
        }));
        this.renderSteps();

        // Re-initialize search selectors after render
        this.steps.forEach((step, index) => {
            if (['add_relation', 'remove_relation', 'replace_relation'].includes(step.type)) {
                this.initEntrySearchSelect(index, step.target);
            }
        });
    }
}

/**
 * Main BulkEditor class - orchestrates the bulk editing interface
 */
class BulkEditor {
    constructor() {
        this.selectedEntries = new Set();
        this.currentOperation = null;
        this.checkboxColumnAdded = false;
        this.conditionBuilder = null;
        this.pipelineEditor = null;
        this.init();
    }

    init() {
        this.setupSelectionHandlers();
        this.setupBulkActionPanel(); // Must come before setupOperationHandlers
        this.setupOperationHandlers();
        this.setupEntriesRenderedListener();
        this.setupModalHandlers();
        console.log('[BulkEditor] Initialized');
    }

    setupEntriesRenderedListener() {
        let retryCount = 0;
        const maxRetries = 5;

        const handleEntriesRendered = (event) => {
            console.log('[BulkEditor] entriesRendered event received, count:', event.detail.entryCount);
            this.addCheckboxColumn();

            if (!this.checkboxColumnAdded && retryCount < maxRetries) {
                retryCount++;
                setTimeout(() => {
                    this.addCheckboxColumn();
                    this.addCheckboxToRows();
                }, 100);
                return;
            }

            this.addCheckboxToRows();
        };

        document.addEventListener('entriesRendered', handleEntriesRendered);

        if (document.querySelector('#entries-list tr[data-entry-id]')) {
            console.log('[BulkEditor] Entries already present, adding checkboxes');
            this.addCheckboxColumn();
            this.addCheckboxToRows();
        }
    }

    setupSelectionHandlers() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('bulk-select-checkbox')) {
                const entryId = e.target.dataset.entryId;
                if (e.target.checked) {
                    this.selectedEntries.add(entryId);
                } else {
                    this.selectedEntries.delete(entryId);
                }
                this.updateSelectionUI();
            }

            if (e.target.id === 'bulk-select-all') {
                this.toggleSelectAll(e.target.checked);
            }
        });
    }

    setupOperationHandlers() {
        const advancedBtn = document.getElementById('bulk-advanced-btn');
        if (advancedBtn) {
            advancedBtn.addEventListener('click', () => this.showAdvancedBulkModal());
        }

        const clearBtn = document.getElementById('bulk-clear-selection-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearSelection());
        }
    }

    setupBulkActionPanel() {
        const entriesHeader = document.querySelector('.card-header');
        if (entriesHeader && !document.getElementById('bulk-actions-panel')) {
            const panel = this.createBulkActionPanel();
            entriesHeader.insertAdjacentHTML('beforeend', panel);
        }
    }

    createBulkActionPanel() {
        return `
            <div id="bulk-actions-panel" class="mt-2" style="display: none;">
                <div class="alert alert-info d-flex align-items-center flex-wrap gap-2">
                    <span class="me-2"><strong>Bulk Actions:</strong> <span id="selected-count">0</span> entries selected</span>
                    <button class="btn btn-sm btn-primary me-2" id="bulk-advanced-btn">
                        <i class="bi bi-pencil"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-secondary" id="bulk-clear-selection-btn">Clear</button>
                </div>
            </div>
        `;
    }

    updateSelectionUI() {
        const count = this.selectedEntries.size;
        const panel = document.getElementById('bulk-actions-panel');
        const countSpan = document.getElementById('selected-count');

        if (panel) {
            panel.style.display = count > 0 ? 'block' : 'none';
            if (countSpan) countSpan.textContent = count;
        }

        const selectAll = document.getElementById('bulk-select-all');
        if (selectAll && count > 0) {
            const totalCheckboxes = document.querySelectorAll('.bulk-select-checkbox').length;
            selectAll.checked = count === totalCheckboxes;
            selectAll.indeterminate = count > 0 && count < totalCheckboxes;
        }
    }

    toggleSelectAll(checked) {
        const checkboxes = document.querySelectorAll('.bulk-select-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = checked;
            const entryId = cb.dataset.entryId;
            if (checked) {
                this.selectedEntries.add(entryId);
            } else {
                this.selectedEntries.delete(entryId);
            }
        });
        this.updateSelectionUI();
    }

    clearSelection() {
        this.selectedEntries.clear();
        this.toggleSelectAll(false);
    }

    addCheckboxColumn() {
        const tableHead = document.getElementById('entries-table-head');
        if (!tableHead) {
            console.log('[BulkEditor] Table head not found');
            return;
        }

        if (this.checkboxColumnAdded) return;

        let selectAllTh = tableHead.querySelector('th.bulk-select-header');
        if (selectAllTh) {
            this.checkboxColumnAdded = true;
            return;
        }

        let firstTh = tableHead.querySelector('th');
        if (!firstTh) return;

        selectAllTh = document.createElement('th');
        selectAllTh.className = 'bulk-select-header';
        selectAllTh.style.width = '40px';
        selectAllTh.innerHTML = `
            <input type="checkbox" id="bulk-select-all" class="form-check-input" title="Select all">
        `;

        tableHead.querySelector('tr').insertBefore(selectAllTh, firstTh);
        this.checkboxColumnAdded = true;
        console.log('[BulkEditor] Checkbox column added to header');
    }

    addCheckboxToRows() {
        const rows = document.querySelectorAll('#entries-list tr[data-entry-id]');
        let addedCount = 0;
        rows.forEach(row => {
            if (!row.querySelector('.bulk-select-checkbox')) {
                const firstTd = row.querySelector('td');
                if (firstTd) {
                    const checkboxTd = document.createElement('td');
                    checkboxTd.innerHTML = `
                        <input type="checkbox" class="form-check-input bulk-select-checkbox"
                                data-entry-id="${row.dataset.entryId}">
                    `;
                    row.insertBefore(checkboxTd, firstTd);
                    addedCount++;
                }
            }
        });
        if (addedCount > 0) {
            console.log(`[BulkEditor] Added ${addedCount} checkboxes to rows`);
        }
    }

    setupModalHandlers() {
        // Execute button
        document.addEventListener('click', (e) => {
            if (e.target.id === 'execute-bulk-action') {
                this.executeBulkAction();
            }
            if (e.target.id === 'preview-bulk-action') {
                this.previewBulkAction();
            }
        });
    }

    showAdvancedBulkModal() {
        const selectedCount = this.selectedEntries.size;
        const modalHtml = `
            <div class="modal fade" id="bulk-editor-modal" tabindex="-1" style="z-index: 1055;">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Bulk Editor</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <!-- Scope Selector -->
                            <div class="card mb-3">
                                <div class="card-header bg-light py-2">
                                    <strong>Which entries to modify?</strong>
                                </div>
                                <div class="card-body py-2">
                                    <div class="form-check mb-2">
                                        <input class="form-check-input" type="radio" name="bulk-scope"
                                            id="scope-selected" value="selected" ${selectedCount > 0 ? 'checked' : ''}>
                                        <label class="form-check-label" for="scope-selected">
                                            <strong>Selected entries</strong>
                                            <span class="text-muted">- operate on ${selectedCount} checked entries</span>
                                        </label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="radio" name="bulk-scope"
                                            id="scope-query" value="query" ${selectedCount === 0 ? 'checked' : ''}>
                                        <label class="form-check-label" for="scope-query">
                                            <strong>Find by conditions</strong>
                                            <span class="text-muted">- query entries matching criteria</span>
                                        </label>
                                    </div>
                                </div>
                            </div>

                            <!-- Query Builder (shown when Query scope selected) -->
                            <div id="query-builder-section" class="${selectedCount > 0 ? 'd-none' : ''}">
                                <div id="condition-builder-container"></div>
                            </div>

                            <!-- Actions Section -->
                            <div class="mt-3">
                                <label class="form-label fw-bold">What to do:</label>
                                <div class="row g-2 mb-2">
                                    <div class="col-md-4">
                                        <select class="form-select" id="quick-action-type">
                                            <option value="set">Set (replace)</option>
                                            <option value="clear">Clear (remove)</option>
                                            <option value="append">Append (add to end)</option>
                                            <option value="prepend">Prepend (add to start)</option>
                                        </select>
                                    </div>
                                    <div class="col-md-4">
                                        <input type="text" class="form-control"
                                            id="quick-action-field" placeholder="Field (e.g., trait, lexical_unit)">
                                    </div>
                                    <div class="col-md-4">
                                        <input type="text" class="form-control"
                                            id="quick-action-value" placeholder="Value">
                                    </div>
                                </div>
                            </div>

                            <!-- Advanced Pipeline -->
                            <div class="mt-3">
                                <button class="btn btn-link btn-sm p-0" type="button"
                                    data-bs-toggle="collapse" data-bs-target="#pipeline-collapse">
                                    <i class="bi bi-chevron-right"></i> Multi-step pipeline
                                </button>
                                <div class="collapse mt-2" id="pipeline-collapse">
                                    <div class="card card-body">
                                        <div id="pipeline-editor-container"></div>
                                    </div>
                                </div>
                            </div>

                            <!-- Entry Count Info -->
                            <div class="alert alert-secondary mt-3 mb-0 py-2">
                                <small>
                                    <strong>Will affect:</strong>
                                    <span id="affected-count">${selectedCount}</span> entries
                                    <span class="text-muted" id="scope-hint">
                                        (${selectedCount > 0 ? 'selected on current page' : 'matching query'})
                                    </span>
                                </small>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-outline-info" id="preview-bulk-action">
                                Preview
                            </button>
                            <button type="button" class="btn btn-primary" id="execute-bulk-action">
                                Execute
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (!document.getElementById('bulk-editor-modal')) {
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }

        // Initialize builders after modal is shown
        const modal = document.getElementById('bulk-editor-modal');
        modal.addEventListener('shown.bs.modal', () => {
            // Scope change handlers
            const scopeSelected = modal.querySelector('#scope-selected');
            const scopeQuery = modal.querySelector('#scope-query');
            const querySection = modal.querySelector('#query-builder-section');
            const affectedCount = modal.querySelector('#affected-count');
            const scopeHint = modal.querySelector('#scope-hint');

            const updateScope = () => {
                if (scopeSelected.checked) {
                    querySection.classList.add('d-none');
                    affectedCount.textContent = this.selectedEntries.size;
                    scopeHint.textContent = '(selected on current page)';
                } else {
                    querySection.classList.remove('d-none');
                    affectedCount.textContent = '?';
                    scopeHint.textContent = '(matching query - will count when executed)';
                }
            };

            scopeSelected?.addEventListener('change', updateScope);
            scopeQuery?.addEventListener('change', updateScope);

            if (!this.conditionBuilder) {
                this.conditionBuilder = new ConditionBuilder(
                    modal.querySelector('#condition-builder-container')
                );
            }
            if (!this.pipelineEditor) {
                this.pipelineEditor = new PipelineEditor(
                    modal.querySelector('#pipeline-editor-container')
                );
            }
        }, { once: true });

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        modal.querySelector('[data-bs-dismiss="modal"]').addEventListener('click', () => {
            bsModal.hide();
        });

        modal.addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    }

    async executeBulkAction() {
        const activeTab = document.querySelector('#bulk-editor-tabs .nav-link.active');
        const condition = this.conditionBuilder?.getCondition();
        const entryIds = Array.from(this.selectedEntries);
        const preview = document.getElementById('preview-mode')?.checked || false;

        if (!condition && entryIds.length === 0) {
            showBulkEditorNotification('Please specify query conditions or select entries', 'error');
            return;
        }

        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

        try {
            let response;

            if (this.pipelineEditor && this.pipelineEditor.steps.length > 0) {
                // Use pipeline
                const pipeline = this.pipelineEditor.getPipeline();
                response = await fetch('/bulk/pipeline', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': csrfToken
                    },
                    body: JSON.stringify({
                        condition,
                        entry_ids: entryIds.length > 0 ? entryIds : undefined,
                        steps: pipeline,
                        preview
                    })
                });
            } else {
                // Use single action
                const actionType = document.getElementById('quick-action-type')?.value || 'set';
                const actionField = document.getElementById('quick-action-field')?.value || 'lexical_unit';
                const actionValue = document.getElementById('quick-action-value')?.value || '';

                response = await fetch('/bulk/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': csrfToken
                    },
                    body: JSON.stringify({
                        condition,
                        entry_ids: entryIds.length > 0 ? entryIds : undefined,
                        action: {
                            type: actionType,
                            field: actionField,
                            value: actionValue
                        },
                        preview
                    })
                });
            }

            const result = await response.json();

            if (response.ok) {
                if (preview) {
                    showBulkEditorNotification(
                        `Preview: ${result.would_affect || result.summary?.success || 0} entries would be affected`,
                        'info'
                    );
                } else {
                    const summary = result.summary || { success: result.results?.length || 0 };
                    showBulkEditorNotification(
                        `Successfully processed ${summary.success || 0} entries${summary.failed ? `, ${summary.failed} failed` : ''}`,
                        'success'
                    );
                    this.clearSelection();
                }

                // Refresh entries table
                if (typeof refreshEntriesTable === 'function') {
                    refreshEntriesTable();
                } else if (typeof loadEntries === 'function') {
                    loadEntries(1, currentSortBy, currentSortOrder);
                }

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('bulk-editor-modal'));
                if (modal) modal.hide();

            } else {
                showBulkEditorNotification(result.error || 'Bulk operation failed', 'error');
            }
        } catch (error) {
            console.error('[BulkEditor] Execute error:', error);
            showBulkEditorNotification('Network error: ' + error.message, 'error');
        }
    }

    async previewBulkAction() {
        // Set preview mode and call execute
        const previewCheckbox = document.getElementById('preview-mode');
        if (previewCheckbox) previewCheckbox.checked = true;
        await this.executeBulkAction();
    }
}

// Initialize on entries page
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('entries-table')) {
        window.bulkEditor = new BulkEditor();
    }
});

// Make available globally
if (typeof window !== 'undefined') {
    window.BulkEditor = BulkEditor;
    window.ConditionBuilder = ConditionBuilder;
    window.PipelineEditor = PipelineEditor;
}
