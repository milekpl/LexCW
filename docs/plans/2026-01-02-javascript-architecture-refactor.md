# JavaScript Architecture Refactor Design

**Date:** 2026-01-02
**Status:** Design Complete - Ready for Implementation
**Current Branch:** `feature/entry-form-refactor`

## Overview

Comprehensive refactor of the JavaScript architecture to introduce:
- **DRY Principle:** Eliminate code duplication (getCsrfToken, showToast, console.log)
- **KIS Principle:** Keep modules small, focused, and single-purpose
- **No inline scripts:** All JS in separate files with `defer`
- **FormEventBus:** Centralized communication
- **FormComponent:** Base class for standardized components
- **Modular code:** Split monolithic entry-form.js (2,385 lines)

## Current State Analysis (Pre-Refactor)

**Codebase Statistics:**
- Total JS files: 50+
- Total lines of JS: 20,806
- Largest file: `entry-form.js` (2,385 lines)

### Critical Duplications Found

| Function | Duplicated In | Should Be In |
|----------|--------------|--------------|
| `getCsrfToken()` | `api-utils.js`, `validation_tool.html:438`, `entry_form_setup.js:3` | `core/api-core.js` |
| `showToast()` | `common.js:93`, `entry-form.js:10` | `ui/toast.js` |
| `console.log()` debug | `form-serializer.js:15`, `ranges-loader.js:18`, `lift-xml-serializer.js:60` | `core/logger.js` |

### Problems to Fix

1. **Inline scripts in HTML templates:**
   - `validation_tool.html:438-570` - inline `getCsrfToken()` and AJAX handler
   - `entry_form_setup.js:3-5` - inline `getCsrfToken()`
   - `entry_form.html` - inline DictionaryApp namespace

2. **Monster files:**
   - `entry-form.js`: 2,385 lines (everything mixed together)
   - `lift-xml-serializer.js`: 1,037 lines (all XML serialization)

3. **No module boundaries:**
   - Utilities scattered across files
   - No clear dependency structure

---

## Architecture Components

### 1. Core Layer (Foundation)

#### 1.1 Logger Module

**File:** `app/static/js/core/logger.js`

```javascript
const Logger = {
    DEBUG: false,  // Toggle for debugging in development

    debug: (...args) => Logger.DEBUG && console.debug('[DEBUG]', ...args),
    info: (...args) => console.info('[INFO]', ...args),
    warn: (...args) => console.warn('[WARN]', ...args),
    error: (...args) => console.error('[ERROR]', ...args),
    time: (label) => console.time(label),
    timeEnd: (label) => console.timeEnd(label)
};
```

**Rule:** No `console.log` anywhere else in the codebase.

#### 1.2 API Core Module

**File:** `app/static/js/core/api-core.js`

```javascript
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta?.content || DictionaryApp?.config?.csrfToken || '';
}

function makeApiRequest(url, method = 'GET', options = {}) { /* ... */ }
function apiGet(url, options) { /* ... */ }
function apiPost(url, data, options) { /* ... */ }
function apiPut(url, data, options) { /* ... */ }
function apiDelete(url, options) { /* ... */ }
```

**Single source of truth for:** `getCsrfToken()` and all API calls.

#### 1.3 Toast Module

**File:** `app/static/js/ui/toast.js`

```javascript
function showToast(message, type = 'info') {
    // Single implementation - used by api-core.js for error messages
}
```

**Delete duplicates:** `common.js:93`, `entry-form.js:10`

#### 1.4 Confirm Dialog Module

**File:** `app/static/js/ui/confirm-dialog.js`

```javascript
function confirmDialog(message, onConfirm, onCancel) {
    // Single confirmation dialog implementation
}
```

### 2. FormEventBus (Event Communication)

**File:** `app/static/js/core/form-event-bus.js`

Centralized event system replacing `window.*` communication.

```javascript
class FormEventBus {
    constructor() {
        this.events = new Map();
        this.onceEvents = new Map();
    }

    on(event, callback) {
        if (!this.events.has(event)) {
            this.events.set(event, new Set());
        }
        this.events.get(event).add(callback);
        return () => this.off(event, callback);
    }

    off(event, callback) {
        if (this.events.has(event)) {
            this.events.get(event).delete(callback);
        }
    }

    emit(event, data = {}) {
        const eventObj = new CustomEvent(event, { detail: data, bubbles: true });
        document.dispatchEvent(eventObj);

        if (this.events.has(event)) {
            this.events.get(event).forEach(cb => cb(data));
        }
        if (this.onceEvents.has(event)) {
            this.onceEvents.get(event).forEach(cb => cb(data));
            this.onceEvents.delete(event);
        }
    }

    once(event, callback) {
        if (!this.onceEvents.has(event)) {
            this.onceEvents.set(event, new Set());
        }
        this.onceEvents.get(event).add(callback);
    }
}

export const eventBus = new FormEventBus();
```

### 3. FormComponent Base Class

**File:** `app/static/js/core/form-component.js`

Base class for all form managers with standardized lifecycle and event communication.

```javascript
class FormComponent {
    static componentName = 'base';
    static dependencies = [];

    constructor(eventBus, element) {
        this.eventBus = eventBus;
        this.element = element;
        this._listeners = [];
    }

    init() {
        this.setupEventListeners();
        this.bindMethods();
        return this;
    }

    destroy() {
        this._listeners.forEach(({ event, handler }) => {
            this.element?.removeEventListener(event, handler);
        });
        this._listeners = [];
    }

    bindMethods() {
        // Bind methods that will be used as event handlers
    }

    setupEventListeners() {
        // Override in subclass
    }

    emit(event, data = {}) {
        this.eventBus.emit(`${this.constructor.componentName}:${event}`, data);
    }

    on(event, handler) {
        const listener = (e) => handler(e.detail);
        this.element?.addEventListener(event, listener);
        this._listeners.push({ event, handler: listener });
        return () => this.off(event, handler);
    }

    query(selector) {
        return this.element?.querySelector(selector);
    }

    queryAll(selector) {
        return this.element?.querySelectorAll(selector);
    }
}

export default FormComponent;
```

### 4. Code Splitting: entry-form.js

**Original:** 2,385 lines (monolithic)

**Split into modules:**

| File | Est. Lines | Responsibility |
|------|------------|----------------|
| `entry-form-main.js` | 200 | Bootstrapper, coordinates other managers |
| `sense-manager.js` | 300 | Sense add/remove/reindex, sense relations |
| `example-manager.js` | 200 | Example management |
| `reversal-manager.js` | 150 | Reversal management |
| `audio-manager.js` | 150 | Audio/pronunciation handling |
| `form-init.js` | 200 | Initialization logic |
| `form-validate.js` | 250 | Form validation |
| `form-submit.js` | 200 | Submit handling |
| `xml-preview.js` | 150 | Preview toggle |
| `entry-form-init.js` | 150 | Extracted from inline scripts |

### 5. Event Communication Map

| Old Pattern | New Pattern |
|-------------|-------------|
| `window.showToast(msg, type)` | `eventBus.emit('toast:show', { message, type })` |
| `window.updateGrammaticalCategoryInheritance()` | `eventBus.emit('grammar:inherit')` |
| `window.reindexSenses()` | `eventBus.emit('senses:reindex')` |
| `window.normalizeIndexedArray()` | Utility function import |
| `window.applySenseRelationsFromDom()` | Utility function import |
| `window.updateXmlPreview()` | `eventBus.emit('xml:preview')` |

### 6. Manager Migration

| Old Global | New Class | Event Bus Events |
|------------|-----------|------------------|
| `window.rangesLoader` | `RangesLoader` | N/A (data layer) |
| `window.xmlSerializer` | `LIFTXMLSerializer` | N/A (utility) |
| `window.FormSerializer` | `FormSerializer` | N/A (utility) |
| `window.livePreviewManager` | `LivePreviewManager` | `live-preview:*` |
| `window.fieldVisibilityManager` | `FieldVisibilityManager` | `field-visibility:*` |
| `window.relationsManager` | `RelationsManager` | `relations:*` |
| `window.pronunciationFormsManager` | `PronunciationFormsManager` | `pronunciation:*` |
| `window.variantFormsManager` | `VariantFormsManager` | `variant:*` |
| `window.senseVariantRelationsManager` | `SenseVariantRelationsManager` | `sense-variant:*` |

### 7. Inline Script Extraction

**File:** `app/static/js/entry-form-init.js`

Extract inline scripts from `entry_form.html`:
- DictionaryApp namespace initialization
- DOMContentLoaded handlers
- Manager initialization

## Implementation Phases

### Phase 1: Core Utilities (Low Risk - Start Here)

**Goal:** Eliminate duplication, no behavior change

| Task | Files | Effort |
|------|-------|--------|
| Create `core/logger.js` | New file | 1 hour |
| Replace all `console.log` with `Logger.*` | 5 files | 2 hours |
| Create `ui/toast.js` | New file | 1 hour |
| Delete `common.js:93` duplicate showToast | Modify file | 30 min |
| Delete `entry-form.js:10` duplicate showToast | Modify file | 30 min |
| Update `api-utils.js` to use toast.js | Modify file | 1 hour |
| Fix `ranges-loader.js:18` console.log | Modify file | 15 min |
| Fix `lift-xml-serializer.js:60` console.log | Modify file | 15 min |

**Verification:** Run unit tests, E2E tests pass

### Phase 2: Extract Inline Scripts (Medium Risk)

**Goal:** Move all JS out of HTML templates

| Task | Files | Effort |
|------|-------|--------|
| Create `entry-form-init.js` | New file | 3 hours |
| Update `validation_tool.html` to use api-core.js | Modify file | 1 hour |
| Update `entry_form_setup.js` to use api-core.js | Modify file | 30 min |
| Extract DictionaryApp namespace to init file | Modify file | 1 hour |

**Verification:** Entry form loads and works normally

### Phase 3: FormEventBus (Foundation)

**Goal:** Add event communication layer

| Task | Files | Effort |
|------|-------|--------|
| Create `core/form-event-bus.js` | New file | 2 hours |
| Create `core/form-component.js` | New file | 2 hours |
| Update one manager to use event bus (pilot) | Modify file | 2 hours |

**Verification:** Pilot manager works with event bus

### Phase 4: Split entry-form.js (High Risk)

**Goal:** Modularize monolithic file

| Task | Files | Effort |
|------|-------|--------|
| Create `entry/sense-manager.js` | New file | 4 hours |
| Create `entry/submit-handler.js` | New file | 3 hours |
| Create `entry/xml-preview.js` | New file | 2 hours |
| Create `entry/validation-handler.js` | New file | 3 hours |
| Create `entry-form-main.js` | New file | 2 hours |
| Refactor remaining entry-form.js logic | Modify file | 4 hours |
| Delete old `entry-form.js` | Delete file | - |

**Verification:** All entry form operations work

### Phase 5: Split lift-xml-serializer.js (Optional)

**Goal:** Modularize XML generation

| Task | Files | Effort |
|------|-------|--------|
| Split into xml/ subdirectory | 5-6 new files | 8 hours |

---

## Implementation Order

1. **Phase 1:** Core Utilities (2 days)
2. **Phase 2:** Extract Inline Scripts (2 days)
3. **Phase 3:** FormEventBus (2 days)
4. **Phase 4:** Split entry-form.js (5 days)
5. **Phase 5:** Split lift-xml-serializer.js (optional, 2 days)

**Total estimated:** 11-13 days (if all phases completed)

## Files to Create

### Core Layer (new directory structure)

```
app/static/js/
  core/
    logger.js                (Phase 1 - new)
    api-core.js              (existing, cleanup)
    form-event-bus.js        (Phase 3 - new)
    form-component.js        (Phase 3 - new)

  ui/
    toast.js                 (Phase 1 - new)
    confirm-dialog.js        (Phase 1 - new)

  entry/
    sense-manager.js         (Phase 4 - new)
    submit-handler.js        (Phase 4 - new)
    xml-preview.js           (Phase 4 - new)
    validation-handler.js    (Phase 4 - new)
    entry-form-main.js       (Phase 4 - new)
    entry-form-init.js       (Phase 2 - new, extracted from inline)

  xml/                       (Phase 5 - optional)
    lift-serializer.js       (new)
    lift-sense.js            (new)
    lift-lexical-unit.js     (new)
    lift-grammatical.js      (new)
    lift-pronunciation.js    (new)
    lift-variant.js          (new)
    lift-relation.js         (new)
    lift-etymology.js        (new)
    lift-annotation.js       (new)
```

## Files to Modify

```
app/templates/entry_form.html  (update script tags)
```

## Files to Delete

```
app/static/js/entry-form.js    (replaced by new modules)
```

## Testing Strategy

1. Run existing E2E tests to verify functionality
2. Run integration tests
3. Run unit tests
4. Manual testing of entry form (add/edit/delete)

## Risk Mitigation

- **Gradual migration:** Event bus is opt-in initially
- **Fallback utilities:** Keep utility functions importable
- **Comprehensive testing:** All existing tests must pass
- **Rollback plan:** Keep old entry-form.js until verification complete
