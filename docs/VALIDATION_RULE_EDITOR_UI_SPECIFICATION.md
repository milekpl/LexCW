# Validation Rule Editor UI Specification

## Overview
The Validation Rule Editor UI allows users to customize validation rules for their dictionary project. The system will provide an initial set of rules based on the existing validation rules in the codebase, with the ability to modify, add, or remove rules per project.

## UI Components

### 1. Main Dashboard
- **Project-specific validation rules list**: Shows all validation rules for the current project
- **Rule categories filter**: Filter by category (entry_level, sense_level, note_validation, etc.)
- **Rule priority filter**: Filter by priority (critical, warning, informational)
- **Search functionality**: Search rules by ID, name, or description
- **Import/Export buttons**: Import/export validation rules as JSON
- **Save/Reset buttons**: Save changes or reset to default rules

### 2. Rule Editor Panel
- **Rule ID field**: Auto-generated ID (e.g., R1.1.1) - editable for new rules
- **Rule name field**: Human-readable name for the rule
- **Description field**: Detailed description of what the rule validates
- **Category dropdown**: Select from available categories (entry_level, sense_level, etc.)
- **Priority dropdown**: Select priority (critical, warning, informational)
- **Path field**: JSONPath expression to target the data element to validate
- **Condition type**: Select condition type (required, if_present, custom, etc.)
- **Validation type**: Select validation type (string, array, object, number, boolean, custom)
- **Validation parameters**: Dynamic fields based on validation type:
  - For string: minLength, maxLength, pattern, not_pattern
  - For array: minItems, maxItems
  - For object: minProperties, maxProperties, keys_in
  - For custom: custom_function selection
- **Error message field**: Customizable error message with template support
- **Client-side toggle**: Enable/disable client-side validation
- **Validation mode**: Select when rule applies (all, save_only, delete_only, draft_only)

### 3. Rule Preview Panel
- **JSON preview**: Shows the rule in JSON format as it will be saved
- **Validation test**: Allows testing the rule against sample data
- **Sample data input**: Text area for entering sample JSON data to test against

### 4. Bulk Operations
- **Enable/Disable selected rules**: Toggle multiple rules at once
- **Delete selected rules**: Remove multiple rules at once
- **Import rules from template**: Load predefined rule sets

## Data Structure

### Validation Rule Schema
```json
{
  "rule_id": "string",
  "name": "string",
  "description": "string",
  "category": "enum",
  "priority": "enum",
  "path": "string (JSONPath)",
  "condition": {
    "type": "string",
    "when": "object (for conditional rules)"
  },
  "validation": {
    "type": "string",
    "minLength": "number",
    "maxLength": "number",
    "pattern": "string",
    "compiled_pattern": "regex (computed)",
    "not_pattern": "string",
    "compiled_not_pattern": "regex (computed)",
    "minItems": "number",
    "maxItems": "number",
    "minProperties": "number",
    "maxProperties": "number",
    "keys_in": "array",
    "custom_function": "string"
  },
  "error_message": "string",
  "client_side": "boolean",
  "validation_mode": "string"
}
```

## Functionality

### 1. Rule Management
- **Add new rule**: Create a new validation rule with default values
- **Edit existing rule**: Modify any existing rule
- **Delete rule**: Remove a rule (with confirmation)
- **Duplicate rule**: Create a copy of an existing rule
- **Reorder rules**: Drag-and-drop to change rule execution order

### 2. Project-Specific Storage
- **Per-project rules**: Each project has its own validation rules file
- **Default rules**: System provides default rules based on existing validation_rules.json
- **Version control**: Track changes to validation rules over time
- **Validation on save**: Validate the rules JSON against schema before saving

### 3. Testing and Validation
- **Real-time validation**: Validate rule configuration as user types
- **Test with sample data**: Test rules against sample entry data
- **Validation results display**: Show validation results with color-coded feedback
- **Error highlighting**: Highlight invalid rule configurations

### 4. Templates and Presets
- **Default template**: Start with rules from validation_rules_v2.json
- **Custom templates**: Save and load rule sets for different project types
- **Import from existing**: Import rules from other projects or JSON files

## UI Layout

### Main Interface
```
┌─────────────────────────────────────────────────────────┐
│ Validation Rule Editor - [Project Name]                 │
├─────────────────────────────────────────────────────────┤
│ [Search] [Filter: Category ▼] [Filter: Priority ▼]      │
│ [Import] [Export] [Save] [Reset] [New Rule]             │
├─────────────────────────────────────────────────────────┤
│ Rule ID    │ Name              │ Category │ Priority    │
│─────────────────────────────────────────────────────────│
│ R1.1.1     │ entry_id_required │ entry... │ critical    │
│ R1.1.2     │ lexical_unit_...  │ entry... │ critical    │
│ ...        │ ...               │ ...      │ ...         │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ Rule Editor Panel                                       │
├─────────────────────────────────────────────────────────┤
│ Rule ID: [R1.1.1        ]                              │
│ Name:   [entry_id_required]                            │
│ Desc:   [Entry ID is required...]                      │
│ Cat:    [entry_level ▼] [Priority: critical ▼]         │
│ Path:   [$.id]                                         │
│ Cond:   [required ▼]                                   │
│ Val:    [string ▼] [Min Length: 1]                     │
│ Error:  [Entry ID is required...]                      │
│ [Client-Side: ✓] [Mode: all ▼]                        │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ Preview & Test Panel                                    │
├─────────────────────────────────────────────────────────┤
│ JSON Preview:                                           │
│ {                                                       │
│   "rule_id": "R1.1.1",                                 │
│   "name": "entry_id_required",                         │
│   ...                                                   │
│ }                                                       │
│                                                         │
│ Test Data:                                              │
│ [Sample JSON entry data for testing...]                 │
│ [Test Rule] [Validation Result: ✓ Valid / ✗ Invalid]    │
└─────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Backend API Endpoints
- `GET /api/projects/{project_id}/validation-rules` - Get project validation rules
- `PUT /api/projects/{project_id}/validation-rules` - Update project validation rules
- `GET /api/validation-rule-templates` - Get available rule templates
- `POST /api/validation-rules/test` - Test validation rules against sample data

### 2. Frontend Components
- **RuleList**: Displays and manages the list of validation rules
- **RuleEditor**: Provides the form for editing rule properties
- **RulePreview**: Shows the JSON representation and test functionality
- **ValidationTester**: Component for testing rules against sample data

### 3. State Management
- **Current project validation rules**: Store in component state
- **Dirty state tracking**: Track unsaved changes
- **Validation status**: Track validation of rule configurations
- **Test results**: Store results of validation tests

## Security and Validation

### 1. Input Validation
- Validate all rule properties against schema
- Sanitize JSONPath expressions to prevent injection
- Validate regex patterns before compilation

### 2. Access Control
- Only project administrators can modify validation rules
- Read-only access for other users
- Audit trail for rule changes

### 3. Data Integrity
- JSON schema validation for rule configurations
- Prevent circular references in conditions
- Validate custom function names exist

## Project-Specific Storage

### 1. File location
- Each project will have its own validation rules file stored at `projects/{project_name}/validation_rules.json`
- Database integration: Validation rules will also be stored in the PostgreSQL database in a `project_validation_rules` table
- Backup integration: Validation rules will be included in project backup archives

### 2. Database Schema
```sql
CREATE TABLE project_validation_rules (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    rule_id VARCHAR(50) NOT NULL,
    rule_config JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_project_validation_rules_project_id ON project_validation_rules(project_id);
CREATE INDEX idx_project_validation_rules_rule_id ON project_validation_rules(rule_id);
```

### 3. File Storage Structure
- **Default location**: `projects/{project_name}/validation_rules.json`
- **Format**: JSON format matching the validation engine schema
- **Versioning**: Include version field to track schema changes
- **Validation**: Validate against JSON schema before saving

### 4. API Integration
- **Load rules**: `GET /api/projects/{project_id}/validation-rules` loads project-specific rules
- **Save rules**: `PUT /api/projects/{project_id}/validation-rules` saves rules to project
- **Validation**: Validate rules against schema before persisting
- **Caching**: Cache rules in memory for performance after loading

### 5. Project Initialization
- **Default rules**: When creating a new project, copy default rules from `validation_rules_v2.json`
- **Migration**: For existing projects, migrate to project-specific rules
- **Fallback**: If project has no custom rules, use system defaults

### 6. Validation Engine Integration
- **Project context**: Validation engine accepts project ID to load appropriate rules
- **Caching**: Cache project rules separately to avoid reloading
- **Fallback mechanism**: If project rules fail to load, use system defaults

### 7. Synchronization
- **File ↔ Database**: Keep file and database storage synchronized
- **Conflict resolution**: Handle concurrent modifications with version checking
- **Consistency checks**: Validate consistency between file and database storage

## Initial Set of Validation Rules

Based on the analysis of the existing validation rules in `validation_rules_v2.json`, the system will provide the following initial set of validation rules when creating a new project:

### 1. Entry-Level Validation Rules
- **R1.1.1**: `entry_id_required` - Entry ID is required and must be non-empty
- **R1.1.2**: `lexical_unit_required` - Lexical unit is required and must contain at least one language entry
- **R1.1.3**: `sense_required_non_variant` - At least one sense is required per entry (except for variant entries)
- **R1.2.1**: `entry_id_format` - Entry ID must match valid format pattern
- **R1.2.2**: `lexical_unit_content_validation` - Lexical unit content must be non-empty strings
- **R1.2.3**: `language_code_validation` - Lexical unit must contain at least one language

### 2. Sense-Level Validation Rules
- **R2.1.1**: `sense_id_required` - Sense ID is required and must be non-empty
- **R2.1.2**: `sense_content_or_variant` - Sense must have definition, gloss, or variant reference
- **R2.2.1**: `definition_content_validation` - Sense definitions must have at least one non-empty language value
- **R2.2.2**: `gloss_content_validation` - Sense glosses must have at least one non-empty language value
- **R2.2.3**: `example_text_validation` - Example texts must be non-empty when example is present
- **R5.2.1**: `subsense_depth` - Subsense nesting must not exceed 3 levels

### 3. Notes-Level Validation Rules
- **R3.1.1**: `unique_note_types` - Note types must be unique within entry
- **R3.2.1**: `multilingual_note_structure` - Multilingual notes must be objects with at least one language

### 4. Pronunciation-Level Validation Rules
- **R4.1.1**: `pronunciation_language_codes` - Pronunciation language codes must be valid

### 5. Relations-Level Validation Rules
- **R5.1.1**: `synonym_antonym_exclusion` - Entries cannot be both synonym and antonym
- **R8.1.1**: `no_circular_component_references` - Component relations must not reference the entry itself
- **R8.1.2**: `no_circular_sense_references` - Sense relations must not reference senses within the same entry
- **R8.1.3**: `no_circular_entry_references` - Entry-level relations must not reference the entry itself

### 6. General Validation Rules
- **R6.1.1**: `unique_languages_in_multitext` - Language codes must be unique in multilingual content
- **R7.1.1**: `date_fields_format` - Date fields must be in ISO8601 format

### 7. Default Configuration
- **Priority levels**: Critical (blocks save), Warning (advisory), Informational (information only)
- **Categories**: Organized by data structure level (entry, sense, notes, etc.)
- **Client-side**: Most rules enabled for real-time validation
- **Validation mode**: Most rules apply to all operations, some only on save

### 8. Predefined Templates
- **Basic Dictionary**: Minimal set of essential validation rules
- **Academic Dictionary**: Full validation with strict requirements
- **Bilingual Dictionary**: Rules optimized for bilingual projects
- **Linguistic Research**: Validation rules for research-focused projects

This initial set provides comprehensive coverage of all major validation requirements while maintaining the flexibility to customize based on specific project needs.
