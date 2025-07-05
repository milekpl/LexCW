/**
 * AutoSaveManager - Handles automatic saving with conflict detection
 * 
 * Features:
 * - Debounced saving (waits for user to stop typing)
 * - Periodic auto-save (every 10 seconds if changes exist)
 * - Validation before save (skips save if critical errors)
 * - Version conflict detection and handling
 * - Visual feedback for save status
 * - Network error handling
 */
class AutoSaveManager {
    constructor(stateManager, validationEngine) {
        this.stateManager = stateManager;
        this.validationEngine = validationEngine;
        
        // Configuration
        this.saveInterval = 10000; // 10 seconds
        this.debounceDelay = 2000;  // 2 seconds after last change
        
        // State tracking
        this.lastSaveVersion = null;
        this.saveTimer = null;
        this.periodicTimer = null;
        this.isActive = false;
        
        // Create debounced save function
        this.debouncedSave = this.debounce(this.performSave.bind(this), this.debounceDelay);
        
        // Initialize save indicator
        this.initializeSaveIndicator();
    }
    
    /**
     * Start the auto-save system
     */
    start() {
        if (this.isActive) {
            console.warn('AutoSaveManager is already active');
            return;
        }
        
        this.isActive = true;
        
        // Start periodic auto-save
        this.periodicTimer = setInterval(() => {
            if (this.stateManager.hasUnsavedChanges()) {
                this.debouncedSave();
            }
        }, this.saveInterval);
        
        // Listen for form changes
        this.stateManager.addChangeListener(() => {
            this.onFormChange();
        });
        
        console.log('AutoSaveManager started');
    }
    
    /**
     * Stop the auto-save system
     */
    stop() {
        this.isActive = false;
        
        if (this.periodicTimer) {
            clearInterval(this.periodicTimer);
            this.periodicTimer = null;
        }
        
        if (this.saveTimer) {
            clearTimeout(this.saveTimer);
            this.saveTimer = null;
        }
        
        console.log('AutoSaveManager stopped');
    }
    
    /**
     * Handle form changes - trigger debounced save
     */
    onFormChange() {
        if (!this.isActive) return;
        
        this.showSaveIndicator('pending');
        this.debouncedSave();
    }
    
    /**
     * Perform the actual save operation
     */
    async performSave() {
        try {
            this.showSaveIndicator('saving');
            
            // Get current form data
            const formData = this.stateManager.serializeToJSON();
            
            // Validate before saving
            const validationResult = await this.validationEngine.validateCompleteForm(formData);
            const criticalErrors = validationResult.errors ? 
                validationResult.errors.filter(e => e.priority === 'critical') : [];
            
            if (criticalErrors.length > 0) {
                console.log('Auto-save skipped due to critical validation errors:', criticalErrors);
                this.showSaveIndicator('validation-error');
                return { success: false, reason: 'validation_errors', errors: criticalErrors };
            }
            
            // Attempt to save
            const response = await fetch('/api/entry/autosave', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    entryData: formData,
                    version: this.lastSaveVersion,
                    timestamp: new Date().toISOString()
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.lastSaveVersion = result.newVersion;
                this.stateManager.markAsSaved();
                this.showSaveIndicator('saved');
                
                // Show warnings if any
                if (result.warnings && result.warnings.length > 0) {
                    console.warn('Auto-save completed with warnings:', result.warnings);
                }
                
                return { success: true, version: result.newVersion };
                
            } else if (result.error === 'version_conflict') {
                this.handleVersionConflict(result);
                return { success: false, reason: 'conflict', conflict: result };
                
            } else {
                console.error('Auto-save failed:', result);
                this.showSaveIndicator('error');
                return { success: false, reason: 'server_error', error: result };
            }
            
        } catch (error) {
            console.error('Auto-save network error:', error);
            this.showSaveIndicator('error');
            return { success: false, reason: 'network_error', error: error.message };
        }
    }
    
    /**
     * Handle version conflicts
     */
    handleVersionConflict(conflictData) {
        this.showSaveIndicator('conflict');
        
        // Create conflict resolution modal
        const modal = this.createConflictModal(conflictData);
        document.body.appendChild(modal);
        
        // Show modal
        modal.style.display = 'block';
    }
    
    /**
     * Create version conflict resolution modal
     */
    createConflictModal(conflictData) {
        const modal = document.createElement('div');
        modal.className = 'autosave-conflict-modal';
        modal.innerHTML = `
            <div class="conflict-modal-content">
                <h3>Version Conflict Detected</h3>
                <p>The entry has been modified by another user or session.</p>
                <div class="conflict-details">
                    <p><strong>Your version:</strong> ${conflictData.clientVersion}</p>
                    <p><strong>Server version:</strong> ${conflictData.serverVersion}</p>
                </div>
                <div class="conflict-actions">
                    <button class="btn-merge" onclick="this.closest('.autosave-conflict-modal').handleMerge()">Merge Changes</button>
                    <button class="btn-overwrite" onclick="this.closest('.autosave-conflict-modal').handleOverwrite()">Overwrite Server</button>
                    <button class="btn-reload" onclick="this.closest('.autosave-conflict-modal').handleReload()">Reload From Server</button>
                    <button class="btn-cancel" onclick="this.closest('.autosave-conflict-modal').handleCancel()">Cancel</button>
                </div>
            </div>
        `;
        
        // Add event handlers
        modal.handleMerge = () => this.resolveConflict('merge', conflictData);
        modal.handleOverwrite = () => this.resolveConflict('overwrite', conflictData);
        modal.handleReload = () => this.resolveConflict('reload', conflictData);
        modal.handleCancel = () => this.resolveConflict('cancel', conflictData);
        
        return modal;
    }
    
    /**
     * Resolve version conflict based on user choice
     */
    async resolveConflict(action, conflictData) {
        const modal = document.querySelector('.autosave-conflict-modal');
        
        switch (action) {
            case 'merge':
                // TODO: Implement intelligent merge
                console.log('Merge functionality not yet implemented');
                break;
                
            case 'overwrite':
                // Force save with override flag
                this.lastSaveVersion = conflictData.serverVersion;
                await this.performSave();
                break;
                
            case 'reload':
                // Reload form with server data
                this.stateManager.updateFromJSON(conflictData.serverData);
                this.lastSaveVersion = conflictData.serverVersion;
                this.showSaveIndicator('reloaded');
                break;
                
            case 'cancel':
                // Just close modal, keep current state
                this.showSaveIndicator('conflict');
                break;
        }
        
        // Remove modal
        if (modal) {
            modal.remove();
        }
    }
    
    /**
     * Initialize save status indicator
     */
    initializeSaveIndicator() {
        // Create save indicator if it doesn't exist
        if (!document.getElementById('autosave-indicator')) {
            const indicator = document.createElement('div');
            indicator.id = 'autosave-indicator';
            indicator.className = 'autosave-indicator';
            
            // Add to page (usually in header or status bar)
            const header = document.querySelector('header, .header, .navbar');
            if (header) {
                header.appendChild(indicator);
            } else {
                document.body.appendChild(indicator);
            }
        }
    }
    
    /**
     * Update save status indicator
     */
    showSaveIndicator(status) {
        const indicator = document.getElementById('autosave-indicator');
        if (!indicator) {
            this.initializeSaveIndicator();
            return this.showSaveIndicator(status);
        }
        
        // Clear existing classes
        indicator.className = 'autosave-indicator';
        
        let message = '';
        let className = '';
        
        switch (status) {
            case 'pending':
                message = 'Changes pending...';
                className = 'pending';
                break;
                
            case 'saving':
                message = 'Saving...';
                className = 'saving';
                break;
                
            case 'saved':
                message = 'Saved';
                className = 'saved';
                // Auto-hide after 3 seconds
                setTimeout(() => {
                    if (indicator.textContent === 'Saved') {
                        indicator.textContent = '';
                        indicator.className = 'autosave-indicator';
                    }
                }, 3000);
                break;
                
            case 'error':
                message = 'Save failed';
                className = 'error';
                break;
                
            case 'validation-error':
                message = 'Validation errors';
                className = 'validation-error';
                break;
                
            case 'conflict':
                message = 'Version conflict';
                className = 'conflict';
                break;
                
            case 'reloaded':
                message = 'Reloaded from server';
                className = 'reloaded';
                setTimeout(() => {
                    if (indicator.textContent === 'Reloaded from server') {
                        indicator.textContent = '';
                        indicator.className = 'autosave-indicator';
                    }
                }, 3000);
                break;
        }
        
        indicator.textContent = message;
        indicator.className = `autosave-indicator ${className}`;
    }
    
    /**
     * Debounce utility function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * Force an immediate save (for manual save button)
     */
    async forceSave() {
        if (this.saveTimer) {
            clearTimeout(this.saveTimer);
            this.saveTimer = null;
        }
        return await this.performSave();
    }
    
    /**
     * Get current save status
     */
    getSaveStatus() {
        return {
            isActive: this.isActive,
            hasUnsavedChanges: this.stateManager.hasUnsavedChanges(),
            lastSaveVersion: this.lastSaveVersion,
            lastSaveTime: this.lastSaveTime
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AutoSaveManager;
} else if (typeof window !== 'undefined') {
    window.AutoSaveManager = AutoSaveManager;
}
