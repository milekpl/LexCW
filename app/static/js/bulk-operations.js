/**
 * Bulk Operations Hub
 *
 * Standalone bulk operations interface that reuses:
 * - ConditionBuilder (from bulk-editor.js) for query conditions
 * - PipelineEditor (from bulk-editor.js) for action pipelines
 *
 * Features:
 * - Build conditions to select entries
 * - Build pipeline of actions
 * - Save pipelines as templates
 * - Execute on matching entries
 */

class BulkOperationsHub {
    constructor() {
        this.conditionBuilder = null;
        this.pipelineEditor = null;
        this.savedPipelines = [];
        this.matchedCount = 0;

        this.init();
    }

    async init() {
        console.log('[BulkOperationsHub] Initializing...');

        // Wait for ConditionBuilder and PipelineEditor to load
        await this.waitForDependencies();

        // Initialize ConditionBuilder
        const conditionContainer = document.getElementById('condition-builder');
        if (conditionContainer) {
            this.conditionBuilder = new ConditionBuilder(conditionContainer);
        }

        // Initialize PipelineEditor
        const pipelineContainer = document.getElementById('pipeline-editor');
        if (pipelineContainer) {
            this.pipelineEditor = new PipelineEditor(pipelineContainer);
        }

        // Load saved pipelines
        await this.loadPipelines();

        // Set up event handlers
        this.setupEventHandlers();

        console.log('[BulkOperationsHub] Initialized');
    }

    async waitForDependencies() {
        // Wait for ConditionBuilder and PipelineEditor to be available
        const maxWait = 5000;
        const checkInterval = 100;
        let waited = 0;

        while ((typeof ConditionBuilder === 'undefined' || typeof PipelineEditor === 'undefined') && waited < maxWait) {
            await new Promise(resolve => setTimeout(resolve, checkInterval));
            waited += checkInterval;
        }

        if (typeof ConditionBuilder === 'undefined') {
            console.error('[BulkOperationsHub] ConditionBuilder not loaded');
        }
        if (typeof PipelineEditor === 'undefined') {
            console.error('[BulkOperationsHub] PipelineEditor not loaded');
        }
    }

    setupEventHandlers() {
        // Execute button
        document.getElementById('execute-pipeline-btn')?.addEventListener('click', () => this.executePipeline());

        // Save pipeline button
        document.getElementById('save-pipeline-btn')?.addEventListener('click', () => this.showSavePipelineModal());

        // Preview button
        document.getElementById('preview-btn')?.addEventListener('click', () => this.previewMatch());

        // Pipeline saved modal confirm
        document.getElementById('confirm-save-pipeline')?.addEventListener('click', () => this.savePipeline());

        // Load pipeline buttons (in the saved pipelines list)
        document.getElementById('saved-pipelines-list')?.addEventListener('click', (e) => {
            if (e.target.matches('.load-pipeline-btn')) {
                const id = e.target.dataset.id;
                this.loadPipeline(id);
            } else if (e.target.matches('.run-pipeline-btn')) {
                const id = e.target.dataset.id;
                this.runPipeline(id);
            } else if (e.target.matches('.delete-pipeline-btn')) {
                const id = e.target.dataset.id;
                this.deletePipeline(id);
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.executePipeline();
            } else if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                this.showSavePipelineModal();
            }
        });
    }

    async previewMatch() {
        const condition = this.conditionBuilder?.getCondition();
        const steps = this.pipelineEditor?.getPipeline();

        if (!condition) {
            this.updateMatchPreview(0);
            showNotification('No conditions specified - will affect all entries', 'warning');
            return;
        }

        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

        try {
            const response = await fetch('/api/bulk/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({ condition, action: steps?.[0] || {} })
            });

            const data = await response.json();
            this.matchedCount = data.would_affect || 0;
            this.updateMatchPreview(this.matchedCount);

            if (this.matchedCount === 0) {
                showNotification('No entries match the conditions', 'info');
            } else {
                showNotification(`Preview: ${this.matchedCount} entries would be affected`, 'success');
            }
        } catch (error) {
            console.error('[BulkOperationsHub] Preview error:', error);
            showNotification('Error generating preview', 'error');
        }
    }

    updateMatchPreview(count) {
        const badge = document.getElementById('match-count-badge');
        if (badge) {
            badge.textContent = count.toLocaleString();
            badge.className = count > 0 ? 'badge bg-success' : 'badge bg-secondary';
        }
    }

    async executePipeline() {
        const steps = this.pipelineEditor?.getPipeline();

        if (!steps || steps.length === 0) {
            showNotification('Please add at least one action to the pipeline', 'warning');
            return;
        }

        const condition = this.conditionBuilder?.getCondition();
        const previewOnly = document.getElementById('preview-mode')?.checked;

        const btn = document.getElementById('execute-pipeline-btn');
        const originalText = btn ? btn.textContent : 'Execute';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Executing...';
        }

        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

        try {
            const response = await fetch('/api/bulk/pipeline', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({
                    condition,
                    steps,
                    preview: previewOnly
                })
            });

            const data = await response.json();

            if (previewOnly) {
                // Preview returns would_affect count
                const affected = data.would_affect || data.summary?.total_success || 0;
                showNotification(`Preview: ${affected} entries would be affected`, 'info');
                this.showPreviewResults(data);
            } else {
                // Execute returns summary with success count
                const changed = data.summary?.total_success || 0;
                showNotification(`Pipeline executed: ${changed} entries changed`, 'success');
                this.showExecutionResults(data);
            }
        } catch (error) {
            console.error('[BulkOperationsHub] Execute error:', error);
            showNotification('Error executing pipeline', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        }
    }

    showPreviewResults(data) {
        // Could show a modal with detailed preview
        console.log('[BulkOperationsHub] Preview results:', data);
    }

    showExecutionResults(data) {
        // Could show a modal with execution summary
        console.log('[BulkOperationsHub] Execution results:', data);
    }

    // ============ PIPELINE TEMPLATES ============

    async loadPipelines() {
        try {
            const response = await fetch('/api/pipelines');
            if (response.ok) {
                const data = await response.json();
                this.savedPipelines = data.pipelines || [];
                this.renderPipelineList();
            }
        } catch (error) {
            console.error('[BulkOperationsHub] Error loading pipelines:', error);
        }
    }

    renderPipelineList() {
        const container = document.getElementById('saved-pipelines-list');
        if (!container) return;

        if (this.savedPipelines.length === 0) {
            container.innerHTML = '<p class="text-muted">No saved pipelines yet.</p>';
            return;
        }

        let html = '<div class="list-group list-group-flush">';

        for (const pipeline of this.savedPipelines) {
            html += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${this.escapeHtml(pipeline.name)}</strong>
                        <span class="badge bg-primary ms-2">${pipeline.steps} steps</span>
                        ${pipeline.description ? `<br><small class="text-muted">${this.escapeHtml(pipeline.description)}</small>` : ''}
                    </div>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary load-pipeline-btn" data-id="${pipeline.id}">
                            <i class="bi bi-download"></i> Load
                        </button>
                        <button class="btn btn-success run-pipeline-btn" data-id="${pipeline.id}">
                            <i class="bi bi-play"></i> Run
                        </button>
                        <button class="btn btn-outline-danger delete-pipeline-btn" data-id="${pipeline.id}">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        }

        html += '</div>';
        container.innerHTML = html;
    }

    showSavePipelineModal() {
        const modal = new bootstrap.Modal(document.getElementById('save-pipeline-modal'));
        modal.show();

        // Pre-fill name with current date
        const nameInput = document.getElementById('pipeline-name');
        if (!nameInput.value) {
            const now = new Date();
            nameInput.value = `Pipeline ${now.toLocaleDateString()} ${now.getHours()}:${now.getMinutes()}`;
        }
    }

    async savePipeline() {
        const name = document.getElementById('pipeline-name')?.value?.trim();
        const description = document.getElementById('pipeline-description')?.value?.trim();
        const steps = this.pipelineEditor?.getPipeline();
        const conditions = this.conditionBuilder?.getCondition();

        if (!name) {
            alert('Please enter a pipeline name');
            return;
        }

        if (!steps || steps.length === 0) {
            alert('Please add at least one action to the pipeline');
            return;
        }

        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

        try {
            const response = await fetch('/api/pipelines', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({ name, description, steps, conditions })
            });

            const data = await response.json();

            if (data.success) {
                showNotification('Pipeline saved successfully!', 'success');
                bootstrap.Modal.getInstance(document.getElementById('save-pipeline-modal')).hide();
                await this.loadPipelines();

                // Clear the name/description for next time
                document.getElementById('pipeline-name').value = '';
                document.getElementById('pipeline-description').value = '';
            } else {
                alert('Error saving pipeline: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('[BulkOperationsHub] Save error:', error);
            alert('Error saving pipeline');
        }
    }

    async loadPipeline(id) {
        try {
            const response = await fetch(`/api/pipelines/${id}`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Load pipeline steps
                    const steps = data.config?.steps || [];
                    this.pipelineEditor?.setPipeline(steps);

                    // Load conditions if present
                    const conditions = data.config?.conditions;
                    if (conditions && this.conditionBuilder) {
                        this.conditionBuilder.setCondition(conditions);
                    }

                    showNotification('Pipeline loaded', 'success');
                }
            }
        } catch (error) {
            console.error('[BulkOperationsHub] Load error:', error);
            showNotification('Error loading pipeline', 'error');
        }
    }

    async runPipeline(id) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

        try {
            const response = await fetch(`/api/pipelines/${id}/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({})
            });

            const data = await response.json();

            if (data.error) {
                showNotification('Error: ' + data.error, 'error');
            } else {
                showNotification(`Pipeline executed: ${data.executed} entries affected`, 'success');
            }
        } catch (error) {
            console.error('[BulkOperationsHub] Run error:', error);
            showNotification('Error running pipeline', 'error');
        }
    }

    async deletePipeline(id) {
        if (!confirm('Delete this pipeline template?')) {
            return;
        }

        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

        try {
            const response = await fetch(`/api/pipelines/${id}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRF-TOKEN': csrfToken
                }
            });
            const data = await response.json();

            if (data.success) {
                showNotification('Pipeline deleted', 'success');
                await this.loadPipelines();
            } else {
                alert('Error deleting pipeline: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('[BulkOperationsHub] Delete error:', error);
            showNotification('Error deleting pipeline', 'error');
        }
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Notification helper
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 300);
    }, 3000);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.bulkOperationsHub = new BulkOperationsHub();
});
