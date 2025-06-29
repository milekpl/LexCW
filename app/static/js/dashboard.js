/**
 * Dictionary Writing System - Dashboard JavaScript
 * 
 * This file contains the functionality for the dashboard/home page.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Fetch all dashboard data at once using the new endpoint
    fetchDashboardData();
    
    // Set up auto-refresh every 5 minutes
    setInterval(fetchDashboardData, 5 * 60 * 1000);
    
    // Set up refresh button
    const refreshBtn = document.getElementById('refresh-stats-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            refreshDashboardStats();
        });
    }
});

/**
 * Fetch and update all dashboard data at once
 */
function fetchDashboardData() {
    fetch('/api/dashboard/stats')
        .then(response => {
            if (!response.ok) {
                throw new Error('Error fetching dashboard data');
            }
            return response.json();
        })
        .then(result => {
            if (result.success) {
                const data = result.data;
                
                // Update stats
                if (data.stats) {
                    const entriesEl = document.querySelector('.card-title.text-primary');
                    const sensesEl = document.querySelector('.card-title.text-success');
                    const examplesEl = document.querySelector('.card-title.text-info');
                    
                    if (entriesEl) entriesEl.textContent = data.stats.entries || 0;
                    if (sensesEl) sensesEl.textContent = data.stats.senses || 0;
                    if (examplesEl) examplesEl.textContent = data.stats.examples || 0;
                }
                
                // Update system status
                if (data.system_status) {
                    updateSystemStatus(data.system_status);
                }
                
                // Update recent activity
                if (data.recent_activity) {
                    updateRecentActivity(data.recent_activity);
                }
                
                console.log('Dashboard data updated successfully', result.cached ? '(cached)' : '(fresh)');
            } else {
                throw new Error(result.error || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showErrorIndicators();
        });
}

/**
 * Update system status in the UI
 */
function updateSystemStatus(systemStatus) {
    // Update DB connection status
    const dbStatusBadge = document.getElementById('db-status-badge');
    if (dbStatusBadge) {
        dbStatusBadge.className = `badge bg-${systemStatus.db_connected ? 'success' : 'danger'} rounded-pill`;
        dbStatusBadge.textContent = systemStatus.db_connected ? 'Connected' : 'Disconnected';
    }
    
    // Update last backup
    const backupBadge = document.getElementById('backup-status-badge');
    if (backupBadge) {
        backupBadge.textContent = systemStatus.last_backup || 'Never';
    }
    
    // Update storage usage
    const storageBadge = document.getElementById('storage-status-badge');
    if (storageBadge) {
        const storagePercent = systemStatus.storage_percent || 0;
        let badgeColor = 'success';
        if (storagePercent >= 95) {
            badgeColor = 'danger';
        } else if (storagePercent >= 80) {
            badgeColor = 'warning';
        }
        storageBadge.className = `badge bg-${badgeColor} rounded-pill`;
        storageBadge.textContent = `${storagePercent}%`;
    }
}

/**
 * Update recent activity in the UI
 */
function updateRecentActivity(activities) {
    const activityList = document.querySelector('.list-group-flush');
    if (!activityList) return;
    
    // Clear existing items
    while (activityList.firstChild) {
        activityList.removeChild(activityList.firstChild);
    }
    
    if (activities && activities.length > 0) {
        // Add activity items
        activities.forEach(activity => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            
            const timestamp = document.createElement('small');
            timestamp.className = 'text-muted';
            timestamp.textContent = formatDate(activity.timestamp);
            
            const br = document.createElement('br');
            
            const actionSpan = document.createElement('strong');
            actionSpan.textContent = activity.action;
            
            const descSpan = document.createTextNode(`: ${activity.description}`);
            
            li.appendChild(timestamp);
            li.appendChild(br);
            li.appendChild(actionSpan);
            li.appendChild(descSpan);
            
            activityList.appendChild(li);
        });
    } else {
        // Show no activity message
        const li = document.createElement('li');
        li.className = 'list-group-item text-center';
        li.textContent = 'No recent activity';
        activityList.appendChild(li);
    }
}

/**
 * Show error indicators for all dashboard elements
 */
function showErrorIndicators() {
    // Show error indicators for stats
    document.querySelectorAll('.card-title').forEach(el => {
        el.textContent = '?';
        el.title = 'Error loading stats';
    });
    
    // Show error indicators on system status badges
    const statusBadges = [
        document.getElementById('db-status-badge'),
        document.getElementById('backup-status-badge'),
        document.getElementById('storage-status-badge')
    ];
    
    statusBadges.forEach(badge => {
        if (badge) {
            badge.className = 'badge bg-secondary rounded-pill';
            badge.textContent = 'Error';
            badge.title = 'Error loading system status';
        }
    });
    
    // Show error message for activity
    const activityList = document.querySelector('.list-group-flush');
    if (activityList) {
        while (activityList.firstChild) {
            activityList.removeChild(activityList.firstChild);
        }
        
        const li = document.createElement('li');
        li.className = 'list-group-item text-center text-danger';
        li.textContent = 'Error loading activity';
        activityList.appendChild(li);
    }
}

/**
 * Manually refresh dashboard statistics
 */
function refreshDashboardStats() {
    const refreshBtn = document.getElementById('refresh-stats-btn');
    if (refreshBtn) {
        // Show loading state
        const icon = refreshBtn.querySelector('i');
        const originalText = refreshBtn.innerHTML;
        refreshBtn.disabled = true;
        if (icon) {
            icon.classList.add('fa-spin');
        }
        
        // Clear cache and fetch fresh data
        fetch('/api/dashboard/clear-cache', { method: 'POST' })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    // Cache cleared, now fetch fresh data
                    return fetchDashboardData();
                } else {
                    throw new Error(result.error || 'Failed to clear cache');
                }
            })
            .then(() => {
                // Show success briefly
                refreshBtn.innerHTML = '<i class="fas fa-check"></i> Updated';
                refreshBtn.classList.remove('btn-outline-secondary');
                refreshBtn.classList.add('btn-success');
                
                setTimeout(() => {
                    refreshBtn.innerHTML = originalText;
                    refreshBtn.classList.remove('btn-success');
                    refreshBtn.classList.add('btn-outline-secondary');
                    refreshBtn.disabled = false;
                    if (icon) {
                        icon.classList.remove('fa-spin');
                    }
                }, 1500);
            })
            .catch(error => {
                console.error('Error refreshing dashboard:', error);
                
                // Show error briefly
                refreshBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
                refreshBtn.classList.remove('btn-outline-secondary');
                refreshBtn.classList.add('btn-danger');
                
                setTimeout(() => {
                    refreshBtn.innerHTML = originalText;
                    refreshBtn.classList.remove('btn-danger');
                    refreshBtn.classList.add('btn-outline-secondary');
                    refreshBtn.disabled = false;
                    if (icon) {
                        icon.classList.remove('fa-spin');
                    }
                }, 1500);
            });
    }
}
