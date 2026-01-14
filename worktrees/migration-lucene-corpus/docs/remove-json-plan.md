# Plan: Remove JSON support from API and refactor to XML-only

Status: Draft — pending confirmation that no internal or external consumers require JSON

Goals
- Simplify API surface by removing JSON handling and making XML the single canonical format (LIFT XML) across the HTTP API.
- Reduce parsing/formatting complexity and eliminate JSON<->XML conversion code paths.
- Update tests, docs, and client-side code to use XML-only endpoints.

Why this might be desired
- The database stores LIFT (XML) natively; using XML end-to-end reduces serialization mismatch and data loss.
- No external API consumers are registered; removing JSON reduces maintenance burden and documentation complexity.

Questions to confirm before proceeding
1. Are there any external consumers of our API that expect JSON (including internal automation scripts, integrations, or CI hooks)?
2. Does the frontend (JS in `app/static/js/`) use `/api/...` endpoints that currently expect or parse JSON responses? If so, can they be switched to XML endpoints or to server-rendered routes instead?
3. Are there any tests that depend on JSON responses that we should preserve or rewrite? (We will update tests as part of the plan.)
4. Do you want to keep small JSON-only endpoints (like cache status) or remove all JSON entirely?

High-Level Implementation Plan
1. Inventory phase (TDD-friendly)
   - Search for any usages of `get_json()`, `request.get_json()`, `jsonify()`, and `response.get_json()` across the repo.
   - Identify endpoints that currently accept JSON input or return JSON responses.
   - Find client-side code, templates, and tests that call these endpoints.
   - Produce a short inventory document with the affected endpoints and callers.

2. Policy decision & scope
   - Confirm with stakeholders (you/team) whether to:
     - (A) Remove JSON support entirely (recommended if no consumers), or
     - (B) Keep a minimal JSON compatibility subset for a defined list of routes.
   - Decide whether to keep `/api/xml/*` namespace for XML and remove `/api/*` JSON behavior, or convert `/api/*` to XML-only.

3. Tests-first changes (safe, revertible)
   - Add failing tests asserting that endpoints no longer accept or return JSON (i.e., posting JSON returns 415 or 400; GET returns XML by default).
   - Add tests for XML responses and XML POST behavior if missing.

4. Implementation changes (small commits)
   - Remove `request.get_json()` uses and replace with XML handling (e.g., `request.get_data(as_text=True)` and use XML parsers).
   - Replace `jsonify()` responses with explicit XML responses using Flask `Response` (set `mimetype='application/xml'`). For endpoints that must still return structured non-XML info (rare), consider returning plain text or small XML fragments.
   - If necessary, consolidate XML handling into `app/api/xml_entries.py` and deprecate JSON endpoints.
   - Remove or simplify conditional branches checking `Content-Type` for JSON.

5. Frontend and template updates
   - Update client-side JavaScript to call `/api/xml/*` endpoints or submit forms as `application/xml` where appropriate.
   - Or, replace API calls with server-rendered views that don't rely on API JSON responses.
   - Update Jinja templates to expect server-rendered data where convenient.

6. API documentation & Flasgger
   - Update Flasgger specs to show `consumes: application/xml` and `produces: application/xml` and remove JSON body examples.
   - Remove `@swag_from` JSON schema examples that are no longer valid.
   - Update `/apidocs/` and `API_DOCUMENTATION.md` accordingly.

7. Tests & CI
   - Update unit tests and integration tests to reflect XML-only behavior.
   - Run full test suite, fix regressions, and ensure coverage remains high.
   - Add new integration tests that verify XML round-trips (create/retrieve/update/delete) behave correctly.

8. Deprecation notes & release
   - Add a clear note in `CHANGELOG.md` and `API_DOCUMENTATION.md` that JSON support was removed in this release.
   - Communicate the change to any stakeholders.

9. Cleanup
   - Remove unused JSON helper functions, imports (`jsonify` where not needed), and doc fragments.
   - Remove JSON examples from docs or archive them if needed.

Risk and mitigation
- Risk: Frontend or tests expect JSON; mitigate by doing the work TDD-style and updating tests and client code in small, reversible commits.
- Risk: Some complex nested structures might be easier to handle in JSON; mitigate by writing XML helper utilities to keep parsing/serialization safe.

Estimated effort
- Inventory & decision: 1-2 developer-days (discovery & confirmation)
- Tests + doc updates: 1-2 dev-days
- Implementation + frontend updates: 2-4 dev-days (depends on scope of front-end calls)
- Testing & cleanup: 1-2 dev-days

Files/areas likely to change (non-exhaustive)
- app/api/entries.py
- app/api/xml_entries.py
- app/api/* (search for JSON patterns)
- app/static/js/* (any fetch/ajax using JSON)
- tests/unit/ and tests/integration/ (update expected response formats)
- API docs: `API_DOCUMENTATION.md`, `app/api/*` flasgger doc blocks
- Templates invoking API endpoints

Next actions I can take
- Run an automated search for uses of JSON APIs and produce the inventory.
- If you confirm "no JSON consumers", I'll convert the above plan into an implementation TODO and start with tests to enforce XML-only behavior.

---

If you want me to proceed, reply with "Proceed" (I will start with the inventory and then implement step-by-step), or answer the questions under "Questions to confirm" if you prefer to discuss first.
