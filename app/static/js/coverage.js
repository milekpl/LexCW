/**
 * Coverage Checker — frontend JS for /coverage page.
 * Communicates with /api/coverage/* endpoints.
 */

(function() {
    'use strict';

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    function apiHeaders() {
        return {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        };
    }

    function getLanguage() {
        return document.getElementById('language-select').value;
    }

    function getTargetLanguage() {
        return document.getElementById('target-language-select').value;
    }

    function showError(containerId, message) {
        const el = document.getElementById(containerId);
        el.classList.remove('d-none');
        el.innerHTML = `<div class="alert alert-danger">${message}</div>`;
    }

    // --- Resource Coverage ---
    document.getElementById('resource-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const file = document.getElementById('resource-file').files[0];
        const resourceType = document.getElementById('resource-type').value;
        if (!file) return;

        // Determine upload endpoint based on resource type
        let endpoint = '/api/coverage/resource';
        if (resourceType === 'clsf') {
            endpoint = '/api/coverage/import-clsf';
        } else if (resourceType === 'dante') {
            endpoint = '/api/coverage/import-dante';
        }

        const formData = new FormData();
        formData.append('file', file);
        if (resourceType === 'text' || resourceType === 'subtlex') {
            formData.append('resource_type', resourceType);
            formData.append('language', getLanguage());
            const tl = getTargetLanguage();
            if (tl) formData.append('target_language', tl);
        }

        try {
            const resp = await fetch(endpoint, {
                method: 'POST',
                body: formData,
            });
            const data = await resp.json();
            if (data.error) {
                showError('resource-results', data.error);
                return;
            }
            renderResourceResults(data);
        } catch (err) {
            showError('resource-results', err.message);
        }
    });

    function renderResourceResults(data) {
        const resultsDiv = document.getElementById('resource-results');
        resultsDiv.classList.remove('d-none');
        
        // Handle CLSF/DANTE import results (different from text/subtlex)
        if (data.metadata) {
            const meta = data.metadata;
            document.getElementById('resource-summary').textContent = 
                `${meta.name || 'Imported'} — ${data.entry_count || 0} entries`;
            
            const tbody = document.getElementById('resource-table-body');
            tbody.innerHTML = '';
            
            // Show metadata summary
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="4">
                <div class="p-3">
                    <h6>${escapeHtml(meta.name || 'Resource')}</h6>
                    <p class="mb-1"><small class="text-muted">${escapeHtml(meta.description || '')}</small></p>
                    <p class="mb-1"><small><strong>Language:</strong> ${escapeHtml(meta.language || '-')}</small></p>
                    <p class="mb-1"><small><strong>Version:</strong> ${escapeHtml(meta.version || '-')}</small></p>
                    ${data.senses_count ? `<p class="mb-1"><small><strong>Senses:</strong> ${data.senses_count}</small></p>` : ''}
                </div>
            </td>`;
            tbody.appendChild(tr);
            return;
        }
        
        document.getElementById('resource-summary').textContent = `${data.entry_count} entries`;

        const tbody = document.getElementById('resource-table-body');
        tbody.innerHTML = '';
        for (const entry of data.entries) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${escapeHtml(entry.headword)}</strong></td>
                <td>${escapeHtml(entry.part_of_speech || '')}</td>
                <td>${(entry.senses || []).length}</td>
                <td>${(entry.senses || []).flatMap(s => s.translations || []).slice(0, 3).join(', ')}</td>
            `;
            tbody.appendChild(tr);
        }
    }

    // --- Text Coverage ---
    document.getElementById('text-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const text = document.getElementById('text-input').value.trim();
        if (!text) return;

        try {
            const resp = await fetch('/api/coverage/text', {
                method: 'POST',
                headers: apiHeaders(),
                body: JSON.stringify({
                    text: text,
                    language: getLanguage(),
                    target_language: getTargetLanguage() || null,
                }),
            });
            const data = await resp.json();
            if (data.error) {
                showError('text-results', data.error);
                return;
            }
            renderTextResults(data);
        } catch (err) {
            showError('text-results', err.message);
        }
    });

    function renderTextResults(data) {
        const resultsDiv = document.getElementById('text-results');
        resultsDiv.classList.remove('d-none');
        document.getElementById('text-summary').textContent = `${data.entry_count} unique lemmas from ${data.input_length} chars`;

        const tbody = document.getElementById('text-table-body');
        tbody.innerHTML = '';
        for (const entry of data.entries) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${escapeHtml(entry.headword)}</strong></td>
                <td>${escapeHtml(entry.part_of_speech || '')}</td>
                <td>${(entry.senses || []).length > 0 ? (entry.senses[0].examples || []).length : 0}</td>
            `;
            tbody.appendChild(tr);
        }
    }

    // --- Systematicity ---
    document.getElementById('run-systematicity').addEventListener('click', async function() {
        try {
            const resp = await fetch(`/api/coverage/systematicity?language=${getLanguage()}`);
            const data = await resp.json();
            if (data.error) {
                showError('systematicity-results', data.error);
                return;
            }
            renderSystematicityResults(data);
        } catch (err) {
            showError('systematicity-results', err.message);
        }
    });

    function renderSystematicityResults(data) {
        const container = document.getElementById('systematicity-results');
        if (!data.checks || data.checks.length === 0) {
            container.innerHTML = `<p class="text-muted">${data.message || 'No checks available.'}</p>`;
            if (data.categories) {
                container.innerHTML += '<h6>Available categories:</h6><ul class="list-group">';
                for (const cat of data.categories) {
                    container.innerHTML += `<li class="list-group-item">${escapeHtml(cat)}</li>`;
                }
                container.innerHTML += '</ul>';
            }
            return;
        }

        let html = `<div class="mb-3"><strong>Overall Coverage:</strong> ${data.overall_coverage.toFixed(1)}%</div>`;
        html += '<div class="table-responsive"><table class="table table-sm table-striped">';
        html += '<thead><tr><th>Category</th><th>Ref</th><th>Found</th><th>Missing</th><th>Coverage</th><th></th></tr></thead><tbody>';

        for (const check of data.checks) {
            const badge = check.coverage_percent >= 90 ? 'bg-success' :
                          check.coverage_percent >= 70 ? 'bg-warning' : 'bg-danger';
            const collapseId = `missing-${check.category.replace(/[^a-z0-9]/gi, '-')}`;
            html += `<tr>
                <td>${escapeHtml(check.category)}</td>
                <td>${check.reference_count}</td>
                <td>${check.found_count}</td>
                <td>${check.missing_count}</td>
                <td><span class="badge ${badge}">${check.coverage_percent.toFixed(1)}%</span></td>
                <td>`;
            if (check.missing_count > 0 && check.missing_items && check.missing_items.length > 0) {
                html += `<button class="btn btn-sm btn-outline-danger" type="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}" aria-expanded="false">
                    ${check.missing_count} missing
                </button>`;
            }
            html += `</td></tr>`;
            if (check.missing_count > 0 && check.missing_items && check.missing_items.length > 0) {
                html += `<tr><td colspan="6" class="p-0"><div id="${collapseId}" class="collapse"><div class="px-3 py-2 bg-light">
                    <strong>Missing items (${check.missing_items.length}${check.missing_count > check.missing_items.length ? ' of ' + check.missing_count : ''}):</strong>
                    <div class="mt-1">${check.missing_items.map(item => `<a href="/entries/add?headword=${encodeURIComponent(item)}" class="badge bg-danger text-decoration-none me-1 mb-1" title="Add entry: ${escapeHtml(item)}">${escapeHtml(item)}</a>`).join('')}</div>
                    ${check.missing_count > check.missing_items.length ? `<small class="text-muted">...and ${check.missing_count - check.missing_items.length} more</small>` : ''}
                </div></div></td></tr>`;
            }
        }
        html += '</tbody></table></div>';
        container.innerHTML = html;
    }

    // --- Sense Alignment ---
    document.getElementById('run-alignment').addEventListener('click', async function() {
        const low = document.getElementById('threshold-low').value;
        const high = document.getElementById('threshold-high').value;

        try {
            const resp = await fetch(`/api/coverage/alignment?language=${getLanguage()}&target_language=${getTargetLanguage()}&threshold_low=${low}&threshold_high=${high}`);
            const data = await resp.json();
            if (data.error) {
                showError('alignment-results', data.error);
                return;
            }
            renderAlignmentResults(data);
        } catch (err) {
            showError('alignment-results', err.message);
        }
    });

    function renderAlignmentResults(data) {
        const resultsDiv = document.getElementById('alignment-results');
        resultsDiv.classList.remove('d-none');
        document.getElementById('alignment-summary').textContent =
            `${data.flagged_count} flagged / ${data.total_checked} checked`;

        const tbody = document.getElementById('alignment-table-body');
        tbody.innerHTML = '';

        if (!data.words || data.words.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-muted">${escapeHtml(data.message || 'No data')}</td></tr>`;
            return;
        }

        for (const w of data.words) {
            const statusBadge = w.status === 'ok' ? 'bg-success' :
                               w.status === 'split_candidate' ? 'bg-info' :
                               w.status === 'merge_candidate' ? 'bg-warning' : 'bg-secondary';
            const tr = document.createElement('tr');

            // Expandable per-sense details
            const perSenseHtml = w.per_sense && w.per_sense.length > 0 ?
                `<div class="mt-2 ps-3 border-start border-2 border-secondary">
                    <small class="text-muted">Per-sense matching:</small>
                    ${w.per_sense.map(ps => {
                        const badge = ps.matched ?
                            '<span class="badge bg-success">✓ Matched</span>' :
                            '<span class="badge bg-danger">✗ No match</span>';
                        return `<div class="mb-1 small">
                            ${badge}
                            <span class="text-muted">Dict:</span> ${escapeHtml(ps.dict_definition.substring(0, 80))}
                            ${ps.matched ? `<span class="text-muted">→</span> <span class="text-success">${escapeHtml(ps.wn_definition.substring(0, 80))}</span>` : ''}
                        </div>`;
                    }).join('')}
                </div>` : '';

            tr.innerHTML = `
                <td><strong>${escapeHtml(w.headword)}</strong></td>
                <td>${w.dict_count}</td>
                <td>${w.wn_count}</td>
                <td>${w.ratio}</td>
                <td><span class="badge ${statusBadge}">${escapeHtml(w.status)}</span></td>
            `;
            tr.style.cursor = 'pointer';
            tr.addEventListener('click', function() {
                const details = this.nextElementSibling;
                if (details && details.tagName === 'TR') {
                    details.classList.toggle('d-none');
                }
            });
            tbody.appendChild(tr);

            // Expandable row for per-sense details
            if (perSenseHtml) {
                const detailsTr = document.createElement('tr');
                detailsTr.classList.add('d-none');
                detailsTr.innerHTML = `<td colspan="5">${perSenseHtml}</td>`;
                tbody.appendChild(detailsTr);
            }
        }
    }

    // --- WordNet Lookup ---
    document.getElementById('wordnet-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const word = document.getElementById('wordnet-word').value.trim();
        if (!word) return;

        try {
            const resp = await fetch(`/api/coverage/wordnet/${encodeURIComponent(word)}?language=${getLanguage()}&target_language=${getTargetLanguage()}`);
            const data = await resp.json();
            if (data.error) {
                showError('wordnet-results', data.error);
                return;
            }
            renderWordnetResults(data);
        } catch (err) {
            showError('wordnet-results', err.message);
        }
    });

    function renderWordnetResults(data) {
        const resultsDiv = document.getElementById('wordnet-results');
        resultsDiv.classList.remove('d-none');

        if (!data.entry) {
            document.getElementById('wordnet-results-header').textContent = `WordNet: ${data.word}`;
            document.getElementById('wordnet-results-body').innerHTML =
                '<p class="text-muted">No synsets found for this word.</p>';
            return;
        }

        document.getElementById('wordnet-results-header').textContent =
            `WordNet: ${data.word} (${data.synset_count} synsets)`;

        // Show coverage summary if available
        let summaryHtml = '';
        if (data.coverage_status) {
            const cs = data.coverage_status;
            if (cs.not_compared_count > 0) {
                summaryHtml = `<div class="alert alert-info mb-3">Dictionary not available for comparison</div>`;
            } else {
                const covered = cs.covered_count;
                const missing = cs.missing_count;
                const total = covered + missing;
                const pct = total > 0 ? Math.round(covered / total * 100) : 0;
                const color = pct >= 80 ? 'success' : pct >= 50 ? 'warning' : 'danger';
                summaryHtml = `<div class="alert alert-${color} mb-3">
                    Dictionary coverage: ${covered}/${total} synsets matched (${pct}%)
                </div>`;
            }
        }

        let html = '<div class="list-group">';
        for (const sense of data.entry.senses) {
            const domain = sense.semantic_domain ? `<span class="badge bg-secondary me-1">${escapeHtml(sense.semantic_domain)}</span>` : '';
            const trans = (sense.translations || []).length > 0 ?
                `<br><small class="text-muted">Translations: ${sense.translations.map(t => escapeHtml(typeof t === 'string' ? t : String(t))).join(', ')}</small>` : '';
            const examples = (sense.examples || []).length > 0 ?
                `<br><small class="text-muted fst-italic">${sense.examples.map(e => {
                    var text = typeof e === 'string' ? e
                        : (e && e.languages ? Object.values(e.languages).join('; ')
                        : (e && e.text ? e.text
                        : String(e)));
                    return '"' + escapeHtml(text) + '"';
                }).join('; ')}</small>` : '';

            // Coverage status for this sense
            const coverageInfo = data.coverage_status && data.coverage_status.senses ?
                data.coverage_status.senses.find(s => s.synset_id === sense.id) : null;
            let coverageBadge = '';
            if (coverageInfo) {
                if (coverageInfo.covered === true) {
                    coverageBadge = '<span class="badge bg-success ms-2">✓ Covered</span>';
                } else if (coverageInfo.covered === false) {
                    coverageBadge = '<span class="badge bg-danger ms-2">✗ Missing</span>';
                } else {
                    coverageBadge = '<span class="badge bg-info ms-2">? Not compared</span>';
                }
            }

            html += `<div class="list-group-item">
                <div class="d-flex justify-content-between">
                    <div>${domain}<strong>${escapeHtml(sense.id)}</strong>: ${escapeHtml(sense.definition)}${coverageBadge}</div>
                </div>${trans}${examples}
            </div>`;
        }
        html += '</div>';
        document.getElementById('wordnet-results-body').innerHTML = summaryHtml + html;
    }

    function escapeHtml(str) {
        if (str == null) return '';
        str = String(str);
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // --- WordNet Gap Analysis ---
    let gapCurrentPage = 1;
    let gapPerPage = 50;
    let gapPagination = { page: 1, per_page: 50, total: 0, pages: 0 };
    let gapCurrentData = null;

    document.getElementById('run-gap-analysis').addEventListener('click', async function() {
        const btn = this;
        btn.disabled = true;
        document.getElementById('gap-loading').classList.remove('d-none');
        document.getElementById('gap-summary').classList.add('d-none');
        document.getElementById('gap-filters').classList.add('d-none');
        document.getElementById('gap-pagination').classList.add('d-none');

        try {
            gapCurrentPage = 1;
            await loadGapPage(1, true);  // Force refresh on initial load
        } catch (err) {
            showError('gap-summary', err.message);
        } finally {
            btn.disabled = false;
            document.getElementById('gap-loading').classList.add('d-none');
        }
    });

    async function loadGapPage(page, forceRefresh = false) {
        const search = document.getElementById('gap-search').value.trim();
        const priority = document.getElementById('gap-filter-priority').value;
        const pos = document.getElementById('gap-filter-pos').value;

        const params = new URLSearchParams({
            language: getLanguage(),
            target_language: getTargetLanguage(),
            page: page,
            per_page: gapPerPage,
        });
        if (search) params.append('search', search);
        if (priority) params.append('priority', priority);
        if (pos) params.append('pos', pos);
        if (forceRefresh) params.append('refresh', 'true');

        const resp = await fetch(`/api/coverage/wordnet-gap?${params}`);
        const data = await resp.json();
        if (data.error) {
            showError('gap-summary', data.error);
            return;
        }

        gapCurrentData = data;
        gapPagination = data.pagination;
        gapCurrentPage = page;

        renderGapAnalysis(data);
    }

    document.getElementById('gap-apply-filters').addEventListener('click', () => {
        gapCurrentPage = 1;
        loadGapPage(1);
    });

    document.getElementById('gap-clear-filters').addEventListener('click', () => {
        document.getElementById('gap-search').value = '';
        document.getElementById('gap-filter-priority').value = '';
        document.getElementById('gap-filter-pos').value = '';
        gapCurrentPage = 1;
        loadGapPage(1);
    });

    // Pagination handlers
    document.getElementById('gap-pagination').addEventListener('click', async function(e) {
        e.preventDefault();
        const pageLink = e.target.closest('.page-link');
        if (!pageLink) return;

        const action = pageLink.dataset.page;
        let newPage = gapCurrentPage;
        if (action === 'prev' && gapCurrentPage > 1) {
            newPage = gapCurrentPage - 1;
        } else if (action === 'next' && gapCurrentPage < gapPagination.pages) {
            newPage = gapCurrentPage + 1;
        }

        if (newPage !== gapCurrentPage) {
            await loadGapPage(newPage);
        }
    });

    function renderGapAnalysis(data) {
        const summary = data.summary || {};
        document.getElementById('gap-summary').classList.remove('d-none');
        document.getElementById('gap-filters').classList.remove('d-none');

        document.getElementById('gap-headword-coverage').textContent =
            summary.headword_coverage ? `${summary.headword_coverage.toFixed(1)}%` : '-';
        document.getElementById('gap-sense-coverage').textContent =
            summary.sense_coverage ? `${summary.sense_coverage.toFixed(1)}%` : '-';
        document.getElementById('gap-missing-hw').textContent = data.missing_headwords_total || 0;
        document.getElementById('gap-total-hw').textContent = summary.total_headwords_baseline || 0;

        // Pagination info
        const start = ((gapCurrentPage - 1) * gapPerPage) + 1;
        const end = Math.min(gapCurrentPage * gapPerPage, data.missing_headwords_total);
        document.getElementById('gap-pagination-info').textContent =
            `${start}-${end} of ${data.missing_headwords_total}`;

        // Missing headwords table
        const missingHw = data.missing_headwords || [];
        const tbody = document.getElementById('gap-missing-hw-body');
        tbody.innerHTML = '';

        if (missingHw.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center">No missing headwords match the current filters</td></tr>';
        } else {
            for (const hw of missingHw) {
                const priorityBadge = hw.priority === 'high' ? 'bg-danger' :
                                     hw.priority === 'medium' ? 'bg-warning' : 'bg-secondary';
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${escapeHtml(hw.headword)}</strong></td>
                    <td>${escapeHtml(hw.pos || '-')}</td>
                    <td><span class="badge ${priorityBadge}">${escapeHtml(hw.priority)}</span></td>
                    <td><small>${escapeHtml((hw.translations || []).slice(0, 3).join(', '))}</small></td>
                    <td><a href="/entries/add?headword=${encodeURIComponent(hw.headword)}&lang=en" class="btn btn-sm btn-outline-primary"><i class="fas fa-plus"></i> Draft</a></td>
                `;
                tbody.appendChild(tr);
            }
        }

        // Pagination controls
        if (gapPagination.pages > 1) {
            document.getElementById('gap-pagination').classList.remove('d-none');
            document.getElementById('gap-page-prev').classList.toggle('disabled', gapCurrentPage <= 1);
            document.getElementById('gap-page-next').classList.toggle('disabled', gapCurrentPage >= gapPagination.pages);
        } else {
            document.getElementById('gap-pagination').classList.add('d-none');
        }

        // Missing senses (in collapsible)
        const missingSenses = data.missing_senses || [];
        const sensesTbody = document.getElementById('gap-missing-senses-body');
        sensesTbody.innerHTML = '';
        if (missingSenses.length > 0) {
            for (const ms of missingSenses) {
                // Extract missing sense definitions
                let missingDefs = [];
                if (ms.missing_senses && ms.missing_senses.length > 0) {
                    missingDefs = ms.missing_senses.map(s => s.definition || s.translations?.[0] || '').filter(Boolean);
                } else if (ms.missing_translations) {
                    missingDefs = ms.missing_translations;
                }
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${escapeHtml(ms.headword)}</strong></td>
                    <td>${ms.flex_senses}</td>
                    <td>${ms.baseline_senses}</td>
                    <td><small>${escapeHtml(missingDefs.slice(0, 3).join('; '))}</small></td>
                `;
                sensesTbody.appendChild(tr);
            }
        } else {
            sensesTbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center">No sense gaps found</td></tr>';
        }
    }
})();
