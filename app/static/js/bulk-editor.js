/**
 * Bulk Editor - Tabular interface for atomic bulk operations
 * Extends existing entries.js patterns and reuses existing components
 */

class BulkEditor {
    constructor() {
        this.selectedEntries = new Set();
        this.currentOperation = null;
        this.validationUI = window.validationUI || new ValidationUI();
        this.init();
    }

    init() {
        this.setupSelectionHandlers();
        this.setupOperationHandlers();
        this.setupBulkActionPanel();
        console.log('[BulkEditor] Initialized');
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
        const traitBtn = document.getElementById('bulk-convert-traits-btn');
        if (traitBtn) {
            traitBtn.addEventListener('click', () => this.showTraitConversionModal());
        }

        const posBtn = document.getElementById('bulk-update-pos-btn');
        if (posBtn) {
            posBtn.addEventListener('click', () => this.showPOSUpdateModal());
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
                    <button class="btn btn-sm btn-primary me-2" id="bulk-convert-traits-btn">Convert Traits</button>
                    <button class="btn btn-sm btn-primary me-2" id="bulk-update-pos-btn">Update POS</button>
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

        // Update select all checkbox state
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

    showTraitConversionModal() {
        const modalHtml = `
            <div class="modal fade" id="trait-conversion-modal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Convert Traits</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">From Trait Value</label>
                                <input type="text" class="form-control" id="from-trait" placeholder="e.g., verb">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">To Trait Value</label>
                                <input type="text" class="form-control" id="to-trait" placeholder="e.g., phrasal-verb">
                            </div>
                            <div class="alert alert-warning">
                                This will affect <strong>${this.selectedEntries.size}</strong> entries
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="execute-trait-conversion">Execute</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (!document.getElementById('trait-conversion-modal')) {
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }

        const modal = new bootstrap.Modal(document.getElementById('trait-conversion-modal'));
        modal.show();

        document.getElementById('execute-trait-conversion').onclick = () => this.executeTraitConversion();

        // Remove modal from DOM when hidden
        document.getElementById('trait-conversion-modal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    }

    async executeTraitConversion() {
        const fromTrait = document.getElementById('from-trait').value;
        const toTrait = document.getElementById('to-trait').value;

        if (!fromTrait || !toTrait) {
            this.validationUI.showError('Please enter both trait values');
            return;
        }

        const entryIds = Array.from(this.selectedEntries);

        // Get CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

        try {
            const response = await fetch('/bulk/traits/convert', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({
                    entry_ids: entryIds,
                    from_trait: fromTrait,
                    to_trait: toTrait
                })
            });

            const result = await response.json();

            if (response.ok) {
                const successCount = result.summary.success;
                this.validationUI.showSuccess(`Successfully updated ${successCount} entries`);
                this.clearSelection();

                const modal = bootstrap.Modal.getInstance(document.getElementById('trait-conversion-modal'));
                if (modal) modal.hide();

                // Refresh entries table if function exists
                if (typeof refreshEntriesTable === 'function') {
                    refreshEntriesTable();
                } else if (typeof loadEntries === 'function') {
                    loadEntries(1, currentSortBy, currentSortOrder);
                }
            } else {
                this.validationUI.showError(result.error || 'Bulk operation failed');
            }
        } catch (error) {
            console.error('[BulkEditor] Trait conversion error:', error);
            this.validationUI.showError('Network error: ' + error.message);
        }
    }

    showPOSUpdateModal() {
        const modalHtml = `
            <div class="modal fade" id="pos-update-modal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Update Part-of-Speech</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">New POS Tag</label>
                                <select class="form-select" id="pos-tag">
                                    <option value="">Select POS...</option>
                                    <option value="noun">Noun</option>
                                    <option value="verb">Verb</option>
                                    <option value="adjective">Adjective</option>
                                    <option value="adverb">Adverb</option>
                                    <option value="preposition">Preposition</option>
                                    <option value="conjunction">Conjunction</option>
                                </select>
                            </div>
                            <div class="alert alert-warning">
                                This will affect <strong>${this.selectedEntries.size}</strong> entries
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="execute-pos-update">Execute</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (!document.getElementById('pos-update-modal')) {
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }

        const modal = new bootstrap.Modal(document.getElementById('pos-update-modal'));
        modal.show();

        document.getElementById('execute-pos-update').onclick = () => this.executePOSUpdate();

        // Remove modal from DOM when hidden
        document.getElementById('pos-update-modal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    }

    async executePOSUpdate() {
        const posTag = document.getElementById('pos-tag').value;

        if (!posTag) {
            this.validationUI.showError('Please select a POS tag');
            return;
        }

        const entryIds = Array.from(this.selectedEntries);

        // Get CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

        try {
            const response = await fetch('/bulk/pos/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({
                    entry_ids: entryIds,
                    pos_tag: posTag
                })
            });

            const result = await response.json();

            if (response.ok) {
                const successCount = result.summary.success;
                this.validationUI.showSuccess(`Successfully updated ${successCount} entries`);
                this.clearSelection();

                const modal = bootstrap.Modal.getInstance(document.getElementById('pos-update-modal'));
                if (modal) modal.hide();

                // Refresh entries table if function exists
                if (typeof refreshEntriesTable === 'function') {
                    refreshEntriesTable();
                } else if (typeof loadEntries === 'function') {
                    loadEntries(1, currentSortBy, currentSortOrder);
                }
            } else {
                this.validationUI.showError(result.error || 'Bulk operation failed');
            }
        } catch (error) {
            console.error('[BulkEditor] POS update error:', error);
            this.validationUI.showError('Network error: ' + error.message);
        }
    }

    clearSelection() {
        this.selectedEntries.clear();
        this.toggleSelectAll(false);
    }

    /**
     * Add checkbox column to entries table
     * Should be called when table headers are rendered
     */
    addCheckboxColumn() {
        const tableHead = document.getElementById('entries-table-head');
        if (!tableHead) return;

        // Add select all checkbox in header if not exists
        let selectAllTh = tableHead.querySelector('th.bulk-select-header');
        if (!selectAllTh) {
            const firstTh = tableHead.querySelector('th');
            if (firstTh) {
                selectAllTh = document.createElement('th');
                selectAllTh.className = 'bulk-select-header';
                selectAllTh.style.width = '40px';
                selectAllTh.innerHTML = `
                    <input type="checkbox" id="bulk-select-all" class="form-check-input" title="Select all">
                `;
                tableHead.insertBefore(selectAllTh, firstTh);
            }
        }
    }

    /**
     * Add checkbox to each row
     * Should be called when table body is rendered
     */
    addCheckboxToRows() {
        const rows = document.querySelectorAll('#entries-list tr[data-entry-id]');
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
                }
            }
        });
    }
}

// Initialize on entries page
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('entries-table')) {
        window.bulkEditor = new BulkEditor();

        // Hook into entries.js rendering to add checkboxes
        // This will be called after loadEntries renders the table
        const originalRenderTableBody = window.renderTableBody;
        if (typeof originalRenderTableBody === 'function') {
            window.renderTableBody = function(entries) {
                originalRenderTableBody(entries);
                if (window.bulkEditor) {
                    window.bulkEditor.addCheckboxColumn();
                    window.bulkEditor.addCheckboxToRows();
                }
            };
        }

        // Add checkboxes immediately if table is already rendered
        if (document.querySelector('#entries-list tr[data-entry-id]')) {
            if (window.bulkEditor) {
                window.bulkEditor.addCheckboxColumn();
                window.bulkEditor.addCheckboxToRows();
            }
        }
    }
});

// Make available globally
if (typeof window !== 'undefined') {
    window.BulkEditor = BulkEditor;
}
