/**
 * Ranges Editor JavaScript
 * Manages the LIFT ranges editor interface
 */

/**
 * Get CSRF token from meta tag or DictionaryApp
 * @returns {string} The CSRF token or empty string if not available
 */
function getCsrfToken() {
    var metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
        return metaTag.getAttribute('content');
    }
    if (typeof DictionaryApp !== 'undefined' && DictionaryApp.config && DictionaryApp.config.csrfToken) {
        return DictionaryApp.config.csrfToken;
    }
    return '';
}

class RangesEditor {
    constructor() {
        this.ranges = {};
        this.currentRangeId = null;
        this.init();
    }
    
    async init() {
        await this.loadRanges();
        await this.loadProjectLanguages(); // Load project languages for language selection dropdowns
        this.setupEventListeners();
        this.renderTable();
    }
    
    async loadRanges() {
        try {
            const result = await apiGet('/api/ranges-editor/');
            console.log('[RangesEditor] loadRanges result:', result);
            this.ranges = result;
            console.log('[RangesEditor] this.ranges set to:', this.ranges);
            // Load custom ranges and mark them
            await this.loadCustomRanges();
            console.log('[RangesEditor] loadRanges complete, ranges count:', Object.keys(this.ranges).length);
        } catch (error) {
            console.error('Failed to load ranges:', error);
            this.showError('Failed to load ranges');
        }
    }

    async loadCustomRanges() {
        try {
            const result = await apiGet('/api/ranges-editor/custom');

            // Mark custom ranges in the UI
            result.forEach(customRange => {
                const rangeElement = document.querySelector(`tr[data-range-id="${customRange.element_id}"]`);
                if (rangeElement) {
                    rangeElement.classList.add('custom-range');
                    rangeElement.setAttribute('data-custom-id', customRange.id);
                }
            });
        } catch (error) {
            console.error('Failed to load custom ranges:', error);
        }
    }

    /**
     * Load project languages for language selection dropdowns
     */
    async loadProjectLanguages() {
        try {
            const response = await fetch('/api/ranges/project-languages'); // Use the new endpoint
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    // Convert the API response format (array of {code, name} objects) to internal format (array of [code, name] tuples)
                    this.projectLanguages = result.data.map(lang => [lang.code, lang.name]);
                    // Populate language dropdowns with project languages
                    this.populateLanguageDropdowns();
                }
            } else {
                // If the project languages endpoint fails, use a default set
                this.projectLanguages = [
                    ['en', 'English'],
                    ['pl', 'Polish'],
                    ['fr', 'French'],
                    ['de', 'German'],
                    ['es', 'Spanish'],
                    ['pt', 'Portuguese']
                ];
                this.populateLanguageDropdowns();
            }
        } catch (error) {
            console.warn('Failed to load project languages:', error);
            // Use default languages as fallback
            this.projectLanguages = [
                ['en', 'English'],
                ['pl', 'Polish'],
                ['fr', 'French'],
                ['de', 'German'],
                ['es', 'Spanish'],
                ['pt', 'Portuguese']
            ];
            this.populateLanguageDropdowns();
        }
    }

    /**
     * Populate language dropdowns with project languages
     */
    populateLanguageDropdowns() {
        if (!this.projectLanguages) return;

        // Populate the element language dropdown in the element modal
        const elementLangSelect = document.getElementById('elementLanguage');
        if (elementLangSelect) {
            // Get current value to preserve selection
            const currentValue = elementLangSelect.value;

            // Clear existing options except the default ones
            elementLangSelect.innerHTML = `
                <option value="" ${currentValue === '' ? 'selected' : ''}>Use system default</option>
                <option value="*" ${currentValue === '*' ? 'selected' : ''}>All languages (*)</option>
            `;

            // Add project languages
            this.projectLanguages.forEach(([code, name]) => {
                const option = document.createElement('option');
                option.value = code;
                option.textContent = `${name} (${code})`;
                option.selected = (currentValue === code);
                elementLangSelect.appendChild(option);
            });
        }
    }

    /**
     * Update language dropdown in element modal when it's shown
     * This ensures the dropdown is always populated with current project languages
     */
    updateElementLanguageDropdown() {
        if (!this.projectLanguages) return;

        // Make sure the dropdown is populated with project languages
        this.populateLanguageDropdowns();
    }
    
    setupEventListeners() {
        // Create range button
        document.getElementById('btnNewRange').addEventListener('click', () => {
            this.showCreateModal();
        });
        
        // Create range modal buttons
        document.getElementById('btnCreateRange').addEventListener('click', () => {
            this.createRange();
        });
        
        // Add language buttons
        document.getElementById('btnAddLabel').addEventListener('click', () => {
            this.addLanguageField('labelsContainer', 'labels');
        });
        
        document.getElementById('btnAddDescription').addEventListener('click', () => {
            this.addLanguageField('descriptionsContainer', 'descriptions');
        });
        
        document.getElementById('btnAddElementDescription').addEventListener('click', () => {
            this.addElementLanguageField();
        });

        document.getElementById('btnAddElementAbbrev').addEventListener('click', () => {
            this.addElementAbbrevField();
        });
        
        // Search box
        document.getElementById('searchRanges').addEventListener('input', (e) => {
            this.filterRanges(e.target.value);
        });
        
        // Remove language field buttons (delegated)
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-remove-lang')) {
                e.target.closest('.input-group').remove();
            }
        });
        
        // Migration strategy radio buttons
        document.querySelectorAll('input[name="migrationStrategy"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const replaceSelect = document.getElementById('replaceRangeSelect');
                if (e.target.value === 'replace') {
                    replaceSelect.style.display = 'block';
                } else {
                    replaceSelect.style.display = 'none';
                }
            });
        });
        
        // New element button
        document.getElementById('btnNewElement').addEventListener('click', () => {
            this.showElementModal();
        });
        
        // Save element button
        document.getElementById('btnSaveElement').addEventListener('click', () => {
            this.saveElement();
        });
        
        // Save edited range
        document.getElementById('btnSaveRange').addEventListener('click', () => {
            this.saveRange();
        });
        
        // Delete confirmation
        document.getElementById('btnConfirmDelete').addEventListener('click', () => {
            this.confirmDelete();
        });
    }
    
    renderTable() {
        console.log('[RangesEditor] renderTable called, this.ranges:', this.ranges);
        const tbody = document.querySelector('#rangesTable tbody');
        tbody.innerHTML = '';
        let rowCount = 0;

        for (const [rangeId, range] of Object.entries(this.ranges)) {
            const row = document.createElement('tr');
            row.setAttribute('data-range-id', rangeId);
            rowCount++;
            row.innerHTML = `
                <td>
                    <strong>${this.escapeHtml(this.getLabel(range))}</strong>
                </td>
                <td>${range.values ? range.values.length : 0}</td>
                <td>
                    ${range.official ? '<span class="badge bg-secondary me-2">Official</span>' : '<span class="badge bg-warning text-dark me-2">Custom</span>'}
                    <button class="btn btn-sm btn-outline-primary" title="Edit"
                            onclick="editor.editRange('${this.escapeHtml(rangeId)}')">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" title="Delete"
                            onclick="editor.deleteRange('${this.escapeHtml(rangeId)}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        }
        console.log('[RangesEditor] renderTable complete, created', rowCount, 'rows');
    }

    filterRanges(searchText) {
        const rows = document.querySelectorAll('#rangesTable tbody tr');
        const search = searchText.toLowerCase();
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            if (text.includes(search)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
    
    getLabel(range) {
        // Prefer explicit label field (set in LIFT or editor) when meaningful
        if (range.label && range.label !== range.id) {
            return range.label;
        }

        // Next, try multilingual labels from the range data
        if (range.labels && range.labels.en) {
            return range.labels.en;
        }
        if (range.labels) {
            const first = Object.keys(range.labels)[0];
            if (first) return range.labels[first];
        }

        // Descriptions can be used as a fallback
        if (range.description && range.description.en) {
            return range.description.en;
        }
        if (range.description) {
            const firstLang = Object.keys(range.description)[0];
            if (firstLang) return range.description[firstLang];
        }

        // If provided by config (FieldWorks-only ranges), use that label if present
        if (range.provided_by_config && range.label) {
            return range.label;
        }

        // Final fallback: humanize the id (replace dashes/underscores and title-case)
        if (range.id) {
            return range.id.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        }

        return '(No label)';
    }
    
    showCreateModal() {
        // Reset form
        document.getElementById('createRangeForm').reset();
        document.getElementById('rangeId').classList.remove('is-invalid');
        
        const modal = new bootstrap.Modal(document.getElementById('createRangeModal'));
        modal.show();
    }
    
    addLanguageField(containerId, groupName) {
        const container = document.getElementById(containerId);
        const div = document.createElement('div');
        div.className = 'input-group mb-2';
        div.setAttribute('data-lang-group', groupName);
        div.innerHTML = `
            <select class="form-select lang-select" style="max-width: 100px">
                <option value="en">en</option>
                <option value="pl">pl</option>
                <option value="pt">pt</option>
                <option value="fr">fr</option>
                <option value="es">es</option>
            </select>
            <input type="text" class="form-control lang-text" placeholder="Text">
            <button type="button" class="btn btn-outline-danger btn-remove-lang">
                <i class="bi bi-trash"></i>
            </button>
        `;
        container.appendChild(div);
    }
    
    collectMultilingualData(containerId) {
        const container = document.getElementById(containerId);
        const inputs = container.querySelectorAll('.input-group');
        const data = {};
        
        inputs.forEach(group => {
            const lang = group.querySelector('.lang-select').value;
            const text = group.querySelector('.lang-text').value.trim();
            if (text) {
                data[lang] = text;
            }
        });
        
        return data;
    }
    
    async createRange() {
        // Get form data
        const rangeId = document.getElementById('rangeId').value.trim();
        const labels = this.collectMultilingualData('labelsContainer');
        const descriptions = this.collectMultilingualData('descriptionsContainer');

        // Validate
        if (!rangeId || Object.keys(labels).length === 0) {
            this.showError('Range ID and at least one label are required');
            return;
        }

        // Call API
        try {
            const csrfToken = getCsrfToken();
            const response = await fetch('/api/ranges-editor/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({
                    id: rangeId,
                    labels: labels,
                    descriptions: descriptions
                })
            });

            const result = await response.json();
            console.log('[RangesEditor] createRange result:', result);

            if (result.success) {
                this.showSuccess('Range created successfully');
                console.log('[RangesEditor] Hiding modal and reloading ranges...');
                bootstrap.Modal.getInstance(document.getElementById('createRangeModal')).hide();
                await this.loadRanges();
                console.log('[RangesEditor] Reload complete, calling renderTable...');
                this.renderTable();
                console.log('[RangesEditor] renderTable complete');
            } else {
                if (result.error.includes('already exists')) {
                    document.getElementById('rangeId').classList.add('is-invalid');
                }
                this.showError('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Failed to create range:', error);
            this.showError('Failed to create range');
        }
    }
    
    async editRange(rangeId) {
        this.currentRangeId = rangeId;
        
        try {
            const response = await fetch(`/api/ranges-editor/${rangeId}`);
            const result = await response.json();
            
            if (!result.success) {
                this.showError('Failed to load range: ' + result.error);
                return;
            }
            
            const range = result.data;
            
            // Populate form
            document.getElementById('editRangeId').textContent = rangeId;
            document.getElementById('editRangeGuid').value = range.guid || '';

            // Show canonical ID and source badge
            document.getElementById('editRangeOriginalId').textContent = range.id || rangeId;
            const badge = document.getElementById('rangeSourceBadge');
            if (range.provided_by_config) {
                badge.textContent = 'FieldWorks (custom)';
                badge.className = 'badge bg-info ms-2';
            } else if (range.fieldworks_standard) {
                // Range is a known FieldWorks standard (declared in metadata)
                badge.textContent = 'FieldWorks (standard)';
                badge.className = 'badge bg-secondary ms-2';
            } else if (range.official) {
                badge.textContent = 'LIFT';
                badge.className = 'badge bg-secondary ms-2';
            } else {
                badge.textContent = 'Custom';
                badge.className = 'badge bg-warning text-dark ms-2';
            }

            // Populate labels (use multilingual labels if present, otherwise use single 'label' fallback)
            const labelsContainer = document.getElementById('editLabelsContainer');
            labelsContainer.innerHTML = '';
            if (range.labels && Object.keys(range.labels).length > 0) {
                for (const [lang, text] of Object.entries(range.labels)) {
                    this.addEditLanguageField('editLabelsContainer', 'labels', lang, text);
                }
            } else if (range.label && typeof range.label === 'string' && range.label !== range.id) {
                this.addEditLanguageField('editLabelsContainer', 'labels', 'en', range.label);
            } else {
                // empty label field for user to add
                this.addEditLanguageField('editLabelsContainer', 'labels');
            }
            
            // Load elements
            await this.loadElements(rangeId);
            
            // Load usage
            await this.loadUsage(rangeId);
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('editRangeModal'));
            modal.show();
            
        } catch (error) {
            console.error('Failed to load range:', error);
            this.showError('Failed to load range');
        }
    }
    
    addEditLanguageField(containerId, groupName, lang = 'en', text = '') {
        const container = document.getElementById(containerId);
        const div = document.createElement('div');
        div.className = 'input-group mb-2';
        div.setAttribute('data-lang-group', groupName);
        div.innerHTML = `
            <select class="form-select lang-select" style="max-width: 100px">
                <option value="en" ${lang === 'en' ? 'selected' : ''}>en</option>
                <option value="pl" ${lang === 'pl' ? 'selected' : ''}>pl</option>
                <option value="pt" ${lang === 'pt' ? 'selected' : ''}>pt</option>
                <option value="fr" ${lang === 'fr' ? 'selected' : ''}>fr</option>
            </select>
            <input type="text" class="form-control lang-text" value="${this.escapeHtml(text)}">
            <button type="button" class="btn btn-outline-danger btn-remove-lang">
                <i class="bi bi-trash"></i>
            </button>
        `;
        container.appendChild(div);
    }
    
    async loadElements(rangeId) {
        try {
            const response = await fetch(`/api/ranges-editor/${rangeId}/elements`);
            const result = await response.json();
            
            if (!result.success) {
                document.getElementById('elementsContainer').innerHTML = 
                    `<p class="text-danger">Error loading elements: ${result.error}</p>`;
                return;
            }
            
            const elements = result.data;
            const container = document.getElementById('elementsContainer');

            if (!elements || elements.length === 0) {
                container.innerHTML = '<p class="text-muted">No elements defined</p>';
                return;
            }

            // Recursive renderer for elements and children
            const renderElement = (elem) => {
                const abbrev = elem.effective_abbrev || elem.abbrev || (elem.abbrevs ? (elem.abbrevs['en'] || Object.values(elem.abbrevs)[0]) : '');
                const label = elem.effective_label || (elem.labels && (elem.labels.en || Object.values(elem.labels)[0])) || elem.value || elem.id;

                const badges = [];
                if (abbrev) {
                    badges.push(`<span class="badge bg-info me-1">${this.escapeHtml(abbrev)}</span>`);
                }
                if (elem.abbrevs && Object.keys(elem.abbrevs).length > 0) {
                    badges.push(Object.entries(elem.abbrevs).map(([lang, abbr]) =>
                        `<span class="badge bg-secondary me-1" title="${this.escapeHtml(lang)}">${this.escapeHtml(abbr)}</span>`
                    ).join(''));
                }

                const desc = (elem.description && (elem.description.en || Object.values(elem.description)[0])) ?
                    `<small class="text-muted">${this.escapeHtml(elem.description.en || Object.values(elem.description)[0])}</small>` : '';

                let html = `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <div class="d-flex align-items-center mb-1">
                                    <strong class="me-2">${this.escapeHtml(elem.id)}</strong>
                                    ${badges.join('')}
                                    <small class="text-muted ms-2">${this.escapeHtml(label)}</small>
                                </div>
                                ${desc}
                            </div>
                            <div class="btn-group">
                                <button class="btn btn-sm btn-outline-primary" title="Edit"
                                        onclick="editor.editElement('${this.escapeHtml(rangeId)}', '${this.escapeHtml(elem.id)}')">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger" title="Delete"
                                        onclick="editor.deleteElement('${this.escapeHtml(rangeId)}', '${this.escapeHtml(elem.id)}')">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `;

                if (elem.children && elem.children.length > 0) {
                    html += `<div class="ms-3">
                                <div class="list-group">
                                    ${elem.children.map(child => renderElement(child)).join('')}
                                </div>
                             </div>`;
                }

                return html;
            };

            container.innerHTML = `
                <div class="list-group">
                    ${elements.map(elem => renderElement(elem)).join('')}
                </div>
            `;
            
        } catch (error) {
            console.error('Failed to load elements:', error);
            document.getElementById('elementsContainer').innerHTML = 
                '<p class="text-danger">Failed to load elements</p>';
        }
    }
    
    async loadUsage(rangeId) {
        try {
            const response = await fetch(`/api/ranges-editor/${rangeId}/usage`);
            const result = await response.json();
            
            if (!result.success) {
                document.getElementById('usageContainer').innerHTML = 
                    `<p class="text-danger">Error loading usage: ${result.error}</p>`;
                return;
            }
            
            const usage = result.data;
            const container = document.getElementById('usageContainer');
            
            // Check if we got grouped stats or simple list
            if (usage.elements) {
                // Grouped by element
                const elementCount = Object.keys(usage.elements).length;
                
                if (elementCount === 0) {
                    container.innerHTML = '<p class="text-success">This range is not currently in use</p>';
                    return;
                }
                
                container.innerHTML = `
                    <div class="alert alert-info">
                        This range has <strong>${elementCount}</strong> element(s) in use across <strong>${usage.total_entries}</strong> entries
                    </div>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Element</th>
                                    <th>Label</th>
                                    <th class="text-end">Count</th>
                                    <th>Sample Entries</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${Object.entries(usage.elements).map(([elementId, data]) => `
                                    <tr>
                                        <td><code>${this.escapeHtml(elementId)}</code></td>
                                        <td>${this.escapeHtml(data.label)}</td>
                                        <td class="text-end"><span class="badge bg-primary">${data.count}</span></td>
                                        <td>
                                            <small class="text-muted">
                                                ${data.sample_entries.slice(0, 3).map(entry => 
                                                    this.escapeHtml(entry.headword)
                                                ).join(', ')}
                                                ${data.sample_entries.length > 3 ? '...' : ''}
                                            </small>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    <p class="text-muted small mt-2">
                        <i class="bi bi-info-circle"></i> Elements not listed here are not currently used and can be safely deleted.
                    </p>
                `;
            } else if (Array.isArray(usage)) {
                // Simple list (for specific element)
                if (usage.length === 0) {
                    container.innerHTML = '<p class="text-success">Not currently in use</p>';
                    return;
                }
                
                container.innerHTML = `
                    <div class="alert alert-info">
                        Used in <strong>${usage.length}</strong> entries
                    </div>
                    <div class="list-group">
                        ${usage.slice(0, 10).map(item => `
                            <div class="list-group-item">
                                <strong>${this.escapeHtml(item.entry_id)}</strong>: ${this.escapeHtml(item.headword)}
                                <span class="badge bg-secondary">${item.count} occurrence(s)</span>
                            </div>
                        `).join('')}
                        ${usage.length > 10 ? `<p class="mt-2 text-muted">...and ${usage.length - 10} more</p>` : ''}
                    </div>
                `;
            }
            
        } catch (error) {
            console.error('Failed to load usage:', error);
            document.getElementById('usageContainer').innerHTML = 
                '<p class="text-danger">Failed to load usage information</p>';
        }
    }
    
    async saveRange() {
        const rangeId = this.currentRangeId;
        const guid = document.getElementById('editRangeGuid').value;
        const labels = this.collectMultilingualData('editLabelsContainer');
        const csrfToken = getCsrfToken();

        try {
            const response = await fetch(`/api/ranges-editor/${rangeId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({
                    guid: guid,
                    labels: labels
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Range updated successfully');
                bootstrap.Modal.getInstance(document.getElementById('editRangeModal')).hide();
                await this.loadRanges();
                this.renderTable();
            } else {
                this.showError('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Failed to save range:', error);
            this.showError('Failed to save range');
        }
    }
    
    async deleteRange(rangeId) {
        this.currentRangeId = rangeId;
        
        // Load usage information
        try {
            const response = await fetch(`/api/ranges-editor/${rangeId}/usage`);
            const result = await response.json();
            
            if (result.success && result.data && result.data.length > 0) {
                // Show usage warning
                document.getElementById('deleteUsageWarning').style.display = 'block';
                document.getElementById('deleteUsageCount').textContent = result.data.length;
                
                // Populate replacement range dropdown
                const select = document.getElementById('replacementRange');
                select.innerHTML = '<option value="">Select replacement...</option>';
                for (const [id, range] of Object.entries(this.ranges)) {
                    if (id !== rangeId) {
                        select.innerHTML += `<option value="${id}">${this.escapeHtml(id)}</option>`;
                    }
                }
            } else {
                document.getElementById('deleteUsageWarning').style.display = 'none';
            }
            
            document.getElementById('deleteRangeName').textContent = rangeId;
            const modal = new bootstrap.Modal(document.getElementById('deleteRangeModal'));
            modal.show();
            
        } catch (error) {
            console.error('Failed to check usage:', error);
            this.showError('Failed to check usage');
        }
    }
    
    async confirmDelete() {
        const rangeId = this.currentRangeId;
        const usageWarning = document.getElementById('deleteUsageWarning');
        let migration = null;
        
        if (usageWarning.style.display !== 'none') {
            // Range is in use, need migration strategy
            const strategy = document.querySelector('input[name="migrationStrategy"]:checked').value;
            
            if (strategy === 'replace') {
                const newValue = document.getElementById('replacementRange').value;
                if (!newValue) {
                    this.showError('Please select a replacement range');
                    return;
                }
                migration = {
                    operation: 'replace',
                    new_value: newValue
                };
            } else {
                migration = {
                    operation: 'remove'
                };
            }
        }

        try {
            const csrfToken = getCsrfToken();
            const response = await fetch(`/api/ranges-editor/${rangeId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({ migration: migration })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Range deleted successfully');
                bootstrap.Modal.getInstance(document.getElementById('deleteRangeModal')).hide();
                await this.loadRanges();
                this.renderTable();
            } else {
                this.showError('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Failed to delete range:', error);
            this.showError('Failed to delete range');
        }
    }
    
    showElementModal(elementData = null) {
        const modal = document.getElementById('elementModal');
        const title = document.getElementById('elementModalTitle');
        const form = document.getElementById('elementForm');
        
        if (elementData) {
            // Edit mode
            title.textContent = 'Edit Element';
            document.getElementById('elementId').value = elementData.id;
            document.getElementById('elementId').readOnly = true;
            // Set single abbreviation field (for backward compatibility)
            document.getElementById('elementAbbrev').value = elementData.abbrev || '';
            // If there are multilingual abbreviations, we'll use the 'en' one as default, or first available
            if (elementData.abbrevs && Object.keys(elementData.abbrevs).length > 0) {
                if (elementData.abbrevs['en']) {
                    document.getElementById('elementAbbrev').value = elementData.abbrevs['en'];
                } else {
                    // Use first available abbreviation
                    const firstLang = Object.keys(elementData.abbrevs)[0];
                    if (firstLang) {
                        document.getElementById('elementAbbrev').value = elementData.abbrevs[firstLang];
                    }
                }
            }
            document.getElementById('elementValue').value = elementData.value || '';
            document.getElementById('elementParent').value = elementData.parent || '';
            
            // Populate descriptions
            const container = document.getElementById('elementDescriptionsContainer');
            container.innerHTML = '';
            if (elementData.description) {
                for (const [lang, text] of Object.entries(elementData.description)) {
                    this.addElementLanguageField(lang, text);
                }
            } else {
                this.addElementLanguageField();
            }

            // Populate multilingual abbreviations
            const abbrevsContainer = document.getElementById('elementAbbrevsContainer');
            abbrevsContainer.innerHTML = '';
            if (elementData.abbrevs) {
                for (const [lang, abbr] of Object.entries(elementData.abbrevs)) {
                    this.addElementAbbrevField(lang, abbr);
                }
            } else {
                this.addElementAbbrevField();
            }

            // Set the display language if available
            if (elementData.language) {
                document.getElementById('elementLanguage').value = elementData.language;
            } else {
                document.getElementById('elementLanguage').value = '';
            }
        } else {
            // Create mode
            title.textContent = 'New Element';
            form.reset();
            document.getElementById('elementId').readOnly = false;
            document.getElementById('elementLanguage').value = ''; // Default to empty (use system default)
            const container = document.getElementById('elementDescriptionsContainer');
            container.innerHTML = '';
            this.addElementLanguageField();

            // Initialize multilingual abbreviations container for create mode
            const abbrevsContainer = document.getElementById('elementAbbrevsContainer');
            abbrevsContainer.innerHTML = '';
            this.addElementAbbrevField();
        }

        new bootstrap.Modal(modal).show();
    }
    
    addElementLanguageField(lang = 'en', text = '') {
        const container = document.getElementById('elementDescriptionsContainer');
        const div = document.createElement('div');
        div.className = 'input-group mb-2';
        div.setAttribute('data-lang-group', 'element-descriptions');
        div.innerHTML = `
            <select class="form-select lang-select" style="max-width: 100px">
                <option value="en" ${lang === 'en' ? 'selected' : ''}>en</option>
                <option value="pl" ${lang === 'pl' ? 'selected' : ''}>pl</option>
                <option value="pt" ${lang === 'pt' ? 'selected' : ''}>pt</option>
            </select>
            <input type="text" class="form-control lang-text" placeholder="Description" value="${this.escapeHtml(text)}">
            <button type="button" class="btn btn-outline-danger btn-remove-lang">
                <i class="bi bi-trash"></i>
            </button>
        `;
        container.appendChild(div);
    }

    addElementAbbrevField(lang = 'en', abbr = '') {
        const container = document.getElementById('elementAbbrevsContainer');
        const div = document.createElement('div');
        div.className = 'input-group mb-2';
        div.setAttribute('data-lang-group', 'element-abbrevs');
        div.innerHTML = `
            <select class="form-select lang-select" style="max-width: 100px">
                <option value="en" ${lang === 'en' ? 'selected' : ''}>en</option>
                <option value="pl" ${lang === 'pl' ? 'selected' : ''}>pl</option>
                <option value="pt" ${lang === 'pt' ? 'selected' : ''}>pt</option>
            </select>
            <input type="text" class="form-control lang-text" placeholder="Abbreviation" value="${this.escapeHtml(abbr)}">
            <button type="button" class="btn btn-outline-danger btn-remove-lang">
                <i class="bi bi-trash"></i>
            </button>
        `;
        container.appendChild(div);
    }
    
    async editElement(rangeId, elementId) {
        try {
            const response = await fetch(`/api/ranges-editor/${rangeId}/elements/${elementId}`);
            const result = await response.json();
            
            if (!result.success) {
                this.showError('Failed to load element: ' + result.error);
                return;
            }
            
            this.showElementModal(result.data);
        } catch (error) {
            console.error('Failed to load element:', error);
            this.showError('Failed to load element');
        }
    }
    
    async saveElement() {
        const elementId = document.getElementById('elementId').value.trim();
        const abbrev = document.getElementById('elementAbbrev').value.trim();
        const value = document.getElementById('elementValue').value.trim();
        const parent = document.getElementById('elementParent').value.trim();
        const isEdit = document.getElementById('elementId').readOnly; // If ID field is read-only, it's edit mode

        if (!elementId) {
            this.showError('Element ID is required');
            return;
        }

        // Collect descriptions
        const descriptions = {};
        document.querySelectorAll('#elementDescriptionsContainer [data-lang-group="element-descriptions"]').forEach(group => {
            const lang = group.querySelector('.lang-select').value;
            const text = group.querySelector('.lang-text').value.trim();
            if (text) {
                descriptions[lang] = text;
            }
        });

        // Collect multilingual abbreviations
        const abbrevs = {};
        document.querySelectorAll('#elementAbbrevsContainer [data-lang-group="element-abbrevs"]').forEach(group => {
            const lang = group.querySelector('.lang-select').value;
            const abbr = group.querySelector('.lang-text').value.trim();
            if (abbr) {
                abbrevs[lang] = abbr;
            }
        });

        // Get the selected display language
        const elementLanguage = document.getElementById('elementLanguage').value;
        const csrfToken = getCsrfToken();
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': csrfToken
        };

        try {
            let response;
            if (isEdit) {
                // Update existing element
                response = await fetch(`/api/ranges-editor/${this.currentRangeId}/elements/${elementId}`, {
                    method: 'PUT',
                    headers: headers,
                    body: JSON.stringify({
                        abbrev: abbrev,
                        abbrevs: abbrevs,
                        value: value,
                        parent: parent,
                        language: elementLanguage || undefined, // Only send if not empty
                        description: descriptions
                    })
                });
            } else {
                // Create new element
                response = await fetch(`/api/ranges-editor/${this.currentRangeId}/elements`, {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({
                        id: elementId,
                        abbrev: abbrev,
                        abbrevs: abbrevs,
                        value: value,
                        parent: parent,
                        language: elementLanguage || undefined, // Only send if not empty
                        description: descriptions
                    })
                });
            }

            const result = await response.json();

            if (result.success) {
                this.showSuccess('Element saved successfully');
                bootstrap.Modal.getInstance(document.getElementById('elementModal')).hide();
                await this.loadElements(this.currentRangeId);
            } else {
                this.showError('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Failed to save element:', error);
            this.showError('Failed to save element');
        }
    }
    
    async deleteElement(rangeId, elementId) {
        if (!confirm(`Delete element "${elementId}"?`)) {
            return;
        }

        const csrfToken = getCsrfToken();
        try {
            const response = await fetch(`/api/ranges-editor/${rangeId}/elements/${elementId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRF-TOKEN': csrfToken
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Element deleted successfully');
                await this.loadElements(rangeId);
            } else {
                this.showError('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Failed to delete element:', error);
            this.showError('Failed to delete element');
        }
    }
    
    showError(message) {
        // Simple alert for now - could be improved with toast notifications
        alert(message);
    }
    
    showSuccess(message) {
        // Simple alert for now - could be improved with toast notifications
        alert(message);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize on page load
let editor;
document.addEventListener('DOMContentLoaded', () => {
    editor = new RangesEditor();
});
