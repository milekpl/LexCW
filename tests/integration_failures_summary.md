# Integration Failures Summary

**Generated:** automatic run (full integration suite)
**Raw log:** `tests/integration_failures_report.txt`

---

## Quick facts ✅
- Tests run: 1320
- Passed: 1199
- Skipped: 52
- Failed: 28
- Errors: 41

---

## High-level patterns (observations) 🔍
1. Database safety checks refusing test DBs
   - Many ERROR stacks show: "Refusing to connect to potentially unsafe database in test mode: <db_name>" (e.g. `test_dict_service_*`, `test_real_integration_*`, `test_dict_search`)
   - This originates from `app/database/basex_connector.py` connect guard.

2. Missing/partial LIFT ranges
   - Several FAILS point to ranges not being available after installation (only `lexical-relation` present in many runs).
   - Logs include parser messages: `MISSING: ./lift:range-element` and lines indicating that `lexical-relation` was added as a default.
   - Affects range-dependent tests: `test_full_ranges_integration`, `test_lift_ranges_integration`, `test_dynamic_ranges`, `test_ranges_installation` and many UI/search tests referencing grammatical-info, variant-type, etc.

3. Search / Live-search / statistics failures
   - Multiple search-related tests are ERRORing / FAILing, likely cascade from DB connection / ranges unavailability.

4. Database DROP race and sessions
   - Some teardown logs show "Database 'test_...' is opened by another process" and drop failures. Drop mitigation code was added, but traces still show races.

5. Exporter errors
   - Exporter integration tests (kindle/sqlite exporters) raised setup errors (likely due to DB connection issues above).

---

## Representative failing test examples
- tests/integration/test_component_sense_relations_crud.py::TestSenseRelationCRUD::test_read_sense_relations (FAIL)
- tests/integration/test_dynamic_ranges.py::test_ranges_api_endpoint (FAIL)
- tests/integration/test_database_drop_integration.py::TestDatabaseDrop::test_drop_database_content (FAIL)
- tests/integration/test_dictionary_service.py::* (many ERROR due to Basex connection guard)
- tests/integration/test_search.py::TestSearch::test_basic_search (ERROR)
- tests/integration/test_live_search_functionality.py::* (ERROR)

(Full list is available in `tests/integration_failures_report.txt`.)

---

## Key log evidence (short excerpts)
- Basex guard: `Refusing to connect to potentially unsafe database in test mode: test_dict_service_22b0adaf`
- Ranges parse warning: `MISSING: ./lift:range-element` and `lexical-relation not found in parsed ranges, adding default`
- Drop race: `Command execution failed: Database 'test_20251224_0015_unit_cf5030' is opened by another process.`

---

## Suggested prioritized next steps (recommended) ✅
1. Fix Basex test-mode safety behavior (highest priority)
   - Investigate `app/database/basex_connector.py` connect guard conditions: either relax for ephemeral `test_*` DB names used by tests, or adjust test harness to mark DBs safe.
   - Add unit tests verifying connectors can create/connect to ephemeral test DB names in test environment.

2. Reproduce and isolate ranges installation failure
   - Re-run the `install_recommended_ranges` flow in isolation with verbose logging and assert that expected ranges (grammatical-info, usage-type, variant-type, lexical-relation, etc.) exist immediately after installation.
   - Add an integration test that asserts presence of `grammatical-info` and others after installation and persistence.

3. Run targeted failing tests locally after (1) and (2)
   - Example commands:
     - `python -m pytest tests/integration/test_ranges_installation.py -q -k install_recommended`
     - `python -m pytest tests/integration/test_dictionary_service.py::TestDictionaryService::test_initialize_database -q`

4. Investigate DROP race traces
   - Confirm the new SHOW SESSIONS + KILL logic is being triggered and log sessions when DROP fails; add unit tests simulating "opened by another process" to assert behavior.

5. Re-run exporters / search tests after DB + ranges fixes
   - Many of the downstream errors should resolve once DB connect/drops and ranges are stable.

---

## Notes / next actions for me
- I can start with either:
  - (A) Basex connector safety check (fast, unblocks many ERRORs)
  - (B) Ranges install trace (required for many FAILs)

Tell me which to prioritize first (or I'll start with the Basex safety check and add a small regression test for it). 

---

If helpful I can also create a smaller reproducible test case (or fixture) that demonstrates the ranges-installation problem and add a test asserting the expected range ids immediately after install.
