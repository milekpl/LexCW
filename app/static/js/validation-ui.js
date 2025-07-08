/**
 * Validation UI Components
 * 
 * Provides real-time validation feedback UI components including:
 * - Inline error display
 * - Section validation badges
 * - Field validation styling
 * - Accessibility support
 * - Detailed message handling
 * - Section and form summaries
 * - Error modals and toast notifications
 */

class ValidationUI {
    constructor() {
        this.validationStates = new Map();
        this.errorContainers = new Map();
        this.sectionBadges = new Map();
        this.accessibilityEnabled = true;
        
        this.init();
    }
    
    init() {
        this.createValidationStyles();
        this.setupValidationContainers();
        this.setupSectionBadges();
        this.setupAccessibilityFeatures();
        
        console.log('✅ ValidationUI initialized');
    }
    
    /**
     * Create CSS classes for validation feedback
     */
    createValidationStyles() {
        if (document.getElementById('validation-ui-styles')) {
            return; // Already exists
        }
        
        const style = document.createElement('style');
        style.id = 'validation-ui-styles';
        style.textContent = `
            /* Field validation states */
            .valid-field {
                border-color: #28a745 !important;
                background-color: #f8fff9;
            }
            
            .invalid-field {
                border-color: #dc3545 !important;
                background-color: #fff8f8;
            }
            
            .warning-field {
                border-color: #ffc107 !important;
                background-color: #fffbf0;
            }
            
            /* Validation feedback containers */
            .validation-feedback {
                display: block;
                margin-top: 0.25rem;
                font-size: 0.875rem;
            }
            
            .invalid-feedback {
                color: #dc3545;
            }
            
            .valid-feedback {
                color: #28a745;
            }
            
            .warning-feedback {
                color: #856404;
            }
            
            /* Validation error lists */
            .validation-error-list {
                list-style: none;
                padding: 0;
                margin: 0;
            }
            
            .validation-error-item {
                padding: 0.125rem 0;
                display: flex;
                align-items: center;
            }
            
            .validation-error-item::before {
                content: "⚠️";
                margin-right: 0.25rem;
            }
            
            .validation-error-item.error::before {
                content: "❌";
            }
            
            .validation-error-item.warning::before {
                content: "⚠️";
            }
            
            .validation-error-item.success::before {
                content: "✅";
            }
            
            /* Section validation badges */
            .validation-badge {
                display: inline-flex;
                align-items: center;
                padding: 0.25rem 0.5rem;
                font-size: 0.75rem;
                font-weight: 600;
                border-radius: 0.375rem;
                margin-left: 0.5rem;
            }
            
            .validation-badge.badge-success {
                color: #155724;
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
            }
            
            .validation-badge.badge-danger {
                color: #721c24;
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
            }
            
            .validation-badge.badge-warning {
                color: #856404;
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
            }
            
            .validation-badge.badge-info {
                color: #0c5460;
                background-color: #d1ecf1;
                border: 1px solid #bee5eb;
            }
            
            /* Loading states */
            .validation-loading {
                opacity: 0.6;
                pointer-events: none;
            }
            
            .validation-spinner {
                display: inline-block;
                width: 1rem;
                height: 1rem;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #007bff;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-right: 0.5rem;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* Accessibility enhancements */
            .validation-feedback[aria-live] {
                position: relative;
            }
            
            .sr-only {
                position: absolute;
                width: 1px;
                height: 1px;
                padding: 0;
                margin: -1px;
                overflow: hidden;
                clip: rect(0, 0, 0, 0);
                white-space: nowrap;
                border: 0;
            }
            
            /* Additional styles from the second class */
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
        
        document.head.appendChild(style);
    }
    
    /**
     * Setup validation containers for form fields
     */
    setupValidationContainers() {
        const formFields = document.querySelectorAll('input, textarea, select');
        
        formFields.forEach(field => {
            const fieldContainer = field.closest('.mb-3, .form-group, .col-md-6, .col-md-4');
            if (!fieldContainer) return;
            
            // Check if validation container already exists
            let validationContainer = fieldContainer.querySelector('.validation-feedback');
            
            if (!validationContainer) {
                validationContainer = document.createElement('div');
                validationContainer.className = 'validation-feedback';
                validationContainer.setAttribute('aria-live', 'polite');
                validationContainer.setAttribute('role', 'status');
                
                // Insert after the field
                const insertAfter = field.nextElementSibling?.classList.contains('form-text') 
                    ? field.nextElementSibling 
                    : field;
                insertAfter.parentNode.insertBefore(validationContainer, insertAfter.nextSibling);
            }
            
            // Store reference
            const fieldId = field.id || field.name || `field_${Date.now()}_${Math.random()}`;
            this.errorContainers.set(fieldId, validationContainer);
            
            // Add validation attributes
            field.setAttribute('data-validation-target', fieldId);
            validationContainer.setAttribute('id', `${fieldId}-feedback`);
            field.setAttribute('aria-describedby', `${fieldId}-feedback`);
        });
    }
    
    /**
     * Setup section validation badges
     */
    setupSectionBadges() {
        const sections = document.querySelectorAll('.card .card-header h5, .card .card-header h4');
        
        sections.forEach(header => {
            const sectionId = this.getSectionId(header);
            if (!sectionId) return;
            
            // Check if badge already exists
            let badge = header.querySelector('.validation-badge');
            
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'validation-badge badge-info section-status';
                badge.textContent = 'Not validated';
                badge.setAttribute('role', 'status');
                badge.setAttribute('aria-live', 'polite');
                
                header.appendChild(badge);
            }
            
            this.sectionBadges.set(sectionId, badge);
        });
    }
    
    /**
     * Setup accessibility features
     */
    setupAccessibilityFeatures() {
        // Add aria-invalid to form fields
        const formFields = document.querySelectorAll('input, textarea, select');
        formFields.forEach(field => {
            if (!field.hasAttribute('aria-invalid')) {
                field.setAttribute('aria-invalid', 'false');
            }
        });
        
        // Create screen reader announcements container
        if (!document.getElementById('validation-announcements')) {
            const announcements = document.createElement('div');
            announcements.id = 'validation-announcements';
            announcements.className = 'sr-only';
            announcements.setAttribute('aria-live', 'assertive');
            announcements.setAttribute('role', 'alert');
            document.body.appendChild(announcements);
        }
    }
    
    /**
     * Display field validation result
     */
    displayFieldValidation(fieldId, result) {
        const field = document.querySelector(`[data-validation-target="${fieldId}"]`) || 
                     document.getElementById(fieldId) ||
                     document.querySelector(`[name="${fieldId}"]`);
        
        if (!field) return;
        
        const container = this.errorContainers.get(fieldId);
        if (!container) return;
        
        // Update field state
        this.validationStates.set(fieldId, result);
        
        // Remove existing validation classes
        field.classList.remove('valid-field', 'invalid-field', 'warning-field');
        container.classList.remove('invalid-feedback', 'valid-feedback', 'warning-feedback');
        
        // Clear container
        container.innerHTML = '';
        
        if (result.errors && result.errors.length > 0) {
            // Show errors
            field.classList.add('invalid-field');
            container.classList.add('invalid-feedback');
            field.setAttribute('aria-invalid', 'true');
            
            const errorList = document.createElement('ul');
            errorList.className = 'validation-error-list';
            
            result.errors.forEach(error => {
                const errorItem = document.createElement('li');
                errorItem.className = 'validation-error-item error';
                errorItem.textContent = error;
                errorList.appendChild(errorItem);
            });
            
            container.appendChild(errorList);
            this.announceValidation(`Error in ${fieldId}: ${result.errors.join(', ')}`);
            
        } else if (result.warnings && result.warnings.length > 0) {
            // Show warnings
            field.classList.add('warning-field');
            container.classList.add('warning-feedback');
            field.setAttribute('aria-invalid', 'false');
            
            const warningList = document.createElement('ul');
            warningList.className = 'validation-error-list';
            
            result.warnings.forEach(warning => {
                const warningItem = document.createElement('li');
                warningItem.className = 'validation-error-item warning';
                warningItem.textContent = warning;
                warningList.appendChild(warningItem);
            });
            
            container.appendChild(warningList);
            
        } else if (result.valid) {
            // Show success
            field.classList.add('valid-field');
            container.classList.add('valid-feedback');
            field.setAttribute('aria-invalid', 'false');
            
            const successItem = document.createElement('div');
            successItem.className = 'validation-error-item success';
            successItem.textContent = 'Valid';
            container.appendChild(successItem);
        }
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
        this.validationStates.set(field, {
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
        field.classList.remove('valid-field', 'invalid-field', 'warning-field');
        
        // Remove error messages
        const errorContainer = this.errorContainers.get(field);
        if (errorContainer) {
            errorContainer.innerHTML = '';
            errorContainer.style.display = 'none';
        }
        
        // Clear stored state
        this.validationStates.delete(field);
    }
    
    /**
     * Mark field as invalid
     * @param {HTMLElement} field - Form field element
     */
    markFieldInvalid(field) {
        field.classList.remove('valid-field', 'warning-field');
        field.classList.add('invalid-field');
        field.setAttribute('aria-invalid', 'true');
    }
    
    /**
     * Mark field as having warnings
     * @param {HTMLElement} field - Form field element
     */
    markFieldWarning(field) {
        field.classList.remove('valid-field', 'invalid-field');
        field.classList.add('warning-field');
        field.setAttribute('aria-invalid', 'false');
    }
    
    /**
     * Mark field as valid
     * @param {HTMLElement} field - Form field element
     */
    markFieldValid(field) {
        field.classList.remove('invalid-field', 'warning-field');
        field.classList.add('valid-field');
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
     * Update section validation badge
     */
    updateSectionStatus(sectionId, sectionResult) {
        const badge = this.sectionBadges.get(sectionId);
        if (!badge) return;
        
        // Remove existing badge classes
        badge.classList.remove('badge-success', 'badge-danger', 'badge-warning', 'badge-info');
        
        if (sectionResult.section_valid) {
            badge.classList.add('badge-success');
            badge.textContent = `✓ Valid (${sectionResult.summary.valid_fields}/${sectionResult.summary.total_fields})`;
        } else if (sectionResult.summary.errors.length > 0) {
            badge.classList.add('badge-danger');
            badge.textContent = `✗ Errors (${sectionResult.summary.errors.length})`;
        } else if (sectionResult.summary.fields_with_warnings > 0) {
            badge.classList.add('badge-warning');
            badge.textContent = `⚠ Warnings (${sectionResult.summary.fields_with_warnings})`;
        } else {
            badge.classList.add('badge-info');
            badge.textContent = 'Validating...';
        }
    }
    
    /**
     * Show validation loading state
     */
    showValidationLoading(fieldId) {
        const field = document.querySelector(`[data-validation-target="${fieldId}"]`) || 
                     document.getElementById(fieldId);
        
        if (field) {
            field.classList.add('validation-loading');
        }
        
        const container = this.errorContainers.get(fieldId);
        if (container) {
            container.innerHTML = '<span class="validation-spinner"></span>Validating...';
        }
    }
    
    /**
     * Hide validation loading state
     */
    hideValidationLoading(fieldId) {
        const field = document.querySelector(`[data-validation-target="${fieldId}"]`) || 
                     document.getElementById(fieldId);
        
        if (field) {
            field.classList.remove('validation-loading');
        }
    }
    
    /**
     * Get section ID from header element
     */
    getSectionId(header) {
        const card = header.closest('.card');
        if (!card) return null;
        
        // Try to determine section from classes or content
        if (card.classList.contains('basic-info-section') || 
            header.textContent.toLowerCase().includes('basic')) {
            return 'basic_info';
        }
        
        if (card.classList.contains('senses-section') || 
            header.textContent.toLowerCase().includes('sense')) {
            return 'senses';
        }
        
        if (card.classList.contains('pronunciation-section') || 
            header.textContent.toLowerCase().includes('pronunciation')) {
            return 'pronunciation';
        }
        
        // Default fallback
        return card.id || 'unknown_section';
    }
    
    /**
     * Announce validation changes for screen readers
     */
    announceValidation(message) {
        if (!this.accessibilityEnabled) return;
        
        const announcements = document.getElementById('validation-announcements');
        if (announcements) {
            announcements.textContent = message;
            
            // Clear after a delay to allow re-announcement
            setTimeout(() => {
                announcements.textContent = '';
            }, 1000);
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
        this.validationStates.set(sectionId, {
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
        const existingBadge = header.querySelector('.validation-badge');
        if (existingBadge) {
            existingBadge.remove();
        }
        
        // Add new badge if there are validation issues
        if (errorCount > 0 || warningCount > 0) {
            const badge = document.createElement('span');
            badge.className = 'validation-badge';
            
            if (errorCount > 0) {
                badge.classList.add('badge-danger');
                badge.textContent = `${errorCount} error${errorCount > 1 ? 's' : ''}`;
            } else if (warningCount > 0) {
                badge.classList.add('badge-warning');
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
        this.validationStates.forEach((state, fieldId) => {
            const field = document.querySelector(`[data-validation-target="${fieldId}"]`) || 
                         document.getElementById(fieldId) ||
                         document.querySelector(`[name="${fieldId}"]`);
            if (field) {
                this.clearFieldErrors(field);
            }
        });
        
        // Clear section badges
        document.querySelectorAll('.validation-badge').forEach(badge => {
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
            fieldsWithState: this.validationStates.size,
            sectionsWithState: this.sectionBadges.size,
            errorContainers: this.errorContainers.size
        };
    }
    
    /**
     * Get the current validation state for a field by its ID
     * @param {string} fieldId
     * @returns {Object|null} Validation state object or null if not found
     */
    getFieldValidationState(fieldId) {
        return this.validationStates.get(fieldId) || null;
    }
}

// Global validation UI instance
window.validationUI = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.validationUI = new ValidationUI();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ValidationUI;
}

// Make available globally
if (typeof window !== 'undefined') {
    window.ValidationUI = ValidationUI;
}