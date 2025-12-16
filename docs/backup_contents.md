# Backup Contents Specification

This document enumerates the files and directories that must be included in a full backup archive for the Lexicographic Curation Workbench (LCW). It defines expected names, locations, and validation rules used by the application and tests.

Required items (present for each backup):
- **LIFT export**: either a single `.lift` file or an exported directory containing the LIFT data. The application will accept both forms. Example names:
  - `dictionary.lift` (file)
  - `dictionary.lift/` (export directory)

- **Ranges export**: canonical ranges file named `lift-ranges` (preferred) placed next to or inside the exported `.lift` directory. 

- **Project settings**: `.settings.json` (or `settings.json` inside export dir). Contains language codes, project-level options, and scheduling configuration.

- **Display profiles / CSS mapping**: `display_profiles.json` (or inside export dir). Contains display-profile definitions and CSS mapping used for rendering/export.

- **Validation rules**: `validation_rules.json` (or inside export dir). This file must be schema-valid; the restore API validates it and returns HTTP 400 if the JSON does not conform to the expected schema.

- **Media folder**: `.media/` directory (or `media/` inside export dir) containing uploaded assets referenced from entries (audio, images). If `include_media` is true during backup creation, this directory must be copied into the backup.

- **Metadata**: `.meta.json` containing backup metadata including at least:
  - `id` (UUID or unique id)
  - `timestamp` (ISO8601 or epoch)
  - `db_name`
  - `file_path` (path to primary lift file or directory)
  - `display_name` (friendly label shown in UI)
  - `description`
  - `includes` (map listing booleans for `ranges`, `settings`, `display_profiles`, `validation_rules`, `media`)

Optional / compatibility items:
- **Additional artifacts**: any `.css`, `.profiles.json`, or auxiliary files referenced by `display_profiles.json` should be present if used by the project.

Naming & placement rules:
- If the backup is an exported directory (e.g., `dictionary.lift/`), all supplementary artifacts should be placed inside that directory (recommended).
- If the backup is a single `.lift` file, supplementary artifacts should be placed alongside it using a leading-dot or explicit names (e.g., `.settings.json`, `lift-ranges`, `dictionary.ranges.xml`, `.meta.json`, `.media/`).
- Zip downloads produced by the API must include the primary lift file or directory and all supplementary artifacts and the `.media` directory when present.

Validation & restore rules:
- On restore, the server must validate `validation_rules.json` against the project's JSON Schema. If validation fails, the restore endpoint must respond with HTTP 400 and an error message describing the schema failures.
- Restores must prefer the canonical `lift-ranges` when present. 
- The server should set the BaseX connector's `database` property before invoking range export/import services so that exported ranges are concrete, not placeholders.
 - If no ranges are available from the project's data sources, the server will generate a minimal, substantive `lift-ranges` export derived from known standard range metadata so backups remain useful and tests can assert real content.
 - If no `display_profiles.json` exists, backups will include a default profile named `default` so restore and rendering flows have a sane fallback.

Tests expectations:
- Tests should assert the presence of: `lift` (file or dir), `lift-ranges`, `.settings.json`, `display_profiles.json`, `validation_rules.json`, `.meta.json`, and `.media/` when `include_media` was requested.
- Tests that verify UI behavior should confirm the API returns `display_name` in `create` responses and the frontend shows it in toasts.

Compression layout (zip):
- The root of the produced zip must contain the lift file or the export directory as a single top-level entry and all supplementary artifacts as sibling files/directories if not inside the export directory. Example:

```
dictionary.zip
├─ dictionary.lift/ (or dictionary.lift file)
├─ lift-ranges
├─ .settings.json
├─ display_profiles.json
├─ validation_rules.json
├─ .meta.json
└─ .media/
```

Backward compatibility:
- None needed. Remove support for any hallucinated artifacts (such as non-existent .xml files for ranges.)

Maintenance note:
- Update this spec whenever new per-project artifacts are introduced (e.g., new config files, CSS profiles). Keep tests in `tests/integration/` aligned with this spec.

-- End of spec
