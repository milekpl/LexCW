/**
 * Query Builder — interactive filter-based query construction.
 *
 * Extracted from query_builder.html inline script.
 * Handles: filter conditions, element references, query preview,
 * validation, preview results, workset creation, and saved queries.
 */

class QueryBuilder {
    constructor() {
        this.filterIndex = 0;
        this._init();
    }

    _init() {
        document.addEventListener('DOMContentLoaded', () => {
            this._initTooltips();
            this._wireButtons();
            this._wireEvents();
            this._loadSavedQueries();
            this._loadEditQuery();   // Load if navigating from workset "Edit Query"
            this.updateQueryPreview();
        });
    }

    _initTooltips() {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));
    }

    _wireButtons() {
        document.getElementById('add-filter-btn')?.addEventListener('click', () => {
            this.addFilterCondition();
            this.updateElementReferences();
        });

        document.getElementById('validate-query-btn')?.addEventListener('click', () => this._validateQuery());
        document.getElementById('preview-query-btn')?.addEventListener('click', () => this._previewQuery());
        document.getElementById('execute-query-btn')?.addEventListener('click', () =>
            new bootstrap.Modal(document.getElementById('createWorksetModal')).show());
        document.getElementById('confirm-create-workset')?.addEventListener('click', () => this._createWorkset());
        document.getElementById('save-query-btn')?.addEventListener('click', () =>
            new bootstrap.Modal(document.getElementById('saveQueryModal')).show());
        document.getElementById('confirm-save-query')?.addEventListener('click', () => this._saveQuery());
    }

    _wireEvents() {
        document.addEventListener('click', e => {
            if (e.target.classList.contains('remove-filter') || e.target.closest('.remove-filter')) {
                this.removeFilterCondition(e.target);
                this.updateElementReferences();
            } else {
                this._handleReferenceSelection(e);
            }
        });

        document.addEventListener('change', e => {
            if (e.target.matches('.field-select')) this.updateElementReferences();
            if (e.target.matches('.field-select, .operator-select, #sort-by-select, #sort-order-select'))
                this.updateQueryPreview();
        });

        document.addEventListener('input', e => {
            if (e.target.matches('.value-input')) this.updateQueryPreview();
        });
    }

    // ── Filter management ────────────────────────────────────────────────

    addFilterCondition() {
        const container = document.getElementById('filter-conditions');
        if (!container) return;
        container.insertAdjacentHTML('beforeend', this._filterHtml(++this.filterIndex));
        this.updateQueryPreview();
    }

    removeFilterCondition(button) {
        button.closest('.filter-condition')?.remove();
        this.updateQueryPreview();
    }

    _filterHtml(idx) {
        const fieldOptions = this._fieldOptions();
        const opOptions = this._operatorOptions();
        return `<div class="filter-condition mb-3" data-filter-index="${idx}">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <select class="form-select field-select">${fieldOptions}</select>
                </div>
                <div class="col-md-3">
                    <select class="form-select operator-select">${opOptions}</select>
                </div>
                <div class="col-md-4">
                    <div class="input-group">
                        <input type="text" class="form-control value-input" placeholder="Enter value">
                        <button class="btn btn-outline-secondary dropdown-toggle reference-btn" type="button" data-bs-toggle="dropdown"><i class="bi bi-link-45deg"></i></button>
                        <ul class="dropdown-menu element-reference-menu">
                            <li><a class="dropdown-item" href="#" data-reference-type="static">Static Value</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li class="dropdown-header">Reference Elements:</li>
                        </ul>
                    </div>
                    <small class="text-muted reference-hint" style="display:none;">Cross-reference to: <span class="reference-target"></span></small>
                </div>
                <div class="col-md-2">
                    <button type="button" class="btn btn-outline-danger btn-sm remove-filter"><i class="bi bi-trash"></i></button>
                </div>
            </div>
        </div>`;
    }

    _fieldOptions() {
        return document.getElementById('filter-conditions')?.querySelector('.field-select')?.innerHTML ||
            '<option value="">Select field...</option>';
    }

    _operatorOptions() {
        return document.getElementById('filter-conditions')?.querySelector('.operator-select')?.innerHTML ||
            '<option value="">Select operator...</option>';
    }

    // ── Element references ───────────────────────────────────────────────

    updateElementReferences() {
        document.querySelectorAll('.filter-condition').forEach((condition, index) => {
            const menu = condition.querySelector('.element-reference-menu');
            if (!menu) return;
            // Remove previous reference items
            menu.querySelectorAll('[data-reference-type="element"]').forEach(el => el.parentElement?.remove());
            document.querySelectorAll('.filter-condition').forEach((ref, refIdx) => {
                if (refIdx < index) {
                    const field = ref.querySelector('.field-select')?.value;
                    if (field) {
                        const li = document.createElement('li');
                        const a = document.createElement('a');
                        a.className = 'dropdown-item';
                        a.href = '#';
                        a.textContent = `Element ${refIdx + 1}: ${field}`;
                        a.setAttribute('data-reference-type', 'element');
                        a.setAttribute('data-element-index', refIdx + 1);
                        a.setAttribute('data-element-field', field);
                        li.appendChild(a);
                        menu.appendChild(li);
                    }
                }
            });
        });
    }

    _handleReferenceSelection(e) {
        if (!e.target.matches('.element-reference-menu .dropdown-item')) return;
        e.preventDefault();
        const condition = e.target.closest('.filter-condition');
        const valueInput = condition?.querySelector('.value-input');
        const hint = condition?.querySelector('.reference-hint');
        const target = condition?.querySelector('.reference-target');

        if (e.target.getAttribute('data-reference-type') === 'static') {
            valueInput.value = '';
            valueInput.placeholder = 'Enter value';
            valueInput.removeAttribute('data-reference-type');
            if (hint) hint.style.display = 'none';
        } else if (e.target.getAttribute('data-reference-type') === 'element') {
            const idx = e.target.getAttribute('data-element-index');
            const field = e.target.getAttribute('data-element-field');
            const refVal = `[ELEMENT ${idx}:${field}]`;
            valueInput.value = refVal;
            valueInput.setAttribute('data-reference-type', 'element');
            valueInput.setAttribute('data-element-index', idx);
            valueInput.setAttribute('data-element-field', field);
            if (target) target.textContent = `Element ${idx}: ${field}`;
            if (hint) hint.style.display = 'block';
        }
    }

    // ── Query operations ─────────────────────────────────────────────────

    getCurrentQuery() {
        const filters = [];
        document.querySelectorAll('.filter-condition').forEach(c => {
            const field = c.querySelector('.field-select')?.value;
            const operator = c.querySelector('.operator-select')?.value;
            const value = c.querySelector('.value-input')?.value;
            if (field && operator && value) filters.push({ field, operator, value });
        });
        return {
            filters,
            sort_by: document.getElementById('sort-by-select')?.value || null,
            sort_order: document.getElementById('sort-order-select')?.value || 'asc'
        };
    }

    updateQueryPreview() {
        const el = document.getElementById('query-preview-json');
        if (el) el.textContent = JSON.stringify(this.getCurrentQuery(), null, 2);
    }

    _csrf() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    _showMessage(type, msg) {
        document.querySelector('.validation-alert')?.remove();
        const div = document.createElement('div');
        div.className = `alert alert-${type} alert-dismissible fade show validation-alert`;
        div.innerHTML = `${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
        const container = document.querySelector('.query-builder-container');
        container?.parentNode?.insertBefore(div, container.nextSibling);
    }

    async _validateQuery() {
        const btn = document.getElementById('validate-query-btn');
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-hourglass"></i> Validating...';
        btn.disabled = true;
        try {
            const r = await fetch('/api/query-builder/validate', {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': this._csrf() },
                body: JSON.stringify(this.getCurrentQuery())
            });
            const data = await r.json();
            if (data.valid) {
                this._showMessage('success', `Valid query! ~${data.estimated_count} results. ${data.performance_score}`);
                const count = document.getElementById('result-count');
                const ind = document.querySelector('#performance-indicator .performance-indicator');
                if (count) count.textContent = data.estimated_count;
                if (ind) { ind.className = `performance-indicator performance-${data.performance_score}`; ind.textContent = `Performance: ${data.performance_score}`; }
            } else {
                this._showMessage('danger', `Invalid: ${(data.validation_errors || []).join(', ')}`);
            }
        } catch (e) { this._showMessage('danger', `Validation failed: ${e.message}`); }
        finally { btn.innerHTML = orig; btn.disabled = false; }
    }

    async _previewQuery() {
        const btn = document.getElementById('preview-query-btn');
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-hourglass"></i> Loading...';
        btn.disabled = true;
        try {
            const q = { ...this.getCurrentQuery(), limit: 10 };
            const r = await fetch('/api/query-builder/preview', {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': this._csrf() },
                body: JSON.stringify(q)
            });
            const data = await r.json();
            if (data.error) this._showMessage('danger', `Preview failed: ${data.error}`);
            else this._showMessage('success', `Found ${data.total_count} entries.`);
        } catch (e) { this._showMessage('danger', `Preview failed: ${e.message}`); }
        finally { btn.innerHTML = orig; btn.disabled = false; }
    }

    async _createWorkset() {
        const name = document.getElementById('workset-name-input')?.value.trim();
        if (!name) { this._showMessage('warning', 'Enter a workset name'); return; }
        const btn = document.getElementById('confirm-create-workset');
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-hourglass"></i> Creating...';
        btn.disabled = true;
        try {
            const r = await fetch('/api/query-builder/execute', {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': this._csrf() },
                body: JSON.stringify({ workset_name: name, query: this.getCurrentQuery() })
            });
            const data = await r.json();
            if (data.success) {
                bootstrap.Modal.getInstance(document.getElementById('createWorksetModal'))?.hide();
                document.getElementById('workset-name-input').value = '';
                this._showMessage('success', `Workset "${data.workset_name}" created with ${data.entry_count} entries! <a href="/workbench/worksets" class="btn btn-sm btn-outline-primary mt-2">View Worksets</a>`);
            } else {
                this._showMessage('danger', `Failed: ${data.error || 'Unknown'}`);
            }
        } catch (e) { this._showMessage('danger', `Failed: ${e.message}`); }
        finally { btn.innerHTML = orig; btn.disabled = false; }
    }

    async _saveQuery() {
        const name = document.getElementById('query-name-input')?.value.trim();
        if (!name) { this._showMessage('warning', 'Enter a query name'); return; }
        const desc = document.getElementById('query-description-input')?.value.trim() || '';
        const btn = document.getElementById('confirm-save-query');
        const orig = btn.textContent;
        btn.textContent = 'Saving...';
        btn.disabled = true;
        try {
            const r = await fetch('/api/query-builder/save', {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': this._csrf() },
                body: JSON.stringify({ name, description: desc, query: this.getCurrentQuery() })
            });
            const data = await r.json();
            if (data.success) {
                bootstrap.Modal.getInstance(document.getElementById('saveQueryModal'))?.hide();
                document.getElementById('query-name-input').value = '';
                document.getElementById('query-description-input').value = '';
                this._showMessage('success', `Query "${data.name}" saved!`);
                this._loadSavedQueries();
            } else {
                this._showMessage('danger', `Failed: ${data.error || 'Unknown'}`);
            }
        } catch (e) { this._showMessage('danger', `Failed: ${e.message}`); }
        finally { btn.textContent = orig; btn.disabled = false; }
    }

    // ── Saved queries ────────────────────────────────────────────────────

    async _loadSavedQueries() {
        const list = document.getElementById('saved-queries-list');
        if (!list) return;
        try {
            const r = await fetch('/api/query-builder/saved');
            const data = await r.json();
            const queries = data.saved_queries || data.queries || [];
            if (queries.length === 0) {
                list.innerHTML = '<p class="text-muted">No saved queries yet</p>';
                return;
            }
            list.innerHTML = queries.map(q => `
                <div class="saved-query-item mb-2 p-2 border rounded" data-query-id="${q.id || ''}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1" style="cursor:pointer" onclick="window.queryBuilder.loadSavedQuery('${this._escapeAttr(q.id || '')}')">
                            <strong>${this._escapeHtml(q.name || 'Unnamed')}</strong>
                            ${q.description ? `<br><small class="text-muted">${this._escapeHtml(q.description)}</small>` : ''}
                        </div>
                        <button class="btn btn-sm btn-outline-danger delete-saved-query-btn" data-query-id="${q.id || ''}" title="Delete"><i class="bi bi-trash"></i></button>
                    </div>
                </div>
            `).join('');

            // Wire delete buttons
            list.querySelectorAll('.delete-saved-query-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = btn.dataset.queryId;
                    try {
                        await fetch(`/api/query-builder/saved/${id}`, {
                            method: 'DELETE',
                            headers: { 'X-CSRF-TOKEN': this._csrf() }
                        });
                        this._loadSavedQueries();
                    } catch (e) { console.error('Delete failed', e); }
                });
            });
        } catch (e) { console.error('Failed to load saved queries', e); }
    }

    _loadEditQuery() {
        try {
            const raw = sessionStorage.getItem('edit-workset-query');
            if (!raw) return;
            sessionStorage.removeItem('edit-workset-query');
            const data = JSON.parse(raw);
            if (data.query) {
                this._populateFromQuery(data.query);
                this._showMessage('info',
                    `Editing query for workset #${data.worksetId}. ` +
                    '<a href="/workbench/worksets" class="btn btn-sm btn-outline-secondary ms-2">Back to Worksets</a>');
            }
        } catch (e) { /* ignore */ }
    }

    async loadSavedQuery(id) {
        try {
            const r = await fetch(`/api/query-builder/saved/${id}`);
            const data = await r.json();
            const query = data.query || data;
            if (query.filters) {
                this._populateFromQuery(query);
            }
        } catch (e) { console.error('Failed to load query', e); }
    }

    _populateFromQuery(query) {
        // Clear existing filters
        document.querySelectorAll('.filter-condition').forEach(el => el.remove());
        this.filterIndex = 0;

        // Add filters
        (query.filters || []).forEach(f => {
            const html = this._filterHtml(++this.filterIndex);
            const container = document.getElementById('filter-conditions');
            container?.insertAdjacentHTML('beforeend', html);
            const last = container?.querySelector('.filter-condition:last-child');
            if (last) {
                const fieldSel = last.querySelector('.field-select');
                const opSel = last.querySelector('.operator-select');
                const valInput = last.querySelector('.value-input');
                if (fieldSel) fieldSel.value = f.field || '';
                if (opSel) opSel.value = f.operator || '';
                if (valInput) valInput.value = f.value || '';
            }
        });

        // Set sort
        if (query.sort_by) {
            const sortBy = document.getElementById('sort-by-select');
            if (sortBy) sortBy.value = query.sort_by;
        }
        if (query.sort_order) {
            const sortOrder = document.getElementById('sort-order-select');
            if (sortOrder) sortOrder.value = query.sort_order;
        }

        this.updateQueryPreview();
        this.updateElementReferences();
    }

    _escapeHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    _escapeAttr(s) {
        return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}

window.queryBuilder = new QueryBuilder();
