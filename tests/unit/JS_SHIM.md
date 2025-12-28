# Node Environment Shim for JavaScript Tests 🔧

Location: `tests/unit/js_node_shim.js`

Purpose
- Provide minimal, safe no-op browser globals when Node `require()` loads browser-oriented JS files during the Python-based syntax validation step and other Node test helpers.
- Avoid invasive changes to production JS files.

What it exposes
- `window` (empty object)
- `document` with safe no-op implementations for `getElementById`, `querySelector`, `querySelectorAll`, `createElement`, `body.appendChild`, `addEventListener`, and a minimal `documentElement.lang`.
- `localStorage` with `getItem`/`setItem` stubs.
- `self` with `importScripts`, `addEventListener`, `postMessage` (for worker-like files).
- `bootstrap` minimal classes used at init time (`Popover`, `Tooltip`, `Modal`, `Toast`).
- `showAppToast` no-op, and a safe `console` if missing.

How it's used
- `tests/unit/test_js_integration.py` prepends `require('./js_node_shim.js')` when creating temporary Node scripts that `require()` JS files to validate syntax.
- The Jez/bundled Jest tests (actual unit JS tests) remain unchanged and run under Jest as usual.

Extending the shim
- If a new browser global is needed by a module at import-time, **extend the shim** in `tests/unit/js_node_shim.js` (do not change production code solely for tests).

Why not modify production files? 💡
- Editing many production JS files to guard for Node can be intrusive and brittle. A centralized shim keeps test-specific adjustments in tests only and avoids changing runtime behavior.

Notes
- We still prefer to write JS modules so they avoid heavy side effects at import time; the shim is for testing convenience and should be updated when new needs appear.
