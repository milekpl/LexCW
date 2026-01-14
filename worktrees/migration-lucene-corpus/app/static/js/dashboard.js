/**
 * Lexicographic Curation Workbench - Dashboard JavaScript
 *
 * This file contains the functionality for the dashboard/home page.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Set up auto-refresh every 5 minutes
    setInterval(fetchDashboardData, 5 * 60 * 1000);
    
    // Set up refresh button
    const refreshBtn = document.getElementById('refresh-stats-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            fetchDashboardData();
        });
    }
    
    // Set up quick backup button
    const quickBackupBtn = document.getElementById('quick-backup-btn');
    if (quickBackupBtn) {
        quickBackupBtn.addEventListener('click', function() {
            createQuickBackup();
        });
    }
});

/**
 * Refresh dashboard data by reloading the page
 * Since there's no separate API endpoint, we refresh to get updated data
 */
function fetchDashboardData() {
    // Refresh the page to get updated dashboard data
    window.location.reload();
}

/**
 * Create a quick backup with proper database name parameter
 */
function createQuickBackup() {
    const quickBackupBtn = document.getElementById('quick-backup-btn');
    if (!quickBackupBtn) return;
    
    const originalText = quickBackupBtn.innerHTML;
    const icon = quickBackupBtn.querySelector('i');
    
    // Show loading state
    quickBackupBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    quickBackupBtn.disabled = true;
    quickBackupBtn.classList.remove('btn-success');
    quickBackupBtn.classList.add('btn-warning');
    
    // Get current database name from the page or use default
    const dbName = window.currentDatabaseName || 'dictionary';
    
    // Make API call to create backup with required db_name parameter
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    const headers = { 'Content-Type': 'application/json' };
    if (csrfToken) {
        headers['X-CSRF-TOKEN'] = csrfToken;
    }

    fetch('/api/backup/create', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
            db_name: dbName,
            backup_type: 'manual',
            name: `Quick Backup ${new Date().toLocaleString()}`,
            description: 'Quick backup created from dashboard'
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(result => {
        if (result.success) {
            // Show success
            quickBackupBtn.innerHTML = '<i class="fas fa-check"></i> Success!';
            quickBackupBtn.classList.remove('btn-warning');
            quickBackupBtn.classList.add('btn-success');
            
            // Refresh dashboard data to show updated backup info
            setTimeout(() => {
                fetchDashboardData();
            }, 500);
            
            // Reset button after 2 seconds
            setTimeout(() => {
                quickBackupBtn.innerHTML = originalText;
                quickBackupBtn.classList.remove('btn-success');
                quickBackupBtn.classList.add('btn-success');
                quickBackupBtn.disabled = false;
            }, 2000);
        } else {
            throw new Error(result.error || 'Unknown error');
        }
    })
    .catch(error => {
        console.error('Error creating backup:', error);
        
        // Show error
        quickBackupBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
        quickBackupBtn.classList.remove('btn-warning');
        quickBackupBtn.classList.add('btn-danger');
        
        // Reset button after 2 seconds
        setTimeout(() => {
            quickBackupBtn.innerHTML = originalText;
            quickBackupBtn.classList.remove('btn-danger');
            quickBackupBtn.classList.add('btn-success');
            quickBackupBtn.disabled = false;
        }, 2000);
    });
}

/**
 * Update system status in the UI
 */
function updateSystemStatus(systemStatus) {
    // Update DB connection status
    const dbStatusBadge = document.getElementById('db-status-badge');
    if (dbStatusBadge) {
        dbStatusBadge.textContent = systemStatus.db_connected ? 'Connected' : 'Disconnected';
        dbStatusBadge.className = `badge bg-${systemStatus.db_connected ? 'success' : 'danger'} rounded-pill`;
    }
    
    // Update backup status
    const backupStatusBadge = document.getElementById('backup-status-badge');
    if (backupStatusBadge) {
        backupStatusBadge.textContent = systemStatus.last_backup || 'Never';
    }
    
    // Update next backup
    const nextBackupBadge = document.getElementById('next-backup-badge');
    if (nextBackupBadge) {
        nextBackupBadge.textContent = systemStatus.next_backup || 'Not scheduled';
    }
    
    // Update backup count
    const backupCountBadge = document.getElementById('backup-count-badge');
    if (backupCountBadge) {
        backupCountBadge.textContent = systemStatus.backup_count || 0;
    }
    
    // Update storage status
    const storageStatusBadge = document.getElementById('storage-status-badge');
    if (storageStatusBadge) {
        const percent = systemStatus.storage_percent || 0;
        storageStatusBadge.textContent = `${percent}%`;
        storageStatusBadge.className = `badge bg-${percent < 80 ? 'success' : 'warning'} rounded-pill`;
    }
}

/**
 * Update recent activity in the UI
 */
function updateRecentActivity(activity) {
    const activityContainer = document.querySelector('.list-group.list-group-flush');
    if (activityContainer) {
        activityContainer.innerHTML = '';
        
        if (activity && activity.length > 0) {
            activity.forEach(item => {
                const li = document.createElement('li');
                li.className = 'list-group-item';
                li.innerHTML = `
                    <small class="text-muted">${item.timestamp}</small><br>
                    <strong>${item.action}</strong>: ${item.description}
                `;
                activityContainer.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.className = 'list-group-item text-center';
            li.textContent = 'No recent activity';
            activityContainer.appendChild(li);
        }
    }
}

/**
 * Show error indicators when data fetching fails
 */
function showErrorIndicators() {
    // Show error state for system status
    const dbStatusBadge = document.getElementById('db-status-badge');
    if (dbStatusBadge) {
        dbStatusBadge.textContent = 'Error';
        dbStatusBadge.className = 'badge bg-danger rounded-pill';
    }
    
    const backupStatusBadge = document.getElementById('backup-status-badge');
    if (backupStatusBadge) {
        backupStatusBadge.textContent = 'Error';
        backupStatusBadge.className = 'badge bg-danger rounded-pill';
    }
    
    const nextBackupBadge = document.getElementById('next-backup-badge');
    if (nextBackupBadge) {
        nextBackupBadge.textContent = 'Error';
        nextBackupBadge.className = 'badge bg-danger rounded-pill';
    }
    
    const backupCountBadge = document.getElementById('backup-count-badge');
    if (backupCountBadge) {
        backupCountBadge.textContent = 'Error';
        backupCountBadge.className = 'badge bg-danger rounded-pill';
    }
    
    const storageStatusBadge = document.getElementById('storage-status-badge');
    if (storageStatusBadge) {
        storageStatusBadge.textContent = 'Error';
        storageStatusBadge.className = 'badge bg-danger rounded-pill';
    }
}