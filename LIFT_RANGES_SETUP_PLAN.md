## Note on Variant-Types and Complex-Form-Types

According to the LIFT 0.13 standard, variant-types and complex-form-types are not defined in the `.lift-ranges` XML file. Instead, they are represented as traits on lexical relations or variants, and their values are discovered dynamically from the data or set up per project (often via a custom editor or database insert).

**Best Practice:**
- Maintain a recommended set of variant-types and complex-form-types (e.g., dialect, register, compound, reduplicated) in a separate JSON or YAML file for easy editing and installation.
- Enhance the install procedure for new projects to read these sets and insert them into the database or expose them via the editor/API, ensuring lexicographers have access to best-practice values from the start.
- Document these recommended sets alongside the `.lift-ranges` file for clarity and future customization.

This approach keeps the project setup minimal, standards-compliant, and easily extensible for future needs.
# LIFT Ranges Setup & Best Practice Implementation Plan

## Objective
Create a robust, reusable, and standards-compliant system for initializing LIFT ranges (including semantic domains, variant-types, complex-form-types, etc.) with recommended values and definitions, supporting lexicographers working on minority languages.

## Motivation
- Enable lexicographers to rely on a rich semantic classification system (e.g., semantic domains) and best-practice variant/complex form types.
- Ensure project/test environments are initialized with meaningful, recommended values, not just empty range definitions.
- Align with contemporary lexicographic standards (e.g., SIL Fieldworks).

## Stages

### 1. Prepare Minimal, Trimmed-Down LIFT Ranges File
- Create a new `.lift-ranges` XML file containing:
  - All required range definitions (semantic domains, variant-types, complex-form-types, etc.)
  - A curated set of recommended values for each range, with labels, definitions, and metadata.
- Semantic domains should reflect a practical classification system (e.g., DDP4, SIL domains).
- Variant-types and complex-form-types should include best-practice examples (e.g., dialect, register, compound, reduplicated).

### 2. Implement Import & Install Logic
- Add or update backend logic to:
  - Import the trimmed-down `.lift-ranges` file at project/test initialization.
  - Ensure all ranges and their values are loaded into the database and exposed via the API.
- Provide a management command or API endpoint for re-installing/re-initializing ranges as needed.

### 3. Integration Test Setup
- Update integration tests to:
  - Use the new install logic to guarantee all required ranges and values are present.
  - Assert that semantic domains, variant-types, and complex-form-types are available and correct.
  - Clean up or reset ranges/values after tests if needed.

### 4. UI/Editor Support
- Ensure the ranges editor and query builder UI:
  - Display all recommended values for each range.
  - Allow lexicographers to add, edit, or remove values as needed.
  - Provide definitions and metadata for each value to support best practice.

### 5. Documentation & Best Practice Guidance
- Document the recommended values and their intended use (e.g., why certain variant-types are included).
- Provide guidance for lexicographers on customizing ranges for their language/project.
- Reference SIL Fieldworks and other standards for further reading.

## Deliverables
- `minimal.lift-ranges` file with curated values
- Backend logic for importing/installing ranges and values
- Updated integration tests
- UI/editor improvements (if needed)
- Documentation on best practices

## Next Steps
1. Draft the trimmed-down `.lift-ranges` file with recommended values.
2. Implement the import/install logic.
3. Update tests and documentation.

---
This plan ensures a standards-based, user-friendly, and testable approach to LIFT range setup for minority language lexicography.
