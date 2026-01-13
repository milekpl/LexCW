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
            getElementById: function () { return null; },
            querySelector: function () { return null; },
            querySelectorAll: function () { return []; },
            createElement: function () { return { appendChild: function () {}, innerHTML: '', className: '', textContent: '', value: '', setAttribute: function () {} }; },
            body: { appendChild: function () {} },
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

    // Some modules expect a global console - ensure it exists
    if (typeof console === 'undefined') {
        global.console = { log: function () {}, warn: function () {}, error: function () {}, debug: function () {} };
    }

    // Export nothing - this is only intended for side-effects
    module.exports = {};
})();
