# Implementation Plan: CSS Mapping System

This document outlines the implementation tasks for the CSS Mapping System feature, based on the requirements in `specification.md`.

1.  [x] **CSS Mapping Configuration**
    *   This epic covers the implementation of a system for configuring the mapping between LIFT elements and CSS styles.

    1.1. [x] **Build Admin Interface for CSS Rule Management**
        *   Build an admin interface for managing the CSS mapping rules.
        *   Implemented: Web UI on `/display-profiles` (`display_profiles.html` + `display-profiles.js`) with drag & drop ordering, element rules, live CSS editor, debounced syntax validator (`/api/profiles/validate-css`), template switcher, import/export, and live preview (`/api/profiles/preview`).
        *   **Requirements**: `7.5`, `18.2`

    1.2. [x] **Implement LIFT-to-CSS Mapping Engine**
        *   Implement a mapping engine that transforms LIFT XML into styled HTML based on the configured rules.
        *   Implemented: `CSSMappingService.render_entry()` in `app/services/css_mapping_service.py`.
        *   **Requirements**: `7.5`, `18.2`

    1.3. [x] **Create Customizable Style Templates**
        *   Create customizable style templates that can be used to quickly change the appearance of the dictionary.
        *   Implemented: 4 built-in themes (Dictionary Classic, Modern Clean, Academic, Compact) in `app/services/css_mapping_service.py` with endpoints `GET /api/display-profiles/templates` and `POST .../apply-template`.
        *   **Requirements**: `7.5`, `18.2`

    1.4. [x] **Add Preview Functionality for Styling Changes**
        *   Add a preview functionality that allows users to see how their styling changes will look before they are saved.
        *   Implemented: POST `/api/profiles/preview` endpoint in `app/api/display_profiles.py:440`.
        *   **Requirements**: `7.5`, `18.2`

2.  [ ] **Enhanced Entry Display**
    *   This epic covers the implementation of an enhanced entry display.

    2.1. [x] **Implement Full Dictionary-Style Formatting**
        *   Implement a full dictionary-style formatting for the entry display.
        *   Implemented: `LIFTToHTMLTransformer` & `CSSMappingService` render headwords, IPA pronunciations in `/.../`, range-resolved POS tags/abbreviations, sense hierarchy numbering, language-tagged definitions, example blocks with translation quotes, etymologies, and cross-reference relation headwords. Integrated into `entry_view.html`.
        *   **Requirements**: `7.2`, `18.2`

    2.2. [x] **Add In-Place Editing Capabilities**
        *   Add in-place editing capabilities to the entry display.
        *   **Requirements**: `7.2`, `18.2`

    2.3. [x] **Create Side-by-Side Comparison Views**
        *   Create side-by-side comparison views for comparing different versions of an entry.
        *   **Requirements**: `7.2`, `18.2`

    2.4. [x] **Enhance Responsive Design for Mobile**
        *   Enhance the responsive design of the entry display for mobile devices.
        *   **Requirements**: `2.3.1`, `18.2`
