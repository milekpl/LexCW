# Implementation Plan: Entry List

This document outlines the implementation tasks for the Entry List feature, based on the requirements in `specification.md` and `TODO.md`.

1.  [ ] **Enhanced Entry List**
    *   This epic covers the implementation of an enhanced entry list with sorting and configurable columns.

    1.1. [ ] **Implement Sorting on All Columns**
        *   Implement sorting on all columns in the entry list, including Lexeme, Citation Form, Part of Speech, Definition, Gloss, and Last Modified Date.
        *   **Requirements**: `TODO.md #2`

    1.2. [x] **Implement Configurable Columns**
        *   Implement the ability to show, hide, and reorder columns in the entry list.
        *   The user's column configuration is saved in the browser's `localStorage`.
        *   **Requirements**: `TODO.md #2`

    1.3. [ ] **Fix Cache Invalidation on Entry Deletion**
        *   Fix the bug that causes the entry list to still display a deleted entry.
        *   The cache should be updated or cleared when an entry is deleted.
        *   **Requirements**: `TODO.md #5`
