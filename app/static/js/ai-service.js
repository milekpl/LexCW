/**
 * AI Service Frontend
 *
 * Provides UI for AI-powered proofreading and entry drafting.
 * Communicates with /api/ai/* endpoints.
 */

class AIServiceUI {
    constructor(options = {}) {
        this.options = {
            onProofreadResult: options.onProofreadResult || null,
            onDraftResult: options.onDraftResult || null,
            ...options
        };
        this._initButtons();
    }

    _initButtons() {
        // Proofread button in entry form
        const proofreadBtn = document.getElementById('btn-ai-proofread');
        if (proofreadBtn) {
            proofreadBtn.addEventListener('click', () => this.proofreadCurrentEntry());
        }

        // Draft button
        const draftBtn = document.getElementById('btn-ai-draft');
        if (draftBtn) {
            draftBtn.addEventListener('click', () => this.showDraftModal());
        }

        // POS Tagger button
        const posBtn = document.getElementById('btn-pos-tagger');
        if (posBtn) {
            posBtn.addEventListener('click', () => this.predictPosCurrentEntry());
        }
    }


    /**
     * Gather current entry data from the form (via EtymologyFormsManager, etc.)
     */
    gatherEntryData() {
        const data = {};

        // Lexical unit
        data.lexical_unit = {};
        document.querySelectorAll('[name^="lexical_unit."]').forEach(input => {
            const name = input.name;
            const match = name.match(/lexical_unit\.(.+)/);
            if (match && input.value.trim()) {
                data.lexical_unit[match[1]] = input.value.trim();
            }
        });

        // Grammatical info
        const posSelect = document.querySelector('[name="grammatical_info"]');
        if (posSelect && posSelect.value) {
            data.grammatical_info = posSelect.value;
        }

        // Senses
        data.senses = [];
        document.querySelectorAll('.sense-item').forEach((item, i) => {
            const sense = { definitions: {}, examples: [] };
            const posEl = item.querySelector(`[name="senses[${i}][grammatical_info]"]`);
            if (posEl && posEl.value) sense.grammatical_info = posEl.value;

            // Definitions by language
            item.querySelectorAll('[name^="senses[' + i + '][definitions]"]').forEach(input => {
                const match = input.name.match(/senses\[\d+\]\[definitions\]\[(.+)\]/);
                if (match && input.value.trim()) {
                    sense.definitions[match[1]] = input.value.trim();
                }
            });

            if (Object.keys(sense.definitions).length > 0) {
                data.senses.push(sense);
            }
        });

        // Pronunciations
        data.pronunciations = {};
        document.querySelectorAll('[name^="pronunciations["]').forEach(input => {
            const match = input.name.match(/pronunciations\[(\d+)\]\.value/);
            if (match && input.value.trim()) {
                data.pronunciations['seh-fonipa'] = input.value.trim();
            }
        });

        // Etymology (Alpine-owned since §13)
        var etymEl = document.querySelector('[x-data^="etymology"]');
        if (etymEl && window.Alpine) {
            var etymData = window.Alpine.$data(etymEl);
            if (etymData && etymData.items) {
                data.etymologies = JSON.parse(JSON.stringify(etymData.items));
            }
        }

        return data;
    }

    async predictPosCurrentEntry() {
        const entryData = this.gatherEntryData();
        const resultsPanel = document.getElementById('ai-results-panel');
        if (!resultsPanel) return;

        resultsPanel.innerHTML = '<div class="spinner-border spinner-border-sm text-success" role="status"></div> Predicting POS...';

        try {
            const resp = await fetch('/api/pos/tag-entry', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ entry: entryData })
            });
            const data = await resp.json();
            if (data.success && data.prediction) {
                const pred = data.prediction;
                const posVal = pred.predicted_pos;
                const confPct = Math.round((pred.confidence || 0.8) * 100);
                resultsPanel.innerHTML = `
                    <div class="alert alert-success mt-2 py-2 mb-0 d-flex align-items-center justify-content-between">
                        <div>
                            <strong>Predicted POS:</strong> <span class="badge bg-success">${posVal}</span> (${confPct}% confidence via ${pred.method || 'smart tagger'})
                        </div>
                        <button type="button" class="btn btn-sm btn-success py-0" id="btn-apply-predicted-pos">Apply</button>
                    </div>
                `;
                document.getElementById('btn-apply-predicted-pos')?.addEventListener('click', () => {
                    const posSelect = document.querySelector('[name="grammatical_info"]') || document.querySelector('[name="pos"]');
                    if (posSelect) {
                        posSelect.value = posVal;
                        posSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
            } else {
                resultsPanel.innerHTML = `<div class="alert alert-warning mt-2 py-1 mb-0">${data.error || 'Could not predict POS'}</div>`;
            }
        } catch (err) {
            resultsPanel.innerHTML = `<div class="alert alert-danger mt-2 py-1 mb-0">POS prediction error: ${err.message}</div>`;
        }
    }


    /**
     * Proofread the current entry in the form.
     */
    async proofreadCurrentEntry() {
        const btn = document.getElementById('btn-ai-proofread');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
        }

        try {
            const entryData = this.gatherEntryData();
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

            const response = await fetch('/api/ai/proofread', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({ entry_data: entryData })
            });

            const result = await response.json();

            if (response.ok) {
                this.showProofreadResults(result);
            } else {
                this.showError(result.error || 'Proofreading failed');
            }
        } catch (e) {
            console.error('AI proofread error:', e);
            this.showError('Network error during proofreading');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-robot"></i> AI Proofread';
            }
        }
    }

    /**
     * Display proofreading results in a panel.
     */
    showProofreadResults(result) {
        // Remove existing panel
        const existing = document.getElementById('ai-results-panel');
        if (existing) existing.remove();

        const issues = result.issues || result.suggestions || [];
        const summary = result.summary || '';

        const panel = document.createElement('div');
        panel.id = 'ai-results-panel';
        panel.className = 'card mt-3 border-info';
        panel.innerHTML = `
            <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
                <span><i class="fas fa-robot"></i> AI Proofreading Results</span>
                <button type="button" class="btn-close btn-close-white" onclick="document.getElementById('ai-results-panel').remove()"></button>
            </div>
            <div class="card-body">
                ${summary ? `<p class="fw-bold">${this._escapeHtml(summary)}</p>` : ''}
                ${issues.length === 0 ? '<p class="text-success"><i class="fas fa-check-circle"></i> No issues found!</p>' : ''}
                <div class="list-group">
                    ${issues.map((issue, i) => {
                        const hasFix = issue.corrected_text && issue.corrected_text.trim();
                        return `
                        <div class="list-group-item list-group-item-${issue.severity === 'error' ? 'danger' : issue.severity === 'warning' ? 'warning' : 'info'}">
                            <div class="d-flex justify-content-between align-items-start">
                                <div class="flex-grow-1">
                                    <div class="d-flex justify-content-between">
                                        <strong>${this._escapeHtml(issue.field || 'general')}</strong>
                                        <span class="badge bg-${issue.severity === 'error' ? 'danger' : issue.severity === 'warning' ? 'warning' : 'secondary'}">${issue.severity || 'info'}</span>
                                    </div>
                                    <p class="mb-1">${this._escapeHtml(issue.message || '')}</p>
                                    ${issue.suggestion ? `<small class="text-muted d-block">${this._escapeHtml(issue.suggestion)}</small>` : ''}
                                    ${hasFix ? `<small class="text-primary d-block mt-1"><strong>Corrected:</strong> ${this._escapeHtml(issue.corrected_text)}</small>` : ''}
                                </div>
                                ${hasFix ? `
                                <button type="button" class="btn btn-sm btn-outline-success ms-2 apply-fix-btn"
                                        data-field="${this._escapeAttr(issue.field)}"
                                        data-value="${this._escapeAttr(issue.corrected_text)}"
                                        title="Apply this fix">
                                    <i class="fas fa-check"></i> Apply
                                </button>` : ''}
                            </div>
                        </div>`;
                    }).join('')}
                </div>
            </div>
        `;

        // Wire Apply buttons
        panel.querySelectorAll('.apply-fix-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const field = btn.dataset.field;
                const value = btn.dataset.value;
                if (this._applyFix(field, value)) {
                    btn.classList.remove('btn-outline-success');
                    btn.classList.add('btn-success');
                    btn.innerHTML = '<i class="fas fa-check"></i> Applied';
                    btn.disabled = true;
                } else {
                    btn.classList.add('btn-outline-danger');
                    btn.innerHTML = '<i class="fas fa-times"></i> Field not found';
                }
            });
        });
        const form = document.querySelector('#entry-form');
        if (form) {
            form.insertAdjacentElement('afterend', panel);
        } else {
            this.container?.appendChild(panel);
        }
    }

    /**
     * Show the AI Draft modal.
     */
    showDraftModal() {
        const existing = document.getElementById('aiDraftModal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'aiDraftModal';
        modal.className = 'modal fade';
        modal.tabIndex = -1;
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title"><i class="fas fa-magic"></i> AI Draft Entry</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Word or phrase to draft an entry for</label>
                            <input type="text" class="form-control" id="ai-draft-description"
                                   placeholder="e.g., 'ephemeral' or 'a type of traditional Polish dance'">
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">Source language</label>
                                <input type="text" class="form-control" id="ai-draft-source-lang" value="en" maxlength="10">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Target language(s)</label>
                                <input type="text" class="form-control" id="ai-draft-target-langs" value="pl,en" maxlength="50">
                            </div>
                        </div>
                        <div id="ai-draft-result" class="border rounded p-3 bg-light" style="display:none; max-height: 400px; overflow-y: auto;">
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" id="btn-ai-draft-generate">
                            <i class="fas fa-wand-magic-sparkles"></i> Generate
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        modal.addEventListener('hidden.bs.modal', () => modal.remove());

        // Generate button
        modal.querySelector('#btn-ai-draft-generate').addEventListener('click', async () => {
            await this.generateDraft(modal);
        });
    }

    async generateDraft(modal) {
        const description = modal.querySelector('#ai-draft-description').value.trim();
        const sourceLang = modal.querySelector('#ai-draft-source-lang').value.trim() || 'en';
        const targetLangs = modal.querySelector('#ai-draft-target-langs').value.trim() || 'en';
        const resultDiv = modal.querySelector('#ai-draft-result');
        const genBtn = modal.querySelector('#btn-ai-draft-generate');

        if (!description) {
            this.showError('Please enter a word or phrase');
            return;
        }

        genBtn.disabled = true;
        genBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div><p class="mt-2">AI is drafting...</p></div>';

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
            const response = await fetch('/api/ai/draft', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({
                    description,
                    source_lang: sourceLang,
                    target_langs: targetLangs
                })
            });

            const result = await response.json();

            if (response.ok) {
                resultDiv.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <strong>Generated Entry:</strong>
                        <button type="button" class="btn btn-sm btn-success" id="btn-apply-draft">
                            <i class="fas fa-check"></i> Apply to Form
                        </button>
                    </div>
                    ${result.notes ? `<p class="text-muted small">${this._escapeHtml(result.notes)}</p>` : ''}
                    <pre class="bg-white p-3 rounded border" style="font-size: 0.85em; white-space: pre-wrap;">${this._escapeHtml(result.entry_yaml || JSON.stringify(result.entry_data || {}, null, 2))}</pre>
                `;

                // Apply button
                const applyBtn = resultDiv.querySelector('#btn-apply-draft');
                if (applyBtn && result.entry_data) {
                    applyBtn.addEventListener('click', () => {
                        this.applyDraftedEntry(result.entry_data);
                        const bsModal = bootstrap.Modal.getInstance(modal);
                        if (bsModal) bsModal.hide();
                    });
                }
            } else {
                resultDiv.innerHTML = `<div class="alert alert-danger">${this._escapeHtml(result.error || 'Drafting failed')}</div>`;
            }
        } catch (e) {
            console.error('AI draft error:', e);
            resultDiv.innerHTML = '<div class="alert alert-danger">Network error during drafting</div>';
        } finally {
            genBtn.disabled = false;
            genBtn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> Generate';
        }
    }

    /**
     * Apply a drafted entry to the form (populate basic fields).
     */
    applyDraftedEntry(entryData) {
        // Lexical unit
        if (entryData.lexical_unit) {
            Object.entries(entryData.lexical_unit).forEach(([lang, text]) => {
                const input = document.querySelector(`[name="lexical_unit.${lang}"]`);
                if (input) input.value = text;
            });
        }

        // Grammatical info
        if (entryData.senses && entryData.senses[0] && entryData.senses[0].grammatical_info) {
            const posSelect = document.querySelector('[name="grammatical_info"]');
            if (posSelect) {
                const options = Array.from(posSelect.options);
                const match = options.find(o => o.value === entryData.senses[0].grammatical_info || o.text === entryData.senses[0].grammatical_info);
                if (match) posSelect.value = match.value;
            }
        }

        // Definitions (first sense, first language)
        if (entryData.senses && entryData.senses[0] && entryData.senses[0].definitions) {
            Object.entries(entryData.senses[0].definitions).forEach(([lang, text]) => {
                const input = document.querySelector(`[name="senses[0][definitions][${lang}]"]`);
                if (input) input.value = text;
            });
        }
    }

    showError(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show mt-2';
        alert.innerHTML = `${message} <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
        const form = document.querySelector('#entry-form');
        if (form) {
            form.parentNode?.insertBefore(alert, form);
        }
        setTimeout(() => alert.remove(), 6000);
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    _escapeAttr(str) {
        return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    /**
     * Apply a corrected value to a form field based on the AI's field path.
     * Maps common field paths to form element selectors.
     */
    _applyFix(field, value) {
        if (!field || !value) return false;

        // Try to find the form element by matching common field path patterns
        const selectors = this._fieldPathToSelectors(field);

        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) {
                if (el.tagName === 'SELECT') {
                    // Try to find an option matching the value
                    const options = Array.from(el.options);
                    const match = options.find(o =>
                        o.value === value || o.textContent.trim() === value
                    );
                    if (match) {
                        el.value = match.value;
                    } else {
                        el.value = value; // Set raw value (may not be valid)
                    }
                } else {
                    el.value = value;
                }
                // Trigger input/change events so other JS handlers notice
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                // Scroll to the field
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                el.focus();
                return true;
            }
        }
        return false;
    }

    /**
     * Convert an AI field path to possible CSS selectors for form elements.
     * Examples:
     *   "lexical_unit.en" → [name="lexical_unit.en"]
     *   "senses[0].definitions.en" → [name="senses[0][definitions][en]"], [name^="senses[0][definitions][en]"]
     *   "grammatical_info" → [name="grammatical_info"]
     *   "pronunciation.seh-fonipa" → [name^="pronunciations["]
     */
    _fieldPathToSelectors(field) {
        const selectors = [];

        // Direct name match
        selectors.push(`[name="${field}"]`);

        // Handle dotted paths like "lexical_unit.en"
        if (field.includes('.')) {
            const parts = field.split('.');
            // Try the first part as a name
            selectors.push(`[name="${parts[0]}.${parts.slice(1).join('.')}"]`);
        }

        // Handle bracket paths like "senses[0].definitions.en"
        const bracketMatch = field.match(/^(\w+)\[(\d+)\]\.(.+)$/);
        if (bracketMatch) {
            const [, base, idx, rest] = bracketMatch;
            const bracketName = `${base}[${idx}][${rest.replace(/\./g, '][')}]`;
            selectors.push(`[name="${bracketName}"]`);
            selectors.push(`[name^="${bracketName}"]`);
        }

        // Handle "pronunciation.seh-fonipa" → look for pronunciation value inputs
        if (field.startsWith('pronunciation.')) {
            selectors.push('[name^="pronunciations["]');
        }

        // Handle "grammatical_info" at entry level
        if (field === 'grammatical_info') {
            selectors.push('[name="grammatical_info"]');
        }

        return selectors;
    }
}

window.AIServiceUI = AIServiceUI;
