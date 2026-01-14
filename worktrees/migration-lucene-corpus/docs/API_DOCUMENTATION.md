# API Endpoint Definitions

This document lists all the API endpoints, their HTTP methods, and where they are defined in the codebase.

## File: `app/__init__.py`

### `/`

- **Endpoint Name:** `index`
- **HTTP Methods:** `GET`
- **Handler Function:** `index`
- **Defined at:** `app/__init__.py:175-182`

---

### `/health`

- **Endpoint Name:** `health_check`
- **HTTP Methods:** `GET`
- **Handler Function:** `health_check`
- **Defined at:** `app/__init__.py:185-188`

---

## File: `app/api/dashboard.py`

### `/api/dashboard/clear-cache`

- **Endpoint Name:** `api.dashboard_api.clear_dashboard_cache`
- **HTTP Methods:** `POST`
- **Handler Function:** `clear_dashboard_cache`
- **Defined at:** `app/api/dashboard.py:144-172`

---

### `/api/dashboard/stats`

- **Endpoint Name:** `api.dashboard_api.get_dashboard_stats`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_dashboard_stats`
- **Defined at:** `app/api/dashboard.py:19-141`

---

## File: `app/api/entries.py`

### `/api/entries/`

- **Endpoint Name:** `api.entries.list_entries`
- **HTTP Methods:** `GET`
- **Handler Function:** `list_entries`
- **Defined at:** `app/api/entries.py:31-229`

---

### `/api/entries/`

- **Endpoint Name:** `api.entries.create_entry`
- **HTTP Methods:** `POST`
- **Handler Function:** `create_entry`
- **Defined at:** `app/api/entries.py:324-489`

---

### `/api/entries/<string:entry_id>`

- **Endpoint Name:** `api.entries.get_entry`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_entry`
- **Defined at:** `app/api/entries.py:232-321`

---

### `/api/entries/<string:entry_id>`

- **Endpoint Name:** `api.entries.update_entry`
- **HTTP Methods:** `PUT`
- **Handler Function:** `update_entry`
- **Defined at:** `app/api/entries.py:492-650`

---

### `/api/entries/<string:entry_id>`

- **Endpoint Name:** `api.entries.delete_entry`
- **HTTP Methods:** `DELETE`
- **Handler Function:** `delete_entry`
- **Defined at:** `app/api/entries.py:653-677`

---

### `/api/entries/<string:entry_id>/related`

- **Endpoint Name:** `api.entries.get_related_entries`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_related_entries`
- **Defined at:** `app/api/entries.py:680-715`

---

### `/api/entries/clear-cache`

- **Endpoint Name:** `api.entries.clear_entries_cache`
- **HTTP Methods:** `POST`
- **Handler Function:** `clear_entries_cache`
- **Defined at:** `app/api/entries.py:718-746`

---

## File: `app/api/entry_autosave_working.py`

### `/api/entry/autosave`

- **Endpoint Name:** `autosave.autosave_entry`
- **HTTP Methods:** `POST`
- **Handler Function:** `autosave_entry`
- **Defined at:** `app/api/entry_autosave_working.py:18-97`

---

### `/api/entry/autosave/test`

- **Endpoint Name:** `autosave.test_autosave`
- **HTTP Methods:** `GET`
- **Handler Function:** `test_autosave`
- **Defined at:** `app/api/entry_autosave_working.py:100-107`

---

## File: `app/api/export.py`

### `/api/export/download/<path:filename>`

- **Endpoint Name:** `api.export_api.download_export`
- **HTTP Methods:** `GET`
- **Handler Function:** `download_export`
- **Defined at:** `app/api/export.py:231-287`

---

### `/api/export/kindle`

- **Endpoint Name:** `api.export_api.export_kindle`
- **HTTP Methods:** `POST`
- **Handler Function:** `export_kindle`
- **Defined at:** `app/api/export.py:113-177`

---

### `/api/export/lift`

- **Endpoint Name:** `api.export_api.export_lift`
- **HTTP Methods:** `GET`
- **Handler Function:** `export_lift`
- **Defined at:** `app/api/export.py:45-110`

---

### `/api/export/sqlite`

- **Endpoint Name:** `api.export_api.export_sqlite`
- **HTTP Methods:** `POST`
- **Handler Function:** `export_sqlite`
- **Defined at:** `app/api/export.py:180-228`

---

## File: `app/api/pronunciation.py`

### `/api/pronunciation/delete/<filename>`

- **Endpoint Name:** `pronunciation.delete_audio`
- **HTTP Methods:** `DELETE`
- **Handler Function:** `delete_audio`
- **Defined at:** `app/api/pronunciation.py:156-208`

---

### `/api/pronunciation/info/<filename>`

- **Endpoint Name:** `pronunciation.get_audio_info`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_audio_info`
- **Defined at:** `app/api/pronunciation.py:211-265`

---

### `/api/pronunciation/upload`

- **Endpoint Name:** `pronunciation.upload_audio`
- **HTTP Methods:** `POST`
- **Handler Function:** `upload_audio`
- **Defined at:** `app/api/pronunciation.py:29-153`

---

## File: `app/api/query_builder.py`

### `/api/query-builder/execute`

- **Endpoint Name:** `query_builder.execute_query`
- **HTTP Methods:** `POST`
- **Handler Function:** `execute_query`
- **Defined at:** `app/api/query_builder.py:211-258`

---

### `/api/query-builder/preview`

- **Endpoint Name:** `query_builder.preview_query`
- **HTTP Methods:** `POST`
- **Handler Function:** `preview_query`
- **Defined at:** `app/api/query_builder.py:73-117`

---

### `/api/query-builder/save`

- **Endpoint Name:** `query_builder.save_query`
- **HTTP Methods:** `POST`
- **Handler Function:** `save_query`
- **Defined at:** `app/api/query_builder.py:120-167`

---

### `/api/query-builder/saved`

- **Endpoint Name:** `query_builder.get_saved_queries`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_saved_queries`
- **Defined at:** `app/api/query_builder.py:170-208`

---

### `/api/query-builder/validate`

- **Endpoint Name:** `query_builder.validate_query`
- **HTTP Methods:** `POST`
- **Handler Function:** `validate_query`
- **Defined at:** `app/api/query_builder.py:23-70`

---

## File: `app/api/ranges.py`

### `/api/ranges`

- **Endpoint Name:** `ranges.get_all_ranges`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_all_ranges`
- **Defined at:** `app/api/ranges.py:19-91`

**Notes:**
- The API returns only ranges defined in your project's LIFT data or custom ranges persisted in the SQL DB. There are no hardcoded fallback lists returned by default. If a range has no values, the UI will show a hint and administrators should add values via the Ranges Editor (Settings → Ranges). Recommended default ranges can be installed explicitly during project setup via the `install_recommended_ranges` action.

---

### `/api/ranges/<range_id>`

- **Endpoint Name:** `ranges.get_specific_range`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_specific_range`
- **Defined at:** `app/api/ranges.py:94-224`

---

### `/api/ranges/etymology-types`

- **Endpoint Name:** `ranges.get_etymology_types_range`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_etymology_types_range`
- **Defined at:** `app/api/ranges.py:396-450`

---

### `/api/ranges/grammatical-info`

- **Endpoint Name:** `ranges.get_grammatical_info_range`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_grammatical_info_range`
- **Defined at:** `app/api/ranges.py:227-249`

---

### `/api/ranges/language-codes`

- **Endpoint Name:** `ranges.get_language_codes`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_language_codes`
- **Defined at:** `app/api/ranges.py:529-584`

---

### `/api/ranges/lexical-relation`

- **Endpoint Name:** `ranges.get_relation_types_range`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_relation_types_range`
- **Defined at:** `app/api/ranges.py:346-368`

---

### `/api/ranges/semantic-domain-ddp4`

- **Endpoint Name:** `ranges.get_semantic_domains_range`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_semantic_domains_range`
- **Defined at:** `app/api/ranges.py:371-393`

---

### `/api/ranges/variant-type`

- **Endpoint Name:** `ranges.get_variant_types_range`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_variant_types_range`
- **Defined at:** `app/api/ranges.py:252-343`

---

### `/api/ranges/variant-type`

- **Endpoint Name:** `ranges.get_variant_types_from_traits`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_variant_types_from_traits`
- **Defined at:** `app/api/ranges.py:453-526`

---

## File: `app/api/search.py`

### `/api/search/`

- **Endpoint Name:** `api.search.search_entries`
- **HTTP Methods:** `GET`
- **Handler Function:** `search_entries`
- **Defined at:** `app/api/search.py:48-201`

---

### `/api/search/grammatical`

- **Endpoint Name:** `api.search.search_by_grammatical_info`
- **HTTP Methods:** `GET`
- **Handler Function:** `search_by_grammatical_info`
- **Defined at:** `app/api/search.py:204-237`

---

### `/api/search/ranges`

- **Endpoint Name:** `api.search.get_ranges`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_ranges`
- **Defined at:** `app/api/search.py:240-266`

---

### `/api/search/ranges/<range_id>`

- **Endpoint Name:** `api.search.get_range_values`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_range_values`
- **Defined at:** `app/api/search.py:269-313`

---

### `/api/search/ranges/lexical-relation`

- **Endpoint Name:** `api.search.get_relation_types`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_relation_types`
- **Defined at:** `app/api/search.py:316-357`

---

### `/api/search/ranges/variant-type`

- **Endpoint Name:** `api.search.get_variant_types`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_variant_types`
- **Defined at:** `app/api/search.py:360-401`

---

## File: `app/api/validation.py`

### `/api/validation/batch`

- **Endpoint Name:** `validation_bp.validate_batch`
- **HTTP Methods:** `POST`
- **Handler Function:** `validate_batch`
- **Defined at:** `app/api/validation.py:153-218`

---

### `/api/validation/check`

- **Endpoint Name:** `validation_bp.check_entry_data`
- **HTTP Methods:** `POST`
- **Handler Function:** `check_entry_data`
- **Defined at:** `app/api/validation.py:91-151`

---

### `/api/validation/dictionary`

- **Endpoint Name:** `validation_bp.validate_dictionary`
- **HTTP Methods:** `GET`
- **Handler Function:** `validate_dictionary`
- **Defined at:** `app/api/validation.py:51-89`

---

### `/api/validation/entry/<string:entry_id>`

- **Endpoint Name:** `validation_bp.validate_entry`
- **HTTP Methods:** `GET`
- **Handler Function:** `validate_entry`
- **Defined at:** `app/api/validation.py:12-49`

---

### `/api/validation/rules`

- **Endpoint Name:** `validation_bp.get_validation_rules`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_validation_rules`
- **Defined at:** `app/api/validation.py:258-285`

---

### `/api/validation/schema`

- **Endpoint Name:** `validation_bp.get_validation_schema`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_validation_schema`
- **Defined at:** `app/api/validation.py:221-255`

---

## File: `app/api/validation_service.py`

### `/api/validation/entry`

- **Endpoint Name:** `validation_service.validate_entry`
- **HTTP Methods:** `POST`
- **Handler Function:** `validate_entry`
- **Defined at:** `app/api/validation_service.py:19-176`
- **Description:** Validates JSON entry data using the centralized validation engine. Returns validation results with errors, warnings, and info.
- **Request Body:** JSON entry data with structure: `{id, lexical_unit, senses, pronunciations, notes, relations}`
- **Response:** `{valid, errors[], warnings[], info[], error_count, has_critical_errors}`

---

### `/api/validation/xml`

- **Endpoint Name:** `validation_service.validate_xml_entry`
- **HTTP Methods:** `POST`
- **Handler Function:** `validate_xml_entry`
- **Defined at:** `app/api/validation_service.py:179-305`
- **Description:** Validates LIFT XML entry data using the centralized validation engine. Parses XML to Entry object and applies same validation rules as JSON endpoint.
- **Request Body:** LIFT XML string for a single entry (Content-Type: application/xml or text/xml)
- **Response:** `{valid, errors[], warnings[], info[], error_count, has_critical_errors}`
- **Example Request:**
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <entry id="test-1">
    <lexical-unit>
      <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense id="s1">
      <definition>
        <form lang="en"><text>A procedure for critical evaluation</text></form>
      </definition>
    </sense>
  </entry>
  ```

---

### `/api/validation/rules`

- **Endpoint Name:** `validation_service.get_validation_rules`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_validation_rules`
- **Defined at:** `app/api/validation_service.py:308-350`
- **Description:** Returns all available validation rules with their metadata, categories, and priorities
- **Response:** `{rules, categories[], priorities[]}`

---

### `/api/validation/rules/<rule_id>`

- **Endpoint Name:** `validation_service.get_validation_rule`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_validation_rule`
- **Defined at:** `app/api/validation_service.py:353-410`
- **Description:** Returns details for a specific validation rule by ID
- **Response:** Rule details including rule_id, name, description, category, priority, path, validation criteria

---

### `/validation/batch`

- **Endpoint Name:** `validation_bp.validation_batch`
- **HTTP Methods:** `POST`
- **Handler Function:** `validation_batch`
- **Defined at:** `app/api/validation.py:305-319`

---

### `/validation/check`

- **Endpoint Name:** `validation_bp.validation_check`
- **HTTP Methods:** `POST`
- **Handler Function:** `validation_check`
- **Defined at:** `app/api/validation.py:287-303`

---

### `/validation/rules`

- **Endpoint Name:** `validation_bp.validation_rules`
- **HTTP Methods:** `GET`
- **Handler Function:** `validation_rules`
- **Defined at:** `app/api/validation.py:333-343`

---

### `/validation/schema`

- **Endpoint Name:** `validation_bp.validation_schema`
- **HTTP Methods:** `GET`
- **Handler Function:** `validation_schema`
- **Defined at:** `app/api/validation.py:321-331`

---

## File: `app/api/validation_endpoints.py`

### `/api/validation/field`

- **Endpoint Name:** `validation_api.validate_field`
- **HTTP Methods:** `POST`
- **Handler Function:** `validate_field`
- **Defined at:** `app/api/validation_endpoints.py:203-224`

---

### `/api/validation/form`

- **Endpoint Name:** `validation_api.validate_form`
- **HTTP Methods:** `POST`
- **Handler Function:** `validate_form`
- **Defined at:** `app/api/validation_endpoints.py:249-265`

---

### `/api/validation/health`

- **Endpoint Name:** `validation_api.health_check`
- **HTTP Methods:** `GET`
- **Handler Function:** `health_check`
- **Defined at:** `app/api/validation_endpoints.py:268-279`

---

### `/api/validation/section`

- **Endpoint Name:** `validation_api.validate_section`
- **HTTP Methods:** `POST`
- **Handler Function:** `validate_section`
- **Defined at:** `app/api/validation_endpoints.py:226-247`

---

## File: `app/routes/api_routes.py`

### `/api/entries`

- **Endpoint Name:** `additional_api.list_entries`
- **HTTP Methods:** `GET`
- **Handler Function:** `list_entries`
- **Defined at:** `app/routes/api_routes.py:61-90`

---

### `/api/entries/<entry_id>`

- **Endpoint Name:** `additional_api.get_entry`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_entry`
- **Defined at:** `app/routes/api_routes.py:93-109`

---

### `/api/queries/validate`

- **Endpoint Name:** `additional_api.validate_query`
- **HTTP Methods:** `POST`
- **Handler Function:** `validate_query`
- **Defined at:** `app/routes/api_routes.py:221-253`

---

### `/api/ranges`

- **Endpoint Name:** `additional_api.get_all_ranges`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_all_ranges`
- **Defined at:** `app/routes/api_routes.py:113-127`

---

### `/api/ranges/<range_type>`

- **Endpoint Name:** `additional_api.get_range_by_type`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_range_by_type`
- **Defined at:** `app/routes/api_routes.py:130-189`

---

### `/api/ranges/language-codes`

- **Endpoint Name:** `additional_api.get_language_codes`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_language_codes`
- **Defined at:** `app/routes/api_routes.py:192-217`

---

### `/api/search`

- **Endpoint Name:** `additional_api.search_entries`
- **HTTP Methods:** `GET`
- **Handler Function:** `search_entries`
- **Defined at:** `app/routes/api_routes.py:21-58`

---

## File: `app/routes/corpus_routes.py`

### `/api/corpus/cleanup`

- **Endpoint Name:** `corpus.cleanup_corpus`
- **HTTP Methods:** `POST`
- **Handler Function:** `cleanup_corpus`
- **Defined at:** `app/routes/corpus_routes.py:306-327`

---

### `/api/corpus/convert/tmx-to-csv`

- **Endpoint Name:** `corpus.convert_tmx_to_csv`
- **HTTP Methods:** `POST`
- **Handler Function:** `convert_tmx_to_csv`
- **Defined at:** `app/routes/corpus_routes.py:350-406`

---

### `/api/corpus/deduplicate`

- **Endpoint Name:** `corpus.deduplicate_corpus`
- **HTTP Methods:** `POST`
- **Handler Function:** `deduplicate_corpus`
- **Defined at:** `app/routes/corpus_routes.py:330-347`

---

### `/api/corpus/stats`

- **Endpoint Name:** `corpus.get_corpus_stats`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_corpus_stats`
- **Defined at:** `app/routes/corpus_routes.py:121-176`

---

### `/api/corpus/stats/ui`

- **Endpoint Name:** `corpus.get_corpus_stats_ui`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_corpus_stats_ui`
- **Defined at:** `app/routes/corpus_routes.py:179-303`

---

### `/api/corpus/upload`

- **Endpoint Name:** `corpus.upload_corpus`
- **HTTP Methods:** `POST`
- **Handler Function:** `upload_corpus`
- **Defined at:** `app/routes/corpus_routes.py:51-118`

---

## File: `app/routes/worksets_routes.py`

### `/api/worksets`

- **Endpoint Name:** `worksets.create_workset`
- **HTTP Methods:** `POST`
- **Handler Function:** `create_workset`
- **Defined at:** `app/routes/worksets_routes.py:16-44`

---

### `/api/worksets/<workset_id>`

- **Endpoint Name:** `worksets.get_workset`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_workset`
- **Defined at:** `app/routes/worksets_routes.py:47-69`

---

### `/api/worksets/<workset_id>`

- **Endpoint Name:** `worksets.delete_workset`
- **HTTP Methods:** `DELETE`
- **Handler Function:** `delete_workset`
- **Defined at:** `app/routes/worksets_routes.py:94-106`

---

### `/api/worksets/<workset_id>/bulk-update`

- **Endpoint Name:** `worksets.bulk_update_workset`
- **HTTP Methods:** `POST`
- **Handler Function:** `bulk_update_workset`
- **Defined at:** `app/routes/worksets_routes.py:109-134`

---

### `/api/worksets/<workset_id>/progress`

- **Endpoint Name:** `worksets.get_workset_progress`
- **HTTP Methods:** `GET`
- **Handler Function:** `get_workset_progress`
- **Defined at:** `app/routes/worksets_routes.py:137-157`

---

### `/api/worksets/<workset_id>/query`

- **Endpoint Name:** `worksets.update_workset_query`
- **HTTP Methods:** `PUT`
- **Handler Function:** `update_workset_query`
- **Defined at:** `app/routes/worksets_routes.py:72-91`

---

## File: `app/views.py`

### `/`

- **Endpoint Name:** `main.index`
- **HTTP Methods:** `GET`
- **Handler Function:** `index`
- **Defined at:** `app/views.py:42-136`

---

### `/activity-log`

- **Endpoint Name:** `main.activity_log`
- **HTTP Methods:** `GET`
- **Handler Function:** `activity_log`
- **Defined at:** `app/views.py:800-807`

---

### `/api/activity`

- **Endpoint Name:** `main.api_activity`
- **HTTP Methods:** `GET`
- **Handler Function:** `api_activity`
- **Defined at:** `app/views.py:859-876`

---

### `/api/pronunciations/generate`

- **Endpoint Name:** `main.api_generate_pronunciation`
- **HTTP Methods:** `POST`
- **Handler Function:** `api_generate_pronunciation`
- **Defined at:** `app/views.py:879-910`

---

### `/api/stats`

- **Endpoint Name:** `main.api_stats`
- **HTTP Methods:** `GET`
- **Handler Function:** `api_stats`
- **Defined at:** `app/views.py:826-843`

---

### `/api/system/status`

- **Endpoint Name:** `main.api_system_status`
- **HTTP Methods:** `GET`
- **Handler Function:** `api_system_status`
- **Defined at:** `app/views.py:846-856`

---

### `/api/test-search`

- **Endpoint Name:** `main.api_test_search`
- **HTTP Methods:** `GET`
- **Handler Function:** `api_test_search`
- **Defined at:** `app/views.py:947-979`

---

### `/audio/<filename>`

- **Endpoint Name:** `main.audio_file`
- **HTTP Methods:** `GET`
- **Handler Function:** `audio_file`
- **Defined at:** `app/views.py:810-821`

---

### `/corpus-management`

- **Endpoint Name:** `main.corpus_management`
- **HTTP Methods:** `GET`
- **Handler Function:** `corpus_management`
- **Defined at:** `app/views.py:22-39`

---

### `/debug/ranges`

- **Endpoint Name:** `main.debug_ranges`
- **HTTP Methods:** `GET`
- **Handler Function:** `debug_ranges`
- **Defined at:** `app/views.py:1016-1019`

---

### `/entries`

- **Endpoint Name:** `main.entries`
- **HTTP Methods:** `GET`
- **Handler Function:** `entries`
- **Defined at:** `app/views.py:139-144`

---

### `/entries/<entry_id>`

- **Endpoint Name:** `main.view_entry`
- **HTTP Methods:** `GET`
- **Handler Function:** `view_entry`
- **Defined at:** `app/views.py:147-171`

---

### `/entries/<entry_id>/edit`

- **Endpoint Name:** `main.edit_entry`
- **HTTP Methods:** `GET, POST`
- **Handler Function:** `edit_entry`
- **Defined at:** `app/views.py:174-331`

---

### `/entries/add`

- **Endpoint Name:** `main.add_entry`
- **HTTP Methods:** `GET, POST`
- **Handler Function:** `add_entry`
- **Defined at:** `app/views.py:334-471`

---

### `/export`

- **Endpoint Name:** `main.export_options`
- **HTTP Methods:** `GET`
- **Handler Function:** `export_options`
- **Defined at:** `app/views.py:699-704`

---

### `/export/download/<path:filename>`

- **Endpoint Name:** `main.download_export`
- **HTTP Methods:** `GET`
- **Handler Function:** `download_export`
- **Defined at:** `app/views.py:707-757`

---

### `/export/kindle`

- **Endpoint Name:** `main.export_kindle`
- **HTTP Methods:** `GET`
- **Handler Function:** `export_kindle`
- **Defined at:** `app/views.py:597-653`

---

### `/export/lift`

- **Endpoint Name:** `main.export_lift`
- **HTTP Methods:** `GET`
- **Handler Function:** `export_lift`
- **Defined at:** `app/views.py:561-594`

---

### `/export/sqlite`

- **Endpoint Name:** `main.export_sqlite`
- **HTTP Methods:** `GET`
- **Handler Function:** `export_sqlite`
- **Defined at:** `app/views.py:656-696`

---

### `/import/lift`

- **Endpoint Name:** `main.import_lift`
- **HTTP Methods:** `GET, POST`
- **Handler Function:** `import_lift`
- **Defined at:** `app/views.py:515-558`

---

### `/search`

- **Endpoint Name:** `main.search`
- **HTTP Methods:** `GET`
- **Handler Function:** `search`
- **Defined at:** `app/views.py:474-512`

---

### `/settings`

- **Endpoint Name:** `main.settings`
- **HTTP Methods:** `GET`
- **Handler Function:** `settings`
- **Defined at:** `app/views.py:790-797`

---

### `/test-search`

- **Endpoint Name:** `main.test_search`
- **HTTP Methods:** `GET`
- **Handler Function:** `test_search`
- **Defined at:** `app/views.py:913-944`

---

### `/tools/bulk-edit` (and `/tools/batch-edit` for backward compatibility)

- **Endpoint Name:** `main.batch_edit`
- **HTTP Methods:** `GET`
- **Handler Function:** `batch_edit`
- **Defined at:** `app/views.py:760-767`
- **Description:** Bulk editing interface for dictionary entries (currently not implemented)

---

### `/tools/pronunciation`

- **Endpoint Name:** `main.pronunciation`
- **HTTP Methods:** `GET`
- **Handler Function:** `pronunciation`
- **Defined at:** `app/views.py:780-787`

---

### `/tools/validation`

- **Endpoint Name:** `main.validation`
- **HTTP Methods:** `GET`
- **Handler Function:** `validation`
- **Defined at:** `app/views.py:770-777`

---

### `/workbench/bulk-operations`

- **Endpoint Name:** `workbench.bulk_operations`
- **HTTP Methods:** `GET`
- **Handler Function:** `bulk_operations`
- **Defined at:** `app/views.py:1005-1013`

---

### `/workbench/query-builder`

- **Endpoint Name:** `workbench.query_builder`
- **HTTP Methods:** `GET`
- **Handler Function:** `query_builder`
- **Defined at:** `app/views.py:983-991`

---

### `/workbench/worksets`

- **Endpoint Name:** `workbench.worksets`
- **HTTP Methods:** `GET`
- **Handler Function:** `worksets`
- **Defined at:** `app/views.py:994-1002`

---

## File: `/home/jules/.pyenv/versions/3.12.11/lib/python3.12/site-packages/flasgger/base.py`

### `/apidocs/index.html`

- **Endpoint Name:** `flasgger.<lambda>`
- **HTTP Methods:** `GET`
- **Handler Function:** `<lambda>`
- **Defined at:** `/home/jules/.pyenv/versions/3.12.11/lib/python3.12/site-packages/flasgger/base.py:661-661`

---

## File: `/home/jules/.pyenv/versions/3.12.11/lib/python3.12/site-packages/flask/scaffold.py`

### `/flasgger_static/<path:filename>`

- **Endpoint Name:** `flasgger.static`
- **HTTP Methods:** `GET`
- **Handler Function:** `send_static_file`
- **Defined at:** `/home/jules/.pyenv/versions/3.12.11/lib/python3.12/site-packages/flask/scaffold.py:303-319`

---

## File: `/home/jules/.pyenv/versions/3.12.11/lib/python3.12/site-packages/flask/views.py`

### `/apidocs/`

- **Endpoint Name:** `flasgger.apidocs`
- **HTTP Methods:** `GET`
- **Handler Function:** `apidocs`
- **Defined at:** `/home/jules/.pyenv/versions/3.12.11/lib/python3.12/site-packages/flask/views.py:105-109`

---

### `/apispec.json`

- **Endpoint Name:** `flasgger.apispec`
- **HTTP Methods:** `GET`
- **Handler Function:** `apispec`
- **Defined at:** `/home/jules/.pyenv/versions/3.12.11/lib/python3.12/site-packages/flask/views.py:105-109`

---

### `/oauth2-redirect.html`

- **Endpoint Name:** `flasgger.oauth_redirect`
- **HTTP Methods:** `GET`
- **Handler Function:** `oauth_redirect`
- **Defined at:** `/home/jules/.pyenv/versions/3.12.11/lib/python3.12/site-packages/flask/views.py:105-109`

---
