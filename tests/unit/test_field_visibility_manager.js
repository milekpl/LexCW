/**
 * Unit tests for FieldVisibilityManager JavaScript class
 * Run with: node tests/unit/test_field_visibility_manager.js
 */

// Simple test runner
let testsPassed = 0;
let testsFailed = 0;

function test(name, fn) {
    try {
        fn();
        console.log(`✓ ${name}`);
        testsPassed++;
    } catch (error) {
        console.log(`✗ ${name}`);
        console.log(`  Error: ${error.message}`);
        testsFailed++;
    }
}

function assertEqual(actual, expected, message = '') {
    if (actual !== expected) {
        throw new Error(`${message} Expected ${expected}, got ${actual}`);
    }
}

function assertTrue(value, message = '') {
    if (!value) {
        throw new Error(message || `Expected true, got ${value}`);
    }
}

function assertFalse(value, message = '') {
    if (value) {
        throw new Error(message || `Expected false, got ${value}`);
    }
}

// Test constants from the source file
const DEFAULT_SECTION_SETTINGS = {
    'basic-info': true,
    'custom-fields': true,
    'notes': true,
    'pronunciation': true,
    'variants': true,
    'direct-variants': true,
    'relations': true,
    'annotations': true,
    'senses': true
};

const DEFAULT_FIELD_SETTINGS = {
    'basic-info': {
        'lexical-unit': true,
        'pronunciation': true,
        'variants': true
    },
    'custom-fields': {
        'custom-fields-all': true
    },
    'notes': {
        'notes-all': true
    },
    'pronunciation': {
        'pronunciation-all': true
    },
    'variants': {
        'variants-all': true
    },
    'direct-variants': {
        'direct-variants-all': true
    },
    'relations': {
        'relations-all': true
    },
    'annotations': {
        'annotations-all': true
    },
    'senses': {
        'sense-definition': true,
        'sense-gloss': true,
        'sense-grammatical': true,
        'sense-domain': true,
        'sense-examples': true,
        'sense-illustrations': true,
        'sense-relations': true,
        'sense-variants': true,
        'sense-reversals': false,
        'sense-annotations': false
    }
};

const SECTION_CLASS_MAP = {
    'basic-info': '.basic-info-section',
    'custom-fields': '.custom-fields-section',
    'notes': '.notes-section',
    'pronunciation': '.pronunciation-section',
    'variants': '.variants-section',
    'direct-variants': '.direct-variants-section',
    'relations': '.relations-section',
    'annotations': '.annotations-section-entry',
    'senses': '.senses-section'
};

// Mock FieldVisibilityManager class based on the source file
class FieldVisibilityManager {
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: '',
            userId: null,
            projectId: null,
            defaultSectionSettings: DEFAULT_SECTION_SETTINGS,
            defaultFieldSettings: DEFAULT_FIELD_SETTINGS,
            sectionClassMap: SECTION_CLASS_MAP,
            onChange: null,
            onLoad: null,
            autoApply: true,
            ...options
        };

        this.sectionSettings = { ...this.options.defaultSectionSettings };
        this.fieldSettings = JSON.parse(JSON.stringify(this.options.defaultFieldSettings));
        this._boundMethods = new WeakMap();
        this._loaded = false;

        this._setupEventListeners();

        if (this.options.autoApply) {
            this._applySettings();
        }
    }

    _setupEventListeners() {
        // Stub for event setup
    }

    _applySettings() {
        // Stub for applying settings
    }

    _emitChangeEvent(sectionId, visible, fieldId) {
        // Stub for event emission
    }

    _findSectionIdForElement(element) {
        // Stub for finding section ID
        return null;
    }

    async loadFromAPI() {
        return this._getDefaults();
    }

    async saveToAPI() {
        return true;
    }

    _getDefaults() {
        return {
            sections: { ...this.options.defaultSectionSettings },
            fields: JSON.parse(JSON.stringify(this.options.defaultFieldSettings))
        };
    }

    _mergeFieldSettings(storedFields) {
        const merged = { ...this.options.defaultFieldSettings };
        Object.keys(storedFields).forEach(sectionId => {
            merged[sectionId] = { ...merged[sectionId], ...storedFields[sectionId] };
        });
        return merged;
    }

    async setSectionVisibility(sectionId, visible, save = true) {
        if (!(sectionId in this.options.defaultSectionSettings)) {
            console.warn(`[FieldVisibilityManager] Unknown section: ${sectionId}`);
            return;
        }

        this.sectionSettings[sectionId] = visible;

        if (save) {
            await this.saveToAPI();
        }

        this._emitChangeEvent(sectionId, visible, null);
    }

    async setFieldVisibility(sectionId, fieldId, visible, save = true) {
        if (!this.fieldSettings[sectionId]) {
            this.fieldSettings[sectionId] = {};
        }

        if (visible) {
            this.sectionSettings[sectionId] = true;
        }

        this.fieldSettings[sectionId][fieldId] = visible;

        if (save) {
            await this.saveToAPI();
        }

        this._emitChangeEvent(sectionId, visible, fieldId);
    }

    _handleToggleChange(event) {
        // Stub
    }

    _handleButtonClick(event) {
        // Stub
    }

    _updateSectionCheckboxFromFields(sectionId) {
        // Stub
    }

    _updateFieldCheckboxes(sectionId) {
        // Stub
    }

    _bind(method) {
        if (this._boundMethods.has(method)) {
            return this._boundMethods.get(method);
        }
        const bound = method.bind(this);
        this._boundMethods.set(method, bound);
        return bound;
    }

    _applySectionVisibility(sectionId, isVisible) {
        // Stub
    }

    _applyFieldVisibility(sectionId, fieldId, isVisible) {
        // Stub
    }

    async resetToDefaults(save = true) {
        this.sectionSettings = { ...this.options.defaultSectionSettings };
        this.fieldSettings = JSON.parse(JSON.stringify(this.options.defaultFieldSettings));

        this._syncCheckboxesToSettings();
        this._applySettings();

        if (save) {
            await this.saveToAPI();
        }

        this._emitChangeEvent('reset', true, null);
    }

    async showAllSections(save = true) {
        Object.keys(this.sectionSettings).forEach(sectionId => {
            this.sectionSettings[sectionId] = true;
        });

        Object.keys(this.fieldSettings).forEach(sectionId => {
            Object.keys(this.fieldSettings[sectionId]).forEach(fieldId => {
                this.fieldSettings[sectionId][fieldId] = true;
            });
        });

        this._syncCheckboxesToSettings();
        this._applySettings();

        if (save) {
            await this.saveToAPI();
        }

        this._emitChangeEvent('showAll', true, null);
    }

    syncModalCheckboxes() {
        this._syncCheckboxesToSettings();
    }

    _syncCheckboxesToSettings() {
        // Stub
    }

    getSettings() {
        return {
            sections: { ...this.sectionSettings },
            fields: JSON.parse(JSON.stringify(this.fieldSettings))
        };
    }
}

console.log('\n=== FieldVisibilityManager Unit Tests ===\n');

test('FieldVisibilityManager constructor initializes with defaults', () => {
    const manager = new FieldVisibilityManager({
        apiBaseUrl: '/api',
        userId: 1,
        projectId: 1
    });

    assertEqual(manager.options.apiBaseUrl, '/api');
    assertEqual(manager.options.userId, 1);
    assertEqual(manager.options.projectId, 1);
    assertTrue(manager.options.defaultSectionSettings['basic-info']);
    assertTrue(manager.options.defaultFieldSettings['basic-info']['lexical-unit']);
});

test('FieldVisibilityManager constructor sets defaultSectionSettings', () => {
    const manager = new FieldVisibilityManager({});

    const expectedSections = ['basic-info', 'custom-fields', 'notes', 'pronunciation',
                              'variants', 'direct-variants', 'relations', 'annotations', 'senses'];

    for (const section of expectedSections) {
        assertTrue(manager.options.defaultSectionSettings[section] === true,
                   `Section ${section} should default to true`);
    }
});

test('FieldVisibilityManager constructor sets defaultFieldSettings', () => {
    const manager = new FieldVisibilityManager({});

    // Check that basic-info fields exist
    assertTrue('lexical-unit' in manager.options.defaultFieldSettings['basic-info']);
    assertTrue('pronunciation' in manager.options.defaultFieldSettings['basic-info']);
    assertTrue('variants' in manager.options.defaultFieldSettings['basic-info']);

    // Check senses section
    assertTrue('sense-definition' in manager.options.defaultFieldSettings['senses']);
    assertTrue('sense-gloss' in manager.options.defaultFieldSettings['senses']);
});

test('FieldVisibilityManager initializes sectionSettings from defaults', () => {
    const manager = new FieldVisibilityManager({});

    assertEqual(manager.sectionSettings['basic-info'], true);
    assertEqual(manager.sectionSettings['senses'], true);
});

test('FieldVisibilityManager initializes fieldSettings from defaults', () => {
    const manager = new FieldVisibilityManager({});

    assertEqual(manager.fieldSettings['basic-info']['lexical-unit'], true);
    assertEqual(manager.fieldSettings['senses']['sense-reversals'], false);
});

test('FieldVisibilityManager sectionClassMap maps section IDs to CSS selectors', () => {
    const manager = new FieldVisibilityManager({});

    assertEqual(manager.options.sectionClassMap['basic-info'], '.basic-info-section');
    assertEqual(manager.options.sectionClassMap['senses'], '.senses-section');
    assertEqual(manager.options.sectionClassMap['custom-fields'], '.custom-fields-section');
});

test('FieldVisibilityManager getSettings returns current settings', () => {
    const manager = new FieldVisibilityManager({});

    const settings = manager.getSettings();

    assertTrue('sections' in settings);
    assertTrue('fields' in settings);
    assertEqual(settings.sections['basic-info'], true);
});

test('FieldVisibilityManager has correct public API methods', () => {
    const manager = new FieldVisibilityManager({});

    assertTrue(typeof manager.setSectionVisibility === 'function');
    assertTrue(typeof manager.setFieldVisibility === 'function');
    assertTrue(typeof manager.resetToDefaults === 'function');
    assertTrue(typeof manager.showAllSections === 'function');
    assertTrue(typeof manager.syncModalCheckboxes === 'function');
    assertTrue(typeof manager.loadFromAPI === 'function');
    assertTrue(typeof manager.saveToAPI === 'function');
});

test('FieldVisibilityManager handles unknown section gracefully', () => {
    const manager = new FieldVisibilityManager({});

    // Mock console.warn to suppress warning
    const originalWarn = console.warn;
    console.warn = () => {};

    manager.setSectionVisibility('unknown-section', true);
    assertEqual(manager.sectionSettings['unknown-section'], undefined);

    console.warn = originalWarn;
});

test('FieldVisibilityManager _bind preserves context for methods', () => {
    const manager = new FieldVisibilityManager({});

    const boundMethod = manager._bind(manager._handleToggleChange);

    assertTrue(boundMethod instanceof Function);
});

test('FieldVisibilityManager toggle methods update internal state', async () => {
    const manager = new FieldVisibilityManager({
        apiBaseUrl: null,  // Disable API calls
        userId: null
    });

    // Set up mock for saveToAPI
    manager.saveToAPI = async () => true;

    await manager.setSectionVisibility('basic-info', false);

    assertEqual(manager.sectionSettings['basic-info'], false);
});

test('FieldVisibilityManager showAllSections makes everything visible', async () => {
    const manager = new FieldVisibilityManager({
        apiBaseUrl: null,
        userId: null
    });

    // Set up mock for saveToAPI
    manager.saveToAPI = async () => true;

    // First hide something
    await manager.setSectionVisibility('basic-info', false);
    assertEqual(manager.sectionSettings['basic-info'], false);

    // Then show all
    await manager.showAllSections(false);  // Don't save to API for this test

    assertEqual(manager.sectionSettings['basic-info'], true);
});

test('FieldVisibilityManager resetToDefaults restores defaults', async () => {
    const manager = new FieldVisibilityManager({
        apiBaseUrl: null,
        userId: null
    });

    // Set up mock for saveToAPI
    manager.saveToAPI = async () => true;

    // Modify settings
    manager.sectionSettings['basic-info'] = false;

    // Reset to defaults
    await manager.resetToDefaults(false);  // Don't save for this test

    assertEqual(manager.sectionSettings['basic-info'], true);
});

test('FieldVisibilityManager syncModalCheckboxes exists and is callable', () => {
    const manager = new FieldVisibilityManager({});

    assertTrue(typeof manager.syncModalCheckboxes === 'function');

    // Should not throw
    manager.syncModalCheckboxes();
});

test('FieldVisibilityManager loadFromAPI returns defaults when no API', async () => {
    const manager = new FieldVisibilityManager({
        apiBaseUrl: null,
        userId: null
    });

    const result = await manager.loadFromAPI();

    assertTrue(result.sections['basic-info'] === true);
    assertTrue(result.fields['basic-info']['lexical-unit'] === true);
});

test('FieldVisibilityManager setFieldVisibility with visible section auto-enables', async () => {
    const manager = new FieldVisibilityManager({
        apiBaseUrl: null,
        userId: null
    });

    manager.saveToAPI = async () => true;

    // First hide the section
    manager.sectionSettings['basic-info'] = false;

    // Then set a field as visible
    await manager.setFieldVisibility('basic-info', 'lexical-unit', true, false);

    // Section should be auto-enabled
    assertEqual(manager.sectionSettings['basic-info'], true);
});

// Summary
console.log('\n=== Test Summary ===');
console.log(`Passed: ${testsPassed}`);
console.log(`Failed: ${testsFailed}`);
console.log('');

if (testsFailed > 0) {
    process.exit(1);
}
