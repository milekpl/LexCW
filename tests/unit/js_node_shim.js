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
        global.document = {
            // Keep readyState 'loading' so modules attach DOMContentLoaded listeners
            // rather than executing initialization immediately on require().
            readyState: 'loading',
            getElementById: function () { return null; },
            querySelector: function () { return null; },
            querySelectorAll: function () { return []; },
            createElement: function () { return { appendChild: function () {}, innerHTML: '', className: '', textContent: '', value: '', setAttribute: function () {} }; },
            body: { appendChild: function () {} },
            addEventListener: function () {},
            documentElement: { lang: 'en' }
        };
    }

    // Provide a minimal jQuery-like stub so modules that call $(...) don't crash.
    if (typeof global.$ === 'undefined') {
        global.$ = function () {
            // Return an object with commonly used chained methods as no-ops.
            return {
                select2: function () { return this; },
                on: function () { return this; },
                val: function () { return ''; },
                find: function () { return []; },
                closest: function () { return this; },
                addClass: function () { return this; },
                removeClass: function () { return this; },
                text: function () { return ''; },
                html: function () { return ''; }
            };
        };
        global.jQuery = global.$;
    }

    if (typeof localStorage === 'undefined') {
        global.localStorage = { getItem: function () { return null; }, setItem: function () {} };
    }

    // XMLHttpRequest: csrf.js and auth.js wrap it at import time to attach the CSRF
    // token and to handle 401/403 centrally. Node has no XHR, so without this the
    // syntax check crashes on require(). A constructor with a patchable prototype is
    // enough — nothing here is ever called.
    if (typeof XMLHttpRequest === 'undefined') {
        global.XMLHttpRequest = function () {};
        global.XMLHttpRequest.prototype.open = function () {};
        global.XMLHttpRequest.prototype.send = function () {};
        global.XMLHttpRequest.prototype.setRequestHeader = function () {};
        global.XMLHttpRequest.prototype.addEventListener = function () {};
    }

    // window.location is read by auth.js to build the ?next= redirect.
    if (typeof global.window === 'object' && !global.window.location) {
        global.window.location = {
            href: 'http://localhost/',
            origin: 'http://localhost',
            pathname: '/',
            search: '',
            assign: function () {}
        };
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

    // Provide a minimal RangesLoader stub so server-side syntax checks don't fail
    if (typeof RangesLoader === 'undefined') {
        global.RangesLoader = class {
            constructor() { }
            load() { return Promise.resolve(); }
        };
    }

    // Some modules expect a global console - ensure it exists
    if (typeof console === 'undefined') {
        global.console = { log: function () {}, warn: function () {}, error: function () {}, debug: function () {} };
    }

    // Export nothing - this is only intended for side-effects
    module.exports = {};
})();
