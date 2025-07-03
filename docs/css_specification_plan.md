# Specification: LIFT to CSS Mapping and Rendering Engine v1.0

## 1. Introduction

### 1.1 Purpose

This document specifies the design and implementation plan for the **LIFT to CSS Mapping and Rendering Engine**. This engine is a core component of the Lexicographic Curation Workbench (LCW), responsible for transforming raw LIFT XML data into a formatted, human-readable dictionary view. It will power both the in-application entry preview and various export formats (e.g., HTML, Kindle).

The system must be highly configurable, allowing lexicographers to define the visual structure and style of dictionary entries, including element order, typography, and layout. It must also intelligently handle complex lexicographic structures, such as the grouping of subentries under a main entry.

### 1.2 Scope

-   **Data Model**: Define a schema for "Display Profiles" that store mapping and ordering rules.
   **Backend Service**: Create a service to manage Display Profiles and perform the LIFT-to-HTML transformation.
   **API Endpoints**: Expose functionality for managing profiles and rendering entry previews.
   **TDD Framework**: All development will strictly follow the Red-Green-Refactor cycle with comprehensive test coverage.
   **Structural Awareness**: The engine must understand and render root-based/stem-based entry structures, grouping subentries under their main entry.

## 2. Core Requirements

### 2.1 LIFT Element Analysis

Based on an analysis of `sample-lift-file.lift`, the system must support styling and ordering for the following key LIFT elements and their components:

-   **Entry Level**: `entry`, `lexical-unit`, `pronunciation`, `note` (entry-level)
-   **Sense Level**: `sense`, `grammatical-info`, `definition`, `gloss`, `reversal`, `note` (sense-level)
-   **Example Level**: `example`, `form` (source language), `translation` (target language)
-   **Relation Level**: `relation` (e.g., `synonim`, `antonim`), including its `ref` and text content. 
-   **Etymology Level**: `etymology`, including its `form` and `gloss`.
-   **Traits and Fields**: `trait` (e.g., `usage-type`, `domain-type`), `field` (custom fields).

LIFT ranges and trait names specify the abbreviations that can be used to mark up the element (e.g., a relation type may have a full label or an abbreviation in many languages). These should be selectable.

### 2.2 Functional Requirements

1.  **Display Profiles**: The system will use "Display Profiles" to manage different sets of styling and layout rules. Users should be able to create, edit, and switch between profiles (e.g., "Web View", "Print Export", "Kindle").
2.  **Element Ordering**: Administrators must be able to define the display order of elements within an entry (e.g., `pronunciation` before `grammatical-info`).
3.  **CSS Styling**: Administrators must be able to assign CSS classes to any mappable LIFT element, allowing for full stylistic control (font, color, weight, indentation, etc.).
4.  **Structural Grouping**: The engine must support different dictionary views:
   -   **List View**: Every entry is rendered as a separate block.
   -   **Root-Based/Stem-Based View**: Entries identified as subentries (via `_component-lexeme` relation) must be grouped and indented under their main entry.
5.  **Conditional Display**: The system should support hiding empty elements to maintain a clean layout.

## 3. Data Model: Display Profile

A Display Profile will be stored as a JSON object with the following structure. This allows for flexibility and easy storage in a PostgreSQL JSONB column or a configuration file.

```json
{
  "profile_id": "unique-profile-uuid",
  "profile_name": "Default Web View",
  "description": "Standard profile for viewing entries in the web UI.",
  "view_type": "root-based",
  "elements": [
    {
      "lift_element": "lexical-unit",
      "display_order": 1,
      "css_class": "headword",
      "prefix": "",
      "suffix": ""
    },
    {
      "lift_element": "pronunciation",
      "display_order": 2,
      "css_class": "pronunciation",
      "prefix": "[",
      "suffix": "]"
    },
    {
      "lift_element": "sense",
      "display_order": 3,
      "css_class": "sense-block",
      "children": [
        {
          "lift_element": "grammatical-info",
          "display_order": 1,
          "css_class": "pos-tag",
          "prefix": "",
          "suffix": ""
        },
        {
          "lift_element": "definition",
          "display_order": 2,
          "css_class": "definition",
          "prefix": "",
          "suffix": ""
        }
      ]
    }
  ]
}
```

## 4. Test-Driven Development Plan

### 4.1 Phase 1: Backend Service and API

This phase focuses on creating the core logic for managing profiles and transforming LIFT XML into styled HTML.

#### 4.1.1 Test Plan (Red Phase)

1.  **API Tests for Profile Management**:
    -   `test_create_profile`: `POST /api/display-profiles` with valid JSON returns 201.
    -   `test_get_profile`: `GET /api/display-profiles/{id}` returns the correct profile.
    -   `test_list_profiles`: `GET /api/display-profiles` returns a list of all profiles.
    -   `test_update_profile`: `PUT /api/display-profiles/{id}` updates and returns the profile.
    -   `test_delete_profile`: `DELETE /api/display-profiles/{id}` returns 204.

2.  **Service Tests for Rendering Logic**:
    -   `test_render_simple_entry`: A service method correctly transforms a simple entry into HTML with default styling.
    -   `test_render_with_custom_profile`: The service method uses a custom profile to apply specific CSS classes.
    -   `test_element_order_is_respected`: The generated HTML elements appear in the order specified by the profile's `element_order`.
    -   `test_hide_empty_elements`: An element with no content in the LIFT XML is not rendered in the HTML.
    -   `test_root_based_grouping`: Given a main entry (`acid test`) and its component (`test`), the service renders them as a single, nested block.
    -   `test_list_view_renders_separately`: With `view_type: "list"`, the same entries are rendered as two separate blocks.

#### 4.1.2 Implementation Plan (Green & Refactor Phase)

1.  **Create `CSSMappingService`**:
    -   Location: `app/services/css_mapping_service.py`.
    -   Responsibilities:
        -   CRUD operations for Display Profiles (initially using a JSON file for storage, later a DB table).
        -   A core `render_entry(entry_xml, profile)` method that uses `lxml` to traverse the XML and build the HTML output.
        -   Logic to query for and group subentries based on `_component-lexeme` relations when `view_type` is `root-based`.

2.  **Create API Endpoints**:
    -   Location: `app/api/display.py`.
    -   Implement CRUD endpoints for `/api/display-profiles`.
    -   Implement a preview endpoint: `GET /api/entries/{id}/preview?profile_id={profile_id}`. This endpoint will use the `CSSMappingService` to generate and return the HTML for a specific entry.

3.  **Refactor**:
    -   Ensure the transformation logic is decoupled from the data source (BaseX). It should accept an XML string or `lxml` element.
    -   Optimize the subentry lookup to avoid excessive database queries.

### 4.2 Phase 2: Frontend UI for Profile Management

This phase focuses on building the user interface for administrators to manage the Display Profiles.

#### 4.2.1 Test Plan (Red Phase)

1.  **UI Component Tests (Jest/Vue Test Utils)**:
    -   Test that the list of mappable LIFT elements renders correctly.
    -   Test that CSS class input fields update the component's state.

2.  **End-to-End Tests (Selenium/Cypress)**:
    -   `test_admin_can_navigate_to_mapping_page`: User can access the new admin page.
    -   `test_admin_can_create_and_save_profile`: A user can create a new profile, reorder elements via drag-and-drop, assign classes, and save. The changes should persist on page reload.
    -   `test_preview_pane_updates_on_style_change`: When a CSS class is changed in the editor, the preview pane for a sample entry updates to reflect the new style without a full page reload.
    -   `test_view_type_switcher_updates_preview`: Switching `view_type` from "list" to "root-based" correctly re-renders the preview to show grouped entries.

#### 4.2.2 Implementation Plan (Green & Refactor Phase)

1.  **Create Admin Template**:
    -   Location: `app/templates/admin/display_profiles.html`.
    -   Layout: A two-column layout. Left column for the profile editor, right column for the live preview.

2.  **Develop JavaScript Editor Component**:
    -   Location: `app/static/js/display_profile_editor.js`.
    -   Fetch a list of all mappable elements from a new API endpoint (`/api/lift-schema/elements`).
    -   Use `SortableJS` or a similar library to allow drag-and-drop reordering of the elements.
    -   On any change (reorder, style change), send the current profile configuration to the preview API endpoint (`/api/entries/{sample_id}/preview`) and update the preview `div`.
    -   A "Save" button will `POST` the final profile JSON to the `/api/display-profiles` endpoint.

3.  **Refactor**:
    -   Abstract the editor into reusable WebComponents for maintainability.
    -   Ensure the UI is fully responsive and accessible.

## 5. Structural Grouping Logic

The core of the "root-based" view is identifying and grouping related entries.

### 5.1 Identifying Subentries

An entry is considered a subentry if it is the target of a `relation` with `type="_component-lexeme"`.

**Example from `sample-lift-file.lift`**:
The entry for `aptitude test` is a subentry of `test1`.

```xml
<entry id="aptitude test_0fcaa962-e671-486b-8c29-1016d085620c">
    ...
    <relation type="_component-lexeme" ref="test1_3696e240-ad25-4bdc-abc5-b9d863bf5dbe" order="0">
      <trait name="is-primary" value="true"/>
      <trait name="complex-form-type" value="Compound"/>
      <trait name="hide-minor-entry" value="1"/>
    </relation>
    ...
</entry>
```

### 5.2 Rendering Algorithm for Root-Based View

When rendering an entry:
1.  Check if the entry has any `_component-lexeme` relations pointing *to* it. If so, it's a main entry.
2.  If it is a main entry, query the database for all other entries that have a `_component-lexeme` relation pointing to its `id`. These are its subentries.
3.  Render the main entry's HTML block.
4.  Iterate through the found subentries. For each subentry:
    -   Render its HTML block using the same display profile.
    -   Wrap the subentry's HTML in a container with a `subentry` CSS class for indentation and styling.
    -   Append this block to the main entry's block.
5.  If an entry is a subentry (i.e., it has a `_component-lexeme` relation pointing *from* it), it should not be rendered as a top-level item in the list. The rendering service should have a mechanism to skip already-rendered subentries.

## 6. Default CSS and Styling

The application will ship with a default `dictionary.css` file that provides basic, professional styling for the generated HTML. This file will contain classes like:

```css
/* d:/Dokumenty/slownik-wielki/flask-app/static/css/dictionary.css */

.entry-block {
    margin-bottom: 1.5em;
    border-left: 3px solid transparent;
}

.headword {
    font-size: 1.2em;
    font-weight: bold;
    color: #333;
}

.pronunciation {
    font-family: 'Doulos SIL', 'Charis SIL', serif;
    color: #555;
    margin-left: 0.5em;
}

.sense-block {
    margin-left: 1em;
    margin-top: 0.5em;
}

.pos-tag {
    font-style: italic;
    color: #777;
}

.definition {
    margin-left: 1em;
}

.subentry {
    margin-left: 2em;
    padding-left: 1em;
    border-left: 2px solid #eee;
}
```

This CSS file will be customizable and extendable through the Display Profile management UI.

## 7. Integration with Export Modules

The `CSSMappingService` will be a dependency for all export modules that produce styled output (HTML, Kindle, PDF).

-   **Kindle Export**: The Kindle exporter will call the `CSSMappingService` to generate the core HTML for the dictionary content. **IMPORTANT**: CSS will be replaced by direct styling as far as possible, since the use of styles makes the dictionary files much larger. Thus, a processor will be used to replace ALL CSS styling in-situ with HTML tags directly. It will then inject Kindle-specific CSS, HTML, and metadata before compiling the `.mobi` file.

-   **Flutter Export**: The Flutter export will use this service directly, as it exports HTML without Kindle tags to SQLite. Styles need not be flattened there.

<!--
[PROMPT_SUGGESTION]Based on the new specification, create the initial Python files for the models, services, and API endpoints, including the test files with failing tests (the "Red" phase of TDD).[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]Draft the HTML and JavaScript for the Display Profile editor UI, including the drag-and-drop list for element reordering.[/PROMPT_SUGGESTION]
->