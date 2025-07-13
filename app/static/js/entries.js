/**
 * Dictionary Writing System - Entries List JavaScript
 * 
 * This file contains the functionality for the entries list page.
 */

// --- Configuration & State ---
const ENTRIES_CONFIG = {
    defaultLimit: 20,
    columns: [
        { id: 'headword', label: 'Headword', sortable: true, defaultVisible: true, apiSortKey: 'lexical_unit' },
        { id: 'citation_form', label: 'Citation Form', sortable: true, defaultVisible: false, apiSortKey: 'citation_form' },
        { id: 'part_of_speech', label: 'Part of Speech', sortable: true, defaultVisible: true, apiSortKey: 'part_of_speech' },
        { id: 'gloss', label: 'Gloss', sortable: true, defaultVisible: false, apiSortKey: 'gloss' },
        { id: 'definition', label: 'Definition', sortable: true, defaultVisible: true, apiSortKey: 'definition' },
        { id: 'sense_count', label: 'Senses', sortable: false, defaultVisible: true },
        { id: 'example_count', label: 'Examples', sortable: false, defaultVisible: true },
        { id: 'date_modified', label: 'Last Modified', sortable: true, defaultVisible: true, apiSortKey: 'date_modified' },
        { id: 'actions', label: 'Actions', sortable: false, defaultVisible: true, fixedWidth: '120px' }
    ],
    localStorageKeys: {
        visibleColumns: 'entriesVisibleColumns',
        sortBy: 'entriesSortBy',
        sortOrder: 'entriesSortOrder'
    },
    primaryLang: 'en' // Used for extracting multilingual fields like gloss, definition
};

let currentSortBy = localStorage.getItem(ENTRIES_CONFIG.localStorageKeys.sortBy) || 'lexical_unit';
let currentSortOrder = localStorage.getItem(ENTRIES_CONFIG.localStorageKeys.sortOrder) || 'asc';
let currentPage = 1;
let visibleColumns = loadVisibleColumns();

// --- Initialization ---
document.addEventListener('DOMContentLoaded', function() {
    initializeColumnVisibilityMenu();
    initializeSortButtons(); // For existing dedicated sort buttons
    loadEntries(currentPage, currentSortBy, currentSortOrder);
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('btn-filter').addEventListener('click', () => loadEntries(1, currentSortBy, currentSortOrder));
    document.getElementById('filter-entries').addEventListener('keyup', (e) => {
        if (e.key === 'Enter') loadEntries(1, currentSortBy, currentSortOrder);
    });
    document.getElementById('refresh-entries-btn').addEventListener('click', refreshEntries);

    // Delete modal handling
    const deleteModal = document.getElementById('deleteModal');
    const deleteModalInstance = new bootstrap.Modal(deleteModal);
    let currentDeleteId = null;

    document.getElementById('entries-list').addEventListener('click', function(e) {
        if (e.target.closest('.delete-btn')) {
            e.preventDefault();
            const row = e.target.closest('tr');
            currentDeleteId = row.dataset.entryId;
            document.getElementById('delete-entry-name').textContent = row.querySelector('[data-column-id="headword"] a, [data-column-id="headword"]').textContent;
            deleteModalInstance.show();
        }
    });

    document.getElementById('confirm-delete').addEventListener('click', function() {
        if (currentDeleteId) {
            deleteEntry(currentDeleteId);
            deleteModalInstance.hide();
        }
    });
}

// --- Column Visibility ---
function loadVisibleColumns() {
    const stored = localStorage.getItem(ENTRIES_CONFIG.localStorageKeys.visibleColumns);
    if (stored) {
        try {
            const parsed = JSON.parse(stored);
            // Ensure it's an array of strings
            if (Array.isArray(parsed) && parsed.every(item => typeof item === 'string')) {
                 // Ensure at least one column is always visible
                if (parsed.length > 0) return parsed;
            }
        } catch (e) {
            console.error("Error parsing visible columns from localStorage", e);
        }
    }
    return ENTRIES_CONFIG.columns.filter(c => c.defaultVisible).map(c => c.id);
}

function saveVisibleColumns() {
    localStorage.setItem(ENTRIES_CONFIG.localStorageKeys.visibleColumns, JSON.stringify(visibleColumns));
}

function initializeColumnVisibilityMenu() {
    const menu = document.getElementById('column-visibility-menu');
    menu.innerHTML = ''; // Clear existing items

    ENTRIES_CONFIG.columns.forEach(col => {
        if (col.id === 'actions' && ENTRIES_CONFIG.columns.length > 1 && visibleColumns.length === 1 && visibleColumns[0] === 'actions') {
            // Prevent hiding 'Actions' if it's the last visible column
        }

        const li = document.createElement('li');
        const label = document.createElement('label');
        label.className = 'dropdown-item';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'form-check-input me-2';
        checkbox.value = col.id;
        checkbox.checked = visibleColumns.includes(col.id);

        // Prevent unchecking the last visible column
        if (visibleColumns.length === 1 && checkbox.checked) {
            checkbox.disabled = true;
        }

        checkbox.addEventListener('change', function() {
            const colId = this.value;
            if (this.checked) {
                if (!visibleColumns.includes(colId)) {
                    visibleColumns.push(colId);
                }
            } else {
                // Ensure at least one column remains visible
                if (visibleColumns.length > 1) {
                    visibleColumns = visibleColumns.filter(id => id !== colId);
                } else {
                    this.checked = true; // Re-check if it's the last one
                    return; // Don't proceed with update
                }
            }
            saveVisibleColumns();
            updateDisabledStatesInColumnMenu();
            loadEntries(currentPage, currentSortBy, currentSortOrder); // Reload to reflect changes
        });

        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(col.label));
        li.appendChild(label);
        menu.appendChild(li);
    });
}

function updateDisabledStatesInColumnMenu() {
    const checkboxes = document.querySelectorAll('#column-visibility-menu input[type="checkbox"]');
    const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
    checkboxes.forEach(cb => {
        cb.disabled = (checkedCount === 1 && cb.checked);
    });
}


// --- Sorting ---
function initializeSortButtons() {
    // For existing dedicated sort buttons (Lexeme, Date)
    const btnSortLexeme = document.getElementById('btn-sort-lexeme');
    if (btnSortLexeme) {
        btnSortLexeme.addEventListener('click', function() {
            handleSortClick('lexical_unit', this);
        });
    }
    const btnSortDate = document.getElementById('btn-sort-date');
    if (btnSortDate) {
        btnSortDate.addEventListener('click', function() {
            handleSortClick('date_modified', this);
        });
    }
}

function handleSortClick(sortByApi, buttonElement = null) {
    if (currentSortBy === sortByApi) {
        currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortBy = sortByApi;
        currentSortOrder = 'asc';
    }
    localStorage.setItem(ENTRIES_CONFIG.localStorageKeys.sortBy, currentSortBy);
    localStorage.setItem(ENTRIES_CONFIG.localStorageKeys.sortOrder, currentSortOrder);

    loadEntries(1, currentSortBy, currentSortOrder);
}

function updateSortIcons() {
    // Clear existing sort icons from dedicated buttons
    ['btn-sort-lexeme', 'btn-sort-date'].forEach(btnId => {
        const btn = document.getElementById(btnId);
        if (btn) {
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = icon.className.replace(/fa-sort-alpha-up|fa-sort-alpha-down|fa-calendar-check/, '');
                if (btnId === 'btn-sort-lexeme') icon.classList.add('fa-sort-alpha-down');
                if (btnId === 'btn-sort-date') icon.classList.add('fa-calendar');
            }
        }
    });
    
    // Clear icons from dynamic headers
    document.querySelectorAll('#entries-table-head th .sort-icon').forEach(icon => {
        icon.className = 'sort-icon fas fa-sort ms-1 text-muted';
    });

    // Apply icon to current sort column (dynamic header)
    const activeHeader = document.querySelector(`#entries-table-head th[data-sort-key="${currentSortBy}"]`);
    if (activeHeader) {
        const icon = activeHeader.querySelector('.sort-icon');
        if (icon) {
            icon.classList.remove('fa-sort', 'text-muted');
            icon.classList.add(currentSortOrder === 'asc' ? 'fa-sort-up' : 'fa-sort-down');
            icon.classList.remove('text-muted');
        }
    } else {
        // Apply icon to dedicated button if that's the active sort
        if (currentSortBy === 'lexical_unit') {
            const btn = document.getElementById('btn-sort-lexeme');
            if(btn) btn.querySelector('i').className = `fas ${currentSortOrder === 'asc' ? 'fa-sort-alpha-down' : 'fa-sort-alpha-up'}`;
        } else if (currentSortBy === 'date_modified') {
            const btn = document.getElementById('btn-sort-date');
            if(btn) btn.querySelector('i').className = `fas ${currentSortOrder === 'asc' ? 'fa-calendar' : 'fa-calendar-check'}`;
        }
    }
}


// --- Data Loading & Display ---
function loadEntries(page = 1, sortBy = 'lexical_unit', sortOrder = 'asc') {
    currentPage = page; // Update global current page
    currentSortBy = sortBy;
    currentSortOrder = sortOrder;

    const tableHead = document.getElementById('entries-table-head');
    const entriesList = document.getElementById('entries-list');
    const colCount = visibleColumns.length;

    // Show loading state
    tableHead.innerHTML = `<tr><th colspan="${colCount}" class="text-center">Loading...</th></tr>`;
    entriesList.innerHTML = `
        <tr>
            <td colspan="${colCount}" class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading entries...</p>
            </td>
        </tr>
    `;

    const filter = document.getElementById('filter-entries').value;
    const limit = ENTRIES_CONFIG.defaultLimit;
    const offset = (page - 1) * limit;

    let url = `/api/entries/?limit=${limit}&offset=${offset}&sort_by=${sortBy}&sort_order=${sortOrder}`;
    if (filter) {
        url += `&filter_text=${encodeURIComponent(filter)}`;
    }

    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('Error fetching entries');
            return response.json();
        })
        .then(data => {
            renderTableHeaders();
            renderTableBody(data.entries);
            updatePagination(data.total_count, limit, page);
            document.getElementById('entry-count').textContent = `Showing ${data.entries.length} of ${data.total_count} entries`;
            updateSortIcons();
        })
        .catch(error => {
            console.error('Error:', error);
            entriesList.innerHTML = `
                <tr>
                        if (!entry.date_modified) {
                            console.warn('Entry missing date_modified:', entry);
                        }
                    <td colspan="${colCount}" class="text-center py-4 text-danger">
                        <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                        <p>Error loading entries. Please try again.</p>
                    </td>
                </tr>
            `;
        });
}

function renderTableHeaders() {
    const tableHead = document.getElementById('entries-table-head');
    tableHead.innerHTML = '';
    const tr = document.createElement('tr');

    ENTRIES_CONFIG.columns.forEach(colConfig => {
        if (visibleColumns.includes(colConfig.id)) {
            const th = document.createElement('th');
            th.textContent = colConfig.label;
            if (colConfig.fixedWidth) {
                th.style.width = colConfig.fixedWidth;
            }
            if (colConfig.sortable) {
                th.style.cursor = 'pointer';
                th.dataset.sortKey = colConfig.apiSortKey || colConfig.id;
                const icon = document.createElement('i');
                icon.className = 'sort-icon fas fa-sort ms-1 text-muted';
                th.appendChild(icon);
                th.addEventListener('click', function() {
                    handleSortClick(this.dataset.sortKey, null);
                });
            }
            tr.appendChild(th);
        }
    });
    tableHead.appendChild(tr);
    updateSortIcons(); // Ensure icons are correct after header render
}

function renderTableBody(entries) {
    const entriesList = document.getElementById('entries-list');
    entriesList.innerHTML = '';
    const colCount = visibleColumns.length;

    if (entries.length === 0) {
        entriesList.innerHTML = `
            <tr>
                <td colspan="${colCount}" class="text-center py-4">
                    <p>No entries found.</p>
                </td>
            </tr>
        `;
        return;
    }

    const template = document.getElementById('entry-template');

    if (entries.length > 0) {
        console.log('First entry object:', entries[0]);
    }
    entries.forEach(entry => {
        // Debug: log date_modified for each entry
        console.log(`[DEBUG] entry.id=${entry.id} date_modified=`, entry.date_modified);

        const clone = document.importNode(template.content, true);
        const tr = clone.querySelector('tr');
        tr.dataset.entryId = entry.id;

        // Clear existing cells from template, we'll add only visible ones
        tr.innerHTML = '';

        ENTRIES_CONFIG.columns.forEach(colConfig => {
            if (visibleColumns.includes(colConfig.id)) {
                const td = document.createElement('td');
                td.dataset.columnId = colConfig.id; // For easier selection later if needed

                switch (colConfig.id) {
                    case 'headword':
                        const entryLink = document.createElement('a');
                        entryLink.className = 'entry-link fw-bold';
                        let headwordText = getMultilingualField(entry.lexical_unit, ENTRIES_CONFIG.primaryLang);
                        entryLink.textContent = headwordText;
                        entryLink.href = `/entries/${entry.id}`;
                        if (entry.homograph_number) {
                            const subscript = document.createElement('sub');
                            subscript.textContent = entry.homograph_number;
                            subscript.style.fontSize = '0.8em';
                            subscript.style.color = '#6c757d';
                            entryLink.appendChild(subscript);
                        }
                        td.appendChild(entryLink);
                        break;
                    case 'citation_form':
                        // Assuming citation_form is a direct string or multilingual object
                        // For simplicity, let's assume it's entry.citation_form.text or similar
                        // This might need adjustment based on actual data structure from API
                        let citationText = '';
                        if (entry.citations && entry.citations.length > 0) {
                           citationText = getMultilingualField(entry.citations[0].form, ENTRIES_CONFIG.primaryLang);
                        }
                        td.textContent = citationText || '—';
                        break;
                    case 'part_of_speech':
                        let pos = entry.grammatical_info || (entry.senses && entry.senses.length > 0 ? entry.senses[0].grammatical_info : '');
                        const badge = document.createElement('span');
                        badge.className = 'badge bg-secondary';
                        badge.textContent = pos || '—';
                        td.appendChild(badge);
                        break;
                    case 'gloss':
                        let glossText = entry.senses && entry.senses.length > 0 ? getMultilingualField(entry.senses[0].gloss, ENTRIES_CONFIG.primaryLang) : '';
                        td.textContent = glossText || '—';
                        break;
                    case 'definition':
                        let defText = entry.senses && entry.senses.length > 0 ? getMultilingualField(entry.senses[0].definition, ENTRIES_CONFIG.primaryLang) : '';
                        td.textContent = defText || '—';
                        break;
                    case 'sense_count':
                        td.textContent = entry.senses ? entry.senses.length : 0;
                        break;
                    case 'example_count':
                        let exampleCount = 0;
                        if (entry.senses) {
                            entry.senses.forEach(sense => {
                                if (sense.examples) exampleCount += sense.examples.length;
                            });
                        }
                        td.textContent = exampleCount;
                        break;
                    case 'date_modified':
                        td.textContent = formatDate(entry.date_modified);
                        break;
                    case 'actions':
                        td.innerHTML = `
                            <div class="btn-group btn-group-sm">
                                <a href="/entries/${entry.id}/edit" class="btn btn-outline-primary edit-btn" title="Edit"><i class="fas fa-edit"></i></a>
                                <a href="/entries/${entry.id}" class="btn btn-outline-info view-btn" title="View"><i class="fas fa-eye"></i></a>
                                <button type="button" class="btn btn-outline-danger delete-btn" title="Delete"><i class="fas fa-trash"></i></button>
                            </div>`;
                        if (colConfig.fixedWidth) td.style.width = colConfig.fixedWidth;
                        break;
                    default:
                        td.textContent = 'N/A';
                }
                tr.appendChild(td);
            }
        });
        entriesList.appendChild(tr);
    });
}

// --- Utility Functions ---
function getMultilingualField(fieldValue, preferredLang) {
    if (!fieldValue) return '';
    if (typeof fieldValue === 'string') return fieldValue; // Legacy or non-multilingual
    if (typeof fieldValue === 'object') {
        if (fieldValue[preferredLang]) return fieldValue[preferredLang];
        const firstLang = Object.keys(fieldValue)[0];
        if (firstLang) return fieldValue[firstLang];
    }
    return '';
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
    if (totalPages <= 1) return;

    const createPageItem = (text, pageNum, isDisabled = false, isActive = false, isControl = false) => {
        const li = document.createElement('li');
        li.className = `page-item ${isDisabled ? 'disabled' : ''} ${isActive ? 'active' : ''}`;
        const a = document.createElement('a');
        a.className = 'page-link';
        a.href = '#';
        if (isControl) {
            a.setAttribute('aria-label', text);
            a.innerHTML = text === 'Previous' ? '<span aria-hidden="true">&laquo;</span>' : '<span aria-hidden="true">&raquo;</span>';
        } else {
            a.textContent = text;
        }
        if (!isDisabled && !isActive) {
            a.addEventListener('click', (e) => {
                e.preventDefault();
                loadEntries(pageNum, currentSortBy, currentSortOrder);
            });
        }
        li.appendChild(a);
        return li;
    };

    pagination.appendChild(createPageItem('Previous', currentPage - 1, currentPage === 1, false, true));

    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    if (endPage - startPage < 4 && totalPages > 4) {
        startPage = Math.max(1, endPage - 4);
    }

    for (let i = startPage; i <= endPage; i++) {
        pagination.appendChild(createPageItem(i.toString(), i, false, i === currentPage));
    }

    pagination.appendChild(createPageItem('Next', currentPage + 1, currentPage === totalPages, false, true));
}


function deleteEntry(entryId) {
    fetch(`/api/entries/${entryId}`, { method: 'DELETE' })
        .then(response => {
            if (!response.ok) throw new Error('Error deleting entry');
            return response.json();
        })
        .then(() => {
            showBootstrapAlert('Entry deleted successfully.', 'success');
            loadEntries(currentPage, currentSortBy, currentSortOrder); // Reload current page
        })
        .catch(error => {
            console.error('Error:', error);
            showBootstrapAlert('Failed to delete entry.', 'danger');
        });
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    let date = new Date(dateStr);
    
    // Check date is valid
    if (isNaN(date.getTime())) {
        console.warn('Invalid date format received:', dateStr);
        return 'Invalid';
    }
    
    // Use toLocaleDateString and toLocaleTimeString for better internationalization
    // Override if necessary for application-specific timezone
    return (
        date.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: '2-digit',
        }) + 
        ' ' +
        date.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: true,
        })
    );
}

function refreshEntries() {
    const refreshBtn = document.getElementById('refresh-entries-btn');
    const icon = refreshBtn.querySelector('i');
    const originalIconClass = icon.className;

    refreshBtn.disabled = true;
    icon.className = 'fas fa-sync-alt fa-spin';

    fetch('/api/entries/clear-cache', { method: 'POST' })
        .then(response => response.json())
        .then(result => {
            if (!result.success) console.warn("Cache clear might have failed, but proceeding with refresh.");
            // Always reload entries
            loadEntries(1, currentSortBy, currentSortOrder); // Reset to page 1 on refresh

            icon.className = 'fas fa-check text-success'; // Success icon
            setTimeout(() => {
                icon.className = originalIconClass;
                refreshBtn.disabled = false;
            }, 1500);
        })
        .catch(error => {
            console.error('Error refreshing entries:', error);
            loadEntries(1, currentSortBy, currentSortOrder); // Still try to reload
            icon.className = 'fas fa-exclamation-triangle text-danger'; // Error icon
             setTimeout(() => {
                icon.className = originalIconClass;
                refreshBtn.disabled = false;
            }, 2000);
        });
}

// Helper for Bootstrap alerts
function showBootstrapAlert(message, type = 'info') {
    const container = document.querySelector('.container'); // Adjust selector if needed
    if (!container) return;

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-3`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    // Insert after the first row, typically where breadcrumbs/page title might be
    const firstRow = container.querySelector('.row');
    if (firstRow && firstRow.nextSibling) {
        container.insertBefore(alertDiv, firstRow.nextSibling);
    } else if (firstRow) {
         container.appendChild(alertDiv); // Fallback if no next sibling
    } else {
        container.prepend(alertDiv); // Fallback if no row found
    }

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alertInstance = bootstrap.Alert.getOrCreateInstance(alertDiv);
        if (alertInstance) {
            alertInstance.close();
        }
    }, 5000);
}
