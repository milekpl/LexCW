/**
 * Toast Notification Utility
 *
 * Single source of truth for showing toast notifications.
 * Provides a consistent UI for success, error, warning, and info messages.
 *
 * Usage:
 *   showToast('Operation completed successfully', 'success');
 *   showToast('An error occurred', 'error');
 *   showToast('Warning message', 'warning');
 *   showToast('Information message', 'info');
 */

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - Message type: 'success', 'error', 'warning', 'info' (default: 'info')
 */
function showToast(message, type = 'info') {
    // Map type to Bootstrap alert class
    const typeMap = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    };

    const alertClass = typeMap[type] || `alert-${type}`;

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
    toast.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 1056;
        min-width: 300px;
        max-width: 500px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-top: 10px;
    `;

    toast.innerHTML = `
        ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    document.body.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(toast);
        if (bsAlert) {
            bsAlert.close();
        } else if (toast.parentNode) {
            toast.remove();
        }
    }, 4000);
}

/**
 * Escape HTML to prevent XSS
 * @param {string} html - HTML string to escape
 * @returns {string} Escaped HTML
 */
function escapeHtml(html) {
    if (!html) return '';
    const div = document.createElement('div');
    div.textContent = html;
    return div.innerHTML;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { showToast, escapeHtml };
}

// Also make available globally for legacy code
window.showToast = showToast;
window.escapeHtml = escapeHtml;
