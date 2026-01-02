/**
 * Lexicographic Curation Workbench - Common JavaScript
 * 
 * This file contains common functionality used across multiple pages.
 */

document.addEventListener('DOMContentLoaded', function() {
        // Initialize popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
        
        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    
    // Auto-dismiss alerts
    const autoDismissAlerts = document.querySelectorAll('.alert.auto-dismiss');
    autoDismissAlerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    });

/**
 * Format a date string
 * 
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    
    return date.toLocaleDateString() + ' ' + 
           date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Format a file size
 * 
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size with units
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Truncate text to a specified length
 * 
 * @param {string} text - Text to truncate
 * @param {number} length - Maximum length
 * @returns {string} Truncated text
 */
function truncateText(text, length = 100) {
    if (!text) return '';
    if (text.length <= length) return text;
    
    return text.substring(0, length) + '...';
}

/**
 * Escape HTML to prevent XSS
 *
 * @param {string} html - HTML string to escape
 * @returns {string} Escaped HTML
 * @deprecated Use ui/toast.js::escapeHtml instead
 */
function escapeHtml(html) {
    const div = document.createElement('div');
    div.textContent = html;
    return div.innerHTML;
}

/**
 * Create a confirmation dialog
 * 
 * @param {string} message - Confirmation message
 * @param {Function} onConfirm - Function to call on confirmation
 * @param {Function} onCancel - Function to call on cancel
 */
function confirmDialog(message, onConfirm, onCancel = null) {
    // Check if an existing confirmation modal is in the DOM
    let confirmModal = document.getElementById('confirm-dialog-modal');
    
    if (!confirmModal) {
        // Create modal element
        confirmModal = document.createElement('div');
        confirmModal.id = 'confirm-dialog-modal';
        confirmModal.className = 'modal fade';
        confirmModal.setAttribute('tabindex', '-1');
        confirmModal.setAttribute('aria-hidden', 'true');
        
        // Create modal content
        confirmModal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Confirmation</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p id="confirm-dialog-message"></p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="confirm-dialog-confirm-btn">Confirm</button>
                    </div>
                </div>
            </div>
        `;
        
        // Add to DOM
        document.body.appendChild(confirmModal);
    }
    
    // Set the message
    document.getElementById('confirm-dialog-message').textContent = message;
    
    // Get the modal instance
    const modal = new bootstrap.Modal(confirmModal);
    
    // Set up confirm button
    const confirmBtn = document.getElementById('confirm-dialog-confirm-btn');
    
    // Remove any existing event listeners
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    
    // Add new event listener
    newConfirmBtn.addEventListener('click', function() {
        modal.hide();
        if (typeof onConfirm === 'function') {
            onConfirm();
        }
    });
    
    // Handle cancel
    confirmModal.addEventListener('hidden.bs.modal', function() {
        if (typeof onCancel === 'function') {
            onCancel();
        }
    }, { once: true });
    
    // Show the modal
    modal.show();
}
