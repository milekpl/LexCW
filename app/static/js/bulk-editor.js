/**
 * Bulk Editor - Tabular interface for atomic bulk operations
 * Extends existing entries.js patterns and reuses existing components
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

class BulkEditor {
    constructor() {
        this.selectedEntries = new Set();
        this.currentOperation = null;
        this.checkboxColumnAdded = false; // Track if checkbox column exists
        this.init();
    }

    init() {
        this.setupSelectionHandlers();
        this.setupOperationHandlers();
        this.setupBulkActionPanel();
        this.setupEntriesRenderedListener();
        console.log('[BulkEditor] Initialized');
    }

    /**
     * Listen for entriesRendered event from entries.js
     * This is the reliable way to add checkboxes after table is rendered
     */
    setupEntriesRenderedListener() {
        let retryCount = 0;
        const maxRetries = 5;

        const handleEntriesRendered = (event) => {
            console.log('[BulkEditor] entriesRendered event received, count:', event.detail.entryCount);

            // First try to add checkbox column
            this.addCheckboxColumn();

            // If column wasn't added (no header yet), retry
            if (!this.checkboxColumnAdded && retryCount < maxRetries) {
                retryCount++;
                console.log(`[BulkEditor] Header not ready, will retry (${retryCount}/${maxRetries})`);
                setTimeout(() => {
                    this.addCheckboxColumn();
                    this.addCheckboxToRows();
                }, 100);
                return;
            }

            // Add checkboxes to rows
            this.addCheckboxToRows();
        };

        document.addEventListener('entriesRendered', handleEntriesRendered);

        // Also check immediately in case entries are already rendered
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
            showBulkEditorNotification('Please enter both trait values', 'error');
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
                showBulkEditorNotification(`Successfully updated ${successCount} entries`, 'success');
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
                showBulkEditorNotification(result.error || 'Bulk operation failed', 'error');
            }
        } catch (error) {
            console.error('[BulkEditor] Trait conversion error:', error);
            showBulkEditorNotification('Network error: ' + error.message, 'error');
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
            showBulkEditorNotification('Please select a POS tag', 'error');
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
                showBulkEditorNotification(`Successfully updated ${successCount} entries`, 'success');
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
                showBulkEditorNotification(result.error || 'Bulk operation failed', 'error');
            }
        } catch (error) {
            console.error('[BulkEditor] POS update error:', error);
            showBulkEditorNotification('Network error: ' + error.message, 'error');
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
        if (!tableHead) {
            console.log('[BulkEditor] Table head not found, will retry');
            return;
        }

        // Already added
        if (this.checkboxColumnAdded) return;

        // Check if checkbox column already exists
        let selectAllTh = tableHead.querySelector('th.bulk-select-header');
        if (selectAllTh) {
            this.checkboxColumnAdded = true;
            return;
        }

        // The table uses <tr><th>...</th></tr> structure
        // FirstTh needs to be a <th> element, not the <tr>
        let firstTh = tableHead.querySelector('th');
        if (!firstTh) {
            // If no th exists yet, wait for next render
            console.log('[BulkEditor] No header cells found yet');
            return;
        }

        // Create the checkbox header
        selectAllTh = document.createElement('th');
        selectAllTh.className = 'bulk-select-header';
        selectAllTh.style.width = '40px';
        selectAllTh.innerHTML = `
            <input type="checkbox" id="bulk-select-all" class="form-check-input" title="Select all">
        `;

        // Insert before the first th (they're all in the same tr parent)
        tableHead.querySelector('tr').insertBefore(selectAllTh, firstTh);
        this.checkboxColumnAdded = true;
        console.log('[BulkEditor] Checkbox column added to header');
    }

    /**
     * Add checkbox to each row
     * Should be called when table body is rendered
     */
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
}
