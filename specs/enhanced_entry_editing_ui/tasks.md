# Implementation Plan: Enhanced Entry Editing UI

This document outlines the implementation tasks for enhancing the entry editing UI, based on the requirements in `specification.md` and `TODO.md`.

1.  [ ] **Rebuild Etymology Editor**
    *   This epic covers the work required to rebuild the etymology editor with proper Form/Gloss LIFT objects.

    1.1. [ ] **Rebuild Etymology Editor with Form/Gloss Objects**
        *   Rebuild the etymology editor to use Form/Gloss LIFT objects.
        *   This will allow for more structured and consistent etymology data.
        *   **Requirements**: `7.2.2`, `18.2`, `TODO.md #6`

    1.2. [ ] **Fix Etymology Type Population**
        *   Ensure that the etymology type dropdown is populated from the LIFT ranges.
        *   **Requirements**: `7.2.2`, `18.2`, `TODO.md #7`

2.  [x] **Add Multilingual Editing Support**
    *   This epic covers the work required to add multilingual editing support to the entry editing UI.

    2.1. [x] **Add Multilingual Editing Support with Language Attributes**
        *   Add support for editing multilingual fields with language attributes.
        *   This will allow users to edit fields in multiple languages.
        *   **Requirements**: `7.2.2`, `18.2`

3.  [ ] **Implement Real-time IPA Validation**
    *   This epic covers the work required to implement real-time IPA validation in the pronunciation editor.

    3.1. [ ] **Implement Real-time IPA Validation in the Pronunciation Editor**
        *   Implement real-time IPA validation in the pronunciation editor.
        *   Illegal characters or sequences (based on per-dictionary rules defined in Sec 15.3) should be underlined in red.
        *   **Requirements**: `7.2.2`, `15.3`, `18.2`

4.  [x] **Enhanced Relation Editor**
    *   This epic covers the work required to enhance the relation editor.

    4.1. [x] **Replace Relation GUID Input with a Progressive Search Form**
        *   Replace the relation GUID input with a progressive search form for linking entries/senses.
        *   This will make it easier for users to link entries.
        *   **Requirements**: `7.2.2`, `18.2`

5.  [ ] **Implement Reordering of Senses and Other Lists**
    *   This epic covers the implementation of reordering functionality for senses and other lists in the entry form.

    5.1. [x] **Implement Reordering of Senses**
        *   Implement drag-and-drop reordering of senses in the entry form.
        *   The new order should be saved when the entry is saved.
        *   **Requirements**: `TODO.md #1`

    5.2. [ ] **Generalize Reordering Functionality**
        *   Refactor the reordering functionality to be general enough to be used for other lists, such as pronunciations, notes, and examples.
        *   **Requirements**: `TODO.md #1`

6.  [ ] **Fix Entry Form Bugs**
    *   This epic covers fixing various bugs in the entry form.

    6.1. [ ] **Fix Saving Entry without a Sense**
        *   Fix the bug that prevents saving an entry that has a definition but no sense.
        *   **Requirements**: `TODO.md #3`

    6.2. [x] **Fix Deleting Entry from UI**
        *   Fix the bug that prevents deleting an entry from the UI, especially for entries without a sense.
        *   **Requirements**: `TODO.md #4`

7.  [ ] **UI Testing with Playwright**
    *   This epic covers the implementation of a comprehensive UI testing suite for the entry form using Playwright.

    7.1. [x] **Set up Playwright with Pytest**
        *   Install and configure Playwright to work with Pytest.
        *   Created a basic test to ensure the integration is working.

    7.2. [x] **Write Comprehensive Tests for the Entry Form**
        *   Wrote a comprehensive test for deleting entries, covering:
            *   Creating and deleting entries.
            *   Verifying success messages and UI updates.
