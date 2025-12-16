/**
 * Entry Form Undo/Redo functionality
 * Handles operation history, undo/redo buttons, and tooltips
 */

class EntryFormUndoRedo {
    constructor() {
        this.undoBtn = document.getElementById('undo-btn');
        this.redoBtn = document.getElementById('redo-btn');
        this.historyDropdown = document.getElementById('operationHistoryDropdown');
        this.historyList = document.getElementById('operation-history-list');
        this.operationHistory = [];

        this.init();
    }

    init() {
        // Bind event listeners
        this.undoBtn.addEventListener('click', () => this.performUndo());
        this.redoBtn.addEventListener('click', () => this.performRedo());

        // Load initial operation history
        this.loadOperationHistory();

        // Set up periodic refresh of operation history
        setInterval(() => this.loadOperationHistory(), 5000); // Refresh every 5 seconds
    }

    async loadOperationHistory() {
        try {
            const response = await fetch('/api/backup/operations');
            if (!response.ok) {
                console.warn('Failed to load operation history:', response.status);
                return;
            }

            const data = await response.json();
            this.operationHistory = data.operations || [];
            this.updateButtons();
            this.updateHistoryDropdown();
        } catch (error) {
            console.error('Error loading operation history:', error);
        }
    }

    updateButtons() {
        const undoStack = this.operationHistory.filter(op => op.status === 'completed');
        const redoStack = this.operationHistory.filter(op => op.status === 'undone');

        // Update undo button
        if (undoStack.length > 0) {
            const lastOperation = undoStack[undoStack.length - 1];
            this.undoBtn.disabled = false;
            this.undoBtn.title = `Undo: ${this.getOperationDescription(lastOperation)}`;
        } else {
            this.undoBtn.disabled = true;
            this.undoBtn.title = 'Undo last operation';
        }

        // Update redo button
        if (redoStack.length > 0) {
            const lastUndoneOperation = redoStack[redoStack.length - 1];
            this.redoBtn.disabled = false;
            this.redoBtn.title = `Redo: ${this.getOperationDescription(lastUndoneOperation)}`;
        } else {
            this.redoBtn.disabled = true;
            this.redoBtn.title = 'Redo last undone operation';
        }
    }

    updateHistoryDropdown() {
        if (this.operationHistory.length === 0) {
            this.historyList.innerHTML = '<li><a class="dropdown-item disabled">No operations yet</a></li>';
            return;
        }

        const items = this.operationHistory.slice(-10).reverse().map(op => {
            const description = this.getOperationDescription(op);
            const timestamp = new Date(op.timestamp).toLocaleString();
            const statusIcon = this.getStatusIcon(op.status);
            const statusClass = op.status === 'completed' ? 'text-success' :
                              op.status === 'undone' ? 'text-warning' : 'text-danger';

            return `
                <li>
                    <a class="dropdown-item" href="#" title="${timestamp}">
                        <i class="${statusIcon} ${statusClass} me-2"></i>
                        ${description}
                        <small class="text-muted ms-2">${timestamp}</small>
                    </a>
                </li>
            `;
        });

        this.historyList.innerHTML = items.join('');
    }

    getOperationDescription(operation) {
        const type = operation.type || 'unknown';
        const entryId = operation.entry_id || 'unknown';

        switch (type) {
            case 'create_entry':
                return `Created entry ${entryId}`;
            case 'update_entry':
                return `Updated entry ${entryId}`;
            case 'delete_entry':
                return `Deleted entry ${entryId}`;
            case 'merge_entries':
                return `Merged entries`;
            case 'split_entry':
                return `Split entry ${entryId}`;
            default:
                return `Operation: ${type}`;
        }
    }

    getStatusIcon(status) {
        switch (status) {
            case 'completed':
                return 'fas fa-check-circle';
            case 'undone':
                return 'fas fa-undo';
            case 'failed':
                return 'fas fa-exclamation-triangle';
            default:
                return 'fas fa-question-circle';
        }
    }

    async performUndo() {
        if (this.undoBtn.disabled) return;

        try {
            this.undoBtn.disabled = true;
            this.undoBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Undoing...';

            const response = await fetch('/api/backup/operations/undo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const result = await response.json();
                this.showToast('Operation undone successfully', 'success');

                // Reload the page to reflect changes
                setTimeout(() => window.location.reload(), 1000);
            } else {
                const error = await response.json();
                this.showToast(`Undo failed: ${error.error || 'Unknown error'}`, 'error');
                this.undoBtn.disabled = false;
                this.undoBtn.innerHTML = '<i class="fas fa-undo"></i> Undo';
            }
        } catch (error) {
            console.error('Error performing undo:', error);
            this.showToast('Network error during undo operation', 'error');
            this.undoBtn.disabled = false;
            this.undoBtn.innerHTML = '<i class="fas fa-undo"></i> Undo';
        }
    }

    async performRedo() {
        if (this.redoBtn.disabled) return;

        try {
            this.redoBtn.disabled = true;
            this.redoBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Redoing...';

            const response = await fetch('/api/backup/operations/redo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const result = await response.json();
                this.showToast('Operation redone successfully', 'success');

                // Reload the page to reflect changes
                setTimeout(() => window.location.reload(), 1000);
            } else {
                const error = await response.json();
                this.showToast(`Redo failed: ${error.error || 'Unknown error'}`, 'error');
                this.redoBtn.disabled = false;
                this.redoBtn.innerHTML = '<i class="fas fa-redo"></i> Redo';
            }
        } catch (error) {
            console.error('Error performing redo:', error);
            this.showToast('Network error during redo operation', 'error');
            this.redoBtn.disabled = false;
            this.redoBtn.innerHTML = '<i class="fas fa-redo"></i> Redo';
        }
    }

    showToast(message, type = 'info') {
        // Use existing toast system if available, otherwise fallback to alert
        if (window.showAppToast) {
            window.showAppToast(message, type);
        } else {
            alert(message);
        }
    }

    // Method to record operations (called by form submission handlers)
    async recordOperation(type, entryId, data = {}) {
        try {
            const operationData = {
                type: type,
                entry_id: entryId,
                timestamp: new Date().toISOString(),
                data: data
            };

            const response = await fetch('/api/backup/operations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(operationData)
            });

            if (response.ok) {
                // Refresh operation history
                await this.loadOperationHistory();
            } else {
                console.warn('Failed to record operation:', response.status);
            }
        } catch (error) {
            console.error('Error recording operation:', error);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('undo-btn')) {
        window.entryFormUndoRedo = new EntryFormUndoRedo();
    }
});