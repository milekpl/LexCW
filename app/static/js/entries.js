/**
 * Dictionary Writing System - Entries List JavaScript
 * 
 * This file contains the functionality for the entries list page.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize entries list
    loadEntries();
    
    // Set up event listeners
    document.getElementById('btn-filter').addEventListener('click', function() {
        loadEntries(1);
    });
    
    document.getElementById('filter-entries').addEventListener('keyup', function(e) {
        if (e.key === 'Enter') {
            loadEntries(1);
        }
    });
    
    document.getElementById('btn-sort-lexeme').addEventListener('click', function() {
        if (this.querySelector('i').classList.contains('fa-sort-alpha-down')) {
            this.querySelector('i').classList.replace('fa-sort-alpha-down', 'fa-sort-alpha-up');
            loadEntries(1, 'lexical_unit', 'desc');
        } else {
            this.querySelector('i').classList.replace('fa-sort-alpha-up', 'fa-sort-alpha-down');
            loadEntries(1, 'lexical_unit', 'asc');
        }
    });
    
    document.getElementById('btn-sort-date').addEventListener('click', function() {
        if (this.querySelector('i').classList.contains('fa-calendar')) {
            this.querySelector('i').classList.replace('fa-calendar', 'fa-calendar-check');
            loadEntries(1, 'date_modified', 'desc');
        } else {
            this.querySelector('i').classList.replace('fa-calendar-check', 'fa-calendar');
            loadEntries(1, 'date_modified', 'asc');
        }
    });
    
    // Delete modal handling
    const deleteModal = document.getElementById('deleteModal');
    const deleteModalInstance = new bootstrap.Modal(deleteModal);
    let currentDeleteId = null;
    
    document.getElementById('entries-list').addEventListener('click', function(e) {
        // Handle delete button click
        if (e.target.closest('.delete-btn')) {
            e.preventDefault();
            const row = e.target.closest('tr');
            const entryId = row.dataset.entryId;
            const entryName = row.querySelector('.entry-link').textContent;
            
            document.getElementById('delete-entry-name').textContent = entryName;
            currentDeleteId = entryId;
            deleteModalInstance.show();
        }
    });
    
    document.getElementById('confirm-delete').addEventListener('click', function() {
        if (currentDeleteId) {
            deleteEntry(currentDeleteId);
            deleteModalInstance.hide();
        }
    });
    
    // Refresh button
    document.getElementById('refresh-entries-btn').addEventListener('click', function() {
        refreshEntries();
    });
});

/**
 * Load entries with pagination and filtering
 * 
 * @param {number} page - Page number
 * @param {string} sortBy - Field to sort by
 * @param {string} sortOrder - Sort order (asc or desc)
 */
function loadEntries(page = 1, sortBy = 'lexical_unit', sortOrder = 'asc') {
    // Show loading state
    document.getElementById('entries-list').innerHTML = `
        <tr>
            <td colspan="6" class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading entries...</p>
            </td>
        </tr>
    `;
    
    // Get filter value
    const filter = document.getElementById('filter-entries').value;
    
    // Calculate offset based on page
    const limit = 20;
    const offset = (page - 1) * limit;
    
    // Build API URL
    let url = `/api/entries/?limit=${limit}&offset=${offset}&sort_by=${sortBy}&sort_order=${sortOrder}`;
    if (filter) {
        url += `&filter_text=${encodeURIComponent(filter)}`;
    }
    
    // Fetch entries from API
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Error fetching entries');
            }
            return response.json();
        })
        .then(data => {
            displayEntries(data.entries);
            updatePagination(data.total_count, limit, page);
            document.getElementById('entry-count').textContent = `Showing ${data.entries.length} of ${data.total_count} entries`;
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('entries-list').innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-danger">
                        <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                        <p>Error loading entries. Please try again.</p>
                    </td>
                </tr>
            `;
        });
}

/**
 * Display entries in the table
 * 
 * @param {Array} entries - Array of entry objects
 */
function displayEntries(entries) {
    const entriesList = document.getElementById('entries-list');
    entriesList.innerHTML = '';
    
    if (entries.length === 0) {
        entriesList.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4">
                    <p>No entries found matching your filter.</p>
                </td>
            </tr>
        `;
        return;
    }
    
    const template = document.getElementById('entry-template');
    
    entries.forEach(entry => {
        // Clone the template
        const clone = document.importNode(template.content, true);
        
        // Set entry data
        const row = clone.querySelector('tr');
        row.dataset.entryId = entry.id;
        
        const entryLink = clone.querySelector('.entry-link');
        // Handle lexical_unit as a dictionary with language codes
        let headword = '';
        if (typeof entry.lexical_unit === 'object') {
            // Prefer English if available
            if (entry.lexical_unit.en) {
                headword = entry.lexical_unit.en;
            } else {
                // Otherwise, take the first available language
                const firstLang = Object.keys(entry.lexical_unit)[0];
                if (firstLang) {
                    headword = entry.lexical_unit[firstLang];
                }
            }
        } else if (typeof entry.lexical_unit === 'string') {
            // For backward compatibility
            headword = entry.lexical_unit;
        }
        
        entryLink.textContent = headword;
        entryLink.href = `/entries/${entry.id}`;
        
        // If we have multiple languages, show them in a smaller font
        if (typeof entry.lexical_unit === 'object' && Object.keys(entry.lexical_unit).length > 1) {
            const languages = Object.keys(entry.lexical_unit).join(', ');
            const languageSpan = document.createElement('span');
            languageSpan.className = 'small text-muted ms-2';
            languageSpan.textContent = `[${languages}]`;
            entryLink.appendChild(languageSpan);
        }
        
        if (entry.citation_form) {
            clone.querySelector('.citation-form').textContent = entry.citation_form;
        } else {
            clone.querySelector('.citation-form').remove();
        }
        
        // Get grammatical info from the first sense that has it
        let grammaticalInfo = 'unknown';
        if (entry.senses && entry.senses.length > 0) {
            for (const sense of entry.senses) {
                if (sense.grammatical_info) {
                    grammaticalInfo = sense.grammatical_info;
                    break;
                }
            }
        }
        clone.querySelector('.pos-tag').textContent = grammaticalInfo;
        
        clone.querySelector('.sense-count').textContent = entry.senses ? entry.senses.length : 0;
        
        let exampleCount = 0;
        if (entry.senses) {
            entry.senses.forEach(sense => {
                if (sense.examples) {
                    exampleCount += sense.examples.length;
                }
            });
        }
        clone.querySelector('.example-count').textContent = exampleCount;
        
        clone.querySelector('.date-modified').textContent = formatDate(entry.date_modified);
        
        // Set action button links
        clone.querySelector('.edit-btn').href = `/entries/${entry.id}/edit`;
        clone.querySelector('.view-btn').href = `/entries/${entry.id}`;
        
        // Append to the list
        entriesList.appendChild(clone);
    });
}

/**
 * Update pagination controls
 * 
 * @param {number} totalCount - Total number of entries
 * @param {number} limit - Entries per page
 * @param {number} currentPage - Current page number
 */
function updatePagination(totalCount, limit, currentPage) {
    const pagination = document.getElementById('pagination');
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
            loadEntries(currentPage - 1);
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
                loadEntries(i);
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
            loadEntries(currentPage + 1);
        });
    }
    
    nextLi.appendChild(nextLink);
    pagination.appendChild(nextLi);
}

/**
 * Delete an entry
 * 
 * @param {string} entryId - ID of the entry to delete
 */
function deleteEntry(entryId) {
    fetch(`/api/entries/${entryId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error deleting entry');
        }
        return response.json();
    })
    .then(data => {
        // Show success message
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.innerHTML = `
            <strong>Success!</strong> Entry deleted successfully.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.row'));
        
        // Reload entries
        loadEntries();
    })
    .catch(error => {
        console.error('Error:', error);
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show';
        alertDiv.innerHTML = `
            <strong>Error!</strong> Failed to delete entry.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.row'));
    });
}

/**
 * Format a date string
 * 
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return 'Today ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
        return 'Yesterday ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays < 7) {
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        return days[date.getDay()];
    } else {
        return date.toLocaleDateString();
    }
}

/**
 * Refresh the entries list with cache clearing
 */
function refreshEntries() {
    const refreshBtn = document.getElementById('refresh-entries-btn');
    if (refreshBtn) {
        // Show loading state
        const icon = refreshBtn.querySelector('i');
        const originalInner = refreshBtn.innerHTML;
        refreshBtn.disabled = true;
        if (icon) {
            icon.classList.add('fa-spin');
        }
        
        // Clear cache and reload entries
        fetch('/api/entries/clear-cache', { method: 'POST' })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    // Cache cleared, now reload entries
                    loadEntries();
                    
                    // Show success briefly
                    refreshBtn.innerHTML = '<i class="fas fa-check"></i>';
                    refreshBtn.classList.remove('btn-outline-secondary');
                    refreshBtn.classList.add('btn-success');
                    
                    setTimeout(() => {
                        refreshBtn.innerHTML = originalInner;
                        refreshBtn.classList.remove('btn-success');
                        refreshBtn.classList.add('btn-outline-secondary');
                        refreshBtn.disabled = false;
                        if (icon) {
                            icon.classList.remove('fa-spin');
                        }
                    }, 1500);
                } else {
                    throw new Error(result.error || 'Failed to clear cache');
                }
            })
            .catch(error => {
                console.error('Error refreshing entries:', error);
                
                // Still try to reload entries even if cache clear failed
                loadEntries();
                
                // Show error briefly
                refreshBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                refreshBtn.classList.remove('btn-outline-secondary');
                refreshBtn.classList.add('btn-danger');
                
                setTimeout(() => {
                    refreshBtn.innerHTML = originalInner;
                    refreshBtn.classList.remove('btn-danger');
                    refreshBtn.classList.add('btn-outline-secondary');
                    refreshBtn.disabled = false;
                    if (icon) {
                        icon.classList.remove('fa-spin');
                    }
                }, 1500);
            });
    } else {
        // Fallback if button not found
        loadEntries();
    }
}
