# Implementation Plan: Entry List

This document outlines the implementation tasks for the Entry List feature, based on the requirements in `specification.md` and `TODO.md`.

1.  [x] **Enhanced Entry List**
    *   This epic covers the implementation of an enhanced entry list with sorting and configurable columns.

    1.1. [x] **Implement Sorting on All Columns**
        *   Implement sorting on all columns in the entry list, including Lexeme, Citation Form, Part of Speech, Definition, Gloss, and Last Modified Date.
        *   Implemented: `dictionary_service.py:1330-1366` has XQuery ORDER BY mappings for all 7 sort fields (lexical_unit, id, date_modified, citation_form, part_of_speech, gloss, definition). Frontend sends sort parameters via `entries.js`.
        *   **Requirements**: `TODO.md #2`

    1.2. [x] **Implement Configurable Columns**
        *   Implement the ability to show, hide, and reorder columns in the entry list.
        *   The user's column configuration is saved in the browser's `localStorage`.
        *   **Requirements**: `TODO.md #2`

    1.3. [x] **Fix Cache Invalidation on Entry Deletion**
        *   Fix the bug that causes the entry list to still display a deleted entry.
        *   The cache should be updated or cleared when an entry is deleted.
        *   Implemented: All entry CRUD endpoints (`entries.py` + `xml_entries.py`) call `cache.clear_pattern('entries:*')` on create, update, and delete.
        *   **Requirements**: `TODO.md #5`
