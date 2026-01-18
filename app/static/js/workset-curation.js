/**
 * Workset Curation Module
 *
 * Provides workset list view and sequential entry curation with:
 * - Workset list with progress indicators
 * - Navigation (prev/next/first/last)
 * - Status toggles (pending/done/review)
 * - Favorite toggle
 * - Keyboard shortcuts
 */

class WorksetCuration {
    constructor() {
        this.currentWorksetId = null;
        this.currentPosition = 0;
        this.totalEntries = 0;
        this.currentEntry = null;
        this.currentCuration = null;
        this.navigationHistory = [];

        this.init();
    }

    getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    init() {
        // Check if we're on workset list or curation page
        if (document.getElementById('workset-list')) {
            this.loadWorksets();
        } else if (document.getElementById('curation-view')) {
            this.initCurationView();
        }

        // Set up keyboard shortcuts
        this.setupKeyboardShortcuts();
    }

    // ============ WORKSET LIST ============

    async loadWorksets() {
        const container = document.getElementById('workset-list');
        if (!container) return;

        container.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div> Loading worksets...</div>';

        try {
            const response = await fetch('/api/worksets');
            const data = await response.json();

            if (!data.success) {
                container.innerHTML = '<div class="alert alert-danger">Failed to load worksets</div>';
                return;
            }

            this.renderWorksetList(data.worksets, container);
        } catch (error) {
            console.error('[WorksetCuration] Error loading worksets:', error);
            container.innerHTML = '<div class="alert alert-danger">Error loading worksets</div>';
        }
    }

    renderWorksetList(worksets, container) {
        if (!worksets || worksets.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <h5>No Worksets Yet</h5>
                    <p>Create a workset using the <a href="/workbench/query-builder">Query Builder</a></p>
                </div>
            `;
            return;
        }

        // Bulk actions toolbar
        let html = `
            <div class="d-flex justify-content-between align-items-center mb-3 p-3 bg-light rounded" id="bulk-toolbar">
                <div class="form-check">
                    <input type="checkbox" class="form-check-input" id="select-all-worksets">
                    <label class="form-check-label" for="select-all-worksets">Select All</label>
                </div>
                <div id="selected-actions" style="display: none;">
                    <span class="text-muted me-2"><span id="selected-count">0</span> selected</span>
                    <button class="btn btn-sm btn-danger" id="bulk-delete-btn">
                        <i class="bi bi-trash"></i> Delete Selected
                    </button>
                </div>
            </div>
        `;

        html += '<div class="row">';

        for (const ws of worksets) {
            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100 workset-card" data-workset-id="${ws.id}">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <div class="form-check mb-0">
                                <input type="checkbox" class="form-check-input workset-checkbox" data-id="${ws.id}">
                            </div>
                            <h6 class="mb-0 text-truncate" style="max-width: 200px;" title="${ws.name}">${ws.name}</h6>
                            <div class="dropdown">
                                <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown">
                                    <i class="bi bi-three-dots"></i>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end">
                                    <li><a class="dropdown-item curate-btn" href="/workbench/worksets/${ws.id}/curate"><i class="bi bi-pencil"></i> Curate</a></li>
                                    <li><a class="dropdown-item view-entries-btn" href="#" data-workset-id="${ws.id}"><i class="bi bi-list"></i> View Entries</a></li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li><a class="dropdown-item text-danger delete-workset-btn" href="#" data-workset-id="${ws.id}"><i class="bi bi-trash"></i> Delete</a></li>
                                </ul>
                            </div>
                        </div>
                        <div class="card-body">
                            <p class="card-text text-muted small">${ws.total_entries} entries</p>
                            <div class="progress mb-2" style="height: 8px;">
                                <div class="progress-bar bg-secondary" role="progressbar" style="width: 100%"></div>
                            </div>
                            <p class="card-text small text-muted">Created: ${new Date(ws.created_at).toLocaleDateString()}</p>
                            <a href="/workbench/worksets/${ws.id}/curate" class="btn btn-primary btn-sm w-100">
                                <i class="bi bi-pencil"></i> Start Curation
                            </a>
                        </div>
                    </div>
                </div>
            `;
        }

        html += '</div>';
        container.innerHTML = html;

        // Set up bulk selection handlers
        this.setupBulkSelection();

        // Set up event listeners
        container.querySelectorAll('.delete-workset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const wsId = e.currentTarget.dataset.worksetId;
                this.deleteWorkset(wsId);
            });
        });

        container.querySelectorAll('.view-entries-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const wsId = e.currentTarget.dataset.worksetId;
                this.showWorksetEntries(wsId);
            });
        });
    }

    setupBulkSelection() {
        const selectAll = document.getElementById('select-all-worksets');
        const checkboxes = document.querySelectorAll('.workset-checkbox');
        const selectedActions = document.getElementById('selected-actions');
        const selectedCount = document.getElementById('selected-count');
        const bulkDeleteBtn = document.getElementById('bulk-delete-btn');

        const updateSelection = () => {
            const selected = Array.from(checkboxes)
                .filter(cb => cb.checked)
                .map(cb => parseInt(cb.dataset.id));
            const count = selected.length;

            if (selectedActions) {
                selectedActions.style.display = count > 0 ? 'block' : 'none';
            }
            if (selectedCount) {
                selectedCount.textContent = count;
            }
            if (selectAll) {
                selectAll.checked = count === checkboxes.length;
            }

            return selected;
        };

        if (selectAll) {
            selectAll.addEventListener('change', (e) => {
                checkboxes.forEach(cb => {
                    cb.checked = e.target.checked;
                });
                updateSelection();
            });
        }

        checkboxes.forEach(cb => {
            cb.addEventListener('change', () => updateSelection());
        });

        if (bulkDeleteBtn) {
            bulkDeleteBtn.addEventListener('click', async () => {
                const selected = updateSelection();
                if (selected.length === 0) {
                    alert('Please select at least one workset');
                    return;
                }
                if (!confirm(`Delete ${selected.length} selected worksets? Entries will not be affected.`)) {
                    return;
                }

                try {
                    const response = await fetch('/api/worksets/bulk/delete', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-TOKEN': this.getCsrfToken()
                        },
                        body: JSON.stringify({ ids: selected })
                    });
                    const data = await response.json();

                    if (data.success) {
                        this.loadWorksets();
                        alert(`Deleted ${data.deleted} worksets`);
                    } else {
                        alert('Error: ' + (data.error || 'Unknown error'));
                    }
                } catch (error) {
                    console.error('[WorksetCuration] Bulk delete error:', error);
                    alert('Error deleting worksets');
                }
            });
        }
    }

    async deleteWorkset(worksetId) {
        if (!confirm('Delete this workset? Entries will not be affected.')) {
            return;
        }

        try {
            const response = await fetch(`/api/worksets/${worksetId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRF-TOKEN': this.getCsrfToken()
                }
            });
            const data = await response.json();

            if (data.success) {
                this.loadWorksets();
            } else {
                alert('Failed to delete workset: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('[WorksetCuration] Error deleting workset:', error);
            alert('Error deleting workset');
        }
    }

    async showWorksetEntries(worksetId) {
        // Show modal with entries list
        let modal = document.getElementById('workset-entries-modal');
        if (!modal) {
            modal = this.createEntriesModal();
            document.body.appendChild(modal);
        }

        const modalInstance = bootstrap.Modal.getOrCreateInstance(modal);
        modalInstance.show();

        const container = modal.querySelector('#workset-entries-list');
        container.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div> Loading...</div>';

        try {
            const response = await fetch(`/api/worksets/${worksetId}/entries`);
            const data = await response.json();

            if (data.error) {
                container.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                return;
            }

            this.renderEntriesList(data, container);
        } catch (error) {
            console.error('[WorksetCuration] Error loading entries:', error);
            container.innerHTML = '<div class="alert alert-danger">Error loading entries</div>';
        }
    }

    renderEntriesList(data, container) {
        const { workset, entries, pagination } = data;

        let html = `
            <h5>${workset.name}</h5>
            <p class="text-muted">${workset.total_entries} entries</p>
            <div class="list-group list-group-flush" style="max-height: 400px; overflow-y: auto;">
        `;

        for (const item of entries) {
            const entry = item.entry;
            const lexeme = entry.lexical_unit?.en || entry.id;
            const status = item.curation.status;
            const statusClass = status === 'done' ? 'success' : status === 'review' ? 'warning' : 'secondary';

            html += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${this.escapeHtml(lexeme)}</strong>
                        <span class="badge bg-${statusClass} ms-2">${status}</span>
                        ${item.curation.is_favorite ? '<i class="bi bi-star-fill text-warning ms-1"></i>' : ''}
                    </div>
                    <a href="/entries/${entry.id}/edit" class="btn btn-sm btn-outline-primary">Edit</a>
                </div>
            `;
        }

        html += '</div>';
        container.innerHTML = html;
    }

    createEntriesModal() {
        const div = document.createElement('div');
        div.id = 'workset-entries-modal';
        div.className = 'modal fade';
        div.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Workset Entries</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="workset-entries-list"></div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        return div;
    }

    // ============ CURATION VIEW ============

    initCurationView() {
        const wsId = document.getElementById('curation-view')?.dataset.worksetId;
        if (!wsId) return;

        this.currentWorksetId = parseInt(wsId);
        this.loadCurationProgress();
        this.loadCurrentEntry(0);

        this.setupCurationControls();
    }

    async loadCurationProgress() {
        try {
            const response = await fetch(`/api/worksets/${this.currentWorksetId}/progress`);
            const data = await response.json();

            if (data.error) {
                console.error('[WorksetCuration] Error loading progress:', data.error);
                return;
            }

            this.totalEntries = data.total;
            this.renderProgressBar(data);
        } catch (error) {
            console.error('[WorksetCuration] Error loading progress:', error);
        }
    }

    renderProgressBar(data) {
        const container = document.getElementById('progress-container');
        if (!container) return;

        container.innerHTML = `
            <div class="progress mb-2" style="height: 20px;">
                <div class="progress-bar bg-success" style="width: ${data.progress_percent}%"></div>
                <div class="progress-bar bg-warning" style="width: ${(data.review / data.total * 100) || 0}%"></div>
                <div class="progress-bar bg-secondary" style="width: ${(data.pending / data.total * 100) || 0}%"></div>
            </div>
            <div class="d-flex justify-content-between small text-muted">
                <span><i class="bi bi-check-circle text-success"></i> ${data.done} done</span>
                <span><i class="bi bi-exclamation-triangle text-warning"></i> ${data.review} review</span>
                <span><i class="bi bi-clock text-secondary"></i> ${data.pending} pending</span>
                <span>${data.progress_percent}% complete</span>
            </div>
        `;
    }

    async loadCurrentEntry(position = 0) {
        const container = document.getElementById('entry-content');
        if (!container) return;

        this.currentPosition = position;
        container.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div> Loading entry...</div>';

        try {
            const url = `/api/worksets/${this.currentWorksetId}/navigation/current?position=${position}`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.error) {
                container.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                return;
            }

            this.currentEntry = data.entry;
            this.currentCuration = data.curation;

            this.renderEntry(data);
            this.updateNavigation(data.navigation);
            this.updateStatusButtons(data.curation.status);
            this.updateFavoriteButton(data.curation.is_favorite);
        } catch (error) {
            console.error('[WorksetCuration] Error loading entry:', error);
            container.innerHTML = '<div class="alert alert-danger">Error loading entry</div>';
        }
    }

    renderEntry(data) {
        const container = document.getElementById('entry-content');
        const entry = data.entry;
        const lexeme = entry.lexical_unit?.en || 'Unknown';
        const pos = entry.grammatical_info?.trait?.value || '';

        let html = `
            <div class="entry-display">
                <h3 class="entry-lexeme">
                    ${this.escapeHtml(lexeme)}
                    ${pos ? `<span class="badge bg-secondary ms-2">${this.escapeHtml(pos)}</span>` : ''}
                </h3>
        `;

        // Render senses
        if (entry.senses && entry.senses.length > 0) {
            html += '<div class="entry-senses">';
            for (const sense of entry.senses) {
                html += '<div class="sense-item mb-3">';
                if (sense.definition) {
                    html += `<p class="definition">${this.escapeHtml(sense.definition)}</p>`;
                }
                if (sense.gloss) {
                    html += `<p class="gloss text-muted fst-italic">${this.escapeHtml(sense.gloss)}</p>`;
                }
                if (sense.examples && sense.examples.length > 0) {
                    html += '<ul class="examples list-unstyled ms-4">';
                    for (const ex of sense.examples) {
                        html += `<li><i class="bi bi-quote text-muted"></i> ${this.escapeHtml(ex)}</li>`;
                    }
                    html += '</ul>';
                }
                html += '</div>';
            }
            html += '</div>';
        }

        html += `
                <div class="entry-actions mt-4">
                    <a href="/entries/${entry.id}/edit" class="btn btn-primary">
                        <i class="bi bi-pencil"></i> Edit Entry
                    </a>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    updateNavigation(nav) {
        const posDisplay = document.getElementById('position-display');
        if (posDisplay) {
            posDisplay.textContent = `Entry ${nav.current_position + 1} of ${nav.total}`;
        }

        const prevBtn = document.getElementById('btn-prev');
        const nextBtn = document.getElementById('btn-next');
        const firstBtn = document.getElementById('btn-first');
        const lastBtn = document.getElementById('btn-last');

        if (prevBtn) prevBtn.disabled = !nav.has_prev;
        if (nextBtn) nextBtn.disabled = !nav.has_next;
        if (firstBtn) firstBtn.disabled = nav.current_position === 0;
        if (lastBtn) lastBtn.disabled = nav.current_position === nav.total - 1;
    }

    updateStatusButtons(currentStatus) {
        document.querySelectorAll('.status-btn').forEach(btn => {
            const status = btn.dataset.status;
            btn.classList.toggle('active', status === currentStatus);
        });
    }

    updateFavoriteButton(isFavorite) {
        const btn = document.getElementById('btn-favorite');
        if (btn) {
            btn.classList.toggle('active', isFavorite);
            btn.innerHTML = isFavorite
                ? '<i class="bi bi-star-fill"></i> Favorited'
                : '<i class="bi bi-star"></i> Add to Favorites';
        }
    }

    setupCurationControls() {
        // Navigation buttons
        document.getElementById('btn-first')?.addEventListener('click', () => this.navigate('first'));
        document.getElementById('btn-prev')?.addEventListener('click', () => this.navigate('prev'));
        document.getElementById('btn-next')?.addEventListener('click', () => this.navigate('next'));
        document.getElementById('btn-last')?.addEventListener('click', () => this.navigate('last'));

        // Status buttons
        document.querySelectorAll('.status-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.setStatus(btn.dataset.status);
            });
        });

        // Favorite button
        document.getElementById('btn-favorite')?.addEventListener('click', () => {
            this.toggleFavorite();
        });

        // Position jump
        const jumpInput = document.getElementById('jump-position');
        if (jumpInput) {
            jumpInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const pos = parseInt(jumpInput.value) - 1;
                    if (pos >= 0 && pos < this.totalEntries) {
                        this.loadCurrentEntry(pos);
                    }
                }
            });
        }
    }

    async navigate(direction) {
        try {
            const response = await fetch(
                `/api/worksets/${this.currentWorksetId}/navigation/${direction}`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': this.getCsrfToken()
                    },
                    body: JSON.stringify({ position: this.currentPosition })
                }
            );
            const data = await response.json();

            if (data.error) {
                console.error('[WorksetCuration] Navigation error:', data.error);
                return;
            }

            this.currentEntry = data.entry;
            this.currentCuration = data.curation;

            this.renderEntry(data);
            this.updateNavigation(data.navigation);
            this.updateStatusButtons(data.curation.status);
            this.updateFavoriteButton(data.curation.is_favorite);

            // Update progress
            this.loadCurationProgress();
        } catch (error) {
            console.error('[WorksetCuration] Navigation error:', error);
        }
    }

    async setStatus(status) {
        if (!this.currentEntry) return;

        try {
            const response = await fetch(
                `/api/worksets/${this.currentWorksetId}/entries/${this.currentEntry.id}/status`,
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': this.getCsrfToken()
                    },
                    body: JSON.stringify({ status })
                }
            );
            const data = await response.json();

            if (data.success) {
                this.currentCuration.status = status;
                this.updateStatusButtons(status);
                this.loadCurationProgress();

                // Auto-advance if marking done
                if (status === 'done') {
                    this.navigate('next');
                }
            }
        } catch (error) {
            console.error('[WorksetCuration] Error setting status:', error);
        }
    }

    async toggleFavorite() {
        if (!this.currentEntry) return;

        const isFavorite = !this.currentCuration?.is_favorite;

        try {
            const response = await fetch(
                `/api/worksets/${this.currentWorksetId}/entries/${this.currentEntry.id}/favorite`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': this.getCsrfToken()
                    },
                    body: JSON.stringify({ is_favorite: isFavorite })
                }
            );
            const data = await response.json();

            if (data.success) {
                if (this.currentCuration) {
                    this.currentCuration.is_favorite = isFavorite;
                }
                this.updateFavoriteButton(isFavorite);
            }
        } catch (error) {
            console.error('[WorksetCuration] Error toggling favorite:', error);
        }
    }

    // ============ KEYBOARD SHORTCUTS ============

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Only work if not in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            switch (e.key) {
                case 'ArrowLeft':
                    e.preventDefault();
                    this.navigate('prev');
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.navigate('next');
                    break;
                case 'd':
                case 'D':
                    e.preventDefault();
                    this.setStatus('done');
                    break;
                case 'r':
                case 'R':
                    e.preventDefault();
                    this.setStatus('review');
                    break;
                case 'p':
                case 'P':
                    e.preventDefault();
                    this.setStatus('pending');
                    break;
                case 'f':
                case 'F':
                    e.preventDefault();
                    this.toggleFavorite();
                    break;
                case 'Home':
                    e.preventDefault();
                    this.navigate('first');
                    break;
                case 'End':
                    e.preventDefault();
                    this.navigate('last');
                    break;
            }
        });
    }

    // ============ UTILITIES ============

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.worksetCuration = new WorksetCuration();
});
