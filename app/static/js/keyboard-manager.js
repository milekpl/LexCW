/**
 * KeyboardManager - Central keyboard shortcut system for the lexicographic workbench
 *
 * Features:
 * - Centralized shortcut registry with priority support
 * - Context-aware shortcut activation
 * - Form field navigation with Ctrl+Arrow keys
 * - Sense navigation and reordering
 * - WordStar-style shortcuts for text editing
 * - Dynamic shortcut hint rendering on buttons
 * - Native input behavior preservation (Ctrl+A/C/V/X/Z/Y)
 *
 * Classes:
 * - KeyboardManager: Main controller
 * - UndoRedoManager: Manages undo/redo state
 * - FieldNavigator: Navigates between form fields
 * - SenseNavigator: Navigates between sense items
 * - ShortcutHintRenderer: Renders hints on buttons
 */

(function() {
    'use strict';

    // ========== UndoRedoManager ==========

    /**
     * UndoRedoManager - Manages undo/redo state for form operations
     */
    class UndoRedoManager {
        constructor() {
            this.undoStack = [];
            this.redoStack = [];
            this.maxHistorySize = 100;
            this.isProcessing = false;
            this._init();
        }

        _init() {
            document.addEventListener('formStateChanged', (e) => {
                this.push(e.detail.state, e.detail.description);
            });
        }

        push(state, description = 'Change') {
            if (this.isProcessing) return;

            this.undoStack.push({
                state: this._deepClone(state),
                timestamp: new Date(),
                description
            });

            this.redoStack = [];

            if (this.undoStack.length > this.maxHistorySize) {
                this.undoStack.shift();
            }

            this._updateButtons();
        }

        undo() {
            if (this.undoStack.length === 0) {
                this._showNotification('Nothing to undo', 'warning');
                return null;
            }

            const currentState = this.undoStack.pop();
            this.redoStack.push(currentState);

            const previousState = this.undoStack.length > 0
                ? this.undoStack[this.undoStack.length - 1]
                : null;

            this._updateButtons();

            if (previousState) {
                this._restoreState(previousState.state);
                this._showNotification(`Undid: ${currentState.description}`, 'success');
            }

            return previousState?.state || null;
        }

        redo() {
            if (this.redoStack.length === 0) {
                this._showNotification('Nothing to redo', 'warning');
                return null;
            }

            const nextState = this.redoStack.pop();
            this.undoStack.push(nextState);

            this._updateButtons();
            this._restoreState(nextState.state);
            this._showNotification(`Redid: ${nextState.description}`, 'success');

            return nextState.state;
        }

        _restoreState(state) {
            document.dispatchEvent(new CustomEvent('restoreFormState', {
                detail: { state }
            }));

            if (window.formStateManager && typeof window.formStateManager.updateFromJSON === 'function') {
                window.formStateManager.updateFromJSON(state);
            }
        }

        _updateButtons() {
            const undoBtn = document.getElementById('undo-btn');
            const redoBtn = document.getElementById('redo-btn');

            if (undoBtn) {
                undoBtn.disabled = this.undoStack.length === 0;
                undoBtn.title = this.undoStack.length > 0
                    ? `Undo: ${this.undoStack[this.undoStack.length - 1].description}`
                    : 'Nothing to undo';
            }

            if (redoBtn) {
                redoBtn.disabled = this.redoStack.length === 0;
                redoBtn.title = this.redoStack.length > 0
                    ? `Redo: ${this.redoStack[this.redoStack.length - 1].description}`
                    : 'Nothing to redo';
            }
        }

        _deepClone(obj) {
            return JSON.parse(JSON.stringify(obj));
        }

        _showNotification(message, type = 'info') {
            if (typeof window.showAppToast === 'function') {
                window.showAppToast(message, type);
            } else if (typeof showToast === 'function') {
                showToast(message, type);
            }
        }

        getStats() {
            return { undo: this.undoStack.length, redo: this.redoStack.length };
        }

        clear() {
            this.undoStack = [];
            this.redoStack = [];
            this._updateButtons();
        }
    }

    // ========== FieldNavigator ==========

    /**
     * FieldNavigator - Navigates between form fields
     */
    class FieldNavigator {
        constructor(container, options = {}) {
            this.container = container;
            this.selector = options.selector ||
                'input:not([disabled]):not([type="hidden"]), ' +
                'textarea:not([disabled]), ' +
                'select:not([disabled]), ' +
                'button:not([disabled]), ' +
                '[contenteditable="true"]:not([disabled])';
            this.fields = [];
            this.currentIndex = -1;
            this._init();
        }

        _init() {
            this._scanFields();

            if (typeof MutationObserver !== 'undefined') {
                const observer = new MutationObserver(() => this._scanFields());
                observer.observe(this.container, {
                    childList: true,
                    subtree: true
                });
            }
        }

        _scanFields() {
            this.fields = Array.from(this.container.querySelectorAll(this.selector))
                .filter(el => {
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && style.visibility !== 'hidden';
                });

            if (document.activeElement && this.fields.includes(document.activeElement)) {
                this.currentIndex = this.fields.indexOf(document.activeElement);
            } else if (this.currentIndex >= this.fields.length) {
                this.currentIndex = this.fields.length - 1;
            }
        }

        next() {
            if (this.fields.length === 0) return null;
            this.currentIndex = (this.currentIndex + 1) % this.fields.length;
            return this.fields[this.currentIndex];
        }

        prev() {
            if (this.fields.length === 0) return null;
            this.currentIndex = this.currentIndex <= 0
                ? this.fields.length - 1
                : this.currentIndex - 1;
            return this.fields[this.currentIndex];
        }

        first() {
            if (this.fields.length === 0) return null;
            this.currentIndex = 0;
            return this.fields[0];
        }

        last() {
            if (this.fields.length === 0) return null;
            this.currentIndex = this.fields.length - 1;
            return this.fields[this.currentIndex];
        }

        current() {
            if (this.currentIndex < 0 || this.currentIndex >= this.fields.length) return null;
            return this.fields[this.currentIndex];
        }

        navigateTo(target) {
            const index = typeof target === 'number'
                ? target
                : this.fields.indexOf(target);
            if (index >= 0 && index < this.fields.length) {
                this.currentIndex = index;
                return this.fields[index];
            }
            return null;
        }

        count() {
            return this.fields.length;
        }
    }

    // ========== SenseNavigator ==========

    /**
     * SenseNavigator - Navigates between sense items
     */
    class SenseNavigator {
        constructor(container, options = {}) {
            this.container = container;
            this.senseSelector = options.senseSelector || '.sense-item:not(#default-sense-template)';
            this.senses = [];
            this.currentSense = null;
            this.currentSubsense = null;
            this._init();
        }

        _init() {
            this._scanSenses();

            if (typeof MutationObserver !== 'undefined') {
                const observer = new MutationObserver(() => this._scanSenses());
                const sensesContainer = this.container.querySelector('#senses-container');
                if (sensesContainer) {
                    observer.observe(sensesContainer, {
                        childList: true,
                        subtree: true
                    });
                }
            }
        }

        _scanSenses() {
            const container = this.container.querySelector('#senses-container') || this.container;
            this.senses = Array.from(container.querySelectorAll(this.senseSelector));
        }

        next() {
            if (this.senses.length === 0) return null;
            const currentIndex = this.senses.indexOf(this.currentSense);
            const nextIndex = (currentIndex + 1) % this.senses.length;
            this.currentSense = this.senses[nextIndex];
            this.currentSubsense = null;
            return this.currentSense;
        }

        prev() {
            if (this.senses.length === 0) return null;
            const currentIndex = this.senses.indexOf(this.currentSense);
            const prevIndex = currentIndex <= 0 ? this.senses.length - 1 : currentIndex - 1;
            this.currentSense = this.senses[prevIndex];
            this.currentSubsense = null;
            return this.currentSense;
        }

        first() {
            if (this.senses.length === 0) return null;
            this.currentSense = this.senses[0];
            this.currentSubsense = null;
            return this.currentSense;
        }

        last() {
            if (this.senses.length === 0) return null;
            this.currentSense = this.senses[this.senses.length - 1];
            this.currentSubsense = null;
            return this.currentSense;
        }

        getCurrent() {
            const focusedElement = document.activeElement;
            const closestSense = focusedElement?.closest('.sense-item');
            if (closestSense && this.senses.includes(closestSense)) {
                this.currentSense = closestSense;
            }
            return this.currentSense;
        }

        count() {
            return this.senses.length;
        }

        navigateTo(target) {
            const index = typeof target === 'number'
                ? target
                : this.senses.indexOf(target);
            if (index >= 0 && index < this.senses.length) {
                this.currentSense = this.senses[index];
                this.currentSubsense = null;
                return this.currentSense;
            }
            return null;
        }

        highlight(sense) {
            sense.classList.add('keyboard-focused');
            setTimeout(() => {
                sense.classList.remove('keyboard-focused');
            }, 500);
        }
    }

    // ========== ShortcutHintRenderer ==========

    /**
     * ShortcutHintRenderer - Renders keyboard shortcut hints on buttons
     */
    class ShortcutHintRenderer {
        static formatCombo(combo) {
            return combo
                .split('+')
                .map(part => {
                    switch (part.toLowerCase()) {
                        case 'ctrl': return 'Ctrl';
                        case 'shift': return 'Shift';
                        case 'alt': return 'Alt';
                        case 'enter': return 'Enter';
                        case 'arrowup': return '↑';
                        case 'arrowdown': return '↓';
                        case 'arrowleft': return '←';
                        case 'arrowright': return '→';
                        case 'arrowup': return '↑';
                        case 'arrowdown': return '↓';
                        case 'home': return 'Home';
                        case 'end': return 'End';
                        case 'backspace': return '←';
                        case 'delete': return 'Del';
                        case 'tab': return 'Tab';
                        case ' ': return 'Space';
                        default: return part.toUpperCase();
                    }
                })
                .join('+');
        }

        static render(container, keyboardManager, options = {}) {
            const hintClass = options.hintClass || 'shortcut-hint';
            const buttons = container.querySelectorAll('[data-shortcut]');

            buttons.forEach(button => {
                this.attachToButton(button, keyboardManager, hintClass);
            });
        }

        static attachToButton(button, keyboardManager, hintClass = 'shortcut-hint') {
            const existingHint = button.querySelector(`.${hintClass}`);
            if (existingHint) return;

            const shortcutCombo = button.dataset.shortcut;
            if (!shortcutCombo) return;

            const badge = document.createElement('span');
            badge.className = hintClass;
            badge.dataset.shortcutHint = shortcutCombo;
            badge.textContent = this.formatCombo(shortcutCombo);

            badge.style.cssText = `
                display: inline-block;
                padding: 2px 6px;
                margin-left: 6px;
                font-size: 0.7em;
                font-weight: 600;
                color: #6c757d;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-family: monospace;
                vertical-align: middle;
            `;

            button.appendChild(badge);
        }

        static showHints(container) {
            const el = typeof container === 'string'
                ? document.querySelector(container)
                : container;
            if (!el) return;
            el.querySelectorAll('.shortcut-hint').forEach(hint => {
                hint.style.display = '';
            });
        }

        static hideHints(container) {
            const el = typeof container === 'string'
                ? document.querySelector(container)
                : container;
            if (!el) return;
            el.querySelectorAll('.shortcut-hint').forEach(hint => {
                hint.style.display = 'none';
            });
        }
    }

    // ========== KeyboardManager (Main) ==========

    /**
     * KeyboardManager - Central keyboard shortcut system
     */
    class KeyboardManager {
        constructor(options = {}) {
            this.shortcuts = new Map();
            this.currentContext = '';
            this.defaultContext = options.defaultContext || '#entry-form, #bulk-operations-container, #bulk-editor';
            this.enableWordStar = options.enableWordStar !== false;
            this.enableHints = options.enableHints !== false;

            this.undoRedoManager = new UndoRedoManager();
            this.fieldNavigator = null;
            this.senseNavigator = null;
            this.isFormMode = false;
            this.lastFocusedInput = null;

            this.wordStarActions = [];
            this._waitingForWordStarChar = false;
            this._waitingForWordStarPrefix = false;

            this._init();
        }

        _init() {
            this._setupGlobalListeners();
            this._registerBuiltInShortcuts();

            if (this.enableWordStar) {
                this._registerWordStarActions();
            }
        }

        _setupGlobalListeners() {
            document.addEventListener('keydown', (e) => this._handleKeyDown(e), true);

            document.addEventListener('focusin', (e) => this._handleFocusIn(e));
            document.addEventListener('focusout', (e) => this._handleFocusOut(e));
        }

        _handleKeyDown(e) {
            const combo = this._getKeyCombo(e);

            // Handle WordStar prefix (Ctrl+Y)
            if (this.enableWordStar && e.ctrlKey && e.key.toLowerCase() === 'y') {
                e.preventDefault();
                this._waitingForWordStarPrefix = true;
                return;
            }

            // If waiting for WordStar character
            if (this._waitingForWordStarPrefix && !e.ctrlKey) {
                this._waitingForWordStarPrefix = false;
                const action = e.key.toUpperCase();
                this.executeWordStarAction(action);
                return;
            }

            // Reset WordStar state if key was released
            if (this._waitingForWordStarPrefix && e.type === 'keyup' && e.key.toLowerCase() === 'y') {
                this._waitingForWordStarPrefix = false;
            }

            // Handle form shortcuts
            if (this.isFormMode) {
                const handled = this._tryExecuteShortcut(combo, e);
                if (handled) return;
            }
        }

        _handleFocusIn(e) {
            const element = e.target;

            if (element.matches('input:not([disabled]), textarea:not([disabled]), select:not([disabled])')) {
                this.lastFocusedInput = element;
            }

            if (this.defaultContext) {
                const contextElement = element.closest(this.defaultContext);
                if (contextElement && !this.isFormMode) {
                    this.currentContext = this.defaultContext;
                    this._activateFormMode(contextElement);
                }
            }
        }

        _handleFocusOut(e) {
            if (this.currentContext && this.defaultContext) {
                const contextElement = e.target.closest(this.defaultContext);
                if (!contextElement) {
                    this.currentContext = '';
                    this._deactivateFormMode();
                }
            }
        }

        _getKeyCombo(e) {
            const parts = [];

            if (e.ctrlKey) parts.push('ctrl');
            if (e.shiftKey) parts.push('shift');
            if (e.altKey) parts.push('alt');
            if (e.metaKey) parts.push('meta');

            const keyMap = {
                'arrowup': 'arrowup',
                'arrowdown': 'arrowdown',
                'arrowleft': 'arrowleft',
                'arrowright': 'arrowright',
                'enter': 'enter',
                'escape': 'escape',
                ' ': 'space'
            };

            const key = keyMap[e.key.toLowerCase()] || e.key.toLowerCase();
            parts.push(key);

            return parts.join('+');
        }

        _isTextInput(element) {
            const tagName = element.tagName.toLowerCase();
            if (tagName === 'textarea') return true;
            if (tagName === 'input') {
                const type = element.type.toLowerCase();
                return ['text', 'search', 'email', 'password', 'number', 'tel', 'url'].includes(type) || type === '';
            }
            if (element.isContentEditable) return true;
            return false;
        }

        _tryExecuteShortcut(combo, e) {
            const inInput = this._isTextInput(e.target);

            // Native shortcuts that should always work in inputs
            const nativeShortcuts = ['ctrl+a', 'ctrl+c', 'ctrl+v', 'ctrl+x', 'ctrl+z', 'ctrl+y'];
            if (inInput && nativeShortcuts.includes(combo)) {
                return false; // Let native behavior work
            }

            const applicable = Array.from(this.shortcuts.values())
                .filter(s => s.combo === combo)
                .sort((a, b) => b.priority - a.priority);

            for (const shortcut of applicable) {
                if (shortcut.context && !e.target.closest(shortcut.context)) {
                    continue;
                }

                if (inInput && !shortcut.allowInInput) {
                    continue;
                }

                if (shortcut.preventDefault) {
                    e.preventDefault();
                    e.stopPropagation();
                }

                shortcut.handler(e);
                return true;
            }

            return false;
        }

        _activateFormMode(contextElement) {
            this.isFormMode = true;
            this.fieldNavigator = new FieldNavigator(contextElement);
            this.senseNavigator = new SenseNavigator(contextElement);

            if (this.enableHints) {
                ShortcutHintRenderer.showHints(contextElement);
            }
        }

        _deactivateFormMode() {
            this.isFormMode = false;
            this.fieldNavigator = null;
            this.senseNavigator = null;

            if (this.enableHints) {
                ShortcutHintRenderer.hideHints(document.body);
            }
        }

        _registerBuiltInShortcuts() {
            // Save
            this.registerShortcut('ctrl+s', (e) => {
                e.preventDefault();
                this._triggerAction('save');
            }, {
                context: this.defaultContext,
                description: 'Save entry',
                priority: 100
            });

            // Validate
            this.registerShortcut('ctrl+enter', (e) => {
                e.preventDefault();
                this._triggerAction('validate');
            }, {
                context: this.defaultContext,
                description: 'Validate entry',
                priority: 90
            });

            // Undo
            this.registerShortcut('ctrl+z', (e) => {
                if (!e.target.matches('input, textarea')) {
                    e.preventDefault();
                    this.undoRedoManager.undo();
                }
            }, {
                context: this.defaultContext,
                description: 'Undo',
                priority: 80
            });

            // Redo
            this.registerShortcut('ctrl+y', (e) => {
                if (!e.target.matches('input, textarea')) {
                    e.preventDefault();
                    this.undoRedoManager.redo();
                }
            }, {
                context: this.defaultContext,
                description: 'Redo',
                priority: 80
            });

            // Field navigation
            this.registerShortcut('ctrl+arrowright', (e) => {
                e.preventDefault();
                this.navigateField('next');
            }, {
                context: this.defaultContext,
                description: 'Next field',
                priority: 70
            });

            this.registerShortcut('ctrl+arrowleft', (e) => {
                e.preventDefault();
                this.navigateField('prev');
            }, {
                context: this.defaultContext,
                description: 'Previous field',
                priority: 70
            });

            // Sense navigation
            this.registerShortcut('arrowdown', (e) => {
                if (this._isInSenseContainer(e.target)) {
                    e.preventDefault();
                    this.navigateSense('next');
                }
            }, {
                context: this.defaultContext,
                description: 'Next sense',
                priority: 75,
                allowInInput: true
            });

            this.registerShortcut('arrowup', (e) => {
                if (this._isInSenseContainer(e.target)) {
                    e.preventDefault();
                    this.navigateSense('prev');
                }
            }, {
                context: this.defaultContext,
                description: 'Previous sense',
                priority: 75,
                allowInInput: true
            });

            // Sense reordering
            this.registerShortcut('ctrl+arrowup', (e) => {
                e.preventDefault();
                this._reorderSense('up');
            }, {
                context: this.defaultContext,
                description: 'Move sense up',
                priority: 85
            });

            this.registerShortcut('ctrl+arrowdown', (e) => {
                e.preventDefault();
                this._reorderSense('down');
            }, {
                context: this.defaultContext,
                description: 'Move sense down',
                priority: 85
            });

            // Add new sense
            this.registerShortcut('ctrl+shift+n', (e) => {
                e.preventDefault();
                this._triggerAction('add-sense');
            }, {
                context: this.defaultContext,
                description: 'Add new sense',
                priority: 50
            });

            // Help
            this.registerShortcut('ctrl+/', (e) => {
                e.preventDefault();
                this._showHelp();
            }, {
                context: this.defaultContext,
                description: 'Show keyboard shortcuts',
                priority: 10
            });
        }

        _isInSenseContainer(element) {
            return !!(
                element.closest('#senses-container') ||
                element.closest('.sense-item') ||
                element.matches('.sense-item')
            );
        }

        _reorderSense(direction) {
            if (!this.senseNavigator) return;

            const current = this.senseNavigator.getCurrent();
            if (!current) return;

            const reorderingManager = window.reorderingManager;
            if (!reorderingManager) {
                // Fallback: find and click the move button
                const button = current.querySelector(`.move-${direction === 'up' ? 'up' : 'down'}-btn`);
                if (button) {
                    button.click();
                }
                return;
            }

            const button = current.querySelector(`.move-${direction === 'up' ? 'up' : 'down'}-btn`);
            if (button) {
                reorderingManager.moveItemUp(button, 'sense');
            }
        }

        _triggerAction(action) {
            const event = new CustomEvent('keyboardAction', {
                detail: { action },
                bubbles: true
            });
            document.dispatchEvent(event);

            switch (action) {
                case 'save':
                    const saveBtn = document.querySelector('#save-btn');
                    if (saveBtn) saveBtn.click();
                    break;
                case 'validate':
                    const validateBtn = document.querySelector('#validate-btn');
                    if (validateBtn) validateBtn.click();
                    break;
                case 'add-sense':
                    const addSenseBtn = document.querySelector('#add-sense-btn, .add-sense-btn');
                    if (addSenseBtn) addSenseBtn.click();
                    break;
            }
        }

        _showHelp() {
            let helpModal = document.getElementById('shortcut-help-modal');

            if (helpModal) {
                const modal = bootstrap.Modal.getInstance(helpModal);
                if (modal) {
                    modal.hide();
                    return;
                }
                helpModal.remove();
            }

            const helpContent = this._generateHelpContent();

            const modalHtml = `
                <div class="modal fade" id="shortcut-help-modal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Keyboard Shortcuts</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                ${helpContent}
                            </div>
                            <div class="modal-footer">
                                <small class="text-muted">Press Ctrl+/ to toggle this help</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modalEl = document.getElementById('shortcut-help-modal');
            const modal = new bootstrap.Modal(modalEl);
            modal.show();

            modalEl.addEventListener('hidden.bs.modal', () => {
                modalEl.remove();
            });
        }

        _generateHelpContent() {
            const shortcuts = [
                { category: 'Basic Actions', items: [
                    { combo: 'Ctrl+S', desc: 'Save entry' },
                    { combo: 'Ctrl+Enter', desc: 'Validate entry' },
                    { combo: 'Ctrl+Z', desc: 'Undo' },
                    { combo: 'Ctrl+Y', desc: 'Redo' }
                ]},
                { category: 'Field Navigation', items: [
                    { combo: 'Ctrl+Right', desc: 'Next field' },
                    { combo: 'Ctrl+Left', desc: 'Previous field' }
                ]},
                { category: 'Sense Navigation', items: [
                    { combo: 'Up/Down', desc: 'Navigate between senses' },
                    { combo: 'Ctrl+Up/Down', desc: 'Move sense up/down' },
                    { combo: 'Ctrl+Shift+N', desc: 'Add new sense' }
                ]},
                { category: 'WordStar Shortcuts', items: [
                    { combo: 'Ctrl+Y D', desc: 'Delete current line' },
                    { combo: 'Ctrl+Y L', desc: 'Duplicate line below' }
                ]}
            ];

            let html = '<div class="row">';

            for (const { category, items } of shortcuts) {
                html += `
                    <div class="col-md-6 mb-3">
                        <h6>${category}</h6>
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th style="width: 45%;">Shortcut</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${items.map(s => `
                                    <tr>
                                        <td><kbd style="font-family: monospace;">${s.combo}</kbd></td>
                                        <td>${s.desc}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            }

            html += '</div>';
            return html;
        }

        _registerWordStarActions() {
            this.wordStarActions = [
                { key: 'D', desc: 'Delete current line', handler: () => this._wordStarDeleteLine() },
                { key: 'L', desc: 'Duplicate line below', handler: () => this._wordStarDuplicateLine() },
                { key: 'Y', desc: 'Delete to end of line', handler: () => this._wordStarDeleteToEOL() }
            ];
        }

        executeWordStarAction(actionKey) {
            const action = this.wordStarActions.find(a => a.key === actionKey.toUpperCase());
            if (action) {
                action.handler();
            }
        }

        _wordStarDeleteLine() {
            const activeElement = document.activeElement;
            if (!this._isTextInput(activeElement)) return;

            const value = activeElement.value;
            const start = activeElement.selectionStart;
            const end = activeElement.selectionEnd;

            const lineStart = value.lastIndexOf('\n', start - 1) + 1;
            const lineEnd = value.indexOf('\n', end);
            const lineEndPos = lineEnd === -1 ? value.length : lineEnd;

            activeElement.value = value.substring(0, lineStart) + value.substring(lineEndPos);
            activeElement.selectionStart = activeElement.selectionEnd = lineStart;
        }

        _wordStarDuplicateLine() {
            const activeElement = document.activeElement;
            if (!this._isTextInput(activeElement)) return;

            const value = activeElement.value;
            const start = activeElement.selectionStart;
            const end = activeElement.selectionEnd;

            const lineStart = value.lastIndexOf('\n', start - 1) + 1;
            const lineEnd = value.indexOf('\n', end);
            const lineEndPos = lineEnd === -1 ? value.length : lineEnd;

            const currentLine = value.substring(lineStart, lineEndPos);
            const insertPos = lineEndPos + (lineEnd === -1 ? 0 : 1);

            activeElement.value = value.substring(0, insertPos) + '\n' + currentLine + value.substring(insertPos);
            activeElement.selectionStart = activeElement.selectionEnd = lineStart + 1 + currentLine.length;
        }

        _wordStarDeleteToEOL() {
            const activeElement = document.activeElement;
            if (!this._isTextInput(activeElement)) return;

            const value = activeElement.value;
            const cursorPos = activeElement.selectionStart;
            const lineEnd = value.indexOf('\n', cursorPos);
            const deleteTo = lineEnd === -1 ? value.length : lineEnd;

            activeElement.value = value.substring(0, cursorPos) + value.substring(deleteTo);
            activeElement.selectionStart = activeElement.selectionEnd = cursorPos;
        }

        // Public API
        registerShortcut(combo, handler, options = {}) {
            const normalizedCombo = combo.toLowerCase().replace(/\s+/g, '+');

            this.shortcuts.set(normalizedCombo, {
                combo: normalizedCombo,
                handler,
                context: options.context || this.defaultContext,
                description: options.description || '',
                priority: options.priority || 0,
                preventDefault: options.preventDefault !== false,
                allowInInput: options.allowInInput || false
            });
        }

        unregisterShortcut(combo) {
            const normalizedCombo = combo.toLowerCase().replace(/\s+/g, '+');
            this.shortcuts.delete(normalizedCombo);
        }

        navigateField(direction) {
            if (!this.fieldNavigator) return;

            let targetField = null;
            switch (direction) {
                case 'next': targetField = this.fieldNavigator.next(); break;
                case 'prev': targetField = this.fieldNavigator.prev(); break;
                case 'first': targetField = this.fieldNavigator.first(); break;
                case 'last': targetField = this.fieldNavigator.last(); break;
            }

            if (targetField) {
                targetField.focus();
                if (targetField.tagName === 'INPUT' || targetField.tagName === 'TEXTAREA') {
                    targetField.select();
                }
            }
        }

        navigateSense(direction) {
            if (!this.senseNavigator) return;

            let targetSense = null;
            switch (direction) {
                case 'next': targetSense = this.senseNavigator.next(); break;
                case 'prev': targetSense = this.senseNavigator.prev(); break;
                case 'first': targetSense = this.senseNavigator.first(); break;
                case 'last': targetSense = this.senseNavigator.last(); break;
            }

            if (targetSense) {
                targetSense.scrollIntoView({ behavior: 'smooth', block: 'center' });
                this.senseNavigator.highlight(targetSense);
            }
        }

        showShortcutHints(container) {
            if (!this.enableHints) return;
            const el = typeof container === 'string'
                ? document.querySelector(container)
                : container;
            if (el) {
                ShortcutHintRenderer.render(el, this);
            }
        }

        getShortcuts() {
            return Array.from(this.shortcuts.values());
        }
    }

    // Export globally
    window.KeyboardManager = KeyboardManager;
    window.UndoRedoManager = UndoRedoManager;
    window.FieldNavigator = FieldNavigator;
    window.SenseNavigator = SenseNavigator;
    window.ShortcutHintRenderer = ShortcutHintRenderer;

    // Auto-initialize on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', function() {
        window.keyboardManager = new KeyboardManager({
            defaultContext: '#entry-form, #bulk-operations-container, #bulk-editor',
            enableWordStar: true,
            enableHints: true
        });

        // Apply hints to forms
        const entryForm = document.getElementById('entry-form');
        if (entryForm) {
            window.keyboardManager.showShortcutHints(entryForm);
        }

        const bulkOps = document.getElementById('bulk-operations-container');
        if (bulkOps) {
            window.keyboardManager.showShortcutHints(bulkOps);
        }
    });

})();
