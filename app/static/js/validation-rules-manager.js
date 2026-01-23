/**
 * Validation Rules Manager
 *
 * Centralized state management for the Validation Rule Editor.
 * Handles loading, saving, and testing validation rules.
 */

/**
 * Get CSRF token from meta tag or DictionaryApp
 * @returns {string} The CSRF token or empty string if not available
 */
function getCsrfToken() {
    var metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
        return metaTag.getAttribute('content');
    }
    if (typeof DictionaryApp !== 'undefined' && DictionaryApp.config && DictionaryApp.config.csrfToken) {
        return DictionaryApp.config.csrfToken;
    }
    return '';
}

class ValidationRulesManager {
    constructor() {
        // State
        this._rules = [];
        this._templates = [];
        this._currentRule = null;
        this._originalRules = [];
        this._dirty = false;
        this._testResults = null;
        this._loading = false;
        this._error = null;

        // Event callbacks
        this._listeners = {
            'rules-loaded': [],
            'rules-changed': [],
            'rule-selected': [],
            'dirty-changed': [],
            'test-completed': [],
            'loading-changed': [],
            'error-changed': []
        };

        // API endpoint base
        this._apiBase = '/api/projects';

        // Bind methods
        this._handleApiResponse = this._handleApiResponse.bind(this);
    }

    // ========== Event System ==========

    on(event, callback) {
        if (this._listeners[event]) {
            this._listeners[event].push(callback);
        }
        return () => this.off(event, callback);
    }

    off(event, callback) {
        if (this._listeners[event]) {
            this._listeners[event] = this._listeners[event].filter(cb => cb !== callback);
        }
    }

    _emit(event, data) {
        if (this._listeners[event]) {
            this._listeners[event].forEach(cb => cb(data));
        }
    }

    // ========== State Getters ==========

    get rules() {
        return [...this._rules];
    }

    get templates() {
        return [...this._templates];
    }

    get currentRule() {
        return this._currentRule;
    }

    get isDirty() {
        return this._dirty;
    }

    get isLoading() {
        return this._loading;
    }

    get error() {
        return this._error;
    }

    get testResults() {
        return this._testResults;
    }

    get rulesCount() {
        return this._rules.length;
    }

    get criticalCount() {
        return this._rules.filter(r => r.priority === 'critical').length;
    }

    get warningCount() {
        return this._rules.filter(r => r.priority === 'warning').length;
    }

    get informationalCount() {
        return this._rules.filter(r => r.priority === 'informational').length;
    }

    // ========== API Methods ==========

    /**
     * Load rules for a project
     * @param {string} projectId - Project identifier
     * @param {boolean} includeDefaults - Include default rules if project has none
     */
    async loadRules(projectId, includeDefaults = false) {
        this._setLoading(true);
        this._setError(null);

        try {
            const url = `${this._apiBase}/${projectId}/validation-rules`;
            const params = new URLSearchParams();
            if (includeDefaults) {
                params.append('include_defaults', 'true');
            }

            const response = await fetch(`${url}?${params}`);
            const data = await this._handleApiResponse(response);

            this._rules = data.rules || [];
            this._originalRules = JSON.parse(JSON.stringify(this._rules));
            this._dirty = false;

            this._emit('rules-loaded', { rules: this._rules, source: data.source });
            this._emit('rules-changed', this._rules);
            this._emit('dirty-changed', false);

            return data;
        } catch (error) {
            this._setError(error.message);
            throw error;
        } finally {
            this._setLoading(false);
        }
    }

    /**
     * Load effective rules (project rules or defaults)
     * @param {string} projectId - Project identifier
     */
    async loadEffectiveRules(projectId) {
        this._setLoading(true);
        this._setError(null);

        try {
            const response = await fetch(`${this._apiBase}/${projectId}/validation-rules/effective`);
            const data = await this._handleApiResponse(response);

            this._rules = data.rules || [];
            this._originalRules = JSON.parse(JSON.stringify(this._rules));
            this._dirty = false;

            this._emit('rules-loaded', { rules: this._rules });
            this._emit('rules-changed', this._rules);
            this._emit('dirty-changed', false);

            return data;
        } catch (error) {
            this._setError(error.message);
            throw error;
        } finally {
            this._setLoading(false);
        }
    }

    /**
     * Save rules for a project
     * @param {string} projectId - Project identifier
     * @param {Array} rules - Rules to save
     * @param {string} createdBy - User who made changes
     */
    async saveRules(projectId, rules, createdBy = null) {
        this._setLoading(true);
        this._setError(null);
        const csrfToken = getCsrfToken();

        try {
            const response = await fetch(`${this._apiBase}/${projectId}/validation-rules`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({ rules, created_by: createdBy })
            });

            const data = await this._handleApiResponse(response);

            if (data.success) {
                this._rules = rules;
                this._originalRules = JSON.parse(JSON.stringify(rules));
                this._dirty = false;

                this._emit('rules-changed', this._rules);
                this._emit('dirty-changed', false);
            }

            return data;
        } catch (error) {
            this._setError(error.message);
            throw error;
        } finally {
            this._setLoading(false);
        }
    }

    /**
     * Delete all rules for a project
     * @param {string} projectId - Project identifier
     */
    async deleteRules(projectId) {
        this._setLoading(true);
        this._setError(null);
        const csrfToken = getCsrfToken();

        try {
            const response = await fetch(`${this._apiBase}/${projectId}/validation-rules`, {
                method: 'DELETE',
                headers: {
                    'X-CSRF-TOKEN': csrfToken
                }
            });

            const data = await this._handleApiResponse(response);

            this._rules = [];
            this._originalRules = [];
            this._dirty = false;

            this._emit('rules-changed', this._rules);
            this._emit('dirty-changed', false);

            return data;
        } catch (error) {
            this._setError(error.message);
            throw error;
        } finally {
            this._setLoading(false);
        }
    }

    /**
     * Load available templates
     * @param {string} category - Optional category filter
     */
    async loadTemplates(category = null) {
        this._setLoading(true);
        this._setError(null);

        try {
            const params = new URLSearchParams();
            if (category) {
                params.append('category', category);
            }

            const response = await fetch(`${this._apiBase}/validation-rule-templates?${params}`);
            const data = await this._handleApiResponse(response);

            this._templates = data.templates || [];

            return data;
        } catch (error) {
            this._setError(error.message);
            throw error;
        } finally {
            this._setLoading(false);
        }
    }

    /**
     * Initialize project rules from a template
     * @param {string} projectId - Project identifier
     * @param {string} templateId - Template to use
     * @param {string} createdBy - User who initialized
     */
    async initializeFromTemplate(projectId, templateId, createdBy = null) {
        this._setLoading(true);
        this._setError(null);
        const csrfToken = getCsrfToken();

        try {
            const response = await fetch(`${this._apiBase}/${projectId}/validation-rules/initialize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({
                    template_id: templateId,
                    created_by: createdBy
                })
            });

            const data = await this._handleApiResponse(response);

            if (data.success) {
                await this.loadRules(projectId);
            }

            return data;
        } catch (error) {
            this._setError(error.message);
            throw error;
        } finally {
            this._setLoading(false);
        }
    }

    /**
     * Add rules from a template to existing project rules (MERGE, not replace)
     * @param {string} projectId - Project identifier
     * @param {string} templateId - Template to add rules from
     * @param {string} createdBy - User who added the rules
     */
    async addFromTemplate(projectId, templateId, createdBy = null) {
        this._setLoading(true);
        this._setError(null);
        const csrfToken = getCsrfToken();

        try {
            const response = await fetch(`${this._apiBase}/${projectId}/validation-rules/add-from-template`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({
                    template_id: templateId,
                    created_by: createdBy
                })
            });

            const data = await this._handleApiResponse(response);

            if (data.success) {
                await this.loadRules(projectId);
            }

            return data;
        } catch (error) {
            this._setError(error.message);
            throw error;
        } finally {
            this._setLoading(false);
        }
    }

    /**
     * Test a rule against sample data
     * @param {Object} ruleConfig - Rule configuration
     * @param {Object} testData - Sample data to validate
     */
    async testRule(ruleConfig, testData) {
        this._setLoading(true);
        this._setError(null);
        const csrfToken = getCsrfToken();

        try {
            const response = await fetch(`${this._apiBase}/validation-rules/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({
                    rule: ruleConfig,
                    test_data: testData
                })
            });

            const data = await this._handleApiResponse(response);
            this._testResults = data;

            this._emit('test-completed', data);

            return data;
        } catch (error) {
            this._setError(error.message);
            throw error;
        } finally {
            this._setLoading(false);
        }
    }

    /**
     * Export rules for a project
     * @param {string} projectId - Project identifier
     */
    async exportRules(projectId) {
        try {
            const response = await fetch(`${this._apiBase}/${projectId}/validation-rules/export`);
            const blob = await this._handleApiResponse(response, true);

            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `validation_rules_${projectId}_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            this._setError(error.message);
            throw error;
        }
    }

    /**
     * Import rules for a project
     * @param {string} projectId - Project identifier
     * @param {Object} importData - Imported rule data
     * @param {boolean} replace - Replace existing rules
     * @param {string} createdBy - User who imported
     */
    async importRules(projectId, importData, replace = false, createdBy = null) {
        this._setLoading(true);
        this._setError(null);
        const csrfToken = getCsrfToken();

        try {
            const response = await fetch(`${this._apiBase}/${projectId}/validation-rules/import`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({
                    rules: importData.rules,
                    replace,
                    created_by: createdBy
                })
            });

            const data = await this._handleApiResponse(response);

            if (data.success) {
                await this.loadRules(projectId);
            }

            return data;
        } catch (error) {
            this._setError(error.message);
            throw error;
        } finally {
            this._setLoading(false);
        }
    }

    // ========== Rule Management ==========

    /**
     * Select a rule for editing
     * @param {Object} rule - Rule to select
     */
    selectRule(rule) {
        this._currentRule = rule;
        this._emit('rule-selected', rule);
    }

    /**
     * Clear rule selection
     */
    clearSelection() {
        this._currentRule = null;
        this._emit('rule-selected', null);
    }

    /**
     * Add a new rule
     * @param {Object} rule - Rule to add
     */
    addRule(rule) {
        const newRule = {
            ...rule,
            rule_id: rule.rule_id || this._generateRuleId()
        };

        this._rules.push(newRule);
        this._markDirty();
        this._emit('rules-changed', this._rules);

        return newRule;
    }

    /**
     * Update an existing rule
     * @param {string} ruleId - Rule ID to update
     * @param {Object} updates - Updated properties
     */
    updateRule(ruleId, updates) {
        const index = this._rules.findIndex(r => r.rule_id === ruleId);
        if (index !== -1) {
            this._rules[index] = { ...this._rules[index], ...updates };
            this._markDirty();
            this._emit('rules-changed', this._rules);

            if (this._currentRule && this._currentRule.rule_id === ruleId) {
                this._currentRule = this._rules[index];
                this._emit('rule-selected', this._currentRule);
            }
        }
    }

    /**
     * Delete a rule
     * @param {string} ruleId - Rule ID to delete
     */
    deleteRule(ruleId) {
        const index = this._rules.findIndex(r => r.rule_id === ruleId);
        if (index !== -1) {
            this._rules.splice(index, 1);
            this._markDirty();
            this._emit('rules-changed', this._rules);

            if (this._currentRule && this._currentRule.rule_id === ruleId) {
                this._currentRule = null;
                this._emit('rule-selected', null);
            }
        }
    }

    /**
     * Reorder rules
     * @param {number} fromIndex - Source index
     * @param {number} toIndex - Destination index
     */
    reorderRules(fromIndex, toIndex) {
        if (fromIndex < 0 || fromIndex >= this._rules.length ||
            toIndex < 0 || toIndex >= this._rules.length) {
            return;
        }

        const [removed] = this._rules.splice(fromIndex, 1);
        this._rules.splice(toIndex, 0, removed);
        this._markDirty();
        this._emit('rules-changed', this._rules);
    }

    /**
     * Duplicate a rule
     * @param {string} ruleId - Rule ID to duplicate
     */
    duplicateRule(ruleId) {
        const rule = this._rules.find(r => r.rule_id === ruleId);
        if (rule) {
            const newRule = {
                ...JSON.parse(JSON.stringify(rule)),
                rule_id: this._generateRuleId(),
                name: `${rule.name} (Copy)`
            };
            const index = this._rules.findIndex(r => r.rule_id === ruleId);
            this._rules.splice(index + 1, 0, newRule);
            this._markDirty();
            this._emit('rules-changed', this._rules);
            return newRule;
        }
        return null;
    }

    /**
     * Toggle rule active state
     * @param {string} ruleId - Rule ID to toggle
     */
    toggleRuleActive(ruleId) {
        const rule = this._rules.find(r => r.rule_id === ruleId);
        if (rule) {
            rule.is_active = !rule.is_active;
            this._markDirty();
            this._emit('rules-changed', this._rules);
        }
    }

    // ========== Undo/Redo ==========

    /**
     * Undo last change
     */
    undo() {
        if (this._canUndo()) {
            const temp = JSON.parse(JSON.stringify(this._rules));
            this._rules = JSON.parse(JSON.stringify(this._redoStack.pop()));
            this._redoStack.push(temp);
            this._dirty = true;
            this._emit('rules-changed', this._rules);
            this._emit('dirty-changed', true);
        }
    }

    /**
     * Redo last undone change
     */
    redo() {
        if (this._canRedo()) {
            const temp = JSON.parse(JSON.stringify(this._rules));
            this._rules = JSON.parse(JSON.stringify(this._undoStack.pop()));
            this._undoStack.push(temp);
            this._dirty = true;
            this._emit('rules-changed', this._rules);
            this._emit('dirty-changed', true);
        }
    }

    _canUndo() {
        return this._undoStack.length > 0;
    }

    _canRedo() {
        return this._redoStack.length > 0;
    }

    // ========== Filtering ==========

    /**
     * Get rules by category
     * @param {string} category - Category filter
     */
    getRulesByCategory(category) {
        return this._rules.filter(r => r.category === category);
    }

    /**
     * Get rules by priority
     * @param {string} priority - Priority filter
     */
    getRulesByPriority(priority) {
        return this._rules.filter(r => r.priority === priority);
    }

    /**
     * Search rules
     * @param {string} query - Search query
     */
    searchRules(query) {
        if (!query.trim()) {
            return this._rules;
        }

        const lowerQuery = query.toLowerCase();
        return this._rules.filter(r =>
            r.rule_id?.toLowerCase().includes(lowerQuery) ||
            r.name?.toLowerCase().includes(lowerQuery) ||
            r.description?.toLowerCase().includes(lowerQuery) ||
            r.category?.toLowerCase().includes(lowerQuery)
        );
    }

    // ========== Reset ==========

    /**
     * Reset rules to original state
     */
    reset() {
        this._rules = JSON.parse(JSON.stringify(this._originalRules));
        this._dirty = false;
        this._emit('rules-changed', this._rules);
        this._emit('dirty-changed', false);
    }

    /**
     * Discard changes and reload
     */
    async discardAndReload(projectId) {
        await this.loadRules(projectId);
    }

    // ========== Private Methods ==========

    _handleApiResponse(response, asBlob = false) {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            });
        }

        if (asBlob) {
            return response.blob();
        }

        return response.json();
    }

    _setLoading(value) {
        this._loading = value;
        this._emit('loading-changed', value);
    }

    _setError(value) {
        this._error = value;
        this._emit('error-changed', value);
    }

    _markDirty() {
        if (!this._dirty) {
            this._dirty = true;
            this._emit('dirty-changed', true);
        }
    }

    _generateRuleId() {
        // Generate a unique rule ID
        const maxId = this._rules.reduce((max, r) => {
            const match = r.rule_id?.match(/R(\d+)\.(\d+)\.(\d+)/);
            if (match) {
                const num = parseInt(match[1]) * 100 + parseInt(match[2]) * 10 + parseInt(match[3]);
                return Math.max(max, num);
            }
            return max;
        }, 0);

        const newNum = maxId + 1;
        const major = Math.floor(newNum / 100);
        const minor = Math.floor((newNum % 100) / 10);
        const patch = newNum % 10;

        return `R${major}.${minor}.${patch}`;
    }
}

// Export as global
window.ValidationRulesManager = ValidationRulesManager;
