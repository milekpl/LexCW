/**
 * Word Sketch Integration for Workset Curation
 *
 * Provides:
 * - Coverage status for entries
 * - Enrichment suggestions
 * - Subentry draft generation
 * - Integration with workset curation workflow
 */

class WordSketchIntegration {
    constructor(options = {}) {
        this.apiBase = options.apiBase || '/api/word-sketch';
        this.worksetId = options.worksetId || null;
        this.currentLemma = options.currentLemma || null;
        this.currentPos = options.currentPos || null;

        // Cache for API responses
        this._cache = new Map();

        // State
        this._listeners = new Map();
    }

    // =====================================================================
    // Event System
    // =====================================================================

    on(event, callback) {
        if (!this._listeners.has(event)) {
            this._listeners.set(event, []);
        }
        this._listeners.get(event).push(callback);
    }

    off(event, callback) {
        const listeners = this._listeners.get(event);
        if (listeners) {
            const index = listeners.indexOf(callback);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        }
    }

    emit(event, data) {
        const listeners = this._listeners.get(event);
        if (listeners) {
            listeners.forEach(cb => cb(data));
        }
    }

    // =====================================================================
    // Coverage API
    // =====================================================================

    /**
     * Get coverage report for a workset
     */
    async getWorksetCoverage(worksetId = this.worksetId) {
        const cacheKey = `coverage:${worksetId}`;
        if (this._cache.has(cacheKey)) {
            return this._cache.get(cacheKey);
        }

        try {
            const response = await fetch(
                `${this.apiBase}/coverage/workset/${worksetId}`
            );
            const data = await response.json();

            if (data.available) {
                this._cache.set(cacheKey, data);
                this.emit('coverage-loaded', data);
            }

            return data;
        } catch (error) {
            console.error('Failed to get workset coverage:', error);
            return { available: false, error: error.message };
        }
    }

    /**
     * Get coverage for a single entry
     */
    async checkEntryCoverage(lemma, pos = null) {
        const cacheKey = `entry:${lemma}:${pos || ''}`;
        if (this._cache.has(cacheKey)) {
            return this._cache.get(cacheKey);
        }

        try {
            const params = new URLSearchParams({ lemma });
            if (pos) params.append('pos', pos);

            const response = await fetch(
                `${this.apiBase}/coverage/entry/${lemma}?${params}`
            );
            const data = await response.json();

            this._cache.set(cacheKey, data);
            this.emit('entry-coverage-loaded', data);

            return data;
        } catch (error) {
            console.error('Failed to check entry coverage:', error);
            return { available: false, error: error.message };
        }
    }

    /**
     * Get lemmas missing coverage in a workset
     */
    async getMissingLemmas(worksetId = this.worksetId) {
        try {
            const response = await fetch(
                `${this.apiBase}/coverage/workset/${worksetId}/missing`
            );
            return await response.json();
        } catch (error) {
            console.error('Failed to get missing lemmas:', error);
            return { count: 0, missing_lemmas: [] };
        }
    }

    // =====================================================================
    // Enrichment API
    // =====================================================================

    /**
     * Get enrichment proposals for a lemma
     */
    async getEnrichments(lemma, options = {}) {
        const {
            pos = null,
            includeExamples = true,
            max = 20
        } = options;

        const cacheKey = `enrich:${lemma}:${pos || ''}`;
        if (this._cache.has(cacheKey)) {
            return this._cache.get(cacheKey);
        }

        try {
            const params = new URLSearchParams({ lemma, include_examples: includeExamples, max });
            if (pos) params.append('pos', pos);

            const response = await fetch(
                `${this.apiBase}/enrich/${lemma}?${params}`
            );
            const data = await response.json();

            if (data.available) {
                this._cache.set(cacheKey, data);
                this.emit('enrichments-loaded', data);
            }

            return data;
        } catch (error) {
            console.error('Failed to get enrichments:', error);
            return { available: false, error: error.message };
        }
    }

    /**
     * Get collocation proposals
     */
    async getCollocations(lemma, options = {}) {
        const { pos = null, minLogdice = 6.0 } = options;

        try {
            const params = new URLSearchParams({ min_logdice: minLogdice });
            if (pos) params.append('pos', pos);

            const response = await fetch(
                `${this.apiBase}/enrich/${lemma}/collocations?${params}`
            );
            return await response.json();
        } catch (error) {
            console.error('Failed to get collocations:', error);
            return { collocations: [], total: 0 };
        }
    }

    /**
     * Get suggested subentry drafts
     */
    async getSubentryDrafts(lemma, options = {}) {
        const {
            pos = null,
            minLogdice = 7.0,
            max = 10
        } = options;

        try {
            const params = new URLSearchParams({ min_logdice: minLogdice, max });
            if (pos) params.append('pos', pos);

            const response = await fetch(
                `${this.apiBase}/enrich/${lemma}/subentries?${params}`
            );
            return await response.json();
        } catch (error) {
            console.error('Failed to get subentry drafts:', error);
            return { drafts: [], total: 0 };
        }
    }

    /**
     * Get example sentences with translations
     */
    async getExamples(lemma, collocate = null, limit = 10) {
        try {
            const params = new URLSearchParams({ limit });
            if (collocate) params.append('collocate', collocate);

            const response = await fetch(
                `${this.apiBase}/enrich/${lemma}/examples?${params}`
            );
            return await response.json();
        } catch (error) {
            console.error('Failed to get examples:', error);
            return { examples: [], total: 0 };
        }
    }

    /**
     * Draft a subentry from collocation data
     */
    async draftSubentry(parentLemma, collocate, relation, relationName, examples) {
        try {
            const response = await fetch(`${this.apiBase}/draft-subentry`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lemma: parentLemma,
                    collocate: collocate,
                    relation: relation,
                    relation_name: relationName,
                    examples: examples
                })
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to draft subentry:', error);
            return { ready_for_review: false, error: error.message };
        }
    }

    // =====================================================================
    // Word Sketch API
    // =====================================================================

    /**
     * Get word sketch for a lemma
     */
    async getWordSketch(lemma, options = {}) {
        const { pos = null, minLogdice = 0, limit = 10 } = options;

        try {
            const params = new URLSearchParams({ lemma, limit, min_logdice: minLogdice });
            if (pos) params.append('pos', pos);

            const response = await fetch(
                `${this.apiBase}/sketch/${lemma}?${params}`
            );
            return await response.json();
        } catch (error) {
            console.error('Failed to get word sketch:', error);
            return { available: false };
        }
    }

    /**
     * Get available grammatical relations
     */
    async getRelations() {
        try {
            const response = await fetch(`${this.apiBase}/relations`);
            return await response.json();
        } catch (error) {
            console.error('Failed to get relations:', error);
            return { available: false, relations: {} };
        }
    }

    // =====================================================================
    // UI Rendering Helpers
    // =====================================================================

    /**
     * Render coverage badge for an entry
     */
    renderCoverageBadge(coverage) {
        if (!coverage.available) {
            return `<span class="badge bg-secondary" title="Word sketch service unavailable">
                <i class="bi bi-question-circle"></i> Unknown
            </span>`;
        }

        if (!coverage.has_coverage) {
            return `<span class="badge bg-danger" title="No corpus coverage found">
                <i class="bi bi-x-circle"></i> No Coverage
            </span>`;
        }

        const score = coverage.coverage_score || 0;
        let badgeClass = 'bg-success';
        let icon = 'bi-check-circle';

        if (score < 0.7) {
            badgeClass = 'bg-warning';
            icon = 'bi-exclamation-triangle';
        }
        if (score < 0.4) {
            badgeClass = 'bg-danger';
        }

        return `<span class="badge ${badgeClass}" title="Coverage score: ${(score * 100).toFixed(0)}%">
            <i class="bi ${icon}"></i> ${(score * 100).toFixed(0)}%
        </span>`;
    }

    /**
     * Render enrichment panel for an entry
     */
    renderEnrichmentPanel(enrichments, options = {}) {
        const { collapsible = true } = options;

        if (!enrichments.available || !enrichments.proposals || enrichments.proposals.length === 0) {
            return `
                <div class="alert alert-info mb-0">
                    <i class="bi bi-info-circle"></i>
                    ${enrichments.available === false
                        ? 'Word sketch service unavailable'
                        : 'No enrichment suggestions available'}
                </div>
            `;
        }

        const collocations = enrichments.proposals.filter(p => p.type === 'collocate');
        const examples = enrichments.proposals.filter(p => p.type === 'example');

        let html = `
            <div class="enrichment-panel">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="mb-0">
                        <i class="bi bi-magic"></i> Enrichment Suggestions
                        <span class="badge bg-secondary ms-1">${enrichments.total}</span>
                    </h6>
                </div>
        `;

        if (collocations.length > 0) {
            html += `
                <div class="mb-3">
                    <h6 class="small text-muted mb-2">Top Collocations</h6>
                    <div class="collocations-list">
                        ${collocations.slice(0, 5).map(c => `
                            <div class="d-flex justify-content-between align-items-center py-1 border-bottom">
                                <div>
                                    <span class="fw-bold">${c.value}</span>
                                    <small class="text-muted ms-1">${c.relation_name || c.relation}</small>
                                </div>
                                <div class="d-flex align-items-center gap-2">
                                    <div class="progress" style="width: 60px; height: 6px;">
                                        <div class="progress-bar" style="width: ${c.confidence * 100}%"></div>
                                    </div>
                                    <small class="text-muted">${(c.confidence * 100).toFixed(0)}%</small>
                                    <button class="btn btn-sm btn-outline-primary add-collate"
                                            data-lemma="${enrichments.lemma}"
                                            data-collocate="${c.value}"
                                            data-relation="${c.relation}"
                                            data-relation-name="${c.relation_name || ''}"
                                            title="Add as collocation">
                                        <i class="bi bi-plus"></i>
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        if (examples.length > 0) {
            html += `
                <div>
                    <h6 class="small text-muted mb-2">Example Sentences</h6>
                    <div class="examples-list">
                        ${examples.slice(0, 3).map(e => `
                            <div class="example-item py-1 border-bottom">
                                <small>"${e.value}"</small>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        html += '</div>';
        return html;
    }

    /**
     * Render coverage report summary for a workset
     */
    renderCoverageSummary(report) {
        if (!report.available) {
            return `
                <div class="alert alert-secondary">
                    <i class="bi bi-wifi-off"></i> Word sketch service unavailable
                </div>
            `;
        }

        const coverage = report.coverage_percentage || 0;
        const missing = report.missing_count || 0;
        const needsEnrichment = report.needs_enrichment_count || 0;

        let statusClass = 'bg-success';
        let statusText = 'Well Covered';

        if (coverage < 70) {
            statusClass = 'bg-warning';
            statusText = 'Partial Coverage';
        }
        if (coverage < 40) {
            statusClass = 'bg-danger';
            statusText = 'Poor Coverage';
        }

        return `
            <div class="coverage-summary">
                <div class="row align-items-center">
                    <div class="col-md-4">
                        <div class="d-flex align-items-center gap-3">
                            <div class="coverage-score ${statusClass}" style="width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 1.2rem;">
                                ${coverage.toFixed(0)}%
                            </div>
                            <div>
                                <div class="fw-bold">${statusText}</div>
                                <small class="text-muted">${report.covered_entries} of ${report.total_entries} entries</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-8">
                        <div class="row text-center">
                            <div class="col-4">
                                <div class="h4 mb-0 text-danger">${missing}</div>
                                <small class="text-muted">Missing Coverage</small>
                            </div>
                            <div class="col-4">
                                <div class="h4 mb-0 text-warning">${needsEnrichment}</div>
                                <small class="text-muted">Need Enrichment</small>
                            </div>
                            <div class="col-4">
                                <div class="h4 mb-0 text-success">${report.total_entries - missing - needsEnrichment}</div>
                                <small class="text-muted">Well Covered</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // =====================================================================
    // Cache Management
    // =====================================================================

    clearCache() {
        this._cache.clear();
        this.emit('cache-cleared');
    }

    clearCacheForLemma(lemma) {
        for (const key of this._cache.keys()) {
            if (key.includes(lemma)) {
                this._cache.delete(key);
            }
        }
    }
}

// Export for use
window.WordSketchIntegration = WordSketchIntegration;
