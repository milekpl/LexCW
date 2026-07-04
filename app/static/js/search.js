/**
 * Lexicographic Curation Workbench - Search JavaScript
 * 
 * Search page with faceted navigation, export, save/load, and search-within-results.
 */

document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        performSearch(1);
    });

    document.getElementById('btn-view-all').addEventListener('click', function() {
        setResultsViewMode('all');
    });
    document.getElementById('btn-view-entries').addEventListener('click', function() {
        setResultsViewMode('entries');
    });
    document.getElementById('btn-view-senses').addEventListener('click', function() {
        setResultsViewMode('senses');
    });
    document.getElementById('btn-view-examples').addEventListener('click', function() {
        setResultsViewMode('examples');
    });

    document.getElementById('save-search-btn').addEventListener('click', function() {
        const modal = new bootstrap.Modal(document.getElementById('save-search-modal'));
        modal.show();
    });

    document.getElementById('save-search-confirm').addEventListener('click', saveCurrentSearch);

    document.getElementById('export-csv-btn').addEventListener('click', function() {
        exportResults('csv');
    });
    document.getElementById('export-json-btn').addEventListener('click', function() {
        exportResults('json');
    });

    document.getElementById('search-within-results').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            filterWithinResults();
        }
    });
    document.getElementById('clear-within-btn').addEventListener('click', function() {
        document.getElementById('search-within-results').value = '';
        filterWithinResults();
    });

    document.getElementById('recent-searches').addEventListener('click', function(e) {
        const removeBtn = e.target.closest('.recent-search-remove');
        if (removeBtn) {
            e.preventDefault();
            const searchItem = removeBtn.closest('li');
            const searchQuery = searchItem.querySelector('.recent-search-link').textContent;
            removeRecentSearch(searchQuery);
            searchItem.remove();
            return;
        }
        const searchLink = e.target.closest('.recent-search-link');
        if (searchLink) {
            e.preventDefault();
            const searchQuery = searchLink.textContent;
            document.getElementById('search-query').value = searchQuery;
            performSearch(1);
        }
    });

    document.getElementById('saved-searches-list').addEventListener('click', function(e) {
        const deleteBtn = e.target.closest('.delete-saved-search');
        if (deleteBtn) {
            e.preventDefault();
            e.stopPropagation();
            const item = deleteBtn.closest('.saved-search-item');
            const searchId = item.dataset.searchId;
            deleteSavedSearch(searchId, item);
            return;
        }
        const item = e.target.closest('.saved-search-item');
        if (item) {
            const query = item.dataset.query;
            const pos = item.dataset.pos;
            if (query) {
                document.getElementById('search-query').value = query;
                if (pos) {
                    _facetFilters['grammatical-info'] = pos;
                }
                performSearch(1);
            }
        }
    });

    loadRecentSearches();
    loadSavedSearches();

    document.getElementById('check-use-regex').addEventListener('change', function() {
        if (this.checked) {
            document.getElementById('check-exact-match').checked = false;
            document.getElementById('check-exact-match').disabled = true;
        } else {
            document.getElementById('check-exact-match').disabled = false;
        }
    });

    const urlParams = new URLSearchParams(window.location.search);
    const queryParam = urlParams.get('q');
    if (queryParam) {
        document.getElementById('search-query').value = queryParam;
        performSearch(1);
    }
});

let _currentSearchParams = null;
let _facetFilters = {};
let _searchResultsHTML = null;

function performSearch(page = 1) {
    document.getElementById('search-initial').style.display = 'none';
    document.getElementById('search-no-results').style.display = 'none';
    document.getElementById('search-results').style.display = 'none';
    document.getElementById('search-loading').style.display = 'block';
    document.getElementById('results-pagination').style.display = 'none';
    document.getElementById('save-search-btn').style.display = 'none';
    document.getElementById('export-csv-btn').style.display = 'none';
    document.getElementById('export-json-btn').style.display = 'none';
    document.getElementById('search-within-container').style.display = 'none';
    document.getElementById('search-within-results').value = '';

    const query = document.getElementById('search-query').value.trim();
    if (!query) {
        document.getElementById('search-loading').style.display = 'none';
        document.getElementById('search-initial').style.display = 'block';
        return;
    }

    const fieldsCheckboxes = document.querySelectorAll('input[name="fields[]"]:checked');
    const fields = Array.from(fieldsCheckboxes).map(cb => cb.value).join(',');
    const posFilter = _facetFilters['grammatical-info'] || document.getElementById('pos-filter').value;
    const exactMatch = document.getElementById('check-exact-match').checked ? 1 : 0;
    const caseSensitive = document.getElementById('check-case-sensitive').checked ? 1 : 0;
    const useRegex = document.getElementById('check-use-regex').checked ? 1 : 0;
    const useSemantic = (document.getElementById('check-semantic-search')?.checked || document.getElementById('check-use-semantic')?.checked) ? 1 : 0;

    const limit = 20;
    const offset = (page - 1) * limit;

    _currentSearchParams = { query, fields, pos: posFilter, exactMatch, caseSensitive, useRegex, useSemantic };

    let url = `/api/search/?q=${encodeURIComponent(query)}&limit=${limit}&offset=${offset}`;
    if (fields) url += `&fields=${fields}`;
    if (posFilter) url += `&pos=${posFilter}`;
    if (exactMatch) url += `&exact_match=${exactMatch}`;
    if (caseSensitive) url += `&case_sensitive=${caseSensitive}`;
    if (useRegex) url += `&use_regex=${useRegex}`;
    if (useSemantic) url += `&use_semantic=${useSemantic}`;

    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('Error performing search');
            return response.json();
        })
        .then(data => {
            document.getElementById('search-loading').style.display = 'none';

            if (data.entries.length === 0) {
                document.getElementById('search-no-results').style.display = 'block';
                document.getElementById('results-pagination').style.display = 'none';
                return;
            }

            displaySearchResults(data.entries);
            _searchResultsHTML = document.getElementById('search-results').innerHTML;
            document.getElementById('search-results').style.display = 'block';

            updatePagination(data.total, limit, page);
            document.getElementById('results-count').textContent = `${data.total} results found`;
            document.getElementById('results-pagination').style.display = 'block';

            if (data.is_semantic) {
                document.getElementById('search-results-header').innerHTML =
                    `Search Results for "${query}" (${data.total} vector matches) <span class="badge bg-primary ms-2"><i class="fas fa-brain me-1"></i> Semantic AI Search</span>`;
            } else {
                document.getElementById('search-results-header').textContent =
                    `Search Results for "${query}" (${data.total} results)`;
            }

            addRecentSearch(query);
            showActionButtons();
            loadFacets();
            document.getElementById('search-within-container').style.display = 'block';
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('search-loading').style.display = 'none';
            document.getElementById('search-no-results').style.display = 'block';
            document.getElementById('search-no-results').querySelector('p.lead').textContent = 'Error performing search';
        });
}

function showActionButtons() {
    document.getElementById('save-search-btn').style.display = 'inline-block';
    document.getElementById('export-csv-btn').style.display = 'inline-block';
    document.getElementById('export-json-btn').style.display = 'inline-block';
}

function loadFacets() {
    const params = _currentSearchParams;
    if (!params) return;

    let url = `/api/search/facets?q=${encodeURIComponent(params.query)}`;
    if (params.fields) url += `&fields=${params.fields}`;
    if (params.pos) url += `&pos=${params.pos}`;
    if (params.exactMatch) url += `&exact_match=${params.exactMatch}`;
    if (params.caseSensitive) url += `&case_sensitive=${params.caseSensitive}`;
    if (params.useRegex) url += `&use_regex=${params.useRegex}`;

    fetch(url)
        .then(r => r.json())
        .then(data => {
            renderFacets(data.facets || {});
            renderActiveFilters();
        })
        .catch(err => console.error('Error loading facets:', err));
}

function renderFacets(facets) {
    const sidebar = document.getElementById('facet-sidebar');
    const content = document.getElementById('facet-content');
    content.innerHTML = '';

    const facetGroupTemplate = document.getElementById('facet-group-template');
    const facetValueTemplate = document.getElementById('facet-value-template');

    let hasFacets = false;

    Object.entries(facets).forEach(([field, values]) => {
        const entries = Object.entries(values);
        if (entries.length === 0) return;

        hasFacets = true;
        const group = document.importNode(facetGroupTemplate.content, true);
        group.querySelector('.facet-group-title').textContent = formatFacetLabel(field);

        const valuesContainer = group.querySelector('.facet-values');

        entries.forEach(([value, count]) => {
            const valEl = document.importNode(facetValueTemplate.content, true);
            const div = valEl.querySelector('.facet-value');
            div.dataset.facetField = field;
            div.dataset.facetValue = value;
            div.querySelector('.facet-value-label').textContent = value;
            div.querySelector('.facet-count').textContent = count;

            div.addEventListener('click', function() {
                applyFacetFilter(field, value);
            });

            valuesContainer.appendChild(valEl);
        });

        content.appendChild(group);
    });

    sidebar.style.display = hasFacets ? 'block' : 'none';
}

function formatFacetLabel(field) {
    const labels = {
        'grammatical-info': 'Part of Speech',
        'semantic-domain': 'Semantic Domain',
        'lexical-relation': 'Lexical Relation',
        'variant-type': 'Variant Type',
    };
    return labels[field] || field.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function applyFacetFilter(field, value) {
    _facetFilters[field] = value;
    performSearch(1);
}

function renderActiveFilters() {
    const container = document.getElementById('active-filters');
    const card = document.getElementById('active-filters-card');
    container.innerHTML = '';

    const params = _currentSearchParams;
    if (!params || !params.pos) {
        card.style.display = 'none';
        return;
    }

    card.style.display = 'block';

    const template = document.getElementById('active-filter-template');
    const el = document.importNode(template.content, true);
    el.querySelector('.active-filter-label').textContent = `POS: ${params.pos}`;
    el.querySelector('.remove-facet').addEventListener('click', function() {
        delete _facetFilters['grammatical-info'];
        performSearch(1);
    });
    container.appendChild(el);
}

function exportResults(format) {
    const params = _currentSearchParams;
    if (!params) return;

    let url = `/api/search/export?format=${format}&q=${encodeURIComponent(params.query)}`;
    if (params.fields) url += `&fields=${params.fields}`;
    if (params.pos) url += `&pos=${params.pos}`;
    if (params.exactMatch) url += `&exact_match=${params.exactMatch}`;
    if (params.caseSensitive) url += `&case_sensitive=${params.caseSensitive}`;
    if (params.useRegex) url += `&use_regex=${params.useRegex}`;

    window.open(url, '_blank');
}

function saveCurrentSearch() {
    const name = document.getElementById('save-search-name').value.trim();
    if (!name) return;

    const params = _currentSearchParams;
    if (!params) return;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    fetch('/api/search/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': csrfToken },
        body: JSON.stringify({
            name: name,
            query: params,
        }),
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const modalEl = document.getElementById('save-search-modal');
                const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                modal.hide();
                document.getElementById('save-search-name').value = '';
                document.getElementById('save-search-desc').value = '';
                loadSavedSearches();
            }
        })
        .catch(err => console.error('Error saving search:', err));
}

function loadSavedSearches() {
    fetch('/api/search/saved')
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('saved-searches-list');
            list.innerHTML = '';

            if (!data.searches || data.searches.length === 0) {
                list.innerHTML = '<li class="list-group-item text-center text-muted small">No saved searches</li>';
                return;
            }

            const template = document.getElementById('saved-search-item-template');
            data.searches.forEach(s => {
                const el = document.importNode(template.content, true);
                const item = el.querySelector('.saved-search-item');
                item.dataset.searchId = s.id;
                item.dataset.query = s.query.query || '';
                item.dataset.pos = s.query.pos || '';
                item.querySelector('.saved-search-name').textContent = s.name;
                const date = new Date(s.created_at);
                item.querySelector('.saved-search-date').textContent = date.toLocaleDateString();
                list.appendChild(el);
            });
        })
        .catch(err => console.error('Error loading saved searches:', err));
}

function deleteSavedSearch(searchId, item) {
    item.remove();
}

function filterWithinResults() {
    const filterText = document.getElementById('search-within-results').value.trim().toLowerCase();
    const resultsContainer = document.getElementById('search-results');

    if (!filterText) {
        if (_searchResultsHTML) {
            resultsContainer.innerHTML = _searchResultsHTML;
        }
        return;
    }

    const results = Array.from(resultsContainer.querySelectorAll('.search-result'));
    results.forEach(result => {
        const text = result.textContent.toLowerCase();
        if (!text.includes(filterText)) {
            result.remove();
        }
    });
}

function displaySearchResults(results) {
    const resultsContainer = document.getElementById('search-results');
    resultsContainer.innerHTML = '';

    const entryTemplate = document.getElementById('entry-result-template');
    const senseTemplate = document.getElementById('sense-result-template');
    const exampleTemplate = document.getElementById('example-result-template');

    results.forEach(result => {
        const clone = document.importNode(entryTemplate.content, true);
        const entryLink = clone.querySelector('.result-entry-link');

        let displayText = result.headword;
        if (!displayText && result.lexical_unit) {
            if (typeof result.lexical_unit === 'string') {
                displayText = result.lexical_unit;
            } else if (typeof result.lexical_unit === 'object') {
                displayText = result.lexical_unit.en || result.lexical_unit.pl ||
                             Object.values(result.lexical_unit)[0] || 'Unknown';
            }
        }

        entryLink.textContent = displayText || 'Unknown Entry';
        entryLink.href = `/entries/${result.id}`;

        if (result.grammatical_info?.part_of_speech) {
            clone.querySelector('.result-pos').textContent = result.grammatical_info.part_of_speech;
        } else {
            clone.querySelector('.result-pos').remove();
        }

        if (result.citation_form) {
            clone.querySelector('.result-entry-citation').textContent = result.citation_form;
        } else {
            clone.querySelector('.result-entry-citation').remove();
        }

        clone.querySelector('.result-edit-link').href = `/entries/${result.id}/edit`;
        clone.querySelector('.result-view-link').href = `/entries/${result.id}`;

        const sensesContainer = clone.querySelector('.result-senses');

        if (result.senses && result.senses.length > 0) {
            result.senses.forEach((sense, index) => {
                const senseClone = document.importNode(senseTemplate.content, true);
                senseClone.querySelector('.sense-number').textContent = index + 1;

                let definitionText = '';
                if (sense.definition) {
                    if (typeof sense.definition === 'string') {
                        definitionText = sense.definition;
                    } else if (typeof sense.definition === 'object') {
                        definitionText = sense.definition.pl || sense.definition.en ||
                                       Object.values(sense.definition)[0] || '[object Object]';
                    }
                }
                senseClone.querySelector('.sense-definition').textContent = definitionText;

                const examplesContainer = senseClone.querySelector('.sense-examples');

                if (sense.examples && sense.examples.length > 0) {
                    sense.examples.forEach(example => {
                        const exampleClone = document.importNode(exampleTemplate.content, true);
                        const exampleText = example.form_text || example.text ||
                                          (typeof example.form === 'object' ? Object.values(example.form)[0] : example.form) ||
                                          '[No example text]';
                        exampleClone.querySelector('.example-text').textContent = exampleText;
                        examplesContainer.appendChild(exampleClone);
                    });
                } else {
                    examplesContainer.remove();
                }

                sensesContainer.appendChild(senseClone);
            });
        } else {
            const noSenses = document.createElement('div');
            noSenses.className = 'text-muted small';
            noSenses.textContent = 'No senses available';
            sensesContainer.appendChild(noSenses);
        }

        resultsContainer.appendChild(clone);
    });

    setResultsViewMode('all');
}

function setResultsViewMode(mode) {
    document.querySelectorAll('#btn-view-all, #btn-view-entries, #btn-view-senses, #btn-view-examples')
        .forEach(btn => btn.classList.remove('active'));
    document.getElementById(`btn-view-${mode}`).classList.add('active');

    const results = document.querySelectorAll('.search-result');
    results.forEach(result => {
        result.style.display = 'block';
        const senses = result.querySelectorAll('.sense-item');
        senses.forEach(sense => {
            sense.style.display = (mode === 'all' || mode === 'senses') ? 'block' : 'none';
        });
        const examples = result.querySelectorAll('.example-item');
        examples.forEach(example => {
            example.style.display = (mode === 'all' || mode === 'examples') ? 'block' : 'none';
        });
        if (mode === 'entries') {
            const sensesContainer = result.querySelector('.result-senses');
            sensesContainer.style.display = 'none';
        } else {
            const sensesContainer = result.querySelector('.result-senses');
            sensesContainer.style.display = 'block';
        }
    });
}

function updatePagination(totalCount, limit, currentPage) {
    const pagination = document.getElementById('search-pagination');
    pagination.innerHTML = '';

    const totalPages = Math.ceil(totalCount / limit);
    if (totalPages <= 1) return;

    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    const prevLink = document.createElement('a');
    prevLink.className = 'page-link';
    prevLink.href = '#';
    prevLink.setAttribute('aria-label', 'Previous');
    prevLink.innerHTML = '<span aria-hidden="true">&laquo;</span>';
    if (currentPage > 1) {
        prevLink.addEventListener('click', (e) => {
            e.preventDefault();
            performSearch(currentPage - 1);
        });
    }
    prevLi.appendChild(prevLink);
    pagination.appendChild(prevLi);

    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }

    for (let i = startPage; i <= endPage; i++) {
        const pageLi = document.createElement('li');
        pageLi.className = `page-item ${i === currentPage ? 'active' : ''}`;
        const pageLink = document.createElement('a');
        pageLink.className = 'page-link';
        pageLink.href = '#';
        pageLink.textContent = i;
        if (i !== currentPage) {
            pageLink.addEventListener('click', (e) => {
                e.preventDefault();
                performSearch(i);
            });
        }
        pageLi.appendChild(pageLink);
        pagination.appendChild(pageLi);
    }

    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    const nextLink = document.createElement('a');
    nextLink.className = 'page-link';
    nextLink.href = '#';
    nextLink.setAttribute('aria-label', 'Next');
    nextLink.innerHTML = '<span aria-hidden="true">&raquo;</span>';
    if (currentPage < totalPages) {
        nextLink.addEventListener('click', (e) => {
            e.preventDefault();
            performSearch(currentPage + 1);
        });
    }
    nextLi.appendChild(nextLink);
    pagination.appendChild(nextLi);
}

function addRecentSearch(query) {
    let recentSearches = JSON.parse(localStorage.getItem('recentSearches')) || [];
    if (recentSearches.includes(query)) {
        recentSearches = recentSearches.filter(item => item !== query);
    }
    recentSearches.unshift(query);
    recentSearches = recentSearches.slice(0, 10);
    localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
    loadRecentSearches();
}

function removeRecentSearch(query) {
    let recentSearches = JSON.parse(localStorage.getItem('recentSearches')) || [];
    recentSearches = recentSearches.filter(item => item !== query);
    localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
}

function loadRecentSearches() {
    const recentSearches = JSON.parse(localStorage.getItem('recentSearches')) || [];
    const container = document.getElementById('recent-searches');
    container.innerHTML = '';

    if (recentSearches.length === 0) {
        const emptyItem = document.createElement('li');
        emptyItem.className = 'list-group-item text-center text-muted';
        emptyItem.textContent = 'No recent searches';
        container.appendChild(emptyItem);
        return;
    }

    const template = document.getElementById('recent-search-template');
    recentSearches.forEach(query => {
        const clone = document.importNode(template.content, true);
        const link = clone.querySelector('.recent-search-link');
        link.textContent = query;
        link.title = `Search for "${query}"`;
        const removeBtn = clone.querySelector('.recent-search-remove');
        removeBtn.title = `Remove "${query}" from recent searches`;
        container.appendChild(clone);
    });
}
