// Node environment shim for requiring browser JS files during tests
// Provides minimal no-op implementations of common browser globals so
// files that access them at module-import time don't crash under Node.
(function () {
    // Only run in Node
    if (typeof global === 'undefined') return;

    if (typeof window === 'undefined') {
        global.window = {};
    }

    if (typeof document === 'undefined') {
        // Minimal DOM element stub
        const _element = () => ({
            appendChild: function () {},
            innerHTML: '',
            className: '',
            textContent: '',
            value: '',
            setAttribute: function () {},
            querySelectorAll: function () { return []; },
            querySelector: function () { return this; },
            addEventListener: function () {},
            classList: {
                remove: function () {},
                add: function () {}
            },
            parentElement: { querySelector: function () { return _element(); } },
            getElementsByClassName: function () { return []; },
            getElementsByName: function () { return []; },
            // Provide style so code that sets requiredIndicator.style.display works
            style: { display: '' },
            remove: function () {},
        });

        global.document = {
            getElementById: function () { return _element(); },
            querySelector: function () { return _element(); },
            querySelectorAll: function () { return []; },
            createElement: function () { return _element(); },
            body: _element(),
            addEventListener: function () {},
            documentElement: { lang: 'en' }
        };
    }

    if (typeof localStorage === 'undefined') {
        global.localStorage = { getItem: function () { return null; }, setItem: function () {} };
    }

    if (typeof self === 'undefined') {
        // For worker scripts
        global.self = { importScripts: function () {}, addEventListener: function () {}, postMessage: function () {} };
    }

    if (typeof bootstrap === 'undefined') {
        // Minimal Bootstrap stubs used in many modules during initialization
        global.bootstrap = {
            Popover: class { constructor() {} },
            Tooltip: class { constructor() {} },
            Modal: class { constructor() { } show() {} hide() {} },
            Toast: class { constructor() {} show() {} }
        };
    }

    if (typeof showAppToast === 'undefined') {
        global.showAppToast = function () {};
    }

    // Provide minimal stubs for UI components expected by scripts under test
    if (typeof RangesLoader === 'undefined') {
        global.RangesLoader = class RangesLoader { constructor() {} };
    }

    // Some modules expect a global console - ensure it exists
    if (typeof console === 'undefined') {
        global.console = { log: function () {}, warn: function () {}, error: function () {}, debug: function () {} };
    }

    // Minimal jQuery stub for modules that call $(...) at import time
    if (typeof global.$ === 'undefined') {
        global.$ = function () {
            return {
                select2: function () {},
                first: function () { return this; },
                on: function () { return this; },
                val: function () { return ''; },
                change: function () { return this; },
                attr: function () { return null; },
                data: function () { return null; },
                find: function () { return this; },
                css: function () { return this; },
                append: function () { return this; }
            };
        };
        global.jQuery = global.$;
    }

    // MutationObserver stub used in some UI modules
    if (typeof global.MutationObserver === 'undefined') {
        global.MutationObserver = class {
            constructor(cb) { this._cb = cb; }
            observe() { /* no-op */ }
            disconnect() { /* no-op */ }
        };
    }

    // Export nothing - this is only intended for side-effects
    module.exports = {};
})();
