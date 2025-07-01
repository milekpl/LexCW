/**
 * Dictionary Writing System - Search JavaScript
 * 
 * This file contains the functionality for the search page.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Set up search form submission
    const searchForm = document.getElementById('search-form');
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        performSearch(1);
    });
    
    // View mode buttons
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
    
    // Load recent searches
    loadRecentSearches();
    
    // Handle recent search clicks
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
    
    // Check for URL parameters to perform a search
    const urlParams = new URLSearchParams(window.location.search);
    const queryParam = urlParams.get('q');
    if (queryParam) {
        document.getElementById('search-query').value = queryParam;
        performSearch(1);
    }
});

/**
 * Perform a search using the form values
 * 
 * @param {number} page - Page number for pagination
 */
function performSearch(page = 1) {
    // Show loading state
    document.getElementById('search-initial').style.display = 'none';
    document.getElementById('search-no-results').style.display = 'none';
    document.getElementById('search-results').style.display = 'none';
    document.getElementById('search-loading').style.display = 'block';
    document.getElementById('results-pagination').style.display = 'none';
    
    // Get form values
    const query = document.getElementById('search-query').value.trim();
    if (!query) {
        document.getElementById('search-loading').style.display = 'none';
        document.getElementById('search-initial').style.display = 'block';
        return;
    }
    
    // Get selected fields
    const fieldsCheckboxes = document.querySelectorAll('input[name="fields[]"]:checked');
    const fields = Array.from(fieldsCheckboxes).map(cb => cb.value).join(',');
    
    // Get part of speech filter
    const posFilter = document.getElementById('pos-filter').value;
    
    // Get search options
    const exactMatch = document.getElementById('check-exact-match').checked ? 1 : 0;
    const caseSensitive = document.getElementById('check-case-sensitive').checked ? 1 : 0;
    
    // Calculate offset for pagination
    const limit = 20;
    const offset = (page - 1) * limit;
    
    // Build API URL
    let url = `/api/search/?q=${encodeURIComponent(query)}&limit=${limit}&offset=${offset}`;
    
    if (fields) {
        url += `&fields=${fields}`;
    }
    
    if (posFilter) {
        url += `&pos=${posFilter}`;
    }
    
    if (exactMatch) {
        url += `&exact_match=${exactMatch}`;
    }
    
    if (caseSensitive) {
        url += `&case_sensitive=${caseSensitive}`;
    }
    
    // Fetch search results from API
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Error performing search');
            }
            return response.json();
        })
        .then(data => {
            console.log('Search API response:', data); // Debug logging
            document.getElementById('search-loading').style.display = 'none';
            
            if (data.entries.length === 0) {
                document.getElementById('search-no-results').style.display = 'block';
                document.getElementById('results-pagination').style.display = 'none';
                return;
            }
            
            // Display results
            console.log('Displaying results:', data.entries); // Debug logging
            displaySearchResults(data.entries);
            document.getElementById('search-results').style.display = 'block';
            
            // Update pagination
            updatePagination(data.total, limit, page);
            document.getElementById('results-count').textContent = `${data.total} results found`;
            document.getElementById('results-pagination').style.display = 'block';
            
            // Update search results header
            document.getElementById('search-results-header').textContent = 
                `Search Results for "${query}" (${data.total} results)`;
                
            // Add to recent searches
            addRecentSearch(query);
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('search-loading').style.display = 'none';
            document.getElementById('search-no-results').style.display = 'block';
            document.getElementById('search-no-results').querySelector('p.lead').textContent = 'Error performing search';
        });
}

/**
 * Display search results
 * 
 * @param {Array} results - Array of search result objects
 */
function displaySearchResults(results) {
    const resultsContainer = document.getElementById('search-results');
    resultsContainer.innerHTML = '';
    
    const entryTemplate = document.getElementById('entry-result-template');
    const senseTemplate = document.getElementById('sense-result-template');
    const exampleTemplate = document.getElementById('example-result-template');
    
    results.forEach(result => {
        // Clone the entry template
        const clone = document.importNode(entryTemplate.content, true);
        
        // Set entry data
        const entryLink = clone.querySelector('.result-entry-link');
        
        // Handle lexical_unit which might be an object with language keys
        let displayText = result.headword;
        if (!displayText && result.lexical_unit) {
            if (typeof result.lexical_unit === 'string') {
                displayText = result.lexical_unit;
            } else if (typeof result.lexical_unit === 'object') {
                // Try common language keys
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
        
        clone.querySelector('.result-entry-id').textContent = `ID: ${result.id}`;
        
        if (result.citation_form) {
            clone.querySelector('.result-entry-citation').textContent = result.citation_form;
        } else {
            clone.querySelector('.result-entry-citation').remove();
        }
        
        // Set edit and view links
        clone.querySelector('.result-edit-link').href = `/entries/${result.id}/edit`;
        clone.querySelector('.result-view-link').href = `/entries/${result.id}`;
        
        // Add senses
        const sensesContainer = clone.querySelector('.result-senses');
        
        if (result.senses && result.senses.length > 0) {
            result.senses.forEach((sense, index) => {
                const senseClone = document.importNode(senseTemplate.content, true);
                
                senseClone.querySelector('.sense-number').textContent = index + 1;
                senseClone.querySelector('.sense-definition').textContent = sense.definition;
                
                const examplesContainer = senseClone.querySelector('.sense-examples');
                
                if (sense.examples && sense.examples.length > 0) {
                    sense.examples.forEach(example => {
                        const exampleClone = document.importNode(exampleTemplate.content, true);
                        exampleClone.querySelector('.example-text').textContent = example.text;
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
        
        // Add to results container
        resultsContainer.appendChild(clone);
    });
    
    // Initialize current view mode
    setResultsViewMode('all');
}

/**
 * Set the view mode for search results
 * 
 * @param {string} mode - View mode ('all', 'entries', 'senses', 'examples')
 */
function setResultsViewMode(mode) {
    // Update active button
    document.querySelectorAll('#btn-view-all, #btn-view-entries, #btn-view-senses, #btn-view-examples')
        .forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(`btn-view-${mode}`).classList.add('active');
    
    // Get all result elements
    const results = document.querySelectorAll('.search-result');
    
    results.forEach(result => {
        // Show the result by default
        result.style.display = 'block';
        
        // Show or hide senses based on mode
        const senses = result.querySelectorAll('.sense-item');
        senses.forEach(sense => {
            sense.style.display = (mode === 'all' || mode === 'senses') ? 'block' : 'none';
        });
        
        // Show or hide examples based on mode
        const examples = result.querySelectorAll('.example-item');
        examples.forEach(example => {
            example.style.display = (mode === 'all' || mode === 'examples') ? 'block' : 'none';
        });
        
        // Handle 'entries' mode specially - hide senses and examples
        if (mode === 'entries') {
            const sensesContainer = result.querySelector('.result-senses');
            sensesContainer.style.display = 'none';
        } else {
            const sensesContainer = result.querySelector('.result-senses');
            sensesContainer.style.display = 'block';
        }
    });
}

/**
 * Update pagination controls
 * 
 * @param {number} totalCount - Total number of search results
 * @param {number} limit - Results per page
 * @param {number} currentPage - Current page number
 */
function updatePagination(totalCount, limit, currentPage) {
    const pagination = document.getElementById('search-pagination');
    pagination.innerHTML = '';
    
    const totalPages = Math.ceil(totalCount / limit);
    if (totalPages <= 1) {
        return;
    }
    
    // Previous button
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
    
    // Page numbers
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
    
    // Next button
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

/**
 * Save a recent search to localStorage
 * 
 * @param {string} query - Search query
 */
function addRecentSearch(query) {
    // Get existing recent searches
    let recentSearches = JSON.parse(localStorage.getItem('recentSearches')) || [];
    
    // Don't add duplicates
    if (recentSearches.includes(query)) {
        // Move to the top of the list
        recentSearches = recentSearches.filter(item => item !== query);
    }
    
    // Add to the beginning of the array
    recentSearches.unshift(query);
    
    // Limit to 10 recent searches
    recentSearches = recentSearches.slice(0, 10);
    
    // Save back to localStorage
    localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
    
    // Update the UI
    loadRecentSearches();
}

/**
 * Remove a recent search from localStorage
 * 
 * @param {string} query - Search query to remove
 */
function removeRecentSearch(query) {
    // Get existing recent searches
    let recentSearches = JSON.parse(localStorage.getItem('recentSearches')) || [];
    
    // Remove the query
    recentSearches = recentSearches.filter(item => item !== query);
    
    // Save back to localStorage
    localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
}

/**
 * Load recent searches from localStorage and display them
 */
function loadRecentSearches() {
    const recentSearches = JSON.parse(localStorage.getItem('recentSearches')) || [];
    const container = document.getElementById('recent-searches');
    
    // Clear container
    container.innerHTML = '';
    
    if (recentSearches.length === 0) {
        const emptyItem = document.createElement('li');
        emptyItem.className = 'list-group-item text-center text-muted';
        emptyItem.textContent = 'No recent searches';
        container.appendChild(emptyItem);
        return;
    }
    
    // Create a list item for each recent search
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
