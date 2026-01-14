/**
 * Validation Rule Preview & Test Component
 *
 * Provides JSON preview and rule testing functionality.
 */

class ValidationRulePreview {
    constructor(manager, containerId) {
        this._manager = manager;
        this._container = document.getElementById(containerId);

        if (!this._container) {
            console.error(`Container with id "${containerId}" not found`);
            return;
        }

        // State
        this._testData = this._getDefaultTestData();
        this._testResult = null;

        // Bind methods
        this._render = this._render.bind(this);
        this._handleTestDataChange = this._handleTestDataChange.bind(this);
        this._handleRunTest = this._handleRunTest.bind(this);
        this._handleLoadSample = this._handleLoadSample.bind(this);
        this._handleClearTest = this._handleClearTest.bind(this);

        // Listen for test results
        this._manager.on('test-completed', this._render);
    }

    // ========== Default Test Data ==========

    _getDefaultTestData() {
        return {
            id: 'entry-001',
            lexical_unit: {
                'en': 'example',
                'pl': 'przykład'
            },
            senses: [
                {
                    id: 'sense-001',
                    definition: {
                        'en': 'A representative form or pattern.',
                        'pl': 'Reprezentatywna forma lub wzorzec.'
                    },
                    gloss: {
                        'en': 'example'
                    },
                    grammatical_info: 'noun'
                }
            ],
            relations: [],
            notes: {}
        };
    }

    // ========== Rendering ==========

    _render(testResult = null) {
        this._testResult = testResult;

        this._container.innerHTML = `
            <div class="rule-preview">
                <div class="rule-preview-header">
                    <h6><i class="bi bi-play-circle"></i> Test Rule</h6>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-secondary" onclick="${this._handleLoadSample.name}('valid')">
                            <i class="bi bi-check-circle"></i> Valid Sample
                        </button>
                        <button class="btn btn-outline-secondary" onclick="${this._handleLoadSample.name}('invalid')">
                            <i class="bi bi-x-circle"></i> Invalid Sample
                        </button>
                        <button class="btn btn-outline-secondary" onclick="${this._handleClearTest.name}()">
                            <i class="bi bi-arrow-clockwise"></i> Clear
                        </button>
                    </div>
                </div>
                <div class="rule-preview-body">
                    <div class="test-data-editor">
                        <label class="form-label">Test Data (JSON)</label>
                        <textarea
                            class="form-control font-monospace"
                            id="test-data-input"
                            rows="12"
                            onchange="${this._handleTestDataChange.name}(event)"
                        >${JSON.stringify(this._testData, null, 2)}</textarea>
                    </div>
                    <div class="test-controls">
                        <button class="btn btn-primary w-100" onclick="${this._handleRunTest.name}()">
                            <i class="bi bi-play-fill"></i> Run Test
                        </button>
                    </div>
                    <div class="test-results">
                        ${this._renderTestResults()}
                    </div>
                </div>
            </div>
        `;

        this._attachEventHandlers();
    }

    _renderTestResults() {
        if (!this._testResult) {
            return `
                <div class="test-results-empty">
                    <p class="text-muted text-center py-4">
                        <i class="bi bi-arrow-right-circle" style="font-size: 2rem;"></i>
                        <br>
                        Enter test data and click "Run Test" to validate the rule
                    </p>
                </div>
            `;
        }

        const { valid, errors, warnings, info } = this._testResult;

        if (valid) {
            return `
                <div class="test-results-valid">
                    <div class="alert alert-success d-flex align-items-center">
                        <i class="bi bi-check-circle-fill me-2" style="font-size: 1.5rem;"></i>
                        <div>
                            <strong>Validation Passed!</strong>
                            <p class="mb-0 small">The test data satisfies the rule requirements.</p>
                        </div>
                    </div>
                </div>
            `;
        }

        const allIssues = [
            ...(errors || []).map(e => ({ type: 'error', message: e })),
            ...(warnings || []).map(e => ({ type: 'warning', message: e })),
            ...(info || []).map(e => ({ type: 'info', message: e }))
        ];

        const itemsHtml = allIssues.map(issue => `
            <div class="test-issue test-issue-${issue.type}">
                <i class="bi bi-${issue.type === 'error' ? 'exclamation-triangle-fill' : issue.type === 'warning' ? 'exclamation-triangle' : 'info-circle-fill'}"></i>
                <span>${this._escapeHtml(issue.message)}</span>
            </div>
        `).join('');

        return `
            <div class="test-results-invalid">
                <div class="alert alert-danger d-flex align-items-center">
                    <i class="bi bi-x-circle-fill me-2" style="font-size: 1.5rem;"></i>
                    <div>
                        <strong>Validation Failed!</strong>
                        <p class="mb-0 small">${allIssues.length} issue(s) found.</p>
                    </div>
                </div>
                <div class="test-issues-list">
                    ${itemsHtml}
                </div>
            </div>
        `;
    }

    // ========== Sample Data ==========

    _getValidSample() {
        return {
            id: 'entry-001',
            lexical_unit: {
                'en': 'example',
                'pl': 'przykład'
            },
            senses: [
                {
                    id: 'sense-001',
                    definition: {
                        'en': 'A representative form or pattern.',
                        'pl': 'Reprezentatywna forma lub wzorzec.'
                    },
                    gloss: {
                        'en': 'example'
                    },
                    grammatical_info: 'noun',
                    examples: [
                        {
                            text: {
                                'en': 'This is a simple example.',
                                'pl': 'To jest prosty przykład.'
                            }
                        }
                    ]
                }
            ],
            relations: [],
            notes: {
                'usage': 'Common in technical documentation.'
            }
        };
    }

    _getInvalidSample() {
        return {
            id: '',  // Empty ID to trigger validation error
            lexical_unit: {},
            senses: [],
            relations: [],
            notes: {}
        };
    }

    // ========== Event Handlers ==========

    _handleTestDataChange(event) {
        try {
            this._testData = JSON.parse(event.target.value);
        } catch (e) {
            // Invalid JSON, keep previous value
        }
    }

    async _handleRunTest() {
        const rule = this._manager.currentRule;
        if (!rule) {
            alert('No rule selected');
            return;
        }

        // Validate JSON
        try {
            JSON.parse(document.getElementById('test-data-input').value);
        } catch (e) {
            alert('Invalid JSON in test data');
            return;
        }

        // Run test
        try {
            await this._manager.testRule(rule, this._testData);
        } catch (error) {
            this._testResult = {
                valid: false,
                errors: [`Test failed: ${error.message}`],
                warnings: [],
                info: []
            };
            this._render();
        }
    }

    _handleLoadSample(type) {
        if (type === 'valid') {
            this._testData = this._getValidSample();
        } else {
            this._testData = this._getInvalidSample();
        }

        document.getElementById('test-data-input').value = JSON.stringify(this._testData, null, 2);
        this._testResult = null;
        this._render();
    }

    _handleClearTest() {
        this._testData = this._getDefaultTestData();
        document.getElementById('test-data-input').value = JSON.stringify(this._testData, null, 2);
        this._testResult = null;
        this._render();
    }

    _attachEventHandlers() {
        // Handlers are attached via inline onclick attributes
    }

    // ========== Public Methods ==========

    setTestData(data) {
        this._testData = data;
        document.getElementById('test-data-input').value = JSON.stringify(data, null, 2);
        this._testResult = null;
        this._render();
    }

    clearResults() {
        this._testResult = null;
        this._render();
    }

    _escapeHtml(text) {
        if (text == null) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }
}

// Export as global
window.ValidationRulePreview = ValidationRulePreview;
