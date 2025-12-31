/**
 * Backup Manager - Handles backup management UI functionality
 */

class BackupManager {
    constructor() {
        this.backupTable = null;
        this.currentBackupId = null;

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadBackupHistory();
        this.loadBackupSettings();
    }

    bindEvents() {
        // Manual backup form
        const backupForm = document.getElementById('manual-backup-form');
        if (backupForm) {
            backupForm.addEventListener('submit', (e) => this.handleCreateBackup(e));
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-backups');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadBackupHistory());
        }

        // Close details panel button
        const closeDetailsBtn = document.getElementById('close-backup-details');
        if (closeDetailsBtn) {
            closeDetailsBtn.addEventListener('click', () => {
                const panel = document.getElementById('backup-details-panel');
                if (panel) {
                    panel.style.display = 'none';
                    const content = document.getElementById('backup-details-content');
                    if (content) content.innerHTML = '';
                }
            });
        }

        // Restore confirmation
        const confirmRestoreBtn = document.getElementById('confirm-restore-btn');
        if (confirmRestoreBtn) {
            confirmRestoreBtn.addEventListener('click', () => this.performRestore());
        }

        // Delete confirmation
        const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', () => this.performDelete());
        }

        // Delegate action buttons (view, validate, delete) from the table body
        const tbody = document.getElementById('backup-history-body');
        if (tbody && !tbody.dataset.backupBound) {
            tbody.addEventListener('click', (e) => {
                const btn = e.target.closest('button, a');
                if (!btn) return;
                const id = btn.dataset.backupId;
                if (!id) return;

                // Two-click confirm flow for destructive actions (no modal): first click arms, second confirms
                if (btn.classList.contains('delete-btn')) {
                    if (btn.dataset.confirm !== 'true') {
                        btn.dataset.confirm = 'true';
                        btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Click to confirm';
                        setTimeout(() => { btn.dataset.confirm = 'false'; btn.innerHTML = '<i class="fas fa-trash-alt"></i>'; }, 7000);
                        return;
                    }
                    this.currentBackupId = id;
                    this.performDelete();
                    return;
                }

                if (btn.classList.contains('restore-row-btn')) {
                    if (btn.dataset.confirm !== 'true') {
                        btn.dataset.confirm = 'true';
                        btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Click to confirm';
                        setTimeout(() => { btn.dataset.confirm = 'false'; btn.innerHTML = '<i class="fas fa-undo"></i> Restore'; }, 7000);
                        return;
                    }
                    this.currentBackupId = id;
                    this.performRestore();
                    return;
                }

                if (btn.classList.contains('view-btn')) {
                    if (btn.disabled) { this.showToast('Backup is pending', 'info'); return; }
                    this.showBackupDetails(id);
                    return;
                }

                if (btn.classList.contains('validate-btn')) {
                    if (btn.disabled) { this.showToast('Backup is pending', 'info'); return; }
                    this.validateBackup(id);
                    return;
                }
            });
            tbody.dataset.backupBound = 'true';
        }
    }

    async handleCreateBackup(event) {
        event.preventDefault();

        const description = document.getElementById('backup-description').value.trim();
        const type = document.getElementById('backup-type').value;
        const createBtn = document.getElementById('create-backup-btn');

        // Update button state
        createBtn.disabled = true;
        createBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating Backup...';

        try {
            // Quick server reachability check to provide clearer errors
            try {
                const ping = await fetch('/api/backup/ping');
                if (!ping.ok) throw new Error('Server ping failed');
            } catch (pingErr) {
                console.error('Server ping failed', pingErr);
                this.showToast('Unable to reach backup API; try refreshing the page', 'error');
                return;
            }
            const response = await fetch('/api/backup/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    db_name: window.CURRENT_DB_NAME || 'dictionary',
                    description: description || null,
                    backup_type: type,
                    include_media: document.getElementById('backup-include-media') ? document.getElementById('backup-include-media').checked : false
                })
            });

            if (response.ok) {
                const result = await response.json();
                document.getElementById('backup-description').value = '';

                // Quietly refresh history; do not insert placeholder rows.
                if (result.op_id) {
                    this.pollOpStatus(result.op_id);
                } else {
                    await this.loadBackupHistory();
                }
            } else {
                const error = await response.json();
                this.showToast(`Backup creation failed: ${error.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Error creating backup:', error);
            this.showToast('Network error during backup creation', 'error');
        } finally {
            createBtn.disabled = false;
            createBtn.innerHTML = '<i class="fas fa-save"></i> Create Backup';
        }
    }

    async pollOpStatus(opId, attempts = 60, interval = 2000) {
        for (let i = 0; i < attempts; i++) {
            try {
                const resp = await fetch(`/api/backup/status/${opId}`);
                if (!resp.ok) {
                    await new Promise(r => setTimeout(r, interval));
                    continue;
                }
                const data = await resp.json();
                if (data && data.op && data.op.status === 'done') {
                    await this.loadBackupHistory();
                    return;
                } else if (data && data.op && data.op.status === 'failed') {
                    this.showToast('Backup failed on server', 'error');
                    await this.loadBackupHistory();
                    return;
                }
            } catch (err) {
                // ignore and retry
            }
            await new Promise(r => setTimeout(r, interval));
        }
        // If we get here, polling timed out; refresh history once and leave pending for manual refresh
        await this.loadBackupHistory();
    }

    async loadBackupHistory() {
        const tbody = document.getElementById('backup-history-body');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center">
                    <i class="fas fa-spinner fa-spin me-2"></i>Loading backup history...
                </td>
            </tr>
        `;

        try {
            const response = await fetch(`/api/backup/history?db_name=${encodeURIComponent(window.CURRENT_DB_NAME || 'dictionary')}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.renderBackupHistory(data.data || []);
        } catch (error) {
            console.error('Error loading backup history:', error);
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Failed to load backup history
                    </td>
                </tr>
            `;
        }
    }

    renderBackupHistory(backups) {
        const tbody = document.getElementById('backup-history-body');
        const countBadge = document.getElementById('backup-count');

        if (countBadge) {
            countBadge.textContent = `${backups.length} backup${backups.length !== 1 ? 's' : ''}`;
        }

        if (backups.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">
                        <i class="fas fa-info-circle me-2"></i>No backups found
                    </td>
                </tr>
            `;
            return;
        }
        // Build data rows (array of arrays) and be defensive about malformed items
        const dataRows = [];
        const expectedCols = $('#backup-history-table thead th').length || 6;
        for (const b of backups) {
            try {
                const cols = this.createBackupRowData(b, expectedCols);
                if (Array.isArray(cols) && cols.length === expectedCols) {
                    dataRows.push(cols);
                } else {
                    console.warn('Skipping malformed backup row data (expected cols=%d, got %d)', expectedCols, (cols && cols.length) || 0, b);
                }
            } catch (e) {
                console.warn('Error building row for backup', b, e);
            }
        }

        const $table = $('#backup-history-table');

        // Remove any placeholder rows from tbody to avoid confusing DataTables
        try {
            tbody.innerHTML = '';
        } catch (e) {
            // ignore if tbody is managed by DataTables
        }

        // Update existing DataTable instance if present
        if (this.backupTable) {
            try {
                this.backupTable.clear();
                if (dataRows.length) this.backupTable.rows.add(dataRows);
                this.backupTable.draw();
                return;
            } catch (e) {
                console.error('Error updating DataTable rows', e);
                try { this.backupTable.destroy(); } catch (ex) { /* ignore */ }
                this.backupTable = null;
                $table.find('tbody').empty();
            }
        }

        // Prepare a minimal columns definition so DataTables knows how many columns to expect
        const columns = Array.from({ length: expectedCols }).map(() => ({}));

        // Initialize DataTable with data to avoid mixing manual DOM changes and DataTables internal state
        this.backupTable = $table.DataTable({
            data: dataRows,
            columns: columns,
            order: [[0, 'desc']],
            pageLength: 25,
            responsive: true,
            columnDefs: [
                { orderable: false, targets: expectedCols - 1 } // Actions column not sortable
            ]
        });
    }

    // Build an array of cell HTML strings for DataTables rows.add API
    createBackupRowData(backup, expectedCols = 6) {
        const date = new Date(backup.timestamp).toLocaleString();
        const size = this.formatFileSize(backup.file_size || 0);
        const statusVal = backup.status || (backup.is_valid ? 'completed' : 'unknown');
        const statusBadge = this.getStatusBadge(statusVal);
        const actions = this.createActionButtons(backup);

        const typeHtml = `<span class="badge bg-secondary">${backup.type || 'full'}</span>`;
        const descHtml = backup.description ? backup.description : '<em>No description</em>';

        let cols = [date, typeHtml, size, descHtml, statusBadge, actions];

        // Normalize to expectedCols
        if (cols.length < expectedCols) {
            while (cols.length < expectedCols) cols.push('');
        } else if (cols.length > expectedCols) {
            // Merge extra columns into the last column
            const extras = cols.slice(expectedCols - 1);
            cols = cols.slice(0, expectedCols - 1);
            cols.push(extras.join(' '));
        }
        return cols;
    }

    createBackupRow(backup) {
        const date = new Date(backup.timestamp).toLocaleString();
        const size = this.formatFileSize(backup.file_size || 0);
        const statusVal = backup.status || (backup.is_valid ? 'completed' : 'unknown');
        const statusBadge = this.getStatusBadge(statusVal);
        const actions = this.createActionButtons(backup);

        return `
            <tr>
                <td>${date}</td>
                <td><span class="badge bg-secondary">${backup.type || 'full'}</span></td>
                <td>${size}</td>
                <td>${backup.description || '<em>No description</em>'}</td>
                <td>${statusBadge}</td>
                <td>${actions}</td>
            </tr>
        `;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    formatScheduleDescription(trigger) {
        // Convert APScheduler cron trigger to human-readable description
        // Example: "cron[month='*', day='*', day_of_week='*', hour='*', minute='0']"
        if (!trigger) return 'Custom schedule';

        // Extract minute, hour, day, month, day_of_week from the trigger string
        const minuteMatch = trigger.match(/minute='([^']*)'/);
        const hourMatch = trigger.match(/hour='([^']*)'/);
        const dayMatch = trigger.match(/day='([^']*)'/);
        const monthMatch = trigger.match(/month='([^']*)'/);
        const dowMatch = trigger.match(/day_of_week='([^']*)'/);

        const minute = minuteMatch ? minuteMatch[1] : '*';
        const hour = hourMatch ? hourMatch[1] : '*';
        const day = dayMatch ? dayMatch[1] : '*';
        const month = monthMatch ? monthMatch[1] : '*';
        const dow = dowMatch ? dowMatch[1] : '*';

        // Determine the schedule type
        if (minute !== '*' && hour === '*' && day === '*' && month === '*' && dow === '*') {
            // Hourly: specific minute every hour
            return `Hourly at minute ${minute}`;
        } else if (minute !== '*' && hour !== '*' && day === '*' && month === '*' && dow === '*') {
            // Daily: specific time every day
            const h = parseInt(hour).toString().padStart(2, '0');
            const m = parseInt(minute).toString().padStart(2, '0');
            return `Daily at ${h}:${m}`;
        } else if (minute !== '*' && hour !== '*' && day === '*' && month === '*' && dow !== '*') {
            // Weekly: specific time on specific day
            const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
            const dayNum = parseInt(dow);
            const dayName = days[dayNum] || dow;
            const h = parseInt(hour).toString().padStart(2, '0');
            const m = parseInt(minute).toString().padStart(2, '0');
            return `Weekly on ${dayName} at ${h}:${m}`;
        } else if (minute !== '*' && hour !== '*' && day !== '*' && month === '*' && dow === '*') {
            // Monthly: specific time on specific day of month
            const h = parseInt(hour).toString().padStart(2, '0');
            const m = parseInt(minute).toString().padStart(2, '0');
            return `Monthly on day ${day} at ${h}:${m}`;
        } else {
            // Fallback to raw trigger
            return trigger;
        }
    }

    getStatusBadge(status) {
        const statusMap = {
            'completed': '<span class="badge bg-success">Completed</span>',
            'failed': '<span class="badge bg-danger">Failed</span>',
            'in_progress': '<span class="badge bg-warning">In Progress</span>',
            'restored': '<span class="badge bg-info">Restored</span>'
        };
        return statusMap[status] || `<span class="badge bg-secondary">${status}</span>`;
    }

    createActionButtons(backup) {
        const isPending = Boolean(backup.is_pending || backup.status === 'in_progress' || backup.status === 'pending');
        const disabledAttr = isPending ? 'disabled' : '';
        const pendingTitle = isPending ? ' title="Pending backup"' : '';

        const viewBtn = `<button class="btn btn-sm btn-outline-info me-1 view-btn" data-backup-id="${backup.id}" ${disabledAttr}${pendingTitle}>
            <i class="fas fa-eye"></i> View
        </button>`;

        const restoreBtn = (backup.is_valid && !isPending) ?
            `<button class="btn btn-sm btn-outline-warning me-1 restore-row-btn" data-backup-id="${backup.id}">
                <i class="fas fa-undo"></i> Restore
            </button>` : '';

        const validateBtn = `<button class="btn btn-sm btn-outline-success me-1 validate-btn" data-backup-id="${backup.id}" ${disabledAttr}${pendingTitle}>
            <i class="fas fa-check-circle"></i> Validate
        </button>`;

        const downloadBtn = `<a class="btn btn-sm btn-outline-primary me-1 ${isPending ? 'disabled' : ''}" href="${isPending ? '#' : '/api/backup/download/' + backup.id}" ${isPending ? 'onclick="return false;"' : ''} ${pendingTitle}>
            <i class="fas fa-download"></i> Download
        </a>`;

        const deleteBtn = `<button class="btn btn-sm btn-outline-danger delete-btn" title="Delete backup" data-backup-id="${backup.id}" ${disabledAttr}${pendingTitle}>
            <i class="fas fa-trash-alt"></i>
        </button>`;
        return `${viewBtn}${downloadBtn}${restoreBtn}${validateBtn}${deleteBtn}`;
    }

    async loadBackupSettings() {
        try {
            // Load backup settings from the API
            const scheduleEl = document.getElementById('current-schedule');
            const directoryEl = document.getElementById('backup-directory');
            const nextBackupEl = document.getElementById('next-backup');

            // Get scheduled backups from the API
            const response = await fetch('/api/backup/scheduled');
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    const scheduledBackups = result.data;
                    
                    // Update schedule information based on actual scheduled backups
                    if (scheduleEl) {
                        if (scheduledBackups && scheduledBackups.length > 0) {
                            // Show actual schedule information with human-readable description
                            const firstBackup = scheduledBackups[0];
                            const trigger = firstBackup.trigger;
                            scheduleEl.textContent = this.formatScheduleDescription(trigger);
                        } else {
                            scheduleEl.textContent = 'No backups scheduled';
                        }
                    }
                    
                    // Update next backup time
                    if (nextBackupEl) {
                        if (scheduledBackups && scheduledBackups.length > 0) {
                            // Find the soonest next backup
                            let soonest = null;
                            for (const backup of scheduledBackups) {
                                if (backup.next_run_time) {
                                    const nextRun = new Date(backup.next_run_time);
                                    if (!soonest || nextRun < soonest) {
                                        soonest = nextRun;
                                    }
                                }
                            }
                            
                            if (soonest) {
                                // Format the date nicely
                                const options = { 
                                    weekday: 'long', 
                                    year: 'numeric', 
                                    month: 'long', 
                                    day: 'numeric',
                                    hour: '2-digit', 
                                    minute: '2-digit'
                                };
                                nextBackupEl.textContent = soonest.toLocaleDateString('en-US', options);
                            } else {
                                nextBackupEl.textContent = 'Schedule available, next run not determined';
                            }
                        } else {
                            nextBackupEl.textContent = 'No backups scheduled';
                        }
                    }
                }
            } else {
                // Fallback to placeholder data if API call fails
                console.warn('Failed to load backup settings, using placeholder data');
                if (scheduleEl) scheduleEl.textContent = 'Daily at 2:00 AM';
                if (directoryEl) directoryEl.textContent = '/var/backups/dictionary';
                if (nextBackupEl) nextBackupEl.textContent = 'Tomorrow at 2:00 AM';
            }

        } catch (error) {
            console.error('Error loading backup settings:', error);
            // Fallback to placeholder data on error
            if (scheduleEl) scheduleEl.textContent = 'Daily at 2:00 AM';
            if (directoryEl) directoryEl.textContent = '/var/backups/dictionary';
            if (nextBackupEl) nextBackupEl.textContent = 'Tomorrow at 2:00 AM';
        }
    }

    async showBackupDetails(backupId) {
        this.currentBackupId = backupId;

        try {
            const response = await fetch(`/api/backup/history/${backupId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const backup = await response.json();
            this.displayBackupDetails(backup);

            // Show inline details panel instead of modal
            const panel = document.getElementById('backup-details-panel');
            if (panel) {
                panel.style.display = 'block';
                panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }

        } catch (error) {
            console.error('Error loading backup details:', error);
            this.showToast('Failed to load backup details', 'error');
        }
    }

    displayBackupDetails(backup) {
        const content = document.getElementById('backup-details-content');
        const restoreBtn = document.getElementById('restore-backup-btn');

        const details = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Backup Information</h6>
                    <dl class="row">
                        <dt class="col-sm-4">ID:</dt>
                        <dd class="col-sm-8">${backup.id}</dd>

                        <dt class="col-sm-4">Type:</dt>
                        <dd class="col-sm-8">${backup.type || 'full'}</dd>

                        <dt class="col-sm-4">Created:</dt>
                        <dd class="col-sm-8">${new Date(backup.timestamp).toLocaleString()}</dd>

                        <dt class="col-sm-4">Size:</dt>
                        <dd class="col-sm-8">${this.formatFileSize(backup.file_size || 0)}</dd>

                        <dt class="col-sm-4">Status:</dt>
                        <dd class="col-sm-8">${this.getStatusBadge(backup.status || (backup.is_valid ? 'completed' : 'unknown'))}</dd>
                    </dl>
                </div>
                <div class="col-md-6">
                    <h6>Additional Details</h6>
                    <dl class="row">
                        <dt class="col-sm-4">Database:</dt>
                        <dd class="col-sm-8">${backup.db_name || 'dictionary'}</dd>

                        <dt class="col-sm-4">Description:</dt>
                        <dd class="col-sm-8">${backup.description || 'No description'}</dd>

                                <dt class="col-sm-4">File Path:</dt>
                        <dd class="col-sm-8"><code>${backup.file_path || 'N/A'}</code></dd>
                    </dl>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-12">
                    <h6>Includes</h6>
                    <ul class="list-inline small">
                        ${backup.includes ? Object.entries(backup.includes).map(([k,v]) => `<li class="list-inline-item me-3"><strong>${k}:</strong> ${v ? '<span class="text-success">Yes</span>' : '<span class="text-muted">No</span>'}</li>`).join('') : ''}
                    </ul>
                </div>
            </div>
        `;


        content.innerHTML = details;

        // Add explanatory note about actions (inline)
        const note = document.createElement('div');
        note.className = 'mt-3 small text-muted';
        note.innerHTML = '<p><strong>Note:</strong> "View" shows details here. "Validate" checks the backup file. "Restore" will replace the current database.</p>';
        content.appendChild(note);

        // Show restore button only for valid backups
        if (restoreBtn) {
            // Allow restore if backup validates OR there's a non-empty file to restore from
            const canRestore = Boolean(backup.is_valid) || (backup.file_size && backup.file_size > 0);
            restoreBtn.style.display = canRestore ? 'inline-block' : 'none';
            // restore button in rows is handled via delegated click; nothing to bind here
        }

        // No modal handling — inline panel is used instead
    }

    confirmRestore(backupId) {
        this.currentBackupId = backupId;
        console.debug('confirmRestore called for', backupId);
        // Inline confirmation using window.confirm to avoid modals
        const ok = window.confirm('Restore this backup? This will replace the current database.');
        if (ok) this.performRestore();
    }



    async performDelete() {
        if (!this.currentBackupId) return;

        const confirmBtn = document.getElementById('confirm-delete-btn');
        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';
        }

        try {
            const response = await fetch(`/api/backup/${this.currentBackupId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                // Don't show an obtrusive success toast/modal on delete; silently refresh list
                try {
                    const modalEl = document.getElementById('deleteConfirmModal');
                    const modal = modalEl ? bootstrap.Modal.getInstance(modalEl) : null;
                    if (modal) modal.hide();
                } catch (e) {
                    // ignore
                }
                await this.loadBackupHistory();
            } else {
                const error = await response.json();
                this.showToast(`Delete failed: ${error.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Error during delete:', error);
            this.showToast('Network error during delete', 'error');
        } finally {
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = 'Yes, Delete';
            }
        }
    }

    async performRestore() {
        if (!this.currentBackupId) return;

        const confirmBtn = document.getElementById('confirm-restore-btn');
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Restoring...';

        try {
            // Get backup details to obtain db_name and file_path
            const detailsResp = await fetch(`/api/backup/history/${this.currentBackupId}`);
            if (!detailsResp.ok) throw new Error('Failed to fetch backup details');
            const backup = await detailsResp.json();

            const response = await fetch(`/api/backup/restore/${this.currentBackupId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ db_name: backup.db_name, backup_file_path: backup.file_path })
            });

            if (response.ok) {
                const result = await response.json();
                this.showToast(result.message || 'Backup restored successfully', 'success');

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('restoreConfirmModal'));
                if (modal) modal.hide();

                // Refresh backup history
                await this.loadBackupHistory();
            } else {
                const error = await response.json();
                this.showToast(`Restore failed: ${error.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Error during restore:', error);
            this.showToast('Network error during restore', 'error');
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Yes, Restore Backup';
        }
    }

    async validateBackup(backupId) {
        try {
            const response = await fetch(`/api/backup/validate_id/${backupId}`);
            if (response.ok) {
                const result = await response.json();
                if (result.valid) {
                    this.showToast('Backup validation successful', 'success');
                } else {
                    const msg = (result.errors && result.errors.join('; ')) || result.error || 'Backup validation failed';
                    this.showToast(msg, 'error');
                }
            } else {
                const err = await response.json();
                this.showToast(err.error || 'Backup validation failed', 'error');
            }
        } catch (error) {
            console.error('Error validating backup:', error);
            this.showToast('Network error during validation', 'error');
        }
    }

    showToast(message, type = 'info') {
        // Use existing toast system if available
        if (window.showAppToast) {
            window.showAppToast(message, type);
        } else if (typeof showAppToast === 'function') {
            showAppToast(message, type);
        } else {
            // Fallback to alert
            alert(message);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // BackupManager is initialized in the template
});