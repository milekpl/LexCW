/**
 * SpreadsheetEditor - Interactive Grid View & Batch Cell Editor
 */

class SpreadsheetEditor {
    constructor() {
        this.entries = [];
        this.dirtyCells = new Map(); // key: "entryId:field" -> { entryId, field, oldValue, newValue }
        this.selectedEntries = new Set();
        this.activeCell = null;
        this.editingCell = null;
        this.currentPage = 1;
        this.totalPages = 1;
        this.totalEntries = 0;
        this.searchQuery = '';
        this.sortField = 'lexical_unit';
        this.sortDir = 'asc';

        this.posOptions = ['noun', 'verb', 'adjective', 'adverb', 'pronoun', 'preposition', 'conjunction', 'interjection', 'particle', 'affix', 'phrase'];
        this.rangesLoader = (typeof RangesLoader !== 'undefined') ? new RangesLoader() : null;
        this.posNormalizerMap = new Map();
        this.posRangeData = null;

        this.initFallbackPOSMap();
        this.init();
    }

    initFallbackPOSMap() {
        const fallbacks = [
            { id: 'Suffix', abbrev: 'su', label: 'Suffix' },
            { id: 'Prefix', abbrev: 'pref', label: 'Prefix' },
            { id: 'Preposition', abbrev: 'pre', label: 'Preposition' },
            { id: 'Noun', abbrev: 'n', label: 'Noun' },
            { id: 'Verb', abbrev: 'v', label: 'Verb' },
            { id: 'Adjective', abbrev: 'adj', label: 'Adjective' },
            { id: 'Adverb', abbrev: 'adv', label: 'Adverb' },
            { id: 'Connective', abbrev: 'c', label: 'Connective' },
            { id: 'Conjunction', abbrev: 'conj', label: 'Conjunction' },
            { id: 'Interjection', abbrev: 'int', label: 'Interjection' },
            { id: 'Article', abbrev: 'art', label: 'Article' },
            { id: 'Determiner', abbrev: 'det', label: 'Determiner' },
            { id: 'Affix', abbrev: 'aff', label: 'Affix' },
            { id: 'Classifier', abbrev: 'clf', label: 'Classifier' }
        ];
        fallbacks.forEach(item => {
            const info = { id: item.id, abbrev: item.abbrev, label: item.label, fullPath: item.label };
            this.posNormalizerMap.set(item.id.toLowerCase(), info);
            this.posNormalizerMap.set(item.abbrev.toLowerCase(), info);
            this.posNormalizerMap.set(item.label.toLowerCase(), info);
        });
    }

    async init() {
        this.bindEvents();
        this.loadGridData();
        await this.loadPOSRange();
    }

    async loadPOSRange() {
        if (!this.rangesLoader) return;
        try {
            const range = await this.rangesLoader.loadRange('grammatical-info');
            if (range && range.values) {
                this.posRangeData = range;
                this.buildPOSNormalizerMap(range.values);
                if (this.entries.length > 0) {
                    this.renderGridRows();
                }
            }
        } catch (e) {
            console.warn('[SpreadsheetEditor] Could not load grammatical-info range:', e);
        }
    }

    buildPOSNormalizerMap(items, parentPath = '') {
        items.forEach(item => {
            const itemId = item.id || item.value || '';
            const itemAbbrev = item.abbrev || (item.abbrevs ? Object.values(item.abbrevs)[0] : '') || '';
            const itemLabel = item.effective_label || (item.labels ? Object.values(item.labels)[0] : '') || itemId;
            const fullPath = parentPath ? `${parentPath} > ${itemLabel}` : itemLabel;

            const info = {
                id: itemId,
                abbrev: itemAbbrev,
                label: itemLabel,
                fullPath: fullPath
            };

            if (itemId) this.posNormalizerMap.set(itemId.toLowerCase(), info);
            if (itemAbbrev) this.posNormalizerMap.set(itemAbbrev.toLowerCase(), info);
            if (itemLabel) this.posNormalizerMap.set(itemLabel.toLowerCase(), info);

            if (item.children && item.children.length > 0) {
                this.buildPOSNormalizerMap(item.children, fullPath);
            }
        });
    }

    formatPOS(rawPOS) {
        if (!rawPOS) return '';
        const key = String(rawPOS).trim().toLowerCase();
        if (this.posNormalizerMap.has(key)) {
            const info = this.posNormalizerMap.get(key);
            return info.label || info.id;
        }
        return rawPOS;
    }

    bindEvents() {
        // Search & Refresh
        const searchInput = document.getElementById('grid-search');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.searchQuery = e.target.value.trim();
                    this.currentPage = 1;
                    this.loadGridData();
                }, 300);
            });
        }

        document.getElementById('btn-refresh-grid')?.addEventListener('click', () => {
            if (this.dirtyCells.size > 0 && !confirm('You have unsaved changes. Refresh anyway?')) {
                return;
            }
            this.dirtyCells.clear();
            this.updateSaveButton();
            this.loadGridData();
        });

        // Save Batch Changes
        document.getElementById('btn-save-batch')?.addEventListener('click', () => {
            this.saveBatchChanges();
        });

        // Checkbox Select All
        document.getElementById('select-all-rows')?.addEventListener('change', (e) => {
            const checked = e.target.checked;
            document.querySelectorAll('.row-checkbox').forEach(cb => {
                cb.checked = checked;
                const id = cb.dataset.id;
                if (checked) this.selectedEntries.add(id);
                else this.selectedEntries.delete(id);
            });
            this.updateBatchButton();
        });

        // Batch Actions
        document.getElementById('batch-set-pos')?.addEventListener('click', async (e) => {
            e.preventDefault();
            const select = document.getElementById('batch-pos-select');
            if (select && this.rangesLoader) {
                await this.rangesLoader.populateSelect(select, 'grammatical-info', {
                    emptyOption: '-- Select Part of Speech --',
                    hierarchical: true,
                    indentChar: '— '
                });
            }
            const modal = new bootstrap.Modal(document.getElementById('modalBatchPOS'));
            modal.show();
        });

        document.getElementById('btn-apply-batch-pos')?.addEventListener('click', () => {
            const posVal = document.getElementById('batch-pos-select').value;
            this.applyBatchPOS(posVal);
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalBatchPOS'));
            modal?.hide();
        });

        document.getElementById('batch-clear-selection')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.clearSelection();
        });

        // Table Header Sort
        document.querySelectorAll('#spreadsheet-table th[data-field]').forEach(th => {
            th.addEventListener('click', () => {
                const field = th.dataset.field;
                if (this.sortField === field) {
                    this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
                } else {
                    this.sortField = field;
                    this.sortDir = 'asc';
                }
                this.loadGridData();
            });
        });

        // Column Visibility Toggles
        document.querySelectorAll('#column-visibility-menu input[data-col]').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const col = e.target.dataset.col;
                const visible = e.target.checked;
                this.toggleColumnVisibility(col, visible);
            });
        });

        // Global Keyboard Handler for Grid Navigation
        document.addEventListener('keydown', (e) => this.handleGlobalKeydown(e));
    }

    async loadGridData() {
        const body = document.getElementById('spreadsheet-body');
        if (!body) return;

        body.innerHTML = `
            <tr>
                <td colspan="10" class="text-center py-4">
                    <div class="spinner-border text-primary spinner-border-sm" role="status"></div>
                    <span class="ms-2">Loading grid entries...</span>
                </td>
            </tr>
        `;

        try {
            const url = `/api/entries?page=${this.currentPage}&per_page=50&filter_text=${encodeURIComponent(this.searchQuery)}&sort_by=${this.sortField}&sort_order=${this.sortDir}`;
            const response = await fetch(url);

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();

            this.entries = data.entries || [];
            this.totalEntries = data.total || this.entries.length;
            this.totalPages = data.pages || Math.ceil(this.totalEntries / 50) || 1;

            this.renderGridRows();
            this.autoDetectEmptyColumns();
            this.renderPagination();
            this.updateStatusInfo();
        } catch (err) {
            console.error('Failed to load grid entries:', err);
            body.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center text-danger py-4">
                        <i class="fas fa-exclamation-triangle me-1"></i> Failed to load dictionary entries: ${err.message}
                    </td>
                </tr>
            `;
        }
    }

    renderGridRows() {
        const body = document.getElementById('spreadsheet-body');
        if (!body) return;

        if (this.entries.length === 0) {
            body.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center py-4 text-muted">
                        No dictionary entries found matching your query.
                    </td>
                </tr>
            `;
            return;
        }

        const rowsHtml = this.entries.map((entry, index) => {
            const entryId = entry.id || entry.entry_id;
            const isSelected = this.selectedEntries.has(entryId);

            // Field values with dirty state overrides
            const lu = this.getFieldValue(entryId, 'lexical_unit', this.extractLexicalUnit(entry));
            const hn = this.getFieldValue(entryId, 'homograph_number', entry.homograph_number || entry.order || '');
            const cf = this.getFieldValue(entryId, 'citation_form', entry.citation_form || '');
            const rawPos = this.getFieldValue(entryId, 'pos', this.extractPOS(entry));
            const displayPos = this.formatPOS(rawPos);
            const pron = this.getFieldValue(entryId, 'pronunciation', this.extractPronunciation(entry));
            const glossEn = this.getFieldValue(entryId, 'gloss_en', this.extractGloss(entry, 'en'));
            const glossPl = this.getFieldValue(entryId, 'gloss_pl', this.extractGloss(entry, 'pl'));
            const defEn = this.getFieldValue(entryId, 'definition_en', this.extractDefinition(entry, 'en'));
            const defPl = this.getFieldValue(entryId, 'definition_pl', this.extractDefinition(entry, 'pl'));
            const notes = this.getFieldValue(entryId, 'notes', this.extractNotes(entry));
            const etym = this.getFieldValue(entryId, 'etymology', this.extractEtymology(entry));

            const sensesCount = entry.senses ? entry.senses.length : (entry.senses_count || 0);
            const examplesCount = this.countExamples(entry);

            return `
                <tr data-entry-id="${entryId}" data-row-idx="${index}">
                    <td class="text-center">
                        <input type="checkbox" class="form-check-input row-checkbox" data-id="${entryId}" ${isSelected ? 'checked' : ''}>
                    </td>
                    <td class="cell-editable ${this.isDirty(entryId, 'lexical_unit') ? 'cell-dirty' : ''}" data-field="lexical_unit" title="Double click to edit">${this.escapeHtml(lu)}</td>
                    <td class="cell-editable text-center ${this.isDirty(entryId, 'homograph_number') ? 'cell-dirty' : ''}" data-field="homograph_number" title="Double click to edit">${this.escapeHtml(hn)}</td>
                    <td class="cell-editable ${this.isDirty(entryId, 'citation_form') ? 'cell-dirty' : ''}" data-field="citation_form" title="Double click to edit">${this.escapeHtml(cf)}</td>
                    <td class="cell-editable ${this.isDirty(entryId, 'pos') ? 'cell-dirty' : ''}" data-field="pos" data-raw-pos="${this.escapeHtml(rawPos)}" title="Double click to edit">
                        ${displayPos ? `<span class="badge bg-secondary badge-pos">${this.escapeHtml(displayPos)}</span>` : '<span class="text-muted small">--</span>'}
                    </td>
                    <td class="cell-editable ${this.isDirty(entryId, 'pronunciation') ? 'cell-dirty' : ''}" data-field="pronunciation" title="Double click to edit">${this.escapeHtml(pron)}</td>
                    <td class="cell-editable ${this.isDirty(entryId, 'gloss_en') ? 'cell-dirty' : ''}" data-field="gloss_en" title="Double click to edit">${this.escapeHtml(glossEn)}</td>
                    <td class="cell-editable ${this.isDirty(entryId, 'gloss_pl') ? 'cell-dirty' : ''}" data-field="gloss_pl" title="Double click to edit">${this.escapeHtml(glossPl)}</td>
                    <td class="cell-editable ${this.isDirty(entryId, 'definition_en') ? 'cell-dirty' : ''}" data-field="definition_en" title="Double click to edit">${this.escapeHtml(defEn)}</td>
                    <td class="cell-editable ${this.isDirty(entryId, 'definition_pl') ? 'cell-dirty' : ''}" data-field="definition_pl" title="Double click to edit">${this.escapeHtml(defPl)}</td>
                    <td class="cell-editable ${this.isDirty(entryId, 'notes') ? 'cell-dirty' : ''}" data-field="notes" title="Double click to edit">${this.escapeHtml(notes)}</td>
                    <td class="cell-editable ${this.isDirty(entryId, 'etymology') ? 'cell-dirty' : ''}" data-field="etymology" title="Double click to edit">${this.escapeHtml(etym)}</td>
                    <td class="text-center text-muted" data-field="senses_count">${sensesCount}</td>
                    <td class="text-center text-muted" data-field="examples_count">${examplesCount}</td>
                    <td class="text-center">
                        <a href="/entries/${entryId}" class="btn btn-xs btn-outline-info p-1" title="View Entry" target="_blank">
                            <i class="fas fa-external-link-alt"></i>
                        </a>
                    </td>
                </tr>
            `;
        }).join('');

        body.innerHTML = rowsHtml;
        this.attachRowCellEvents();
    }

    attachRowCellEvents() {
        // Row Checkboxes
        document.querySelectorAll('.row-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const id = e.target.dataset.id;
                if (e.target.checked) this.selectedEntries.add(id);
                else this.selectedEntries.delete(id);
                this.updateBatchButton();
            });
        });

        // Editable Cells
        document.querySelectorAll('.cell-editable').forEach(cell => {
            cell.addEventListener('dblclick', (e) => {
                this.startCellEdit(cell);
            });

            cell.addEventListener('click', (e) => {
                this.focusCell(cell);
            });
        });
    }

    async startCellEdit(cell) {
        if (this.editingCell) {
            this.commitCellEdit(this.editingCell);
        }

        const row = cell.closest('tr');
        const entryId = row.dataset.entryId;
        const field = cell.dataset.field;
        const currentValue = this.getFieldValue(entryId, field, this.getRawCellValue(cell, field));

        this.editingCell = cell;
        cell.classList.add('cell-editing');

        if (field === 'pos') {
            cell.innerHTML = `<select class="form-select form-select-sm cell-editor-select"><option value="">-- None --</option></select>`;
            const select = cell.querySelector('select');

            if (this.rangesLoader) {
                await this.rangesLoader.populateSelect(select, 'grammatical-info', {
                    selectedValue: currentValue,
                    emptyOption: '-- None --',
                    hierarchical: true,
                    indentChar: '— '
                });
            } else {
                this.posOptions.forEach(opt => {
                    const optElem = document.createElement('option');
                    optElem.value = opt;
                    optElem.textContent = opt;
                    if (opt === currentValue) optElem.selected = true;
                    select.appendChild(optElem);
                });
            }

            select.focus();

            select.addEventListener('blur', () => this.commitCellEdit(cell));
            select.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.commitCellEdit(cell);
                } else if (e.key === 'Escape') {
                    this.cancelCellEdit(cell, currentValue);
                }
            });
        } else {
            cell.innerHTML = `<input type="text" class="cell-editor-input" value="${this.escapeHtml(currentValue)}">`;
            const input = cell.querySelector('input');
            input.focus();
            input.select();

            input.addEventListener('blur', () => this.commitCellEdit(cell));
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.commitCellEdit(cell);
                    this.moveCellFocus('down', row);
                } else if (e.key === 'Tab') {
                    e.preventDefault();
                    this.commitCellEdit(cell);
                    this.moveCellFocus(e.shiftKey ? 'prev' : 'next', row, cell);
                } else if (e.key === 'Escape') {
                    this.cancelCellEdit(cell, currentValue);
                }
            });
        }
    }

    commitCellEdit(cell) {
        if (!cell || !cell.classList.contains('cell-editing')) return;

        const row = cell.closest('tr');
        const entryId = row.dataset.entryId;
        const field = cell.dataset.field;
        const input = cell.querySelector('input, select');

        if (!input) return;

        const newValue = input.value.trim();
        const originalValue = this.getOriginalFieldValue(entryId, field);

        cell.classList.remove('cell-editing');

        if (newValue !== originalValue) {
            const key = `${entryId}:${field}`;
            this.dirtyCells.set(key, { entryId, field, originalValue, newValue });
            cell.classList.add('cell-dirty');
        } else {
            const key = `${entryId}:${field}`;
            this.dirtyCells.delete(key);
            cell.classList.remove('cell-dirty');
        }

        // Re-render cell display content
        if (field === 'pos') {
            const displayValue = this.formatPOS(newValue);
            cell.setAttribute('data-raw-pos', newValue);
            cell.innerHTML = newValue ? `<span class="badge bg-secondary badge-pos">${this.escapeHtml(displayValue)}</span>` : '<span class="text-muted small">--</span>';
        } else {
            cell.textContent = newValue;
        }

        this.editingCell = null;
        this.updateSaveButton();
    }

    cancelCellEdit(cell, originalValue) {
        if (!cell) return;
        cell.classList.remove('cell-editing');
        const field = cell.dataset.field;

        if (field === 'pos') {
            const displayValue = this.formatPOS(originalValue);
            cell.innerHTML = originalValue ? `<span class="badge bg-secondary badge-pos">${this.escapeHtml(displayValue)}</span>` : '<span class="text-muted small">--</span>';
        } else {
            cell.textContent = originalValue;
        }
        this.editingCell = null;
    }

    focusCell(cell) {
        if (this.activeCell) {
            this.activeCell.classList.remove('cell-focused');
        }
        this.activeCell = cell;
        cell.classList.add('cell-focused');
    }

    moveCellFocus(direction, currentRow, currentCell = null) {
        if (direction === 'next' || direction === 'prev') {
            const editables = Array.from(currentRow.querySelectorAll('.cell-editable'));
            const idx = editables.indexOf(currentCell);

            if (direction === 'next' && idx < editables.length - 1) {
                this.startCellEdit(editables[idx + 1]);
            } else if (direction === 'prev' && idx > 0) {
                this.startCellEdit(editables[idx - 1]);
            }
        } else if (direction === 'down') {
            const nextRow = currentRow.nextElementSibling;
            if (nextRow) {
                const targetCell = nextRow.querySelector(`[data-field="${currentCell?.dataset.field || 'lexical_unit'}"]`);
                if (targetCell) this.startCellEdit(targetCell);
            }
        }
    }

    handleGlobalKeydown(e) {
        if (this.editingCell) return; // Ignore if actively typing in cell input

        if (this.activeCell) {
            if (e.key === 'F2' || e.key === 'Enter') {
                e.preventDefault();
                this.startCellEdit(this.activeCell);
            }
        }
    }

    async saveBatchChanges() {
        if (this.dirtyCells.size === 0) return;

        const btn = document.getElementById('btn-save-batch');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Saving...';
        }

        // Group changes by entry_id
        const updatesMap = new Map();
        this.dirtyCells.forEach(({ entryId, field, newValue }) => {
            if (!updatesMap.has(entryId)) {
                updatesMap.set(entryId, { id: entryId, changes: {} });
            }
            updatesMap.get(entryId).changes[field] = newValue;
        });

        const updatesPayload = Array.from(updatesMap.values());

        try {
            const response = await fetch('/api/bulk/batch-update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates: updatesPayload })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const res = await response.json();
            const successCount = res.summary?.success || updatesPayload.length;

            this.dirtyCells.clear();
            this.updateSaveButton();

            this.showToast(`Saved ${successCount} entry change(s) successfully!`, 'success');
            this.loadGridData();

        } catch (err) {
            console.error('Batch save failed:', err);
            this.showToast(`Failed to save changes: ${err.message}`, 'danger');
        } finally {
            this.updateSaveButton();
        }
    }

    applyBatchPOS(newPOS) {
        if (this.selectedEntries.size === 0) return;

        this.selectedEntries.forEach(entryId => {
            const row = document.querySelector(`tr[data-entry-id="${entryId}"]`);
            if (row) {
                const cell = row.querySelector('[data-field="pos"]');
                if (cell) {
                    const originalValue = this.getOriginalFieldValue(entryId, 'pos');
                    const key = `${entryId}:pos`;

                    if (newPOS !== originalValue) {
                        this.dirtyCells.set(key, { entryId, field: 'pos', originalValue, newValue: newPOS });
                        cell.classList.add('cell-dirty');
                    } else {
                        this.dirtyCells.delete(key);
                        cell.classList.remove('cell-dirty');
                    }
                    const displayPOS = this.formatPOS(newPOS);
                    cell.setAttribute('data-raw-pos', newPOS);
                    cell.innerHTML = newPOS ? `<span class="badge bg-secondary badge-pos">${this.escapeHtml(displayPOS)}</span>` : '<span class="text-muted small">--</span>';
                }
            }
        });

        this.updateSaveButton();
        this.showToast(`Updated POS for ${this.selectedEntries.size} selected entry(ies)`, 'info');
    }

    clearSelection() {
        this.selectedEntries.clear();
        document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
        const selectAll = document.getElementById('select-all-rows');
        if (selectAll) selectAll.checked = false;
        this.updateBatchButton();
    }

    // Helper functions
    getFieldValue(entryId, field, defaultVal) {
        const key = `${entryId}:${field}`;
        return this.dirtyCells.has(key) ? this.dirtyCells.get(key).newValue : defaultVal;
    }

    getOriginalFieldValue(entryId, field) {
        const entry = this.entries.find(e => (e.id || e.entry_id) === entryId);
        if (!entry) return '';
        if (field === 'lexical_unit') return this.extractLexicalUnit(entry);
        if (field === 'homograph_number') return entry.homograph_number || entry.order || '';
        if (field === 'citation_form') return entry.citation_form || '';
        if (field === 'pos') return this.extractPOS(entry);
        if (field === 'pronunciation') return this.extractPronunciation(entry);
        if (field === 'gloss_en') return this.extractGloss(entry, 'en');
        if (field === 'gloss_pl') return this.extractGloss(entry, 'pl');
        if (field === 'definition_en') return this.extractDefinition(entry, 'en');
        if (field === 'definition_pl') return this.extractDefinition(entry, 'pl');
        if (field === 'notes') return this.extractNotes(entry);
        if (field === 'etymology') return this.extractEtymology(entry);
        return '';
    }

    getRawCellValue(cell, field) {
        if (field === 'pos') {
            return cell.dataset.rawPos || (cell.querySelector('.badge') ? cell.querySelector('.badge').textContent.trim() : '');
        }
        return cell.textContent.trim();
    }

    isDirty(entryId, field) {
        return this.dirtyCells.has(`${entryId}:${field}`);
    }

    extractLexicalUnit(entry) {
        if (!entry.lexical_unit) return '';
        if (typeof entry.lexical_unit === 'string') return entry.lexical_unit;
        if (typeof entry.lexical_unit === 'object') {
            return entry.lexical_unit.en || entry.lexical_unit.seh || Object.values(entry.lexical_unit)[0] || '';
        }
        return '';
    }

    extractPOS(entry) {
        if (entry.grammatical_info) {
            if (typeof entry.grammatical_info === 'string') return entry.grammatical_info;
            if (typeof entry.grammatical_info === 'object') {
                return entry.grammatical_info.part_of_speech || entry.grammatical_info.value || entry.grammatical_info.trait || '';
            }
        }
        if (entry.pos) return entry.pos;
        return '';
    }

    extractPronunciation(entry) {
        if (!entry.pronunciations) return '';
        if (typeof entry.pronunciations === 'string') return entry.pronunciations;
        if (typeof entry.pronunciations === 'object') {
            return Object.values(entry.pronunciations)[0] || '';
        }
        return '';
    }

    autoDetectEmptyColumns() {
        if (this.entries.length === 0 || this.hasAutoDetectedColumns) return;
        this.hasAutoDetectedColumns = true;

        const columns = ['homograph_number', 'gloss_en', 'gloss_pl', 'definition_en', 'definition_pl', 'citation_form', 'pronunciation', 'notes', 'etymology'];
        columns.forEach(col => {
            let hasData = false;
            if (col === 'homograph_number') hasData = this.entries.some(e => Boolean(e.homograph_number || e.order));
            else if (col === 'gloss_en') hasData = this.entries.some(e => Boolean(this.extractGloss(e, 'en')));
            else if (col === 'gloss_pl') hasData = this.entries.some(e => Boolean(this.extractGloss(e, 'pl')));
            else if (col === 'definition_en') hasData = this.entries.some(e => Boolean(this.extractDefinition(e, 'en')));
            else if (col === 'definition_pl') hasData = this.entries.some(e => Boolean(this.extractDefinition(e, 'pl')));
            else if (col === 'citation_form') hasData = this.entries.some(e => Boolean(e.citation_form));
            else if (col === 'pronunciation') hasData = this.entries.some(e => Boolean(this.extractPronunciation(e)));
            else if (col === 'notes') hasData = this.entries.some(e => Boolean(this.extractNotes(e)));
            else if (col === 'etymology') hasData = this.entries.some(e => Boolean(this.extractEtymology(e)));

            if (!hasData) {
                const cb = document.querySelector(`#column-visibility-menu input[data-col="${col}"]`);
                if (cb) {
                    cb.checked = false;
                    this.toggleColumnVisibility(col, false);
                }
            }
        });
    }

    extractGloss(entry, lang = 'en') {
        if (!entry.senses || entry.senses.length === 0) return '';
        const sense = entry.senses[0];
        if (sense.glosses) {
            if (typeof sense.glosses === 'string') return lang === 'en' ? sense.glosses : '';
            if (typeof sense.glosses === 'object') return sense.glosses[lang] || '';
        }
        if (sense.gloss) {
            if (typeof sense.gloss === 'string') return lang === 'en' ? sense.gloss : '';
            if (typeof sense.gloss === 'object') return sense.gloss[lang] || '';
        }
        return '';
    }

    extractNotes(entry) {
        if (entry.notes) {
            if (Array.isArray(entry.notes)) return entry.notes.join('; ');
            if (typeof entry.notes === 'string') return entry.notes;
        }
        if (entry.senses && entry.senses[0] && entry.senses[0].notes) {
            if (Array.isArray(entry.senses[0].notes)) return entry.senses[0].notes.join('; ');
            if (typeof entry.senses[0].notes === 'string') return entry.senses[0].notes;
        }
        return '';
    }

    extractEtymology(entry) {
        if (entry.etymologies) {
            if (Array.isArray(entry.etymologies)) return entry.etymologies.join('; ');
            if (typeof entry.etymologies === 'string') return entry.etymologies;
        }
        if (entry.etymology) {
            if (typeof entry.etymology === 'string') return entry.etymology;
        }
        return '';
    }

    extractDefinition(entry, lang = 'en') {
        if (!entry.senses || entry.senses.length === 0) return '';
        const sense = entry.senses[0];
        if (sense.definitions) {
            if (typeof sense.definitions === 'string') return lang === 'en' ? sense.definitions : '';
            if (typeof sense.definitions === 'object') {
                return sense.definitions[lang] || '';
            }
        }
        if (sense.definition) {
            if (typeof sense.definition === 'string') return lang === 'en' ? sense.definition : '';
            if (typeof sense.definition === 'object') {
                return sense.definition[lang] || '';
            }
        }
        return '';
    }

    countExamples(entry) {
        if (!entry.senses) return 0;
        let count = 0;
        entry.senses.forEach(s => {
            if (s.examples) count += s.examples.length;
        });
        return count;
    }

    toggleColumnVisibility(colName, visible) {
        document.querySelectorAll(`#spreadsheet-table [data-field="${colName}"]`).forEach(el => {
            el.style.display = visible ? '' : 'none';
        });
    }

    updateSaveButton() {
        const btn = document.getElementById('btn-save-batch');
        const badge = document.getElementById('unsaved-badge');
        if (!btn || !badge) return;

        const count = this.dirtyCells.size;
        badge.textContent = count;
        btn.disabled = count === 0;
        if (count > 0) {
            btn.innerHTML = `<i class="fas fa-save me-1"></i> Save Changes <span class="badge bg-white text-dark ms-1">${count}</span>`;
        } else {
            btn.innerHTML = `<i class="fas fa-save me-1"></i> Save Changes <span class="badge bg-white text-dark ms-1">0</span>`;
        }
    }

    updateBatchButton() {
        const btn = document.getElementById('dropdownBatch');
        const countSpan = document.getElementById('selected-count');
        if (!btn || !countSpan) return;

        const count = this.selectedEntries.size;
        countSpan.textContent = count;
        btn.disabled = count === 0;
    }

    updateStatusInfo() {
        const info = document.getElementById('grid-status-info');
        if (info) {
            info.textContent = `Showing ${this.entries.length} of ${this.totalEntries} entries (Page ${this.currentPage} of ${this.totalPages})`;
        }
    }

    renderPagination() {
        const pag = document.getElementById('grid-pagination');
        if (!pag || this.totalPages <= 1) {
            if (pag) pag.innerHTML = '';
            return;
        }

        const current = this.currentPage;
        const total = this.totalPages;
        const delta = 2;
        const range = [];
        const rangeWithDots = [];
        let l;

        for (let i = 1; i <= total; i++) {
            if (i === 1 || i === total || (i >= current - delta && i <= current + delta)) {
                range.push(i);
            }
        }

        for (let i of range) {
            if (l) {
                if (i - l === 2) {
                    rangeWithDots.push(l + 1);
                } else if (i - l !== 1) {
                    rangeWithDots.push('...');
                }
            }
            rangeWithDots.push(i);
            l = i;
        }

        let html = `
            <li class="page-item ${current === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${current - 1}">&laquo; Prev</a>
            </li>
        `;

        rangeWithDots.forEach(p => {
            if (p === '...') {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            } else {
                html += `
                    <li class="page-item ${p === current ? 'active' : ''}">
                        <a class="page-link" href="#" data-page="${p}">${p}</a>
                    </li>
                `;
            }
        });

        html += `
            <li class="page-item ${current === total ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${current + 1}">Next &raquo;</a>
            </li>
        `;

        pag.innerHTML = html;

        pag.querySelectorAll('.page-link[data-page]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = e.currentTarget;
                const pageNum = parseInt(target.dataset.page, 10);
                if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= this.totalPages && pageNum !== this.currentPage) {
                    this.currentPage = pageNum;
                    this.loadGridData();
                }
            });
        });
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    showToast(message, type = 'success') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.bottom = '20px';
        alertDiv.style.right = '20px';
        alertDiv.style.zIndex = '9999';
        alertDiv.innerHTML = `
            <i class="fas fa-info-circle me-1"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alertDiv);
        setTimeout(() => alertDiv.remove(), 4000);
    }
}

// Instantiate on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.spreadsheetEditor = new SpreadsheetEditor();
});
