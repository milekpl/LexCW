/**
 * Dictionary Writing System - Dashboard JavaScript
 * 
 * This file contains the functionality for the dashboard/home page.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Fetch latest stats
    fetchStats();
    
    // Fetch system status
    fetchSystemStatus();
    
    // Fetch recent activity
    fetchRecentActivity();
});

/**
 * Fetch and update dictionary statistics
 */
function fetchStats() {
    fetch('/api/stats')
        .then(response => {
            if (!response.ok) {
                throw new Error('Error fetching stats');
            }
            return response.json();
        })
        .then(data => {
            // Update the stats in the UI
            document.querySelector('.card-title.text-primary').textContent = data.entries || 0;
            document.querySelector('.card-title.text-success').textContent = data.senses || 0;
            document.querySelector('.card-title.text-info').textContent = data.examples || 0;
        })
        .catch(error => {
            console.error('Error:', error);
            // Show error indicators
            document.querySelectorAll('.card-title').forEach(el => {
                el.textContent = '?';
                el.title = 'Error loading stats';
            });
        });
}

/**
 * Fetch and update system status
 */
function fetchSystemStatus() {
    fetch('/api/system/status')
        .then(response => {
            if (!response.ok) {
                throw new Error('Error fetching system status');
            }
            return response.json();
        })
        .then(data => {
            // Update DB connection status
            const dbStatusBadge = document.querySelector('.badge:nth-of-type(1)');
            dbStatusBadge.className = `badge bg-${data.db_connected ? 'success' : 'danger'} rounded-pill`;
            dbStatusBadge.textContent = data.db_connected ? 'Connected' : 'Disconnected';
            
            // Update last backup
            const backupBadge = document.querySelector('.badge:nth-of-type(2)');
            backupBadge.textContent = data.last_backup || 'Never';
            
            // Update storage usage
            const storageBadge = document.querySelector('.badge:nth-of-type(3)');
            const storagePercent = data.storage_percent || 0;
            storageBadge.className = `badge bg-${storagePercent < 80 ? 'success' : storagePercent < 95 ? 'warning' : 'danger'} rounded-pill`;
            storageBadge.textContent = `${storagePercent}%`;
        })
        .catch(error => {
            console.error('Error:', error);
            // Show error indicators
            document.querySelectorAll('.badge').forEach(el => {
                el.className = 'badge bg-secondary rounded-pill';
                el.textContent = 'Error';
                el.title = 'Error loading system status';
            });
        });
}

/**
 * Fetch and update recent activity
 */
function fetchRecentActivity() {
    fetch('/api/activity?limit=5')
        .then(response => {
            if (!response.ok) {
                throw new Error('Error fetching activity');
            }
            return response.json();
        })
        .then(data => {
            const activityList = document.querySelector('.list-group-flush');
            
            // Clear existing items
            while (activityList.firstChild) {
                activityList.removeChild(activityList.firstChild);
            }
            
            if (data.activities && data.activities.length > 0) {
                // Add activity items
                data.activities.forEach(activity => {
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
        })
        .catch(error => {
            console.error('Error:', error);
            // Show error message
            const activityList = document.querySelector('.list-group-flush');
            
            // Clear existing items
            while (activityList.firstChild) {
                activityList.removeChild(activityList.firstChild);
            }
            
            const li = document.createElement('li');
            li.className = 'list-group-item text-center text-danger';
            li.textContent = 'Error loading activity';
            activityList.appendChild(li);
        });
}
