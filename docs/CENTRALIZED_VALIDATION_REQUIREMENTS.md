# Centralized Validation Requirements Specification

## Overview

This document consolidates all validation requirements for the Lexicographic Curation Workbench (LCW) refactor. The goal is to move from scattered validation logic in models to a centralized, declarative validation system using Schematron (for XML) and a Jsontron-inspired system (for JSON). This specification serves as the single source of truth for all validation rules before implementing the centralized validation system.

## Validation Architecture

### Central Validation System
- **XML Validation**: Schematron (ISO Schematron) using `lxml` with LIFT-specific Schematron rules
- **JSON Validation**: Jsontron-inspired custom validation engine
- **Single Source of Truth**: All validation rules defined in central configuration files
- **Dynamic Rule Loading**: Rules loaded from configuration, not hardcoded in models
- **Layered Validation**: Client-side (UX enhancement) + Server-side (data integrity)

### Current State Analysis
- **Problem**: Validation logic scattered across model classes (`app/models/entry.py`, `app/models/sense.py`, etc.)
- **Solution**: Move all validation to central declarative rulesets
- **Test Coverage**: Comprehensive test suite already exists in `tests/test_validation_rules.py`
- **Migration Path**: Preserve existing test behavior while centralizing implementation

## Validation Rules Inventory

### R1: Entry Level Validation

#### R1.1: Required Fields
- **R1.1.1**: Entry ID is required and must be non-empty
  - **Current Implementation**: `app/models/entry.py:283`
  - **Test Coverage**: `tests/test_validation_rules.py:test_r1_1_1_entry_id_required`
  - **Error Message**: "Entry ID is required"
  - **Priority**: Critical (Must Fix Before Save)

- **R1.1.2**: Lexical unit is required and must contain at least one language entry
  - **Current Implementation**: `app/models/entry.py:287`
  - **Test Coverage**: `tests/test_validation_rules.py:test_r1_1_2_lexical_unit_required`
  - **Error Message**: "Lexical unit is required"
  - **Priority**: Critical (Must Fix Before Save)

- **R1.1.3**: At least one sense is required per entry
  - **Current Implementation**: `app/models/entry.py:291`
  - **Test Coverage**: `tests/test_validation_rules.py:test_r1_1_3_at_least_one_sense_required`
  - **Error Message**: "At least one sense is required"
  - **Priority**: Critical (Must Fix Before Save)

#### R1.2: Field Format Validation
- **R1.2.1**: Entry ID must match pattern `^[a-zA-Z0-9_\- ]+$` (allows spaces per LIFT standard)
  - **Current Implementation**: `app/models/entry.py:295` + `_is_valid_id_format` method
  - **Test Coverage**: `tests/test_validation_rules.py:test_r1_2_1_entry_id_format_validation`
  - **Error Message**: "Invalid entry ID format. Use only letters, numbers, underscores, hyphens, and spaces"
  - **Priority**: Warning (Should Fix)

- **R1.2.2**: Lexical unit must be a dictionary with language codes as keys
  - **Current Implementation**: Implicit in model structure
  - **Test Coverage**: Covered in basic structure tests
  - **Priority**: Critical (Must Fix Before Save)

- **R1.2.3**: Language codes must be from approved project list
  - **Current Implementation**: `app/models/entry.py:300` + `_is_valid_language_code` method
  - **Valid Codes**: {"en", "pl", "fr", "de", "seh-fonipa"}
  - **Error Message**: "Invalid language code: {lang_code}"
  - **Priority**: Warning (Should Fix)

#### R1.3: Structural Validation
- **R1.3.1**: Entry must have unique ID within dictionary
  - **Current Implementation**: Not in model (handled at service level)
  - **Priority**: Critical (Must Fix Before Save)

- **R1.3.2**: Homograph numbers must be unique for entries with same lexical unit
  - **Current Implementation**: Not in model (handled at service level)
  - **Priority**: Warning (Should Fix)

### R2: Sense Level Validation

#### R2.1: Required Fields
- **R2.1.1**: Sense ID is required and must be non-empty
  - **Current Implementation**: `app/models/entry.py:304` (in entry validation loop)
  - **Test Coverage**: `tests/test_validation_rules.py:test_r2_1_1_sense_id_required`
  - **Error Message**: "Sense at index {i} is missing an ID"
  - **Priority**: Critical (Must Fix Before Save)

- **R2.1.2**: Sense definition OR gloss is required (except for variant senses)
  - **Current Implementation**: `app/models/entry.py:308` + `_has_content_or_is_variant` method
  - **Test Coverage**: `tests/test_validation_rules.py:test_r2_1_2_sense_content_or_gloss_required`
  - **Error Message**: "Sense at index {i} must have definition or gloss"
  - **Priority**: Critical (Must Fix Before Save)

- **R2.1.3**: Variant senses must reference valid base sense/entry
  - **Current Implementation**: Basic structure check in `_has_content_or_is_variant`
  - **Test Coverage**: `tests/test_validation_rules.py:test_r2_1_3_variant_sense_validation`
  - **Priority**: Critical (Must Fix Before Save)

#### R2.2: Content Validation
- **R2.2.1**: Sense definitions must be non-empty strings when provided
  - **Current Implementation**: `app/models/entry.py:313`
  - **Test Coverage**: `tests/test_validation_rules.py:test_r2_2_1_definition_content_validation`
  - **Error Message**: "Sense at index {i}: Definition cannot be empty"
  - **Priority**: Warning (Should Fix)

- **R2.2.2**: Sense glosses must be non-empty strings when provided
  - **Current Implementation**: `app/models/entry.py:318`
  - **Test Coverage**: `tests/test_validation_rules.py:test_r2_2_2_gloss_content_validation`
  - **Error Message**: "Sense at index {i}: Gloss cannot be empty"
  - **Priority**: Warning (Should Fix)

- **R2.2.3**: Example texts must be non-empty when example is present
  - **Current Implementation**: `app/models/entry.py:323`
  - **Test Coverage**: `tests/test_validation_rules.py:test_r2_2_3_example_text_validation`
  - **Error Message**: "Sense at index {i}, Example {j + 1}: Example text cannot be empty"
  - **Priority**: Warning (Should Fix)

### R3: Note and Multilingual Content Validation

#### R3.1: Note Structure
- **R3.1.1**: Note types must be unique per entry
  - **Current Implementation**: Not implemented (identified as gap)
  - **Test Coverage**: Tests exist but not implemented
  - **Error Message**: "Duplicate note type: {note_type}"
  - **Priority**: Warning (Should Fix)

- **R3.1.2**: Note content must be non-empty when note type is specified
  - **Current Implementation**: `app/models/entry.py:341`
  - **Error Message**: "Note content cannot be empty for type: {note_type}"
  - **Priority**: Warning (Should Fix)

- **R3.1.3**: Multilingual notes must follow proper language code structure
  - **Current Implementation**: `app/models/entry.py:348`
  - **Error Message**: "Invalid language code in note: {lang}" / "Note content cannot be empty for type: {note_type}, language: {lang}"
  - **Priority**: Warning (Should Fix)

### R4: Pronunciation Validation (IPA-specific)

#### R4.1: Format Validation
- **R4.1.1**: Pronunciation language restricted to "seh-fonipa" only
  - **Current Implementation**: `app/models/entry.py:331`
  - **Test Coverage**: `tests/test_validation_rules.py:test_r4_1_1_pronunciation_language_restriction`
  - **Error Message**: "Pronunciation language must be 'seh-fonipa', found: {lang_code}"
  - **Priority**: Critical (Must Fix Before Save)

- **R4.1.2**: IPA characters must be from approved character set
  - **Current Implementation**: `app/models/entry.py:397` (`_validate_ipa` method)
  - **Valid Characters**: 
    - Vowels: 'ɑæɒəɜɪiʊuʌeɛoɔ'
    - Consonants: 'bdfghjklmnprstwvzðθŋʃʒ'
    - Length markers: 'ː'
    - Stress markers: 'ˈˌ'
    - Special: 'ᵻ'
    - Allowed: space, period
  - **Test Coverage**: `tests/test_validation_rules.py:test_r4_1_2_ipa_character_validation`
  - **Error Message**: "Invalid IPA character: '{char}' at position {i + 1}"
  - **Priority**: Critical (Must Fix Before Save)

#### R4.2: Sequence Validation
- **R4.2.1**: No double stress markers (ˈˈ, ˌˌ, ˈˌ, ˌˈ)
  - **Current Implementation**: `app/models/entry.py:424`
  - **Test Coverage**: `tests/test_validation_rules.py:test_r4_2_1_double_stress_markers`
  - **Error Message**: "Double stress markers not allowed"
  - **Priority**: Warning (Should Fix)

- **R4.2.2**: No double length markers (ːː)
  - **Current Implementation**: Missing (identified gap)
  - **Test Coverage**: Should be added
  - **Error Message**: "Double length markers not allowed"
  - **Priority**: Warning (Should Fix)

- **R4.2.3**: Complex consonants and diphthongs must be valid combinations
  - **Current Implementation**: Not implemented (identified gap)
  - **Test Coverage**: Should be added
  - **Priority**: Informational (Nice to Fix)

### R5: Relation and Reference Validation

#### R5.1: Reference Integrity
- **R5.1.1**: All entry references must point to existing entries
  - **Current Implementation**: Not in model (requires database access)
  - **Priority**: Critical (Must Fix Before Save)

- **R5.1.2**: Sense-level references (entry#sense) must point to existing senses
  - **Current Implementation**: Not in model (requires database access)
  - **Priority**: Critical (Must Fix Before Save)

- **R5.1.3**: Variant references must be valid and not create circular dependencies
  - **Current Implementation**: Not in model (requires database access)
  - **Priority**: Critical (Must Fix Before Save)

#### R5.2: Relation Types
- **R5.2.1**: Relation types must be from LIFT ranges
  - **Current Implementation**: `app/models/entry.py:357` (`_is_valid_relation_type` - not implemented)
  - **Priority**: Warning (Should Fix)

- **R5.2.2**: Variant types must be extracted from LIFT trait data
  - **Current Implementation**: Not implemented (requires LIFT parsing)
  - **Priority**: Warning (Should Fix)

### R6: Part-of-Speech Consistency

#### R6.1: Entry-Sense Consistency
- **R6.1.1**: Entry POS and sense POS must be consistent when both present
  - **Current Implementation**: `app/models/entry.py:980` (`_validate_pos_consistency`)
  - **Test Coverage**: Exists but implementation incomplete
  - **Priority**: Warning (Should Fix)

- **R6.1.2**: Conflicting sense POS values require manual entry POS
  - **Current Implementation**: `app/models/entry.py:980` (partially)
  - **Priority**: Warning (Should Fix)

#### R6.2: POS Format Validation
- **R6.2.1**: POS values must be from approved grammatical ranges
  - **Current Implementation**: Not implemented (requires LIFT ranges)
  - **Priority**: Warning (Should Fix)

### R7: Client-Side Validation

#### R7.1: Form Validation Logic
- **Required Field Indicators**: `app/static/js/entry-form.js:51` - POS required field logic
- **Field Dependencies**: Complex POS inheritance logic in `validatePosConsistency`
- **Variant Form Validation**: `app/static/js/variant-forms.js:263` - required variant type
- **Relation Validation**: `app/static/js/relations_new.js:243` - required relation type

#### R7.2: Real-time Validation Feedback
- **Inline Errors**: Currently limited, needs expansion
- **Progress Indicators**: Basic implementation exists
- **Field State Management**: Partial implementation

### R8: LIFT Schema-Derived Advanced Validation

#### R8.1: Media and Resource Validation
- **R8.1.1**: Media file references must point to existing files
  - **Context**: `pronunciation-content` → `media` → `URLRef-content/@href`
  - **Rule**: All audio/media files referenced in pronunciation sections must exist
  - **Error Message**: "Media file not found: {file_path} referenced in pronunciation"
  - **Priority**: Critical (Must Fix Before Save)

- **R8.1.2**: Illustration file references must point to existing files
  - **Context**: `sense-content` → `illustration` → `URLRef-content/@href`
  - **Rule**: All illustration files referenced in senses must exist
  - **Error Message**: "Illustration file not found: {file_path} referenced in sense"
  - **Priority**: Critical (Must Fix Before Save)

- **R8.1.3**: URL/URI format validation for external references
  - **Context**: All `@href` attributes using `anyURI` datatype
  - **Rule**: External URLs must be valid URIs and accessible (HTTP 200 check optional)
  - **Error Message**: "Invalid URI format: {uri}"
  - **Priority**: Warning (Should Fix)

#### R8.2: Language Code and RFC 4646 Compliance
- **R8.2.1**: Language codes must follow RFC 4646 format
  - **Context**: `form-content/@lang` throughout the schema
  - **Rule**: All language attributes must conform to RFC 4646 (e.g., "en", "seh-fonipa", "pt-BR")
  - **Error Message**: "Invalid language code format: {lang_code}. Must follow RFC 4646"
  - **Priority**: Warning (Should Fix)

- **R8.2.2**: Unique language codes per multitext content
  - **Context**: `multitext-content` Schematron rule
  - **Rule**: Within any multitext element, each language code can appear only once
  - **Error Message**: "Duplicate language code: {lang_code} in multitext content"
  - **Priority**: Critical (Must Fix Before Save)

#### R8.3: Date and DateTime Validation
- **R8.3.1**: Date formats must be valid ISO dates
  - **Context**: `dateCreated`, `dateModified`, `dateDeleted`, `annotation/@when`
  - **Rule**: All date fields must follow ISO 8601 format (YYYY-MM-DD or full datetime)
  - **Error Message**: "Invalid date format: {date}. Use ISO 8601 format"
  - **Priority**: Critical (Must Fix Before Save)

- **R8.3.2**: Creation/modification date logic
  - **Context**: `extensible-without-field-content` dates
  - **Rule**: `dateModified` must be equal to or later than `dateCreated`
  - **Error Message**: "Modification date cannot be earlier than creation date"
  - **Priority**: Warning (Should Fix)

- **R8.3.3**: Deletion date validation
  - **Context**: `entry-content/@dateDeleted`
  - **Rule**: If `dateDeleted` is present, entry should be marked as deleted and not editable
  - **Error Message**: "Cannot modify deleted entry (deleted on {date})"
  - **Priority**: Critical (Must Fix Before Save)

#### R8.4: Annotation and Audit Trail Validation
- **R8.4.1**: Annotation authorship tracking
  - **Context**: `annotation-content/@who`
  - **Rule**: When present, `@who` should reference a valid user/contributor
  - **Error Message**: "Unknown contributor: {who} in annotation"
  - **Priority**: Informational (Nice to Fix)

- **R8.4.2**: Annotation completeness
  - **Context**: `annotation-content` structure
  - **Rule**: Annotations should have either meaningful text content or a value attribute
  - **Error Message**: "Annotation must have text content or value"
  - **Priority**: Warning (Should Fix)

#### R8.5: Relation Semantic Validation
- **R8.5.1**: Abbreviation-expansion length validation
  - **Context**: Relations with type "abbreviation" or "expansion"
  - **Rule**: For abbreviation relations, target should be longer than source; for expansion relations, target should be shorter
  - **Error Message**: "Suspicious {relation_type} relation: target length suggests reversed relationship"
  - **Priority**: Warning (Should Fix)

- **R8.5.2**: Synonym/antonym mutual exclusion
  - **Context**: `relation-content` with synonym/antonym types
  - **Rule**: An entry cannot have both synonym and antonym relations to the same target
  - **Error Message**: "Conflicting relations: entry has both synonym and antonym relations to {target}"
  - **Priority**: Warning (Should Fix)

- **R8.5.3**: Relation order consistency
  - **Context**: `relation-content/@order`
  - **Rule**: When order is specified, values should be sequential without gaps
  - **Error Message**: "Relation order values have gaps or duplicates"
  - **Priority**: Informational (Nice to Fix)

#### R8.6: Field and Trait Uniqueness
- **R8.6.1**: Field type uniqueness per element
  - **Context**: Schematron rule in `field-content`
  - **Rule**: Each parent element can have only one field of each type
  - **Error Message**: "Duplicate field type: {type} in element"
  - **Priority**: Critical (Must Fix Before Save)

- **R8.6.2**: Trait name-value combination validation
  - **Context**: `trait-content` with `@name` and `@value`
  - **Rule**: Trait name-value combinations should be unique within parent element
  - **Error Message**: "Duplicate trait: {name}={value} in element"
  - **Priority**: Warning (Should Fix)

#### R8.7: Subsense and Hierarchical Validation
- **R8.7.1**: Subsense depth limits
  - **Context**: `sense-content` → `subsense` (recursive structure)
  - **Rule**: Subsense nesting should not exceed 3 levels deep to maintain readability
  - **Error Message**: "Subsense nesting too deep (maximum 3 levels)"
  - **Priority**: Warning (Should Fix)

- **R8.7.2**: Subsense inheritance validation
  - **Context**: `subsense` inheriting from parent `sense-content`
  - **Rule**: Subsenses should inherit grammatical info from parent sense if not explicitly specified
  - **Error Message**: "Subsense grammatical info conflicts with parent sense"
  - **Priority**: Informational (Nice to Fix)

#### R8.8: Range and Hierarchy Validation
- **R8.8.1**: Range element parent validation
  - **Context**: `range-element-content/@parent`
  - **Rule**: Parent references must point to existing range elements in the same range
  - **Error Message**: "Range element parent '{parent}' not found in range"
  - **Priority**: Critical (Must Fix Before Save)

- **R8.8.2**: Range hierarchical consistency
  - **Context**: Range element hierarchies
  - **Rule**: Range hierarchies should not contain circular references
  - **Error Message**: "Circular reference detected in range hierarchy"
  - **Priority**: Critical (Must Fix Before Save)

- **R8.8.3**: Range abbreviation-label consistency
  - **Context**: `range-element-content` with `abbrev` and `label`
  - **Rule**: Abbreviations should be shorter than their corresponding labels
  - **Error Message**: "Range abbreviation '{abbrev}' is longer than label '{label}'"
  - **Priority**: Informational (Nice to Fix)

#### R8.9: Translation Type and Content Validation
- **R8.9.1**: Translation type uniqueness
  - **Context**: Schematron rule in `translation-content`
  - **Rule**: Each parent element can have only one translation of each type
  - **Error Message**: "Duplicate translation type: {type}"
  - **Priority**: Critical (Must Fix Before Save)

- **R8.9.2**: Translation type consistency
  - **Context**: `translation-content/@type` with values "back", "free", "literal"
  - **Rule**: Translation types should follow LIFT conventions (back/free/literal)
  - **Error Message**: "Unknown translation type: {type}. Use: back, free, or literal"
  - **Priority**: Warning (Should Fix)

#### R8.10: Etymology Source and Form Validation
- **R8.10.1**: Etymology source validation
  - **Context**: `etymology-content/@source`
  - **Rule**: Etymology source should reference a known language or source text
  - **Error Message**: "Unknown etymology source: {source}"
  - **Priority**: Warning (Should Fix)

- **R8.10.2**: Etymology type validation
  - **Context**: `etymology-content/@type`
  - **Rule**: Etymology type should be from approved etymology classification
  - **Error Message**: "Unknown etymology type: {type}"
  - **Priority**: Warning (Should Fix)

- **R8.10.3**: Etymology form-gloss consistency
  - **Context**: `etymology-content` with `form` and `gloss`
  - **Rule**: If etymology has both form and gloss, they should be in compatible languages
  - **Error Message**: "Etymology form and gloss language mismatch"
  - **Priority**: Informational (Nice to Fix)

## Validation Rule Dependencies

### Database-Dependent Rules
These rules require access to the full dataset and cannot be validated in isolation:
- R1.3.1: Unique entry IDs
- R1.3.2: Unique homograph numbers
- R5.1.1: Entry reference integrity
- R5.1.2: Sense reference integrity
- R5.1.3: Circular reference detection
- R8.4.1: Annotation authorship tracking (user validation)
- R8.8.1: Range element parent validation
- R8.8.2: Range hierarchical consistency

### LIFT-Dependent Rules
These rules require parsing LIFT ranges or trait data:
- R5.2.1: Relation types from LIFT ranges
- R5.2.2: Variant types from LIFT traits
- R6.2.1: POS values from grammatical ranges
- R8.8.3: Range abbreviation-label consistency
- R8.9.2: Translation type consistency
- R8.10.1: Etymology source validation
- R8.10.2: Etymology type validation

### File System-Dependent Rules
These rules require file system access to validate resource references:
- R8.1.1: Media file existence validation
- R8.1.2: Illustration file existence validation
- R8.1.3: URL/URI accessibility validation (optional network check)

### Self-Contained Rules
These rules can be validated from the entry data alone:
- All R1.1.x: Basic required fields
- All R1.2.x: Format validation
- All R2.x: Sense-level validation
- All R3.x: Note validation
- All R4.x: Pronunciation validation
- R8.2.1: RFC 4646 language code format
- R8.2.2: Unique language codes per multitext
- R8.3.1: ISO date format validation
- R8.3.2: Creation/modification date logic
- R8.3.3: Deletion date validation
- R8.4.2: Annotation completeness
- R8.5.1: Abbreviation-expansion length validation
- R8.5.2: Synonym/antonym mutual exclusion
- R8.5.3: Relation order consistency
- R8.6.1: Field type uniqueness (LIFT Schematron rule)
- R8.6.2: Trait name-value combination validation
- R8.7.1: Subsense depth limits
- R8.7.2: Subsense inheritance validation
- R8.9.1: Translation type uniqueness (LIFT Schematron rule)
- R8.10.3: Etymology form-gloss consistency

## Implementation Strategy

### Phase 1: Central Rule Definition
1. **Create**: `validation_rules.json` - Central rule definitions
2. **Create**: `schemas/lift_validation.sch` - Schematron schema for XML
3. **Create**: `services/validation_engine.py` - Core validation engine
4. **Migrate**: All validation logic from models to central engine

### Phase 2: Service Integration
1. **Implement**: PySchematron integration for XML validation
2. **Implement**: JSON validation engine (Jsontron-inspired)
3. **Create**: Validation API endpoints
4. **Update**: Models to use central validation service

### Phase 3: Client-Side Integration
1. **Create**: `static/js/validation_client.js` - Client-side validation
2. **Implement**: Real-time validation feedback
3. **Update**: Form components to use central validation
4. **Add**: Inline error display and field state management

### Phase 4: Testing and Cleanup
1. **Verify**: All existing tests pass with new implementation
2. **Add**: Tests for new validation features
3. **Remove**: Scattered validation logic from models
4. **Document**: Updated validation system

## Success Criteria

1. **All validation rules centrally defined**: No validation logic in model classes
2. **Test compatibility**: All existing validation tests pass unchanged
3. **Performance**: Validation completes within 500ms for typical entries
4. **Extensibility**: New rules can be added via configuration, not code changes
5. **Client-server consistency**: Same validation logic applies on both sides
6. **Error quality**: Clear, actionable error messages with field paths

## Migration Notes

### Backward Compatibility
- All existing API error formats must be preserved
- Existing test expectations must be maintained
- Model interfaces should remain unchanged (validation moves to service layer)

### Configuration Format
The central validation rules should be defined in a declarative format that supports:
- Rule conditions and constraints
- Error message templates
- Priority levels (critical/warning/info)
- Client-side applicability flags
- Dependency specifications (DB/LIFT/self-contained)

### Error Message Consistency
All error messages should follow consistent patterns:
- Field path identification
- Clear problem description
- Actionable correction guidance
- Internationalization support

This specification provides the foundation for implementing a centralized, declarative validation system that replaces the current scattered validation logic while maintaining full backward compatibility and test coverage.
