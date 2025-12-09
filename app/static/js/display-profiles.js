/**
 * Display Profiles Management
 * Handles CRUD operations, drag-and-drop reordering, and live preview
 */

(function() {
    'use strict';

    // State management
    const state = {
        profiles: [],
        currentProfile: null,
        elementRegistry: null,
        sortableInstance: null,
        previewEntry: null
    };

    // API endpoints
    const API = {
        profiles: '/api/profiles',
        registry: '/api/lift',
        display: '/api/display'
    };

    /**
     * Initialize the page
     */
    async function init() {
        try {
            // Load element registry
            await loadElementRegistry();
            
            // Load profiles
            await loadProfiles();
            
            // Set up event listeners
            setupEventListeners();
            
            // Load preview entry
            await loadPreviewEntry();
            
        } catch (error) {
            console.error('Initialization error:', error);
            showError('Failed to initialize page: ' + error.message);
        }
    }

    /**
     * Load LIFT element registry
     */
    async function loadElementRegistry() {
        try {
            const response = await fetch(`${API.registry}/elements/displayable`);
            if (!response.ok) throw new Error('Failed to load element registry');
            
            const data = await response.json();
            state.elementRegistry = data.elements;
            
        } catch (error) {
            console.error('Error loading registry:', error);
            throw error;
        }
    }

    /**
     * Load all profiles
     */
    async function loadProfiles() {
        try {
            console.log('Fetching profiles from:', API.profiles);
            const response = await fetch(API.profiles);
            
            console.log('Response status:', response.status);
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Error response:', errorText);
                throw new Error(`Failed to load profiles: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Profiles loaded:', data);
            state.profiles = data.profiles || [];
            
            renderProfiles();
            
        } catch (error) {
            console.error('Error loading profiles:', error);
            showError('Failed to load profiles: ' + error.message);
            // Clear loading spinners
            document.getElementById('userProfilesList').innerHTML = '<p class="text-danger">Failed to load profiles. Please refresh the page.</p>';
            document.getElementById('systemProfilesList').innerHTML = '<p class="text-danger">Failed to load profiles. Please refresh the page.</p>';
        }
    }

    /**
     * Render profiles list
     */
    function renderProfiles() {
        const userProfiles = state.profiles.filter(p => !p.is_system);
        const systemProfiles = state.profiles.filter(p => p.is_system);
        
        renderProfileList('userProfilesList', userProfiles, false);
        renderProfileList('systemProfilesList', systemProfiles, true);
    }

    /**
     * Render a profile list
     */
    function renderProfileList(containerId, profiles, isSystem) {
        const container = document.getElementById(containerId);
        
        if (profiles.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No ${isSystem ? 'system' : 'user'} profiles found</p>
                    ${!isSystem ? '<button class="btn btn-primary btn-sm" id="btnCreateFirstProfile">Create Your First Profile</button>' : ''}
                </div>
            `;
            if (!isSystem) {
                container.querySelector('#btnCreateFirstProfile')?.addEventListener('click', () => showProfileModal());
            }
            return;
        }
        
        container.innerHTML = profiles.map(profile => createProfileCard(profile, isSystem)).join('');
        
        // Attach event listeners to profile cards
        profiles.forEach(profile => {
            const card = container.querySelector(`[data-profile-id="${profile.id}"]`);
            if (card) {
                attachProfileCardListeners(card, profile);
            }
        });
    }

    /**
     * Create HTML for a profile card
     */
    function createProfileCard(profile, isSystem) {
        const defaultBadge = profile.is_default ? '<span class="badge bg-primary profile-badge">Default</span>' : '';
        const systemBadge = isSystem ? '<span class="badge bg-secondary profile-badge">System</span>' : '';
        const elementCount = profile.elements ? profile.elements.length : 0;
        
        return `
            <div class="profile-card ${profile.is_default ? 'default' : ''} ${isSystem ? 'system' : ''}" data-profile-id="${profile.id}">
                <div class="profile-card-header">
                    <div>
                        <span class="profile-name">${escapeHtml(profile.name)}</span>
                        ${defaultBadge}
                        ${systemBadge}
                    </div>
                    <div class="profile-actions">
                        ${!isSystem ? `
                            <button class="btn btn-sm btn-outline-primary btn-edit" title="Edit">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-secondary btn-duplicate" title="Duplicate">
                                <i class="fas fa-copy"></i>
                            </button>
                            ${!profile.is_default ? `
                                <button class="btn btn-sm btn-outline-info btn-set-default" title="Set as Default">
                                    <i class="fas fa-star"></i>
                                </button>
                            ` : ''}
                            <button class="btn btn-sm btn-outline-success btn-export" title="Export">
                                <i class="fas fa-download"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger btn-delete" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : `
                            <button class="btn btn-sm btn-outline-secondary btn-view" title="View">
                                <i class="fas fa-eye"></i>
                            </button>
                        `}
                    </div>
                </div>
                ${profile.description ? `<div class="profile-description">${escapeHtml(profile.description)}</div>` : ''}
                <div class="profile-meta">
                    <i class="fas fa-layer-group"></i> ${elementCount} elements
                    <span class="ms-3"><i class="fas fa-clock"></i> Updated ${formatDate(profile.updated_at)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners to profile card buttons
     */
    function attachProfileCardListeners(card, profile) {
        card.querySelector('.btn-edit')?.addEventListener('click', () => editProfile(profile));
        card.querySelector('.btn-view')?.addEventListener('click', () => viewProfile(profile));
        card.querySelector('.btn-duplicate')?.addEventListener('click', () => duplicateProfile(profile));
        card.querySelector('.btn-set-default')?.addEventListener('click', () => setDefaultProfile(profile));
        card.querySelector('.btn-export')?.addEventListener('click', () => exportProfile(profile));
        card.querySelector('.btn-delete')?.addEventListener('click', () => deleteProfile(profile));
    }

    /**
     * Show profile modal for create/edit
     */
    function showProfileModal(profile = null) {
        state.currentProfile = profile;
        
        const modal = new bootstrap.Modal(document.getElementById('profileModal'));
        const form = document.getElementById('profileForm');
        const title = document.getElementById('profileModalLabel');
        
        // Reset form
        form.reset();
        
        if (profile) {
            // Edit mode
            title.textContent = 'Edit Display Profile';
            document.getElementById('profileId').value = profile.id;
            document.getElementById('profileName').value = profile.name;
            document.getElementById('profileDescription').value = profile.description || '';
            document.getElementById('profileCustomCSS').value = profile.custom_css || '';
            document.getElementById('showSubentries').checked = profile.show_subentries || false;
            document.getElementById('numberSenses').checked = profile.number_senses !== false;  // Default true
            document.getElementById('isDefault').checked = profile.is_default;
            
            // Load elements
            renderElementConfig(profile.elements || []);
        } else {
            // Create mode
            title.textContent = 'Create Display Profile';
            document.getElementById('profileId').value = '';
            document.getElementById('numberSenses').checked = true;  // Default true for new profiles
            renderElementConfig([]);
        }
        
        setupSortable();
        modal.show();
    }

    /**
     * Render element configuration panel
     */
    function renderElementConfig(elements) {
        const container = document.getElementById('elementConfigContainer');
        
        if (elements.length === 0) {
            container.innerHTML = `
                <div class="text-muted text-center py-3">
                    <i class="fas fa-info-circle"></i> Click "Add Element" to configure display
                </div>
            `;
            return;
        }
        
        container.innerHTML = elements
            .sort((a, b) => (a.display_order || a.order || 0) - (b.display_order || b.order || 0))
            .map((elem, index) => createElementConfigItem(elem, index))
            .join('');
        
        // Attach event listeners
        container.querySelectorAll('.element-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.currentTarget.closest('.element-config-item').remove();
                updatePreview();
            });
        });
        
        container.querySelectorAll('.element-controls input, .element-controls select').forEach(input => {
            input.addEventListener('change', updatePreview);
        });
    }

    /**
     * Create HTML for an element config item
     */
    function createElementConfigItem(elem, index) {
        const elementName = elem.lift_element || elem.element;
        const registryElem = state.elementRegistry?.find(e => e.name === elementName);
        const displayName = registryElem?.display_name || elementName;
        const displayMode = elem.config?.display_mode || 'inline';
        const abbrFormat = elem.config?.abbr_format || 'abbr';
        
        // Check if this element is a range element (grammatical-info, etc.)
        const isRangeElement = elementName === 'grammatical-info' || registryElem?.type === 'range';
        
        return `
            <div class="element-config-item" data-element="${elementName}" data-order="${index}">
                <span class="drag-handle"><i class="fas fa-grip-vertical"></i></span>
                <div class="element-name">
                    <strong>${displayName}</strong>
                    <input type="hidden" name="elements[${index}][lift_element]" value="${elementName}">
                </div>
                <div class="element-controls">
                    <input type="text" 
                           class="form-control form-control-sm" 
                           name="elements[${index}][css_class]" 
                           value="${elem.css_class || ''}" 
                           placeholder="CSS classes"
                           title="CSS classes to apply">
                    <select class="form-select form-select-sm" name="elements[${index}][visibility]" title="Visibility">
                        <option value="always" ${elem.visibility === 'always' ? 'selected' : ''}>Always</option>
                        <option value="if-content" ${(!elem.visibility || elem.visibility === 'if-content') ? 'selected' : ''}>If Content</option>
                        <option value="never" ${elem.visibility === 'never' ? 'selected' : ''}>Never</option>
                    </select>
                    <select class="form-select form-select-sm" name="elements[${index}][display_mode]" title="Display Mode">
                        <option value="inline" ${displayMode === 'inline' ? 'selected' : ''}>Inline</option>
                        <option value="block" ${displayMode === 'block' ? 'selected' : ''}>Block</option>
                    </select>
                    ${isRangeElement ? `
                    <select class="form-select form-select-sm" name="elements[${index}][abbr_format]" title="Abbreviation Format">
                        <option value="abbr" ${abbrFormat === 'abbr' ? 'selected' : ''}>Abbr</option>
                        <option value="label" ${abbrFormat === 'label' ? 'selected' : ''}>Label</option>
                        <option value="full" ${abbrFormat === 'full' ? 'selected' : ''}>Full</option>
                    </select>
                    ` : ''}
                    <input type="text" 
                           class="form-control form-control-sm" 
                           name="elements[${index}][language_filter]" 
                           value="${elem.language_filter || '*'}" 
                           placeholder="Lang (*=all)"
                           style="width: 90px;"
                           title="Language filter (* for all, 'en', 'pl', etc.)">
                    <input type="number" 
                           class="form-control form-control-sm" 
                           name="elements[${index}][display_order]" 
                           value="${elem.display_order || elem.order || index}" 
                           style="width: 70px;" 
                           placeholder="Order"
                           title="Display order">
                    <input type="text" 
                           class="form-control form-control-sm" 
                           name="elements[${index}][prefix]" 
                           value="${elem.prefix || ''}" 
                           placeholder="Prefix"
                           style="width: 90px;"
                           title="Text before element">
                    <input type="text" 
                           class="form-control form-control-sm" 
                           name="elements[${index}][suffix]" 
                           value="${elem.suffix || ''}" 
                           placeholder="Suffix"
                           style="width: 90px;"
                           title="Text after element">
                </div>
                <span class="element-remove" title="Remove element"><i class="fas fa-times"></i></span>
            </div>
        `;
    }

    /**
     * Setup drag-and-drop with SortableJS
     */
    function setupSortable() {
        const container = document.getElementById('elementConfigContainer');
        
        if (state.sortableInstance) {
            state.sortableInstance.destroy();
        }
        
        state.sortableInstance = new Sortable(container, {
            handle: '.drag-handle',
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            onEnd: function() {
                updateElementOrders();
                updatePreview();
            }
        });
    }

    /**
     * Update element order numbers after drag-and-drop
     */
    function updateElementOrders() {
        const items = document.querySelectorAll('.element-config-item');
        items.forEach((item, index) => {
            const orderInput = item.querySelector('[name$="[display_order]"]');
            if (orderInput) {
                orderInput.value = index;
            }
        });
    }

    /**
     * Add element to configuration
     */
    function showAddElementDialog() {
        if (!state.elementRegistry) {
            showError('Element registry not loaded');
            return;
        }
        
        // Group elements by category
        const byCategory = {};
        state.elementRegistry.forEach(elem => {
            const cat = elem.category || 'other';
            if (!byCategory[cat]) byCategory[cat] = [];
            byCategory[cat].push(elem);
        });
        
        // Create dialog HTML
        const categories = Object.keys(byCategory).sort();
        const html = `
            <div class="add-element-selector active">
                <h6>Select Element to Add</h6>
                <div class="row">
                    ${categories.map(cat => `
                        <div class="col-md-6">
                            <h6 class="text-muted">${capitalize(cat)}</h6>
                            <div class="list-group mb-3">
                                ${byCategory[cat].map(elem => `
                                    <button type="button" 
                                            class="list-group-item list-group-item-action" 
                                            data-element="${elem.name}">
                                        ${elem.display_name}
                                    </button>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        const container = document.getElementById('elementConfigContainer');
        const existingSelector = container.querySelector('.add-element-selector');
        if (existingSelector) {
            existingSelector.remove();
        } else {
            container.insertAdjacentHTML('beforeend', html);
            
            container.querySelectorAll('.add-element-selector button').forEach(btn => {
                btn.addEventListener('click', () => {
                    addElement(btn.dataset.element);
                    container.querySelector('.add-element-selector').remove();
                });
            });
        }
    }

    /**
     * Add an element to the configuration
     */
    function addElement(elementName) {
        const registryElem = state.elementRegistry.find(e => e.name === elementName);
        if (!registryElem) {
            showError('Element not found in registry');
            return;
        }
        
        const container = document.getElementById('elementConfigContainer');
        const existingItems = container.querySelectorAll('.element-config-item');
        const index = existingItems.length;
        
        const newElement = {
            lift_element: elementName,
            css_class: registryElem.default_css || '',
            visibility: registryElem.default_visibility || 'if-content',
            display_order: index,
            prefix: '',
            suffix: ''
        };
        
        const html = createElementConfigItem(newElement, index);
        
        if (existingItems.length === 0) {
            container.innerHTML = html;
        } else {
            container.insertAdjacentHTML('beforeend', html);
        }
        
        // Attach listeners to new item
        const newItem = container.lastElementChild;
        newItem.querySelector('.element-remove')?.addEventListener('click', (e) => {
            e.currentTarget.closest('.element-config-item').remove();
            updatePreview();
        });
        
        newItem.querySelectorAll('.element-controls input, .element-controls select').forEach(input => {
            input.addEventListener('change', updatePreview);
        });
        
        setupSortable();
        updatePreview();
    }

    /**
     * Reset elements to default from registry
     */
    async function resetToDefault() {
        try {
            const response = await fetch(`${API.registry}/default-profile`);
            if (!response.ok) throw new Error('Failed to load default profile');
            
            const data = await response.json();
            renderElementConfig(data.profile);
            setupSortable();
            updatePreview();
            showSuccess('Reset to default configuration');
            
        } catch (error) {
            console.error('Error resetting to default:', error);
            showError('Failed to load default configuration');
        }
    }

    /**
     * Update live preview
     */
    async function updatePreview() {
        const previewContainer = document.getElementById('profilePreview');
        const config = getProfileConfig();
        
        try {
            const response = await fetch('/api/profiles/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    elements: config.elements,
                    custom_css: config.custom_css,
                    show_subentries: config.show_subentries,
                    number_senses: config.number_senses
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to render preview');
            }
            
            const data = await response.json();
            previewContainer.innerHTML = data.html || '<p class="text-muted">No preview available</p>';
            
        } catch (error) {
            console.error('Error updating preview:', error);
            previewContainer.innerHTML = `<p class="text-danger">Preview error: ${error.message}</p>`;
        }
    }

    /**
     * Load a sample entry for preview (deprecated - now using server-side sample)
     */
    async function loadPreviewEntry() {
        // No longer needed - preview endpoint uses server-side sample
    }

    /**
     * Get profile configuration from form
     */
    function getProfileConfig() {
        const elements = [];
        const items = document.querySelectorAll('.element-config-item');
        
        items.forEach((item, index) => {
            const elementName = item.dataset.element;
            const displayMode = item.querySelector('[name$="[display_mode]"]')?.value || 'inline';
            const abbrFormat = item.querySelector('[name$="[abbr_format]"]')?.value || 'abbr';
            
            const configObj = {
                display_mode: displayMode
            };
            
            // Only add abbr_format if the dropdown exists (for range elements)
            if (item.querySelector('[name$="[abbr_format]"]')) {
                configObj.abbr_format = abbrFormat;
            }
            
            const config = {
                lift_element: elementName,
                css_class: item.querySelector('[name$="[css_class]"]')?.value || '',
                visibility: item.querySelector('[name$="[visibility]"]')?.value || 'if-content',
                display_order: parseInt(item.querySelector('[name$="[display_order]"]')?.value || index),
                language_filter: item.querySelector('[name$="[language_filter]"]')?.value || '*',
                prefix: item.querySelector('[name$="[prefix]"]')?.value || '',
                suffix: item.querySelector('[name$="[suffix]"]')?.value || '',
                config: configObj
            };
            elements.push(config);
        });
        
        return {
            name: document.getElementById('profileName').value,
            description: document.getElementById('profileDescription').value,
            custom_css: document.getElementById('profileCustomCSS').value,
            show_subentries: document.getElementById('showSubentries').checked,
            number_senses: document.getElementById('numberSenses').checked,
            elements: elements
        };
    }

    /**
     * Save profile (create or update)
     */
    async function saveProfile() {
        const form = document.getElementById('profileForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        const profileId = document.getElementById('profileId').value;
        const config = getProfileConfig();
        config.is_default = document.getElementById('isDefault').checked;
        
        try {
            const url = profileId ? `${API.profiles}/${profileId}` : API.profiles;
            const method = profileId ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save profile');
            }
            
            const profile = await response.json();
            showSuccess(`Profile "${profile.name}" ${profileId ? 'updated' : 'created'} successfully`);
            
            bootstrap.Modal.getInstance(document.getElementById('profileModal')).hide();
            await loadProfiles();
            
        } catch (error) {
            console.error('Error saving profile:', error);
            showError(error.message);
        }
    }

    /**
     * Edit profile
     */
    function editProfile(profile) {
        showProfileModal(profile);
    }

    /**
     * View profile (read-only)
     */
    function viewProfile(profile) {
        showProfileModal(profile);
        // Disable all inputs
        document.querySelectorAll('#profileForm input, #profileForm select, #profileForm textarea').forEach(input => {
            input.disabled = true;
        });
        document.getElementById('btnSaveProfile').disabled = true;
    }

    /**
     * Duplicate profile
     */
    async function duplicateProfile(profile) {
        const newName = prompt(`Enter name for duplicated profile:`, `${profile.name} (Copy)`);
        if (!newName) return;
        
        try {
            const config = {
                name: newName,
                description: profile.description,
                elements: profile.elements,
                is_default: false
            };
            
            const response = await fetch(API.profiles, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to duplicate profile');
            }
            
            showSuccess(`Profile duplicated as "${newName}"`);
            await loadProfiles();
            
        } catch (error) {
            console.error('Error duplicating profile:', error);
            showError(error.message);
        }
    }

    /**
     * Set profile as default
     */
    async function setDefaultProfile(profile) {
        try {
            const response = await fetch(`${API.profiles}/${profile.id}/default`, {
                method: 'POST'
            });
            
            if (!response.ok) throw new Error('Failed to set default profile');
            
            showSuccess(`"${profile.name}" set as default profile`);
            await loadProfiles();
            
        } catch (error) {
            console.error('Error setting default:', error);
            showError('Failed to set default profile');
        }
    }

    /**
     * Export profile
     */
    async function exportProfile(profile) {
        try {
            const response = await fetch(`${API.profiles}/${profile.id}/export`);
            if (!response.ok) throw new Error('Failed to export profile');
            
            const data = await response.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `${profile.name.replace(/\s+/g, '_')}_profile.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            showSuccess('Profile exported successfully');
            
        } catch (error) {
            console.error('Error exporting profile:', error);
            showError('Failed to export profile');
        }
    }

    /**
     * Delete profile
     */
    function deleteProfile(profile) {
        document.getElementById('deleteProfileName').textContent = profile.name;
        const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
        
        document.getElementById('btnConfirmDelete').onclick = async () => {
            try {
                const response = await fetch(`${API.profiles}/${profile.id}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to delete profile');
                }
                
                showSuccess(`Profile "${profile.name}" deleted`);
                bootstrap.Modal.getInstance(document.getElementById('deleteModal')).hide();
                await loadProfiles();
                
            } catch (error) {
                console.error('Error deleting profile:', error);
                showError(error.message);
            }
        };
        
        modal.show();
    }

    /**
     * Create profile from registry default
     */
    async function createDefaultProfile() {
        const name = prompt('Enter name for the new profile:', 'Default Profile');
        if (!name) return;
        
        try {
            const response = await fetch(`${API.profiles}/create-default`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to create profile');
            }
            
            showSuccess(`Profile "${name}" created from defaults`);
            await loadProfiles();
            
        } catch (error) {
            console.error('Error creating default profile:', error);
            showError(error.message);
        }
    }

    /**
     * Import profile from JSON file
     */
    function handleImportProfile() {
        const modal = new bootstrap.Modal(document.getElementById('importModal'));
        modal.show();
        
        document.getElementById('btnConfirmImport').onclick = async () => {
            const fileInput = document.getElementById('importFile');
            const overwrite = document.getElementById('overwriteExisting').checked;
            
            if (!fileInput.files.length) {
                showError('Please select a file');
                return;
            }
            
            try {
                const file = fileInput.files[0];
                const text = await file.text();
                const data = JSON.parse(text);
                
                const response = await fetch(`${API.profiles}/import?overwrite=${overwrite}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to import profile');
                }
                
                showSuccess('Profile imported successfully');
                bootstrap.Modal.getInstance(document.getElementById('importModal')).hide();
                await loadProfiles();
                
            } catch (error) {
                console.error('Error importing profile:', error);
                showError(error.message);
            }
        };
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        document.getElementById('btnCreateProfile')?.addEventListener('click', () => showProfileModal());
        document.getElementById('btnCreateDefault')?.addEventListener('click', createDefaultProfile);
        document.getElementById('btnImportProfile')?.addEventListener('click', handleImportProfile);
        document.getElementById('btnSaveProfile')?.addEventListener('click', saveProfile);
        document.getElementById('btnAddElement')?.addEventListener('click', showAddElementDialog);
        document.getElementById('btnResetElements')?.addEventListener('click', resetToDefault);
        document.getElementById('btnRefreshPreview')?.addEventListener('click', updatePreview);
        
        // CSS help toggle
        document.getElementById('btnToggleCSSHelp')?.addEventListener('click', function() {
            const panel = document.getElementById('cssHelpPanel');
            const collapse = new bootstrap.Collapse(panel, { toggle: true });
            const icon = this.querySelector('i');
            if (panel.classList.contains('show')) {
                this.innerHTML = '<i class="fas fa-question-circle"></i> Show Examples';
            } else {
                this.innerHTML = '<i class="fas fa-times-circle"></i> Hide Examples';
            }
        });
    }

    /**
     * Utility functions
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        return date.toLocaleDateString();
    }

    function capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    function showSuccess(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container').insertBefore(alert, document.querySelector('.container').firstChild);
        setTimeout(() => alert.remove(), 5000);
    }

    function showError(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container').insertBefore(alert, document.querySelector('.container').firstChild);
        setTimeout(() => alert.remove(), 5000);
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', init);

})();
