# CSS View Implementation TODO

Goal: Allow display profiles to control whether a range-based value (e.g., relation type) is rendered using its abbreviation or its full label (or another format like 'full'). This should be selectable per-display-element in a DisplayProfile.

High-level tasks

1. Design display-aspect API and schema (in-progress)
   - Extend `ProfileElement`/`config` schema to include `display_aspect` (values: `abbr`, `label`, `full`).
   - Decide default behavior (backwards compatible: existing profiles default to `abbr`).
   - Document migration approach for existing profiles.

2. Backend: per-element rendering
   - Update `CSSMappingService` to read `display_aspect` and choose between `abbrev` and `label` maps.
   - Provide robust fallbacks (e.g., humanized label when a range label is unavailable).
   - Ensure localization: respect display language config when selecting labels/abbrevs.

3. UI: Profile editor
   - Add UI control (dropdown) to select `Label / Abbrev / Full` per element.
   - Add helpful tooltips explaining the effect and fallback behavior.

4. Tests
   - Unit tests for `CSSMappingService` handling of aspects, fallbacks, and missing ranges.
   - Integration tests exercising display profiles in the rendered HTML (relations, grammatical-info, variants, traits).

5. Docs
   - Update `AGENTS.md` and API doc endpoints with examples.
   - Add a short migration guide and examples of profiles using `label`.

6. Edge cases & QA
   - Verify behavior for multi-word and hyphenated type IDs (title-case humanization).
   - Ensure the system remains robust with mocked/empty ranges during tests (avoid MagicMock type errors).

Estimates: 1-2 days design/spec; 2-3 days implementation; 1 day tests+docs; adjust depending on integration complexity.

Notes
- This feature should be backward compatible and feature-flag-friendly if needed.
- Consider a later enhancement to allow templated display strings (e.g., `"{label} ({abbrev})"`).
