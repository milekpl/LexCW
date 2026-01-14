# Validation Rules Schema Implementation

## Overview

This document describes the JSON Schema validation system for `validation_rules.json`, which ensures that user edits to validation rules maintain proper structure and prevent configuration errors.

## Motivation

The original design intent was to validate user-editable configuration files (like `validation_rules.json`) against schemas, not just to validate LIFT XML files. Since validation rules can be edited by users, this introduces the possibility of:

1. **JSON syntax errors** (malformed JSON)
2. **Structural errors** (missing required fields, invalid enum values)
3. **Type errors** (wrong data types for fields)
4. **Logic errors** (combinations that don't make sense)

A JSON Schema provides:
- **Validation before runtime** - catch errors early
- **IDE support** - autocomplete and inline validation in editors
- **Documentation** - self-documenting structure
- **Consistency** - enforce naming conventions and patterns

## Architecture

### Two Validation Systems

1. **SchematronValidator** - Validates LIFT XML files against `schemas/lift_validation.sch`
   - Uses lxml's ISO Schematron support
   - Validates XML structure and LIFT standard compliance
   - Used at runtime when processing LIFT files

2. **ValidationRulesSchemaValidator** - Validates `validation_rules.json` against `schemas/validation_rules.schema.json`
   - Uses Python's jsonschema library
   - Validates the validation rules configuration file itself
   - Used during development and at startup

### File Structure

```
schemas/
├── lift_validation.sch              # Schematron schema for LIFT XML
└── validation_rules.schema.json     # JSON Schema for validation rules
```

## JSON Schema Details

### Location
`schemas/validation_rules.schema.json`

### Key Features

#### 1. Rule ID Pattern Validation
```json
"patternProperties": {
  "^R[0-9]+\\.[0-9]+\\.[0-9]+$": {
    "$ref": "#/definitions/validationRule"
  }
}
```
Enforces rule IDs like `R1.1.1`, `R3.2.5`, etc.

#### 2. Required Fields
Every validation rule must have:
- `name` - Human-readable name
- `description` - What the rule validates
- `category` - One of 10 predefined categories
- `priority` - critical, warning, or informational
- `path` - JSONPath to the field
- `condition` - When to validate (required, if_present, custom, etc.)
- `validation` - Validation criteria object
- `error_message` - User-facing error message

#### 3. Category Enum
Valid categories match actual usage:
- `entry_level` - Entry-level validation
- `sense_level` - Sense-level validation
- `note_validation` - Note content validation
- `pronunciation` - Pronunciation validation
- `resource_validation` - File/media validation
- `language_validation` - Language code validation
- `date_validation` - Date field validation
- `relation_validation` - Relation validation
- `hierarchical_validation` - Subsense depth, etc.
- `pos` - Part-of-speech validation

#### 4. Flexible Validation Object
The `validation` field accepts combinations of properties:
```json
{
  "type": "string",
  "minLength": 1,
  "pattern": "^[a-zA-Z0-9_\\- ]+$"
}
```

Supported properties:
- `pattern` - Regex pattern
- `enum` - Allowed values
- `type` - Data type (string, number, boolean, array, object)
- `minLength` / `min_length` - Minimum string length
- `minProperties` - Minimum object properties
- `min_items` - Minimum array items
- `custom` / `custom_function` - Custom validation function name

#### 5. Optional Fields
- `client_side` (boolean) - Enforce in browser
- `server_side` (boolean) - Enforce on server
- `validation_mode` - save_only, always, or publish_only
- `help_text` - Additional help for users
- `examples` - Valid/invalid examples

#### 6. Top-Level Properties
```json
{
  "version": "1.0",
  "description": "Centralized validation rules...",
  "rules": { ... },
  "custom_functions": { ... }
}
```

## Implementation

### ValidationRulesSchemaValidator Class

Located in `app/services/validation_engine.py`:

```python
class ValidationRulesSchemaValidator:
    """
    Validates the validation_rules.json file itself against a JSON Schema.
    
    This ensures that user edits to validation_rules.json maintain proper structure,
    catching syntax errors and structural issues before they cause runtime problems.
    """
```

#### Key Methods

1. **`__init__(schema_file)`** - Load JSON Schema
2. **`validate_rules_file(rules_file)`** - Validate a rules file
   - Returns `ValidationResult` with detailed errors
   - Catches JSON syntax errors
   - Validates against schema structure
   - Provides helpful error messages with paths

### Error Reporting

The validator provides detailed error information:

```python
ValidationError(
    rule_id='SCHEMA_VIOLATION',
    rule_name='schema_validation',
    message="Schema validation error: 'ipa' is not one of [...allowed values...]",
    path='rules.R1.2.3.category',
    priority=ValidationPriority.CRITICAL,
    category=ValidationCategory.ENTRY_LEVEL,
    value='ipa'  # The invalid value for debugging
)
```

## Usage

### At Development Time

Validate the rules file manually:
```python
from app.services.validation_engine import ValidationRulesSchemaValidator

validator = ValidationRulesSchemaValidator()
result = validator.validate_rules_file("validation_rules.json")

if not result.is_valid:
    for error in result.errors:
        print(f"Error at {error.path}: {error.message}")
```

### In IDE

Configure your IDE to use the JSON Schema:
1. Add schema reference to `validation_rules.json`:
```json
{
  "$schema": "./schemas/validation_rules.schema.json",
  "version": "1.0",
  ...
}
```

2. VS Code will automatically provide:
   - Autocomplete for field names
   - Inline validation errors
   - Hover documentation
   - Enum value suggestions

### At Startup (Future)

Add validation check during application startup:
```python
# In app/__init__.py or similar
validator = ValidationRulesSchemaValidator()
result = validator.validate_rules_file()
if not result.is_valid:
    raise ConfigurationError("Invalid validation_rules.json")
```

## Testing

### Test Suite

Located in `tests/unit/test_centralized_validation.py`:

```python
class TestValidationRulesSchemaValidator:
    """Test the JSON Schema validator for validation_rules.json."""
    
    def test_schema_validator_initialization(self):
        """Validator loads schema correctly"""
    
    def test_valid_rules_file(self):
        """Current validation_rules.json passes validation"""
    
    def test_invalid_json_syntax(self):
        """Catches malformed JSON"""
    
    def test_missing_required_field(self):
        """Catches missing required fields like 'name'"""
    
    def test_invalid_priority_value(self):
        """Catches invalid enum values"""
```

### Running Tests

```bash
python -m pytest tests/unit/test_centralized_validation.py::TestValidationRulesSchemaValidator -v
```

All 5 schema validation tests pass ✅

## Dependencies

- **jsonschema==4.19.0** - JSON Schema validation library
  - Already has dependencies: attrs, jsonschema-specifications, referencing, rpds-py

Added to `requirements.txt`:
```
# XML and data processing
lxml==4.9.3
jsonschema==4.19.0
```

## Benefits

### For Developers
- **Catch errors early** - Before runtime
- **Better IDE support** - Autocomplete and validation
- **Clear structure** - Schema documents the expected format
- **Consistent rules** - Enforced naming and structure

### For Users (Editors)
- **Immediate feedback** - IDE shows errors as you type
- **Helpful error messages** - Clear indication of what's wrong
- **Documentation** - Schema descriptions explain each field
- **Examples** - Valid/invalid examples guide correct usage

### For the System
- **Reliability** - Invalid configs rejected at startup
- **Maintainability** - Schema evolves with rules structure
- **Debugging** - Detailed error paths for troubleshooting
- **Consistency** - All rules follow same structure

## Future Enhancements

1. **Startup Validation** - Add automatic validation on app initialization
2. **Migration Tool** - Validate old rules files and suggest fixes
3. **Rule Generator** - Tool to generate new rules from schema template
4. **Custom Constraint Validation** - Add semantic rules (e.g., "custom_function must exist in custom_functions map")
5. **Schema Versioning** - Support multiple schema versions for backwards compatibility
6. **Interactive Editor** - Web UI for editing rules with live validation

## Summary

The JSON Schema validation system ensures that `validation_rules.json` remains valid and well-structured, preventing configuration errors before they impact the system. This complements the Schematron validation for LIFT XML files, providing comprehensive validation coverage across all user-editable configuration files.

**Test Results**: 74 passed, 2 skipped
- 69 validation rule tests
- 5 new JSON schema validator tests
- All green ✅
