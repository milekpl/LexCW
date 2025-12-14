/**
 * Ranges Editor JavaScript
 * Manages the LIFT ranges editor interface
 */

class RangesEditor {
    constructor() {
        this.ranges = {};
        this.currentRangeId = null;
        this.init();
    }
    
    async init() {
        await this.loadRanges();
        this.setupEventListeners();
        this.renderTable();
    }
    
    async loadRanges() {
        try {
            const response = await fetch('/api/ranges-editor/');
            const result = await response.json();

            if (result.success) {
                this.ranges = result.data;
                // Load custom ranges and mark them
                await this.loadCustomRanges();
            } else {
                this.showError('Error loading ranges: ' + result.error);
            }
        } catch (error) {
            console.error('Failed to load ranges:', error);
            this.showError('Failed to load ranges');
        }
    }

    async loadCustomRanges() {
        try {
            const response = await fetch('/api/ranges-editor/custom');
            const result = await response.json();

            if (result.success) {
                // Mark custom ranges in the UI
                result.data.forEach(customRange => {
                    const rangeElement = document.querySelector(`tr[data-range-id="${customRange.element_id}"]`);
                    if (rangeElement) {
                        rangeElement.classList.add('custom-range');
                        rangeElement.setAttribute('data-custom-id', customRange.id);
                    }
                });
            }
        } catch (error) {
            console.error('Failed to load custom ranges:', error);
        }
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
        const tbody = document.querySelector('#rangesTable tbody');
        tbody.innerHTML = '';

        for (const [rangeId, range] of Object.entries(this.ranges)) {
            const row = document.createElement('tr');
            row.setAttribute('data-range-id', rangeId);
            row.innerHTML = `
                <td>
                    <strong>${this.escapeHtml(this.getLabel(range))}</strong>
                </td>
                <td>${range.values ? range.values.length : 0}</td>
                <td>
                    ${range.official ? '<span class="badge bg-secondary me-2">Official</span>' : '<span class="badge bg-warning text-dark me-2">Custom</span>'}
                    <button class="btn btn-sm btn-outline-primary" onclick="editor.editRange('${this.escapeHtml(rangeId)}')">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="editor.deleteRange('${this.escapeHtml(rangeId)}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        }
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
            const response = await fetch('/api/ranges-editor/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    id: rangeId,
                    labels: labels,
                    descriptions: descriptions
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Range created successfully');
                bootstrap.Modal.getInstance(document.getElementById('createRangeModal')).hide();
                await this.loadRanges();
                this.renderTable();
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
            
            container.innerHTML = `
                <div class="list-group">
                    ${elements.map(elem => `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between align-items-start">
                                <div class="flex-grow-1">
                                    <div class="d-flex align-items-center mb-1">
                                        <strong class="me-2">${this.escapeHtml(elem.id)}</strong>
                                        ${elem.abbrev ? 
                                            `<span class="badge bg-info">${this.escapeHtml(elem.abbrev)}</span>` : ''}
                                    </div>
                                    ${elem.description && elem.description.en ? 
                                        `<small class="text-muted">${this.escapeHtml(elem.description.en)}</small>` : ''}
                                </div>
                                <div class="btn-group">
                                    <button class="btn btn-sm btn-outline-primary" 
                                            onclick="editor.editElement('${this.escapeHtml(rangeId)}', '${this.escapeHtml(elem.id)}')">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" 
                                            onclick="editor.deleteElement('${this.escapeHtml(rangeId)}', '${this.escapeHtml(elem.id)}')">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
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
        
        try {
            const response = await fetch(`/api/ranges-editor/${rangeId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
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
            const response = await fetch(`/api/ranges-editor/${rangeId}`, {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
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
            document.getElementById('elementAbbrev').value = elementData.abbrev || '';
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
        } else {
            // Create mode
            title.textContent = 'New Element';
            form.reset();
            document.getElementById('elementId').readOnly = false;
            const container = document.getElementById('elementDescriptionsContainer');
            container.innerHTML = '';
            this.addElementLanguageField();
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
        
        try {
            const response = await fetch(`/api/ranges-editor/${this.currentRangeId}/elements`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    id: elementId,
                    abbrev: abbrev,
                    value: value,
                    parent: parent,
                    description: descriptions
                })
            });
            
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
        
        try {
            const response = await fetch(`/api/ranges-editor/${rangeId}/elements/${elementId}`, {
                method: 'DELETE'
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
