/**
 * Word Sketch Browser Page Controller
 *
 * Handles the standalone word sketch browser page with:
 * - Lemma search with POS filtering
 * - LogDice score threshold slider
 * - Grammatical relations tabs
 * - Collocation results display
 * - Custom CQL queries
 * - Examples modal
 */

class WordSketchBrowser {
    constructor() {
        this.apiBase = '/api/word-sketch';
        this.currentData = null;
        this.currentLemma = null;
        this.currentPos = null;

        this.initElements();
        this.bindEvents();
        this.checkServiceStatus();
    }

    initElements() {
        // Search elements
        this.lemmaInput = document.getElementById('lemma-input');
        this.posSelect = document.getElementById('pos-select');
        this.minLogdiceSlider = document.getElementById('min-logdice');
        this.logdiceValue = document.getElementById('logdice-value');
        this.limitSelect = document.getElementById('limit-select');
        this.btnSearch = document.getElementById('btn-search');
        this.btnBrowse = document.getElementById('btn-browse');

        // Custom query elements
        this.customLemmaInput = document.getElementById('custom-lemma');
        this.customPatternInput = document.getElementById('custom-pattern');
        this.btnCustomQuery = document.getElementById('btn-custom-query');

        // State containers
        this.loadingState = document.getElementById('loading-state');
        this.emptyState = document.getElementById('empty-state');
        this.unavailableState = document.getElementById('unavailable-state');
        this.resultsContainer = document.getElementById('results-container');

        // Result elements
        this.resultLemma = document.getElementById('result-lemma');
        this.resultPos = document.getElementById('result-pos');
        this.resultStats = document.getElementById('result-stats');
        this.relationsTabs = document.getElementById('relations-tabs');
        this.relationsContent = document.getElementById('relations-content');

        // Service status
        this.serviceStatus = document.getElementById('service-status');
    }

    bindEvents() {
        // Main search
        this.btnBrowse.addEventListener('click', () => this.handleSearch());
        this.btnSearch.addEventListener('click', () => this.handleSearch());

        // Enter key on lemma input
        this.lemmaInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch();
        });

        // LogDice slider
        this.minLogdiceSlider.addEventListener('input', (e) => {
            this.logdiceValue.textContent = parseFloat(e.target.value).toFixed(1);
        });

        // Quick lemma buttons
        document.querySelectorAll('.quick-lemma').forEach(btn => {
            btn.addEventListener('click', () => {
                this.lemmaInput.value = btn.dataset.lemma;
                this.handleSearch();
            });
        });

        // Custom query
        this.btnCustomQuery.addEventListener('click', () => this.handleCustomQuery());

        // Add to workset button
        document.getElementById('btn-add-to-workset')?.addEventListener('click', () => {
            this.addToWorkset();
        });

        // Copy results button
        document.getElementById('btn-copy-results')?.addEventListener('click', () => {
            this.copyResults();
        });
    }

    async checkServiceStatus() {
        try {
            const response = await fetch(`${this.apiBase}/health`);
            if (response.ok) {
                this.updateServiceStatus('available', 'Service Available');
            } else {
                this.updateServiceStatus('unavailable', 'Service Error');
            }
        } catch (error) {
            this.updateServiceStatus('unavailable', 'Service Unavailable');
        }
    }

    updateServiceStatus(status, message) {
        this.serviceStatus.className = 'badge';

        switch (status) {
            case 'available':
                this.serviceStatus.classList.add('bg-success');
                this.serviceStatus.innerHTML = '<i class="bi bi-check-circle"></i> ' + message;
                break;
            case 'unavailable':
                this.serviceStatus.classList.add('bg-danger');
                this.serviceStatus.innerHTML = '<i class="bi bi-x-circle"></i> ' + message;
                break;
            default:
                this.serviceStatus.classList.add('bg-secondary');
                this.serviceStatus.innerHTML = '<i class="bi bi-question-circle"></i> ' + message;
        }
    }

    async handleSearch() {
        const lemma = this.lemmaInput.value.trim();
        if (!lemma) {
            this.showError('Please enter a lemma');
            return;
        }

        this.currentLemma = lemma;
        this.currentPos = this.posSelect.value || null;
        const minLogdice = parseFloat(this.minLogdiceSlider.value);
        const limit = parseInt(this.limitSelect.value);

        await this.fetchWordSketch(lemma, this.currentPos, minLogdice, limit);
    }

    async handleCustomQuery() {
        const lemma = this.customLemmaInput.value.trim();
        const pattern = this.customPatternInput.value.trim();

        if (!lemma || !pattern) {
            this.showError('Please enter both lemma and CQL pattern');
            return;
        }

        await this.fetchCustomQuery(lemma, pattern);
    }

    async fetchWordSketch(lemma, pos, minLogdice, limit) {
        this.showLoading();

        try {
            const params = new URLSearchParams({
                lemma: lemma,
                limit: limit,
                min_logdice: minLogdice
            });
            if (pos) params.append('pos', pos);

            const response = await fetch(`${this.apiBase}/sketch/${lemma}?${params}`);

            if (!response.ok) {
                if (response.status === 503) {
                    this.showUnavailable();
                    return;
                }
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (!data.available) {
                this.showUnavailable();
                return;
            }

            this.currentData = data;
            this.renderResults(data, lemma, pos);

        } catch (error) {
            console.error('Word sketch fetch error:', error);
            this.showError('Failed to fetch word sketch: ' + error.message);
        }
    }

    async fetchCustomQuery(lemma, pattern) {
        this.showLoading();

        try {
            const response = await fetch(`${this.apiBase}/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lemma: lemma,
                    pattern: pattern
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.currentData = data;
            this.renderCustomResults(data, lemma);

        } catch (error) {
            console.error('Custom query error:', error);
            this.showError('Failed to execute query: ' + error.message);
        }
    }

    renderResults(data, lemma, pos) {
        this.hideAllStates();

        // Update header
        const lemmaSpan = this.resultLemma.querySelector('span');
        lemmaSpan.textContent = lemma;
        this.resultPos.textContent = pos ? `(${pos})` : '';

        // Update stats
        const totalRelations = Object.keys(data.relations || {}).length;
        const totalCollocations = Object.values(data.relations || {})
            .reduce((sum, rel) => sum + (rel.collocations?.length || 0), 0);
        this.resultStats.textContent = `${totalRelations} relations, ${totalCollocations} collocations found`;

        // Render tabs
        this.renderRelationTabs(data.relations);

        // Show results
        this.resultsContainer.style.display = 'block';

        // Update action buttons
        const addBtn = document.getElementById('btn-add-to-workset');
        const viewExamplesBtn = document.getElementById('btn-view-all-examples');

        if (addBtn) addBtn.style.display = 'inline-flex';
        if (viewExamplesBtn && totalCollocations > 0) {
            viewExamplesBtn.style.display = 'inline-flex';
        }
    }

    renderCustomResults(data, lemma) {
        this.hideAllStates();

        this.resultLemma.querySelector('span').textContent = lemma + ' (Custom Query)';
        this.resultPos.textContent = '';
        this.resultStats.textContent = `${data.count || 0} matches found`;

        // Render custom results
        let html = `
            <div class="tab-pane fade show active" id="tab-custom" role="tabpanel">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Query Results</h6>
                    </div>
                    <div class="card-body">
                        <div class="collocation-list">
                            ${this.renderCollocationList(data.collocations || [])}
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.relationsTabs.innerHTML = `
            <li class="nav-item">
                <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-custom" type="button">
                    Results
                </button>
            </li>
        `;
        this.relationsContent.innerHTML = html;

        this.resultsContainer.style.display = 'block';
    }

    renderRelationTabs(relations) {
        if (!relations || Object.keys(relations).length === 0) {
            this.relationsTabs.innerHTML = '<li class="nav-item"><span class="nav-link">No relations found</span></li>';
            this.relationsContent.innerHTML = '';
            return;
        }

        const relationNames = Object.keys(relations);
        let tabsHtml = '';
        let contentHtml = '';

        relationNames.forEach((relationKey, index) => {
            const relation = relations[relationKey];
            const collocations = relation.collocations || [];
            const isActive = index === 0 ? 'active' : '';
            const show = index === 0 ? 'show active' : '';

            // Format relation name for display
            const displayName = this.formatRelationName(relationKey);

            tabsHtml += `
                <li class="nav-item" role="presentation">
                    <button class="nav-link ${isActive}"
                            id="tab-${this.escapeHtml(relationKey)}"
                            data-bs-toggle="tab"
                            data-bs-target="#panel-${this.escapeHtml(relationKey)}"
                            type="button"
                            role="tab">
                        ${this.escapeHtml(displayName)}
                        <span class="badge bg-secondary ms-1">${collocations.length}</span>
                    </button>
                </li>
            `;

            contentHtml += `
                <div class="tab-pane fade ${show}"
                     id="panel-${this.escapeHtml(relationKey)}"
                     role="tabpanel">
                    <div class="collocation-list">
                        ${this.renderCollocationList(collocations, relationKey)}
                    </div>
                </div>
            `;
        });

        this.relationsTabs.innerHTML = tabsHtml;
        this.relationsContent.innerHTML = contentHtml;
    }

    renderCollocationList(collocations, relationKey = null) {
        if (!collocations || collocations.length === 0) {
            return '<div class="text-muted text-center py-4">No collocations found</div>';
        }

        return collocations.map((c, idx) => {
            const logdice = c.logdice || c.score || 0;
            const logdicePercent = (logdice / 14) * 100;
            const examples = c.examples || [];

            return `
                <div class="collocation-item" data-idx="${idx}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="collocation-main">
                            <div class="d-flex align-items-center gap-2 mb-1">
                                <strong class="collocation-word">${this.escapeHtml(c.word || c.value)}</strong>
                                <span class="badge bg-light text-dark">${c.pos || ''}</span>
                                <span class="logdice-badge badge ${this.getLogdiceBadgeClass(logdice)}">
                                    logDice: ${logdice.toFixed(2)}
                                </span>
                            </div>
                            ${c.relation_name ? `<small class="text-muted">${this.escapeHtml(c.relation_name)}</small>` : ''}
                        </div>
                        <div class="collocation-actions">
                            <button class="btn btn-sm btn-outline-primary view-examples-btn"
                                    data-word="${this.escapeHtml(c.word || c.value)}"
                                    data-relation="${relationKey || this.escapeHtml(c.relation || '')}"
                                    title="View examples">
                                <i class="bi bi-quote"></i>
                            </button>
                        </div>
                    </div>
                    <div class="logdice-bar mt-2">
                        <div class="bar" style="width: ${logdicePercent}%"></div>
                    </div>
                    ${examples.length > 0 ? `
                        <div class="examples-preview mt-2">
                            <small class="text-muted">"${this.escapeHtml(examples[0].substring(0, 100))}${examples[0].length > 100 ? '...' : ''}"</small>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
    }

    formatRelationName(relationKey) {
        const names = {
            'noun_modifiers': 'Noun Modifiers',
            'verb_objects': 'Verb Objects',
            'subject_verb': 'Subject + Verb',
            'adjective_noun': 'Adjective + Noun',
            'noun_noun_compounds': 'Noun Compounds',
            'verb_adverb': 'Verb + Adverb',
            'adverb_verb': 'Adverb + Verb',
            'prepositional': 'Prepositional',
            'compound': 'Compound',
            'related': 'Related Terms'
        };
        return names[relationKey] || relationKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    getLogdiceBadgeClass(logdice) {
        if (logdice >= 10) return 'bg-success';
        if (logdice >= 7) return 'bg-primary';
        if (logdice >= 4) return 'bg-warning text-dark';
        return 'bg-secondary';
    }

    async showExamples(word, relation) {
        const modal = new bootstrap.Modal(document.getElementById('examples-modal'));
        const modalBody = document.getElementById('examples-modal-body');
        const modalCollocate = document.getElementById('modal-collocate');

        modalCollocate.textContent = word;
        modalBody.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div></div>';

        modal.show();

        try {
            const response = await fetch(
                `${this.apiBase}/enrich/${this.currentLemma}/examples?collocate=${encodeURIComponent(word)}&limit=10`
            );
            const data = await response.json();

            if (data.examples && data.examples.length > 0) {
                modalBody.innerHTML = data.examples.map(e => `
                    <div class="example-item">
                        <p class="mb-1">"${this.escapeHtml(e.source)}"</p>
                        ${e.translation ? `<p class="text-muted small mb-1"><em>${this.escapeHtml(e.translation)}</em></p>` : ''}
                        <small class="text-muted">${e.corpus || ''}</small>
                    </div>
                `).join('<hr class="my-3">');
            } else {
                modalBody.innerHTML = '<p class="text-muted text-center py-4">No examples found</p>';
            }
        } catch (error) {
            modalBody.innerHTML = `<p class="text-danger text-center py-4">Error loading examples: ${this.escapeHtml(error.message)}</p>`;
        }
    }

    getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    async addToWorkset() {
        if (!this.currentLemma) {
            this.showError('No lemma selected');
            return;
        }

        // Create or get the workset modal
        let modal = document.getElementById('workset-selection-modal');
        if (!modal) {
            modal = this.createWorksetModal();
            document.body.appendChild(modal);
        }

        // Reset modal state
        const modalInstance = bootstrap.Modal.getOrCreateInstance(modal);
        modalInstance.show();

        // Load existing worksets
        await this.loadWorksetsForModal(modal);
    }

    createWorksetModal() {
        const div = document.createElement('div');
        div.id = 'workset-selection-modal';
        div.className = 'modal fade';
        div.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Add to Workset</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <!-- Existing Worksets Section -->
                        <div class="mb-4">
                            <h6 class="border-bottom pb-2 mb-3">Select Existing Workset</h6>
                            <div id="workset-list-container" class="workset-list" style="max-height: 200px; overflow-y: auto;">
                                <div class="text-center py-3">
                                    <div class="spinner-border spinner-border-sm"></div> Loading...
                                </div>
                            </div>
                        </div>

                        <!-- Create New Workset Section -->
                        <div class="border-top pt-3">
                            <h6 class="mb-3">Or Create New Workset</h6>
                            <div class="input-group">
                                <input type="text"
                                       id="new-workset-name"
                                       class="form-control"
                                       placeholder="New workset name">
                                <button type="button" class="btn btn-primary" id="btn-create-workset">
                                    Create
                                </button>
                            </div>
                            <div class="form-text">
                                A new workset will be created with this lemma as a query filter.
                            </div>
                        </div>

                        <!-- Feedback messages -->
                        <div id="workset-modal-feedback" class="mt-3" style="display: none;"></div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    </div>
                </div>
            </div>
        `;

        // Set up event handlers after modal is added to DOM
        div.addEventListener('shown.bs.modal', () => {
            const nameInput = div.querySelector('#new-workset-name');
            if (nameInput) {
                nameInput.focus();
            }
        });

        // Create new workset button handler
        div.querySelector('#btn-create-workset')?.addEventListener('click', async () => {
            const nameInput = div.querySelector('#new-workset-name');
            const name = nameInput?.value.trim();
            if (!name) {
                this.showWorksetFeedback(div, 'Please enter a workset name', 'danger');
                return;
            }
            await this.createWorksetAndAdd(name, div);
        });

        // Enter key on workset name input
        div.querySelector('#new-workset-name')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                div.querySelector('#btn-create-workset')?.click();
            }
        });

        return div;
    }

    async loadWorksetsForModal(modal) {
        const container = modal.querySelector('#workset-list-container');
        if (!container) return;

        container.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm"></div> Loading...</div>';

        try {
            const response = await fetch('/api/worksets');
            const data = await response.json();

            if (data.error) {
                container.innerHTML = '<div class="text-danger py-2">Error loading worksets</div>';
                return;
            }

            const worksets = data.worksets || [];

            if (worksets.length === 0) {
                container.innerHTML = '<p class="text-muted text-center py-3">No existing worksets</p>';
                return;
            }

            let html = '<div class="list-group list-group-flush">';

            for (const ws of worksets) {
                html += `
                    <button type="button"
                            class="list-group-item list-group-item-action d-flex justify-content-between align-items-center workset-item"
                            data-workset-id="${this.escapeHtml(String(ws.id))}"
                            data-workset-name="${this.escapeHtml(ws.name)}">
                        <span>
                            <i class="bi bi-folder me-2"></i>${this.escapeHtml(ws.name)}
                        </span>
                        <span class="badge bg-secondary">${ws.total_entries} entries</span>
                    </button>
                `;
            }

            html += '</div>';
            container.innerHTML = html;

            // Set up click handlers for workset items
            container.querySelectorAll('.workset-item').forEach(item => {
                item.addEventListener('click', async () => {
                    const worksetId = parseInt(item.dataset.worksetId, 10);
                    if (isNaN(worksetId) || worksetId <= 0) {
                        this.showWorksetFeedback(modal, 'Invalid workset ID', 'danger');
                        return;
                    }
                    const worksetName = item.dataset.worksetName;
                    await this.addToExistingWorkset(worksetId, worksetName, modal);
                });
            });

        } catch (error) {
            console.error('[WordSketchBrowser] Error loading worksets:', error);
            container.innerHTML = '<div class="text-danger py-2">Error loading worksets</div>';
        }
    }

    async addToExistingWorkset(worksetId, worksetName, modal) {
        const feedback = modal.querySelector('#workset-modal-feedback');
        feedback.style.display = 'block';
        feedback.innerHTML = '<div class="alert alert-info">Adding lemma to workset...</div>';

        try {
            // Create a query-based workset for the lemma
            const query = {
                filters: [
                    { field: 'lexical_unit', operator: 'equals', value: this.currentLemma }
                ],
                sort_by: 'lexical_unit',
                sort_order: 'asc'
            };

            const response = await fetch(`/api/worksets/${worksetId}/query`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': this.getCsrfToken()
                },
                body: JSON.stringify(query)
            });

            const data = await response.json();

            if (data.error) {
                this.showWorksetFeedback(modal, 'Error: ' + data.error, 'danger');
                return;
            }

            this.showWorksetFeedback(modal,
                `Added "${this.currentLemma}" to workset "${worksetName}". ${data.updated_entries || 0} entries updated.`,
                'success');

            // Close modal after short delay
            setTimeout(() => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            }, 1500);

        } catch (error) {
            console.error('[WordSketchBrowser] Error adding to workset:', error);
            this.showWorksetFeedback(modal, 'Error adding to workset: ' + error.message, 'danger');
        }
    }

    async createWorksetAndAdd(name, modal) {
        const feedback = modal.querySelector('#workset-modal-feedback');
        feedback.style.display = 'block';
        feedback.innerHTML = '<div class="alert alert-info">Creating workset...</div>';

        try {
            // Create a query-based workset for the lemma
            const query = {
                filters: [
                    { field: 'lexical_unit', operator: 'equals', value: this.currentLemma }
                ],
                sort_by: 'lexical_unit',
                sort_order: 'asc'
            };

            const response = await fetch('/api/worksets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': this.getCsrfToken()
                },
                body: JSON.stringify({
                    name: name,
                    query: query
                })
            });

            const data = await response.json();

            if (data.error) {
                this.showWorksetFeedback(modal, 'Error: ' + data.error, 'danger');
                return;
            }

            this.showWorksetFeedback(modal,
                `Created workset "${name}" with ${data.total_entries || 0} entries.`,
                'success');

            // Close modal after short delay
            setTimeout(() => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            }, 1500);

        } catch (error) {
            console.error('[WordSketchBrowser] Error creating workset:', error);
            this.showWorksetFeedback(modal, 'Error creating workset: ' + error.message, 'danger');
        }
    }

    showWorksetFeedback(modal, message, type) {
        const feedback = modal.querySelector('#workset-modal-feedback');
        if (feedback) {
            feedback.style.display = 'block';
            feedback.innerHTML = `<div class="alert alert-${type} mb-0">${message}</div>`;
        }
    }

    copyResults() {
        // Copy collocations to clipboard
        const text = this.generateResultsText();
        navigator.clipboard.writeText(text).then(() => {
            alert('Results copied to clipboard');
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    }

    generateResultsText() {
        if (!this.currentData || !this.currentData.relations) return '';

        let text = `Word Sketch for: ${this.currentLemma}\n\n`;
        text += '='.repeat(50) + '\n\n';

        for (const [relationKey, relation] of Object.entries(this.currentData.relations)) {
            text += `${this.formatRelationName(relationKey)}:\n`;
            text += '-'.repeat(30) + '\n';

            for (const collocation of (relation.collocations || [])) {
                const logdice = collocation.logdice || collocation.score || 0;
                text += `  ${collocation.word || collocation.value} (logDice: ${logdice.toFixed(2)})\n`;
            }
            text += '\n';
        }

        return text;
    }

    showLoading() {
        this.hideAllStates();
        this.loadingState.style.display = 'block';
        this.resultsContainer.style.display = 'none';
    }

    showUnavailable() {
        this.hideAllStates();
        this.unavailableState.style.display = 'block';
    }

    showError(message) {
        this.hideAllStates();
        alert(message);
        this.emptyState.style.display = 'block';
    }

    hideAllStates() {
        this.loadingState.style.display = 'none';
        this.emptyState.style.display = 'none';
        this.unavailableState.style.display = 'none';
        this.resultsContainer.style.display = 'none';
    }

    escapeHtml(text) {
        if (text == null) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    window.wsBrowser = new WordSketchBrowser();
});
