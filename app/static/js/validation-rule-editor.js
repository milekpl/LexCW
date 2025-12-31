/**
 * Validation Rule Editor Component
 *
 * Form for editing validation rule properties with live JSON preview.
 */

class ValidationRuleEditor {
    constructor(manager, containerId) {
        this._manager = manager;
        this._container = document.getElementById(containerId);

        if (!this._container) {
            console.error(`Container with id "${containerId}" not found`);
            return;
        }

        // Form state
        this._formData = {};

        // Bind methods
        this._render = this._render.bind(this);
        this._handleInputChange = this._handleInputChange.bind(this);
        this._handleSave = this._handleSave.bind(this);
        this._handleCancel = this._handleCancel.bind(this);
        this._handleTest = this._handleTest.bind(this);
        this._handleJsonChange = this._handleJsonChange.bind(this);

        // Listen for rule selection
        this._manager.on('rule-selected', this._render);
    }

    // ========== Rendering ==========

    _render(rule) {
        if (!rule) {
            this._container.innerHTML = this._renderEmptyState();
            return;
        }

        // Initialize form data from rule
        this._formData = { ...rule };

        const jsonPreview = this._renderJsonPreview();

        this._container.innerHTML = `
            <div class="rule-editor">
                ${this._renderHeader(rule)}
                <div class="rule-editor-body">
                    <div class="rule-editor-form">
                        ${this._renderFormFields(rule)}
                    </div>
                    <div class="rule-editor-preview">
                        ${jsonPreview}
                    </div>
                </div>
                ${this._renderFooter()}
            </div>
        `;

        this._attachEventHandlers();
    }

    _renderEmptyState() {
        return `
            <div class="rule-editor-empty">
                <div class="text-center text-muted py-5">
                    <i class="bi bi-info-circle" style="font-size: 3rem;"></i>
                    <p class="mt-3">Select a rule to edit</p>
                    <p class="text-muted small">Or add a new rule to get started</p>
                </div>
            </div>
        `;
    }

    _renderHeader(rule) {
        return `
            <div class="rule-editor-header">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h5 class="mb-0">${rule.rule_id ? `<code>${this._escapeHtml(rule.rule_id)}</code> - ` : ''}${this._escapeHtml(rule.name)}</h5>
                        ${rule.description ? `<p class="text-muted mb-0 small">${this._escapeHtml(rule.description)}</p>` : ''}
                    </div>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-secondary" onclick="window.validationRulesApp.duplicateRule('${rule.rule_id}')">
                            <i class="bi bi-copy"></i> Duplicate
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="window.validationRulesApp.deleteRule('${rule.rule_id}')">
                            <i class="bi bi-trash"></i> Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    _renderFormFields(rule) {
        const categories = [
            'entry_level', 'sense_level', 'note_validation',
            'pronunciation_level', 'relations_level', 'hierarchical_validation',
            'resource_validation', 'language_validation', 'general'
        ];

        const priorities = ['critical', 'warning', 'informational'];

        const conditions = [
            { value: 'required', label: 'Required' },
            { value: 'if_present', label: 'If Present' },
            { value: 'custom', label: 'Custom' },
            { value: 'prohibited', label: 'Prohibited' }
        ];

        const validationTypes = [
            { value: 'string', label: 'String' },
            { value: 'number', label: 'Number' },
            { value: 'boolean', label: 'Boolean' },
            { value: 'array', label: 'Array' },
            { value: 'object', label: 'Object' },
            { value: 'custom', label: 'Custom Function' }
        ];

        const categoryOptions = categories.map(c =>
            `<option value="${c}" ${rule.category === c ? 'selected' : ''}>${c}</option>`
        ).join('');

        const priorityOptions = priorities.map(p =>
            `<option value="${p}" ${rule.priority === p ? 'selected' : ''}>${p}</option>`
        ).join('');

        const conditionOptions = conditions.map(c =>
            `<option value="${c.value}" ${rule.condition?.type === c.value ? 'selected' : ''}>${c.label}</option>`
        ).join('');

        const validationTypeOptions = validationTypes.map(t =>
            `<option value="${t.value}" ${rule.validation?.type === t.value ? 'selected' : ''}>${t.label}</option>`
        ).join('');

        return `
            <div class="rule-form-section">
                <h6>Basic Information</h6>
                <div class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label">Rule ID</label>
                        <input
                            type="text"
                            class="form-control"
                            name="rule_id"
                            value="${this._escapeHtml(rule.rule_id || '')}"
                            readonly
                        >
                        <div class="form-text">Unique identifier (auto-generated)</div>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Name *</label>
                        <input
                            type="text"
                            class="form-control"
                            name="name"
                            value="${this._escapeHtml(rule.name || '')}"
                            required
                        >
                    </div>
                    <div class="col-12">
                        <label class="form-label">Description</label>
                        <textarea
                            class="form-control"
                            name="description"
                            rows="2"
                        >${this._escapeHtml(rule.description || '')}</textarea>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Category</label>
                            <select class="form-select" name="category">
                            ${categoryOptions}
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Priority</label>
                        <select class="form-select" name="priority">
                            ${priorityOptions}
                        </select>
                    </div>
                </div>
            </div>

            <div class="rule-form-section">
                <h6>Condition</h6>
                <div class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label">Type</label>
                        <select class="form-select" name="condition_type">
                            ${conditionOptions}
                        </select>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">JSONPath</label>
                        <input
                            type="text"
                            class="form-control font-monospace"
                            name="path"
                            value="${this._escapeHtml(rule.path || '')}"
                            placeholder="$.senses[*].id"
                        >
                        <div class="form-text">JSONPath expression to target field</div>
                    </div>
                </div>
            </div>

            <div class="rule-form-section">
                <h6>Validation</h6>
                <div class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label">Type</label>
                        <select class="form-select" name="validation_type">
                            ${validationTypeOptions}
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Min Length/Items</label>
                        <input
                            type="number"
                            class="form-control"
                            name="minLength"
                            value="${rule.validation?.minLength ?? ''}"
                            min="0"
                        >
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Max Length/Items</label>
                        <input
                            type="number"
                            class="form-control"
                            name="maxLength"
                            value="${rule.validation?.maxLength ?? ''}"
                            min="0"
                        >
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Pattern (Regex)</label>
                        <input
                            type="text"
                            class="form-control font-monospace"
                            name="pattern"
                            value="${this._escapeHtml(rule.validation?.pattern || '')}"
                            placeholder="^pattern$"
                        >
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Custom Function</label>
                        <select class="form-select" name="custom_function">
                            <option value="">None</option>
                            <option value="validate_sense_content_or_variant" ${rule.validation?.custom_function === 'validate_sense_content_or_variant' ? 'selected' : ''}>Validate Sense Content or Variant</option>
                            <option value="validate_sense_required_non_variant" ${rule.validation?.custom_function === 'validate_sense_required_non_variant' ? 'selected' : ''}>Validate Sense Required (Non-Variant)</option>
                            <option value="validate_unique_note_types" ${rule.validation?.custom_function === 'validate_unique_note_types' ? 'selected' : ''}>Validate Unique Note Types</option>
                            <option value="validate_note_content" ${rule.validation?.custom_function === 'validate_note_content' ? 'selected' : ''}>Validate Note Content</option>
                            <option value="validate_synonym_antonym_exclusion" ${rule.validation?.custom_function === 'validate_synonym_antonym_exclusion' ? 'selected' : ''}>Validate Synonym/Antonym Exclusion</option>
                            <option value="validate_subsense_depth" ${rule.validation?.custom_function === 'validate_subsense_depth' ? 'selected' : ''}>Validate Subsense Depth</option>
                            <option value="validate_no_circular_components" ${rule.validation?.custom_function === 'validate_no_circular_components' ? 'selected' : ''}>No Circular Component References</option>
                            <option value="validate_no_circular_sense_relations" ${rule.validation?.custom_function === 'validate_no_circular_sense_relations' ? 'selected' : ''}>No Circular Sense Relations</option>
                            <option value="validate_no_circular_entry_relations" ${rule.validation?.custom_function === 'validate_no_circular_entry_relations' ? 'selected' : ''}>No Circular Entry Relations</option>
                            <option value="validate_relation_targets_exist" ${rule.validation?.custom_function === 'validate_relation_targets_exist' ? 'selected' : ''}>Validate Relation Targets Exist</option>
                            <option value="validate_pos_consistency" ${rule.validation?.custom_function === 'validate_pos_consistency' ? 'selected' : ''}>POS Consistency</option>
                            <option value="validate_conflicting_pos" ${rule.validation?.custom_function === 'validate_conflicting_pos' ? 'selected' : ''}>Conflicting POS</option>
                            <option value="validate_date_fields" ${rule.validation?.custom_function === 'validate_date_fields' ? 'selected' : ''}>Validate Date Fields</option>
                            <option value="validate_language_code_format" ${rule.validation?.custom_function === 'validate_language_code_format' ? 'selected' : ''}>Validate Language Code Format</option>
                            <option value="validate_multilingual_note_structure" ${rule.validation?.custom_function === 'validate_multilingual_note_structure' ? 'selected' : ''}>Validate Multilingual Note Structure</option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="rule-form-section">
                <h6>Error Message</h6>
                <div class="row g-3">
                    <div class="col-12">
                        <input
                            type="text"
                            class="form-control"
                            name="error_message"
                            value="${this._escapeHtml(rule.error_message || '')}"
                            placeholder="Error message shown when validation fails"
                        >
                        <div class="form-text">Use {value} to insert the invalid value in the message</div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderJsonPreview() {
        const jsonStr = JSON.stringify(this._formData, null, 2);
        return `
            <div class="json-preview">
                <div class="json-preview-header">
                    <span>JSON Preview</span>
                    <button class="btn btn-sm btn-outline-secondary" onclick="navigator.clipboard.writeText('${this._escapeHtml(jsonStr.replace(/'/g, "\\'"))}').then(() => alert('Copied!'))">
                        <i class="bi bi-clipboard"></i> Copy
                    </button>
                </div>
                <pre class="json-preview-content"><code>${this._escapeHtml(jsonStr)}</code></pre>
            </div>
        `;
    }

    _renderFooter() {
        return `
            <div class="rule-editor-footer">
                <button class="btn btn-secondary" id="rule-editor-cancel">
                    Cancel
                </button>
                <button class="btn btn-outline-primary" id="rule-editor-test">
                    <i class="bi bi-play-circle"></i> Test Rule
                </button>
                <button class="btn btn-primary" id="rule-editor-save">
                    <i class="bi bi-check-circle"></i> Save Changes
                </button>
            </div>
        `;
    }

    // ========== Event Handlers ==========

    _handleInputChange(event) {
        const { name, value, type } = event.target;

        // Handle nested fields
        if (name === 'rule_id') {
            this._formData.rule_id = value;
        } else if (name === 'name') {
            this._formData.name = value;
        } else if (name === 'description') {
            this._formData.description = value;
        } else if (name === 'category') {
            this._formData.category = value;
        } else if (name === 'priority') {
            this._formData.priority = value;
        } else if (name === 'path') {
            this._formData.path = value;
        } else if (name === 'condition_type') {
            if (!this._formData.condition) this._formData.condition = {};
            this._formData.condition.type = value;
        } else if (name === 'validation_type') {
            if (!this._formData.validation) this._formData.validation = {};
            this._formData.validation.type = value;
        } else if (name === 'minLength') {
            if (!this._formData.validation) this._formData.validation = {};
            this._formData.validation.minLength = value ? parseInt(value) : undefined;
        } else if (name === 'maxLength') {
            if (!this._formData.validation) this._formData.validation = {};
            this._formData.validation.maxLength = value ? parseInt(value) : undefined;
        } else if (name === 'pattern') {
            if (!this._formData.validation) this._formData.validation = {};
            this._formData.validation.pattern = value || undefined;
        } else if (name === 'custom_function') {
            if (!this._formData.validation) this._formData.validation = {};
            this._formData.validation.custom_function = value || undefined;
        } else if (name === 'error_message') {
            this._formData.error_message = value;
        }

        // Update preview
        this._updateJsonPreview();

        // Update manager
        if (this._formData.rule_id) {
            this._manager.updateRule(this._formData.rule_id, this._formData);
        }
    }

    _handleJsonChange(event) {
        try {
            const json = JSON.parse(event.target.value);
            this._formData = json;
            this._manager.updateRule(json.rule_id, json);
            this._updateJsonPreview();
        } catch (e) {
            // Invalid JSON, don't update
        }
    }

    _handleSave() {
        const rule = this._manager.currentRule;
        if (!rule) return;

        // Validate required fields
        if (!this._formData.name) {
            alert('Rule name is required');
            return;
        }

        // Save the rule
        this._manager.updateRule(rule.rule_id, this._formData);

        // Refresh list
        window.validationRulesList?.refresh();

        // Show feedback
        this._showFeedback('Rule saved successfully', 'success');
    }

    _handleCancel() {
        this._manager.clearSelection();
    }

    _handleTest() {
        const rule = this._manager.currentRule;
        if (!rule) return;

        // Open test modal
        window.validationRulesApp?.openTestModal(rule);
    }

    // ========== Helpers ==========

    _updateJsonPreview() {
        const previewEl = this._container.querySelector('.json-preview-content code');
        if (previewEl) {
            previewEl.textContent = JSON.stringify(this._formData, null, 2);
        }
    }

    _showFeedback(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${this._escapeHtml(message)}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        // Append to container or body
        const container = document.getElementById('toast-container') || document.body;
        if (!document.getElementById('toast-container')) {
            container.innerHTML = '<div id="toast-container" class="toast-container position-fixed top-0 end-0 p-3"></div>';
        }
        document.getElementById('toast-container').appendChild(toast);

        // Show toast
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();

        // Remove after hidden
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    _escapeHtml(text) {
        if (text == null) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    _attachEventHandlers() {
        // Attach form field change handlers using event delegation
        const form = this._container.querySelector('.rule-editor-form');
        if (form) {
            form.addEventListener('change', (event) => {
                this._handleInputChange(event);
            });
            form.addEventListener('input', (event) => {
                // For text inputs, update immediately on input
                if (event.target.tagName === 'INPUT' && event.target.type === 'text') {
                    this._handleInputChange(event);
                }
            });
        }

        // Attach button handlers
        const cancelBtn = this._container.querySelector('#rule-editor-cancel');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this._handleCancel());
        }

        const testBtn = this._container.querySelector('#rule-editor-test');
        if (testBtn) {
            testBtn.addEventListener('click', () => this._handleTest());
        }

        const saveBtn = this._container.querySelector('#rule-editor-save');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this._handleSave());
        }
    }
}

// Export as global
window.ValidationRuleEditor = ValidationRuleEditor;
