/**
 * ValidationUI - User interface for displaying validation results
 * 
 * Handles the display of validation errors, warnings, and success states
 * with inline field feedback and section-level summaries.
 * 
 * @author Dictionary System
 * @version 1.0.0
 */

class ValidationUI {
    /**
     * Initialize ValidationUI
     */
    constructor() {
        this.errorContainers = new Map(); // field -> error container element
        this.fieldStates = new Map();     // field -> current validation state
        this.sectionStates = new Map();   // section -> validation summary
        
        this.setupGlobalStyles();
        console.log('[ValidationUI] Initialized');
    }
    
    /**
     * Set up global validation styles
     */
    setupGlobalStyles() {
        // Add validation CSS if not already present
        if (!document.getElementById('validation-styles')) {
            const style = document.createElement('style');
            style.id = 'validation-styles';
            style.textContent = this.getValidationCSS();
            document.head.appendChild(style);
        }
    }
    
    /**
     * Get validation CSS styles
     * @returns {string} CSS styles
     */
    getValidationCSS() {
        return `
            /* Field validation states */
            .field-valid {
                border-color: #28a745 !important;
                box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25) !important;
            }
            
            .field-invalid {
                border-color: #dc3545 !important;
                box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25) !important;
            }
            
            .field-warning {
                border-color: #ffc107 !important;
                box-shadow: 0 0 0 0.2rem rgba(255, 193, 7, 0.25) !important;
            }
            
            /* Validation messages */
            .validation-error {
                color: #dc3545;
                font-size: 0.875em;
                margin-top: 0.25rem;
                display: flex;
                align-items: flex-start;
            }
            
            .validation-warning {
                color: #856404;
                font-size: 0.875em;
                margin-top: 0.25rem;
                display: flex;
                align-items: flex-start;
            }
            
            .validation-success {
                color: #155724;
                font-size: 0.875em;
                margin-top: 0.25rem;
                display: flex;
                align-items: flex-start;
            }
            
            .validation-message-icon {
                margin-right: 0.25rem;
                margin-top: 0.125rem;
                flex-shrink: 0;
            }
            
            .validation-message-text {
                flex: 1;
            }
            
            /* Section validation badges */
            .section-validation-badge {
                font-size: 0.75rem;
                padding: 0.25rem 0.5rem;
                border-radius: 0.375rem;
                margin-left: 0.5rem;
                font-weight: 500;
            }
            
            .section-badge-error {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            
            .section-badge-warning {
                background-color: #fff3cd;
                color: #856404;
                border: 1px solid #ffeaa7;
            }
            
            .section-badge-success {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            
            /* Validation modal */
            .validation-modal .modal-header {
                border-bottom: 1px solid #dee2e6;
            }
            
            .validation-modal .validation-error-item {
                padding: 0.75rem;
                margin-bottom: 0.5rem;
                border: 1px solid #f5c6cb;
                border-radius: 0.375rem;
                background-color: #f8d7da;
            }
            
            .validation-modal .validation-error-rule {
                font-weight: 600;
                color: #721c24;
                font-size: 0.875rem;
            }
            
            .validation-modal .validation-error-message {
                color: #721c24;
                margin-top: 0.25rem;
            }
            
            .validation-modal .validation-error-path {
                color: #6c757d;
                font-size: 0.75rem;
                font-family: monospace;
                margin-top: 0.25rem;
            }
            
            /* Form submission states */
            .form-submitting {
                opacity: 0.7;
                pointer-events: none;
            }
            
            .form-validation-failed {
                border: 2px solid #dc3545;
                border-radius: 0.375rem;
                padding: 1rem;
                margin: 1rem 0;
                background-color: #f8d7da;
            }
            
            /* Animation for validation state changes */
            .validation-message {
                animation: fadeIn 0.3s ease-in-out;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        `;
    }
    
    /**
     * Display validation results for a specific field
     * @param {HTMLElement} field - Form field element
     * @param {Array} validationResults - Array of validation results
     */
    displayFieldErrors(field, validationResults) {
        if (!field) return;
        
        // Clear previous validation state
        this.clearFieldErrors(field);
        
        // Categorize results
        const criticalErrors = validationResults.filter(r => r.priority === 'critical');
        const warnings = validationResults.filter(r => r.priority === 'warning');
        const informational = validationResults.filter(r => r.priority === 'informational');
        
        // Update field state
        if (criticalErrors.length > 0) {
            this.markFieldInvalid(field);
            this.showFieldMessages(field, criticalErrors, 'error');
        } else if (warnings.length > 0) {
            this.markFieldWarning(field);
            this.showFieldMessages(field, warnings, 'warning');
        } else {
            this.markFieldValid(field);
            if (informational.length > 0) {
                this.showFieldMessages(field, informational, 'info');
            }
        }
        
        // Store field state
        this.fieldStates.set(field, {
            valid: criticalErrors.length === 0,
            errors: criticalErrors,
            warnings: warnings,
            informational: informational
        });
    }
    
    /**
     * Clear validation errors for a field
     * @param {HTMLElement} field - Form field element
     */
    clearFieldErrors(field) {
        // Remove validation classes
        field.classList.remove('field-valid', 'field-invalid', 'field-warning');
        
        // Remove error messages
        const errorContainer = this.getErrorContainer(field);
        if (errorContainer) {
            errorContainer.innerHTML = '';
            errorContainer.style.display = 'none';
        }
        
        // Clear stored state
        this.fieldStates.delete(field);
    }
    
    /**
     * Mark field as invalid
     * @param {HTMLElement} field - Form field element
     */
    markFieldInvalid(field) {
        field.classList.remove('field-valid', 'field-warning');
        field.classList.add('field-invalid');
        field.setAttribute('aria-invalid', 'true');
    }
    
    /**
     * Mark field as having warnings
     * @param {HTMLElement} field - Form field element
     */
    markFieldWarning(field) {
        field.classList.remove('field-valid', 'field-invalid');
        field.classList.add('field-warning');
        field.setAttribute('aria-invalid', 'false');
    }
    
    /**
     * Mark field as valid
     * @param {HTMLElement} field - Form field element
     */
    markFieldValid(field) {
        field.classList.remove('field-invalid', 'field-warning');
        field.classList.add('field-valid');
        field.setAttribute('aria-invalid', 'false');
    }
    
    /**
     * Show validation messages for a field
     * @param {HTMLElement} field - Form field element
     * @param {Array} messages - Validation messages
     * @param {string} type - Message type (error, warning, info)
     */
    showFieldMessages(field, messages, type) {
        const errorContainer = this.getErrorContainer(field, true);
        
        messages.forEach(message => {
            const messageElement = this.createMessageElement(message, type);
            errorContainer.appendChild(messageElement);
        });
        
        errorContainer.style.display = 'block';
    }
    
    /**
     * Get or create error container for field
     * @param {HTMLElement} field - Form field element
     * @param {boolean} create - Whether to create if not exists
     * @returns {HTMLElement|null} Error container element
     */
    getErrorContainer(field, create = false) {
        let container = this.errorContainers.get(field);
        
        if (!container && create) {
            container = document.createElement('div');
            container.className = 'validation-messages';
            
            // Insert after field or its wrapper
            const insertTarget = field.closest('.form-group, .mb-3, .form-floating') || field;
            insertTarget.parentNode.insertBefore(container, insertTarget.nextSibling);
            
            this.errorContainers.set(field, container);
        }
        
        return container;
    }
    
    /**
     * Create validation message element
     * @param {Object} message - Validation message object
     * @param {string} type - Message type
     * @returns {HTMLElement} Message element
     */
    createMessageElement(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `validation-message validation-${type}`;
        
        const icon = this.getIconForType(type);
        const ruleId = message.ruleId ? ` (${message.ruleId})` : '';
        
        messageDiv.innerHTML = `
            <span class="validation-message-icon">${icon}</span>
            <span class="validation-message-text">
                ${message.message || message.error}${ruleId}
            </span>
        `;
        
        return messageDiv;
    }
    
    /**
     * Get icon for message type
     * @param {string} type - Message type
     * @returns {string} Icon HTML
     */
    getIconForType(type) {
        switch (type) {
            case 'error':
                return '<i class="fas fa-exclamation-circle"></i>';
            case 'warning':
                return '<i class="fas fa-exclamation-triangle"></i>';
            case 'info':
                return '<i class="fas fa-info-circle"></i>';
            case 'success':
                return '<i class="fas fa-check-circle"></i>';
            default:
                return '<i class="fas fa-info-circle"></i>';
        }
    }
    
    /**
     * Update section validation summary
     * @param {string} sectionId - Section ID
     * @param {Array} allResults - All validation results for section
     */
    showSectionSummary(sectionId, allResults) {
        const section = document.getElementById(sectionId);
        if (!section) return;
        
        const errorCount = allResults.filter(r => r.priority === 'critical').length;
        const warningCount = allResults.filter(r => r.priority === 'warning').length;
        
        this.updateSectionBadge(section, errorCount, warningCount);
        
        // Store section state
        this.sectionStates.set(sectionId, {
            errors: errorCount,
            warnings: warningCount,
            valid: errorCount === 0
        });
    }
    
    /**
     * Update section validation badge
     * @param {HTMLElement} section - Section element
     * @param {number} errorCount - Number of errors
     * @param {number} warningCount - Number of warnings
     */
    updateSectionBadge(section, errorCount, warningCount) {
        // Find section header
        const header = section.querySelector('.card-header, .section-header, h3, h4, h5') || section;
        
        // Remove existing badge
        const existingBadge = header.querySelector('.section-validation-badge');
        if (existingBadge) {
            existingBadge.remove();
        }
        
        // Add new badge if there are validation issues
        if (errorCount > 0 || warningCount > 0) {
            const badge = document.createElement('span');
            badge.className = 'section-validation-badge';
            
            if (errorCount > 0) {
                badge.classList.add('section-badge-error');
                badge.textContent = `${errorCount} error${errorCount > 1 ? 's' : ''}`;
            } else if (warningCount > 0) {
                badge.classList.add('section-badge-warning');
                badge.textContent = `${warningCount} warning${warningCount > 1 ? 's' : ''}`;
            }
            
            header.appendChild(badge);
        }
    }
    
    /**
     * Display complete form validation results
     * @param {Object} validationResult - Complete validation result
     */
    displayFormValidation(validationResult) {
        const { errors = [], warnings = [] } = validationResult;
        
        // Group results by field path
        const resultsByField = new Map();
        
        [...errors, ...warnings].forEach(result => {
            const fieldPath = result.fieldPath || result.field_path;
            if (fieldPath) {
                if (!resultsByField.has(fieldPath)) {
                    resultsByField.set(fieldPath, []);
                }
                resultsByField.get(fieldPath).push(result);
            }
        });
        
        // Update field validation displays
        resultsByField.forEach((results, fieldPath) => {
            const field = this.findFieldByPath(fieldPath);
            if (field) {
                this.displayFieldErrors(field, results);
            }
        });
        
        // Update form-level summary
        this.updateFormSummary(validationResult);
    }
    
    /**
     * Find form field by JSON path
     * @param {string} fieldPath - JSON path
     * @returns {HTMLElement|null} Form field element
     */
    findFieldByPath(fieldPath) {
        // Try to find field with matching data-json-path attribute
        const field = document.querySelector(`[data-json-path="${fieldPath}"]`);
        if (field) return field;
        
        // Fallback: try to find field by name derived from path
        const fieldName = this.pathToFieldName(fieldPath);
        return document.querySelector(`[name="${fieldName}"]`) || 
               document.getElementById(fieldName);
    }
    
    /**
     * Convert JSON path to likely field name
     * @param {string} path - JSON path
     * @returns {string} Field name
     */
    pathToFieldName(path) {
        // Convert $.lexical_unit.seh to lexical_unit_seh
        return path.replace(/^\$\./, '').replace(/\./g, '_').replace(/\[\d+\]/g, '');
    }
    
    /**
     * Update form-level validation summary
     * @param {Object} validationResult - Validation result
     */
    updateFormSummary(validationResult) {
        const { valid, errors = [], warnings = [] } = validationResult;
        
        // Find or create form summary element
        let summary = document.getElementById('form-validation-summary');
        if (!summary) {
            summary = document.createElement('div');
            summary.id = 'form-validation-summary';
            summary.className = 'alert alert-dismissible fade show';
            
            // Insert at top of form
            const form = document.getElementById('entry-form') || document.querySelector('form');
            if (form) {
                form.insertBefore(summary, form.firstChild);
            }
        }
        
        if (!valid && errors.length > 0) {
            summary.className = 'alert alert-danger alert-dismissible fade show';
            summary.innerHTML = `
                <h6><i class="fas fa-exclamation-triangle"></i> Validation Errors</h6>
                <p>Please fix the following ${errors.length} error${errors.length > 1 ? 's' : ''} before submitting:</p>
                <ul class="mb-0">
                    ${errors.slice(0, 5).map(error => `<li>${error.message}</li>`).join('')}
                    ${errors.length > 5 ? `<li>... and ${errors.length - 5} more</li>` : ''}
                </ul>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            summary.style.display = 'block';
        } else if (warnings.length > 0) {
            summary.className = 'alert alert-warning alert-dismissible fade show';
            summary.innerHTML = `
                <h6><i class="fas fa-exclamation-triangle"></i> Validation Warnings</h6>
                <p>Consider addressing these ${warnings.length} warning${warnings.length > 1 ? 's' : ''}:</p>
                <ul class="mb-0">
                    ${warnings.slice(0, 3).map(warning => `<li>${warning.message}</li>`).join('')}
                    ${warnings.length > 3 ? `<li>... and ${warnings.length - 3} more</li>` : ''}
                </ul>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            summary.style.display = 'block';
        } else {
            summary.style.display = 'none';
        }
    }
    
    /**
     * Show validation modal with detailed errors
     * @param {Array} errors - Critical validation errors
     */
    showValidationModal(errors) {
        // Create or update validation modal
        let modal = document.getElementById('validationModal');
        if (!modal) {
            modal = this.createValidationModal();
            document.body.appendChild(modal);
        }
        
        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = `
            <p>Please fix the following critical errors before submitting:</p>
            ${errors.map(error => `
                <div class="validation-error-item">
                    <div class="validation-error-rule">${error.ruleId || 'Validation Error'}</div>
                    <div class="validation-error-message">${error.message}</div>
                    ${error.fieldPath ? `<div class="validation-error-path">Field: ${error.fieldPath}</div>` : ''}
                </div>
            `).join('')}
        `;
        
        // Show modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
    
    /**
     * Create validation modal element
     * @returns {HTMLElement} Modal element
     */
    createValidationModal() {
        const modal = document.createElement('div');
        modal.id = 'validationModal';
        modal.className = 'modal fade validation-modal';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle text-danger"></i>
                            Validation Errors
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <!-- Error content will be inserted here -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `;
        return modal;
    }
    
    /**
     * Show server error message
     * @param {Object} error - Server error object
     */
    showServerError(error) {
        const errorMessage = error.message || 'An error occurred while saving the entry.';
        
        // Show toast or alert
        this.showToast('Error', errorMessage, 'error');
    }
    
    /**
     * Show network error message
     */
    showNetworkError() {
        this.showToast('Network Error', 'Unable to connect to the server. Please check your connection and try again.', 'error');
    }
    
    /**
     * Show toast notification
     * @param {string} title - Toast title
     * @param {string} message - Toast message
     * @param {string} type - Toast type
     */
    showToast(title, message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        // Add to toast container or body
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1050';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.appendChild(toast);
        
        // Show toast
        const bootstrapToast = new bootstrap.Toast(toast);
        bootstrapToast.show();
        
        // Remove after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    /**
     * Clear all validation displays
     */
    clearAllValidation() {
        // Clear field states
        this.fieldStates.forEach((state, field) => {
            this.clearFieldErrors(field);
        });
        
        // Clear section badges
        document.querySelectorAll('.section-validation-badge').forEach(badge => {
            badge.remove();
        });
        
        // Hide form summary
        const summary = document.getElementById('form-validation-summary');
        if (summary) {
            summary.style.display = 'none';
        }
        
        console.log('[ValidationUI] Cleared all validation displays');
    }
    
    /**
     * Get validation statistics
     * @returns {Object} Validation UI statistics
     */
    getStats() {
        return {
            fieldsWithState: this.fieldStates.size,
            sectionsWithState: this.sectionStates.size,
            errorContainers: this.errorContainers.size
        };
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.ValidationUI = ValidationUI;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ValidationUI;
}
