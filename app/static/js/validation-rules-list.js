/**
 * Validation Rules List Component
 *
 * Displays validation rules in a table with filtering, sorting, and search.
 */

class ValidationRulesList {
    constructor(manager, containerId) {
        this._manager = manager;
        this._container = document.getElementById(containerId);

        if (!this._container) {
            console.error(`Container with id "${containerId}" not found`);
            return;
        }

        // State
        this._filterCategory = '';
        this._filterPriority = '';
        this._searchQuery = '';
        this._sortField = 'rule_id';
        this._sortDirection = 'asc';
        this._selectedRuleId = null;

        // Bind methods
        this._render = this._render.bind(this);
        this._handleSort = this._handleSort.bind(this);
        this._handleFilter = this._handleFilter.bind(this);
        this._handleSearch = this._handleSearch.bind(this);
        this._handleSelect = this._handleSelect.bind(this);
        this._handleAction = this._handleAction.bind(this);

        // Initialize
        this._setupEventListeners();
        this._render();
    }

    // ========== Event Setup ==========

    _setupEventListeners() {
        // Listen for rule changes
        this._manager.on('rules-changed', this._render);
        this._manager.on('rule-selected', this._render);

        // Listen for dirty state changes (to show/hide unsaved indicator)
        this._manager.on('dirty-changed', this._render);

        // Listen for error changes
        this._manager.on('error-changed', this._render);
    }

    // ========== Event Handlers ==========

    _handleSort(field) {
        if (this._sortField === field) {
            this._sortDirection = this._sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this._sortField = field;
            this._sortDirection = 'asc';
        }
        this._render();
    }

    _handleFilter(event) {
        const { name, value } = event.target;
        if (name === 'category') {
            this._filterCategory = value;
        } else if (name === 'priority') {
            this._filterPriority = value;
        }
        this._render();
    }

    _handleSearch(event) {
        this._searchQuery = event.target.value;
        this._render();
    }

    _handleSelect(ruleId) {
        this._selectedRuleId = ruleId;
        const rule = this._manager.rules.find(r => r.rule_id === ruleId);
        this._manager.selectRule(rule);
        this._render();
    }

    _handleAction(event) {
        const button = event.target.closest('button');
        if (!button) return;

        const { action, ruleId } = button.dataset;
        event.stopPropagation();

        switch (action) {
            case 'edit':
                this._handleSelect(ruleId);
                break;
            case 'duplicate':
                const newRule = this._manager.duplicateRule(ruleId);
                if (newRule) {
                    this._handleSelect(newRule.rule_id);
                }
                break;
            case 'toggle':
                this._manager.toggleRuleActive(ruleId);
                break;
            case 'delete':
                if (confirm(`Delete rule ${ruleId}?`)) {
                    this._manager.deleteRule(ruleId);
                    if (this._selectedRuleId === ruleId) {
                        this._selectedRuleId = null;
                    }
                }
                break;
        }
    }

    // ========== Rendering ==========

    _render() {
        const rules = this._getFilteredAndSortedRules();
        const categories = this._getCategories();
        const priorities = ['critical', 'warning', 'informational'];

        const isDirty = this._manager.isDirty;

        this._container.innerHTML = `
            ${this._renderHeader(categories, priorities, isDirty)}
            ${this._renderSearchBar()}
            ${this._renderTable(rules)}
            ${this._renderFooter(rules.length)}
        `;

        this._attachEventHandlers();
    }

    _renderHeader(categories, priorities, isDirty) {
        const categoryOptions = categories.map(c =>
            `<option value="${c}" ${this._filterCategory === c ? 'selected' : ''}>${c}</option>`
        ).join('');

        const priorityOptions = priorities.map(p =>
            `<option value="${p}" ${this._filterPriority === p ? 'selected' : ''}>${p}</option>`
        ).join('');

        return `
            <div class="rules-list-header">
                <div class="rules-list-filters">
                    <select name="category" class="form-select">
                        <option value="">All Categories</option>
                        ${categoryOptions}
                    </select>
                    <select name="priority" class="form-select">
                        <option value="">All Priorities</option>
                        ${priorityOptions}
                    </select>
                </div>
                <div class="rules-list-actions">
                    <button class="btn btn-sm btn-outline-primary" id="rules-list-add">
                        <i class="bi bi-plus"></i> Add Rule
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" id="rules-list-import">
                        <i class="bi bi-upload"></i> Import
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" id="rules-list-export">
                        <i class="bi bi-download"></i> Export
                    </button>
                </div>
                ${isDirty ? '<span class="badge bg-warning text-dark">Unsaved changes</span>' : ''}
            </div>
        `;
    }

    _renderSearchBar() {
        return `
            <div class="rules-list-search">
                <input
                    type="text"
                    class="form-control"
                    placeholder="Search rules..."
                    value="${this._escapeHtml(this._searchQuery)}"
                    id="rules-list-search"
                >
            </div>
        `;
    }

    _renderTable(rules) {
        if (rules.length === 0) {
            return `
                <div class="rules-list-empty">
                    <p>No rules found matching your criteria.</p>
                    <button class="btn btn-primary" onclick="window.validationRulesApp.addRule()">
                        Add your first rule
                    </button>
                </div>
            `;
        }

        const rows = rules.map(rule => {
            const isActive = rule.is_active !== false;
            const isSelected = this._selectedRuleId === rule.rule_id;

            const priorityClass = {
                'critical': 'danger',
                'warning': 'warning',
                'informational': 'info'
            }[rule.priority] || 'secondary';

            return `
                <tr
                    class="${isSelected ? 'table-primary' : ''} ${!isActive ? 'text-muted' : ''}"
                    data-rule-id="${this._escapeHtml(rule.rule_id)}"
                    style="cursor: pointer"
                >
                    <td>
                        <input
                            type="checkbox"
                            ${isActive ? 'checked' : ''}
                            data-rule-id="${this._escapeHtml(rule.rule_id)}"
                            class="rule-active-checkbox"
                        >
                    </td>
                    <td>
                        <span class="badge bg-${priorityClass}">${rule.priority || 'N/A'}</span>
                    </td>
                    <td>
                        <code>${this._escapeHtml(rule.rule_id)}</code>
                    </td>
                    <td>${this._escapeHtml(rule.name)}</td>
                    <td><span class="text-muted">${this._escapeHtml(rule.category)}</span></td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button
                                class="btn btn-outline-primary"
                                data-action="edit"
                                data-rule-id="${this._escapeHtml(rule.rule_id)}"
                                title="Edit"
                            >
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button
                                class="btn btn-outline-secondary"
                                data-action="duplicate"
                                data-rule-id="${this._escapeHtml(rule.rule_id)}"
                                title="Duplicate"
                            >
                                <i class="bi bi-copy"></i>
                            </button>
                            <button
                                class="btn btn-outline-danger"
                                data-action="delete"
                                data-rule-id="${this._escapeHtml(rule.rule_id)}"
                                title="Delete"
                            >
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        return `
            <div class="table-responsive">
                <table class="table table-hover rules-list-table">
                    <thead>
                        <tr>
                            <th style="width: 40px">
                                <input type="checkbox" disabled title="Active">
                            </th>
                            <th style="width: 100px" data-sort="priority">Priority</th>
                            <th style="width: 120px" data-sort="rule_id">ID</th>
                            <th data-sort="name">Name</th>
                            <th style="width: 150px" data-sort="category">Category</th>
                            <th style="width: 140px">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        `;
    }

    _renderFooter(count) {
        const totalRules = this._manager.rulesCount;
        const activeRules = this._manager.rules.filter(r => r.is_active !== false).length;

        return `
            <div class="rules-list-footer">
                <span>Showing ${count} of ${totalRules} rules</span>
                <span class="text-muted">(${activeRules} active)</span>
            </div>
        `;
    }

    // ========== Helpers ==========

    _getFilteredAndSortedRules() {
        let rules = this._manager.rules;

        // Filter by category
        if (this._filterCategory) {
            rules = rules.filter(r => r.category === this._filterCategory);
        }

        // Filter by priority
        if (this._filterPriority) {
            rules = rules.filter(r => r.priority === this._filterPriority);
        }

        // Search
        if (this._searchQuery) {
            const query = this._searchQuery.toLowerCase();
            rules = rules.filter(r =>
                r.rule_id?.toLowerCase().includes(query) ||
                r.name?.toLowerCase().includes(query) ||
                r.description?.toLowerCase().includes(query)
            );
        }

        // Sort
        rules = [...rules].sort((a, b) => {
            let aVal = a[this._sortField];
            let bVal = b[this._sortField];

            // Handle priority ordering
            if (this._sortField === 'priority') {
                const order = { 'critical': 0, 'warning': 1, 'informational': 2 };
                aVal = order[aVal] ?? 3;
                bVal = order[bVal] ?? 3;
            }

            // Handle null/undefined
            if (aVal == null) aVal = '';
            if (bVal == null) bVal = '';

            // Compare
            if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = (bVal || '').toLowerCase();
            }

            if (aVal < bVal) return this._sortDirection === 'asc' ? -1 : 1;
            if (aVal > bVal) return this._sortDirection === 'asc' ? 1 : -1;
            return 0;
        });

        return rules;
    }

    _getCategories() {
        const categories = new Set();
        this._manager.rules.forEach(r => {
            if (r.category) categories.add(r.category);
        });
        return Array.from(categories).sort();
    }

    _escapeHtml(text) {
        if (text == null) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    _attachEventHandlers() {
        // Filter dropdowns
        const categorySelect = this._container.querySelector('select[name="category"]');
        if (categorySelect) {
            categorySelect.addEventListener('change', this._handleFilter);
        }

        const prioritySelect = this._container.querySelector('select[name="priority"]');
        if (prioritySelect) {
            prioritySelect.addEventListener('change', this._handleFilter);
        }

        // Search input
        const searchInput = this._container.querySelector('#rules-list-search');
        if (searchInput) {
            searchInput.addEventListener('input', this._handleSearch);
        }

        // Sort headers
        this._container.querySelectorAll('[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                this._handleSort(th.dataset.sort);
            });
            th.style.cursor = 'pointer';
            th.innerHTML += ' <i class="bi bi-chevron-expand"></i>';
        });

        // Table rows - select rule on click
        this._container.querySelectorAll('tbody tr').forEach(tr => {
            tr.addEventListener('click', () => {
                this._handleSelect(tr.dataset.ruleId);
            });
        });

        // Action buttons
        this._container.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', this._handleAction);
        });

        // Active checkboxes
        this._container.querySelectorAll('.rule-active-checkbox').forEach(checkbox => {
            checkbox.addEventListener('click', (e) => {
                e.stopPropagation();
                this._manager.toggleRuleActive(checkbox.dataset.ruleId);
            });
        });

        // Add/Import/Export buttons
        const addBtn = this._container.querySelector('#rules-list-add');
        if (addBtn) {
            addBtn.addEventListener('click', () => window.validationRulesApp.addRule());
        }

        const importBtn = this._container.querySelector('#rules-list-import');
        if (importBtn) {
            importBtn.addEventListener('click', () => window.validationRulesApp.importRules());
        }

        const exportBtn = this._container.querySelector('#rules-list-export');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => window.validationRulesApp.exportRules());
        }
    }

    // ========== Public Methods ==========

    refresh() {
        this._render();
    }

    clearFilters() {
        this._filterCategory = '';
        this._filterPriority = '';
        this._searchQuery = '';
        this._render();
    }
}

// Export as global
window.ValidationRulesList = ValidationRulesList;
