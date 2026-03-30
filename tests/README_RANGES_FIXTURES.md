# Test Ranges Fixtures

This file documents the test fixtures related to LIFT "ranges" used in unit and integration tests.

Why these fixtures exist
- The application treats LIFT ranges as authoritative configuration: if a range (e.g., `lexical-relation`) is missing or empty, the app does **not** invent default values. Tests that need to simulate a configured project must explicitly provide the ranges data.

Available fixtures
- `lexical_relation_ranges` — minimal `lexical-relation` values: `synonym`, `antonym`, `see`.
- `variant_type_ranges` — common `variant-type` values: `inflected`, `spelling`, `dialectal`.
- `complex_form_type_ranges` — common `complex-form-type` values: `Compound`, `Phrase`.
- `common_ranges` — convenience fixture that merges the above three into one dict.

Guidance for writing tests
- To test behavior when the project HAS configured ranges, pass the appropriate fixture (or `common_ranges`) to the code under test.
- To test behavior when the project DOES NOT have configured ranges, do **not** use these fixtures; assert the expected behavior (e.g., relation types are not grouped).

Examples
- Grouping relations: use `lexical_relation_ranges` when verifying that `RelationGroups` places `synonym` relations into `.synonyms`.
- Variant filtering: use `variant_type_ranges` when verifying filtering by `variant-type` trait values.

Keep tests explicit: never rely on implicit defaults for ranges; prefer fixtures that document intent clearly.