# Ranges Parser & Service Audit Report

Date: 2025-12-29

Summary
-------
This document summarizes the audit of the LIFT ranges parsing, storage, service and UI contract. It highlights findings, concrete gaps, and an example failing trace (the *psychologia* case from the sample ranges file).

Key Findings
------------
- Parser robustness:
  - `LIFTRangesParser` supports three hierarchy modes: parent-based (`parent` attribute), nested hierarchy (range-elements nested inside others), and direct flat lists.
  - The parser uses a _namespace-aware_ lookup (`_find`, `_find_elements`) with fallback to plain and wildcard namespaces — this handles non-namespaced FieldWorks exports.
  - `_parse_range_element` collects `labels`, `description`, `abbrev`, `abbrevs`, `traits`, `value`, `guid`, `parent` and provides `children` for nested results. It does not perform inheritance resolution (i.e., it does not mutate child objects to fill missing fields from their parent).

- RangesService behavior:
  - `get_ranges` attempts a `collection('{db}')//lift-ranges` query and will parse returned XML using `LIFTRangesParser`.
  - If no ranges are found, the service will fall back to loading `config/minimal.lift-ranges` from disk (this behavior was added recently and is intentional to make tests/UI usable).
  - The service merges *custom ranges* persisted in the DB (via `CustomRange`) into parsed ranges, and it annotates standard ranges from a `STANDARD_RANGE_METADATA` mapping.
  - `lexical-relation` has special handling to ensure the UI always has relation types even when ranges are missing.

- API & UI contract:
  - `/api/ranges` returns a dict mapping IDs to range objects which contain `id`, `label`, `description`, `values` (list) and other metadata.
  - `ranges-loader.js` and `entry-form.js` already expect hierarchical `values` (a `children` array) for `semantic-domain-ddp4` and support Select2 hierarchical rendering.
  - `domain-type` in the entry form is currently a single-select (needs to be multi-select when we add multiple domain support).

Gaps & Issues Identified
------------------------
1. **No canonical resolved/inherited view**: Parser returns raw elements; there is no non-mutating helper to compute `effective_label`/`effective_abbrev` for a child that lacks its own fields but the parent has them. Tests and UI need such a deterministic helper.

2. **Inconsistent tests & expectations**: Some tests expected `get_ranges()` to be empty when DB had none; code now loads `minimal.lift-ranges` by default. Tests must be updated to reflect current intended behavior or we should add a configurable flag to disable fallback during specific tests.

3. **Edge-cases in hierarchy detection**:
   - In parent-based parsing, _order of children_ is determined by iteration over `parent_map` — this is fine but not deterministic if DB iteration order changes; tests should not assume ordering.
   - Nested and parent-based hierarchies may both be present in malformed inputs — we need to define precedence and document it.

4. **UI behavior**: `domain-type` is single-select at present — requires conversion to multiple select and test adjustments.

Example failing trace (psychologia)
-----------------------------------
- Sample ranges contains:
  - `<range-element id="psychologia" parent="nauka">` with `<form lang="pl"><text>psychologia</text></form>` (value exists; label in Polish exists; parent `nauka` may have label or description).
- Failure mode observed during tests/UI: when child `psychologia` lacks an English label or abbrev and UI expects a single-language label or an `abbrev` for compact display, the displayed text may be empty or fallback to `id`.
- Need: resolved view should provide `effective_label` (prefer English `en` label if available, otherwise fallback to parent label, otherwise id) and `effective_abbrev` (prefer `abbrev` or first `abbrevs` entry; fallback to parent; final fallback to `value[:3]`).

Recommendations & Next Steps
---------------------------
1. Add failing unit tests that assert exactly the desired behaviors (parser raw outputs, inheritance helper output).
2. Implement a `RangesService.get_resolved_ranges(project_id=None)` (or helper method on the parser) that returns the same hierarchical structure but with `effective_*` keys present (non-mutating to canonical data).
3. Update `entry_form` selects to use `effective_label`/`effective_abbrev` for display; convert `domain-type` to multi-select and write tests to ensure values round-trip.
4. Add an option on the service/API to **disable** local fallback to `minimal.lift-ranges` for tests that expect empty DB behavior (or update tests to use the intended fallback behavior).

Files of interest reviewed
-------------------------
- `app/parsers/lift_parser.py` (key methods: `_parse_range_hierarchy, _parse_parent_based, _parse_nested_hierarchy, _parse_range_element`)
- `app/services/ranges_service.py` (`get_all_ranges`, `_load_custom_ranges`, `save_custom_ranges`)
- `app/api/ranges.py` (API endpoints for ranges)
- `app/static/js/ranges-loader.js`, `app/static/js/ranges-editor.js`, `app/templates/entry_form.html`

Conclusion
----------
The codebase already has a strong foundation (parser recognizes multiple hierarchy styles; service merges custom ranges and has UI hooks). The critical missing pieces are: explicit resolved inheritance logic, small API shape additions for resolved view, tests covering the edge cases, and front-end adjustments to support hierarchical multi-select for `domain-type` and `usage-type`.

Next action: add unit tests for parser parsing modes and leave the tests failing (TDD), then implement the minimal helpers to make tests pass.

*Saved: 2025-12-29*
