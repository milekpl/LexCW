# Implementation Plan: Dynamic Range Management

This document outlines the implementation tasks for the Dynamic Range Management feature, based on the requirements in `specification.md`.

1.  [x] **Backend: LIFT Ranges Service and API**
    *   This epic covers the creation of a robust backend service to handle the dynamic loading, parsing, caching, and serving of all range types defined in the LIFT RANGES file.

    1.1. [x] **Create a LIFT Range Parsing Service**
        *   Implement a service that reads and parses the `*.lift-ranges` file.
        *   The parser must support hierarchical structures (parent-child relationships) for ranges like "semantic-domain".
        *   It must correctly parse all 21+ range types as specified in the LIFT v0.13 standard.
        *   **Requirements**: `3.1.1`, `3.1.2`, `3.1.3`, `6.2`

    1.2. [x] **Develop a Caching Layer for Ranges**
        *   Implement a caching mechanism (e.g., using Redis or an in-memory cache) for the parsed LIFT ranges to improve performance.
        *   The cache should be invalidated and refreshed automatically when the `LIFT RANGES` file is modified.
        *   **Requirements**: `3.1.3`, `6.3`

    1.3. [ ] **Implement Fallback to Default Ranges**
        *   Create a fallback mechanism that provides a set of default, hard-coded ranges if the `LIFT RANGES` file is unavailable in the database or parsing fails.
        *   They should come from a standard SIL Fieldworks LIFT file; all empty dictionaries should get these ranges by default loaded from this file as a template.
        *   This ensures the UI remains functional for development and testing even without an empty dictionary (without any entries).
        *   **Requirements**: `3.1.3`

    1.4. [x] **Create API Endpoints for LIFT Ranges**
        *   Develop REST API endpoints to expose the LIFT ranges.
        *   `GET /api/ranges`: Returns a list of all available range types.
        *   `GET /api/ranges/{range_id}`: Returns all values for a specific range, including hierarchical data.
        *   **Requirements**: `3.1.3`, `8.1`

    1.5. [ ] **Write Unit and Integration Tests for the Backend**
        *   Write comprehensive tests for the range parser, ensuring it handles all range types and hierarchies correctly.
        *   Test the caching service for proper cache hits, misses, and invalidation.
        *   Test the API endpoints for correct data return, status codes, and error handling.
        *   Achieve >90% test coverage for all new backend components.
        *   **Requirements**: `4.1`, `16.2.1`

2.  [ ] **Backend: Dynamic Variant and Language Code Services**
    *   This epic focuses on implementing the logic for dynamically sourcing variant types and language codes from the actual LIFT data and project settings, rather than the RANGES file.

    2.1. [x] **Implement Variant Type Extraction from LIFT Data**
        *   Create a service to extract all unique variant types from `<trait>` elements within the main LIFT XML data.
        *   This service should query the BaseX database to get a distinct list of variant types currently in use.
        *   Expose this list via a new API endpoint, e.g., `GET /api/variants/types`.
        *   **Requirements**: `3.1.2`

    2.2. [x] **Implement Language Code Extraction from LIFT Data**
        *   Create a service to extract all unique language codes used in the LIFT XML data (e.g., in `<form>`, `<gloss>`, `<note>` elements).
        *   Expose this list via a new API endpoint, e.g., `GET /api/languages/used`.
        *   **Requirements**: `3.1.3`

    2.3. [ ] **Develop Project Settings Service for Language Codes**
        *   Implement a mechanism to define project-specific admissible language codes (e.g., in a `project_settings.yaml` file or a database table).
        *   The API (`GET /api/languages/available`) must return the *union* of language codes found in the LIFT data and those defined in the project settings.
        *   **Requirements**: `3.1.3`

    2.4. [ ] **Write Tests for Variant and Language Services**
        *   Write tests to verify that variant types are correctly extracted from sample LIFT XML.
        *   Write tests to ensure language codes are correctly extracted and that the union with project settings works as expected.
        *   **Requirements**: `4.1`

3.  [x] **Frontend: UI Integration**
    *   This epic covers updating the frontend UI components to consume the new API endpoints and dynamically populate all relevant dropdowns and selectors.

    3.1. [x] **Create a JavaScript Range Loader Utility**
        *   Develop a reusable JavaScript utility (`ranges-loader.js`) that fetches data from the `/api/ranges/*`, `/api/variants/types`, and `/api/languages/available` endpoints.
        *   This utility should be responsible for populating `<select>` elements dynamically.
        *   It must support rendering hierarchical options (e.g., for semantic domains).
        *   **Requirements**: `3.1.3`, `3.1.5`

    3.2. [x] **Update All Affected UI Components**
        *   Integrate the `ranges-loader.js` utility into all UI components listed in the specification.
        *   **Entry Form**: Grammatical Info, Relationship Types, Etymology Types, Note Languages, Example Translation Types.
        *   **Search Filters & Query Builder**: All dropdowns must use the dynamic data.
        *   **Variant Type Selectors**: Must be populated from the `/api/variants/types` endpoint.
        *   **Language Selectors**: Must be populated from the `/api/languages/available` endpoint.
        *   **Requirements**: `3.1.5`, `7.2.2`

    3.3. [x] **Implement Pronunciation Field Restrictions**
        *   Modify the pronunciation section in the entry form to hardcode the language as "seh-fonipa".
        *   The language selector for pronunciation fields must be removed or hidden from the UI.
        *   **Note**: This is partially implemented. The language is hardcoded in the template, but not enforced as the *only* option in the backend.
        *   **Requirements**: `3.1.4`, `3.1.5`

    3.4. [ ] **Write End-to-End UI Tests**
        *   Use a framework like Playwright to write tests that verify:
        *   All specified dropdowns are populated with data from the APIs.
        *   Hierarchical data is displayed correctly.
        *   The pronunciation language is correctly restricted.
        *   The UI gracefully handles API errors or empty data responses.
        *   **Requirements**: `4.1.3`, `16.3.2`