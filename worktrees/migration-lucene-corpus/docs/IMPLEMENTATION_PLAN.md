# Implementation Plan — Hierarchical LIFT Ranges

**Overview & Goals**

- Fix missing descriptions/abbreviations and ensure hierarchical ranges are correctly parsed, stored, exposed via API, editable in the Ranges Editor as nested lists, and usable in entry form selects.
- Follow TDD: write failing tests first (unit → integration → E2E), then implement the parser/service/API/UI changes, then add docs and rollout notes.

---

## Phases

### Phase 0 — Audit (completed/in-progress)
- Inspect current parser behavior (LIFTRangesParser): how it detects and builds parent-based, nested, and direct hierarchies.
- Identify where labels, description or abbrevs are lost or overwritten.
- Inspect RangesService: merging, caching, resolved views, storage format, and export behavior.
- Inspect API and UI code paths (ranges-editor endpoints, `ranges-loader.js`, `ranges-editor.js`, `entry_form.html`) to confirm expectations on value shapes.
- Produce audit report (in `docs/RANGES_AUDIT_REPORT.md`) with concrete gaps and example failing traces (e.g., `psychologia` parent/child example in the sample ranges file).

### Phase 1 — Testing (TDD)
- Unit tests for `LIFTRangesParser`:
  - Parent-based hierarchy (elements with `parent` attr)
  - Nested hierarchy (range-elements nested)
  - Mixed cases and missing descriptions/abbrevs on child but present on parent
  - Large-file performance (e.g., `semantic-domain-ddp4` from `sample-lift-file`)
- Unit tests for `RangesService`:
  - Ensure `get_all_ranges()` returns nested values with `children`
  - Ensure merges (custom + standard) preserve hierarchy and metadata
  - Tests for serialization / export used by API and UI
- API tests (integration): ensure endpoints return nested data shapes and resolved/inherited options.
- Front-end JS tests: ensure `ranges-loader` and editor render nested data correctly and support search & selection.

### Phase 2 — Parser improvements
- Harden `LIFTRangesParser` to detect nested & parent-based hierarchies consistently.
- Ensure `_parse_range_element` collects `labels`, `description`, `abbrev` and `abbrevs` for parents and children.
- Provide a `resolved` view helper (non-mutating) to compute inherited/effective properties (e.g., `effective_label`).

### Phase 3 — RangesService & Storage
- Canonical stored format supports hierarchical `values` arrays with `children`.
- Add resolved view API/method that returns element with inherited `effective_*` properties applied.
- Update create/update/delete logic to maintain parent/children maps.
- Ensure LIFT export honors nested structure.

### Phase 4 — API & Docs
- GET range endpoints include nested `values`; add optional `resolved=true` to return effective attributes.
- GET element: include parent information and effective attributes.
- POST/PUT element: accept `parent` field with cycle validation.
- Update Flasgger docs and add API tests.

### Phase 5 — Frontend UI Changes
- Ranges Editor: nested tree view (collapsible), inheritance badges for inherited label/abbrev.
- Edit modal: allow setting parent, show inherited values, allow clearing to inherit.
- Entry form selects: reuse hierarchical Select2 logic for domain-type, usage-type (make domain-type multi-select).
- Add front-end tests and manual UAT steps.

### Phase 6 — Integration/E2E & Performance
- Add E2E tests exercising import → parser → service → API → UI.
- Load testing for `semantic-domain-ddp4` (~1.7k nodes): ensure the UI can handle it (lazy load, virtualization, or subtree loading).

### Phase 7 — Docs & Rollout
- Update developer docs (AGENTS.md), add migration notes if persisted shape changes.
- Add feature flags if needed.
- Add demo import scenario to tests.

### Phase 8 — Closeout
- Code review, confirm >90% coverage for new logic, merge, monitor CI.

---

## Immediate next steps (short-term)
1. Finish Phase 0 audit and save report (done here).  
2. Add unit tests for `LIFTRangesParser` (failing tests first — TDD).  
3. Implement minimal parser improvements to make tests pass.  
4. Add `RangesService` tests for resolved view and merging semantics.  


*Saved: 2025-12-29*
