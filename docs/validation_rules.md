# Validation Rules for Lexicographic Curation Workbench

## Overview

This document outlines comprehensive validation rules for the Lexicographic Curation Workbench (LCW) based on the existing codebase analysis and the refactoring specification. These rules will be implemented using Schematron (ISO Schematron) via `lxml` for server-side XML validation and a custom client-side validation system.

## Core Validation Rules

### R1: Entry Level Validation

#### R1.1: Required Fields
- **R1.1.1**: Entry ID is required and must be non-empty
- **R1.1.2**: Lexical unit is required and must contain at least one language entry
- **R1.1.3**: At least one sense is required per entry

#### R1.2: Field Format Validation
- **R1.2.1**: Entry ID must be a valid string matching pattern `^[a-zA-Z0-9_-]+$`
- **R1.2.2**: Lexical unit must be a dictionary with language codes as keys
- **R1.2.3**: Language codes must follow ISO format or project-specific codes (seh, en, pt, etc.)

#### R1.3: Structural Validation
- **R1.3.1**: Entry must have unique ID within the dictionary
- **R1.3.2**: Homograph numbers must be unique for entries with same lexical unit
- **R1.3.3**: Custom fields must follow valid naming conventions

### R2: Sense Level Validation

#### R2.1: Required Fields
- **R2.1.1**: Sense ID is required and must be non-empty
- **R2.1.2**: Sense definition OR gloss is required for all senses except variant senses
- **R2.1.3**: Variant senses must reference a valid base sense/entry

#### R2.2: Content Validation
- **R2.2.1**: Sense definitions must be non-empty strings when provided
- **R2.2.2**: Sense glosses must be non-empty strings when provided
- **R2.2.3**: Example texts must be non-empty when example is present

#### R2.3: Relationship Validation
- **R2.3.1**: Sense relations must reference valid existing entries/senses
- **R2.3.2**: Circular relationships are not allowed
- **R2.3.3**: Relation types must be from approved LIFT ranges

### R3: Note and Multilingual Content Validation

#### R3.1: Note Structure
- **R3.1.1**: Note types must be unique per entry (no duplicate etymology, grammar notes, etc.)
- **R3.1.2**: Note content must be non-empty when note type is specified
- **R3.1.3**: Multilingual notes must follow proper language code structure

#### R3.2: Language Consistency
- **R3.2.1**: All language codes used must exist in the project's language list
- **R3.2.2**: Vernacular language (seh) must be present in lexical unit
- **R3.2.3**: Translation languages must be valid project languages

### R4: Pronunciation Validation (IPA-specific)

#### R4.1: Format Validation
- **R4.1.1**: Pronunciation language must be restricted to "seh-fonipa" only
- **R4.1.2**: IPA characters must be from approved character set (vowels: ɑæɒəɜɪiʊuʌeɔ, consonants: bdfghjklmnprstwvzðθŋʃʒ)
- **R4.1.3**: Length markers (ː) and stress markers (ˈˌ) must follow proper placement rules

#### R4.2: Sequence Validation
- **R4.2.1**: No double stress markers (ˈˈ, ˌˌ, ˈˌ, ˌˈ)
- **R4.2.2**: No double length markers (ːː)
- **R4.2.3**: Complex consonants (tʃ, dʒ) and diphthongs must be valid combinations

### R5: Relation and Reference Validation

#### R5.1: Reference Integrity
- **R5.1.1**: All entry references must point to existing entries
- **R5.1.2**: Sense-level references (entry#sense) must point to existing senses
- **R5.1.3**: Variant references must be valid and not create circular dependencies

#### R5.2: Relation Types
- **R5.2.1**: Relation types must be from LIFT ranges (synonym, antonym, etc.)
- **R5.2.2**: Variant types must be extracted from actual LIFT trait data
- **R5.2.3**: Etymology types must conform to approved classifications

### R6: Part-of-Speech Consistency

#### R6.1: Entry-Sense Consistency
- **R6.1.1**: If entry has POS and senses have POS, they must be consistent
- **R6.1.2**: If senses have conflicting POS values, entry POS must be set manually
- **R6.1.3**: POS inheritance from entry to senses follows LIFT specification

#### R6.2: POS Format Validation
- **R6.2.1**: POS values must be from approved grammatical ranges
- **R6.2.2**: POS abbreviations must match full forms in ranges
- **R6.2.3**: Custom POS values must be properly documented

### R7: Variant and Etymology Validation

#### R7.1: Variant Structure
- **R7.1.1**: Variant forms must have proper language attribution
- **R7.1.2**: Variant types must be extracted from LIFT trait elements
- **R7.1.3**: Variant relationships must not create loops

#### R7.2: Etymology Structure
- **R7.2.1**: Etymology source must be specified
- **R7.2.2**: Etymology type must be from approved classification
- **R7.2.3**: Etymology form and gloss must have proper language codes

### R8: Dynamic Range Compliance

#### R8.1: LIFT Ranges Integration
- **R8.1.1**: All type/category options must come from LIFT ranges file
- **R8.1.2**: Hierarchical relationships between categories must be preserved
- **R8.1.3**: Multilingual labels and abbreviations must be supported

#### R8.2: Data-Driven Validation
- **R8.2.1**: Variant types extracted from actual `<trait>` elements only
- **R8.2.2**: Language codes limited to those found in LIFT XML
- **R8.2.3**: UI components must reflect actual data availability

### R9: Form Submission and State Management

#### R9.1: Client-Side Validation
- **R9.1.1**: Required fields must be validated before submission
- **R9.1.2**: Field format validation must occur on input
- **R9.1.3**: Validation errors must be displayed inline with specific messages

#### R9.2: Server-Side Validation
- **R9.2.1**: All client validations must be re-validated server-side
- **R9.2.2**: PySchematron rules must enforce LIFT specification compliance
- **R9.2.3**: Validation errors must include field paths and correction suggestions

### R10: Performance and Scalability Rules

#### R10.1: Bulk Operations
- **R10.1.1**: Validation must handle 1000+ entries within 5 seconds
- **R10.1.2**: Batch validation must report partial results for large datasets
- **R10.1.3**: Validation caching must be implemented for repeated checks

#### R10.2: Error Reporting
- **R10.2.1**: Validation errors must include line numbers and field paths
- **R10.2.2**: Error messages must be user-friendly and actionable
- **R10.2.3**: Validation progress must be reported for long-running operations

## Validation Rule Priorities

### Critical (Must Fix Before Save)
- R1.1.1, R1.1.2, R1.1.3: Entry essential fields
- R2.1.1, R2.1.2: Sense essential fields
- R4.1.1: Pronunciation language restriction
- R5.1.1, R5.1.2: Reference integrity

### Warning (Should Fix)
- R6.1.1, R6.1.2: POS consistency
- R3.1.1: Duplicate note types
- R4.2.1, R4.2.2: IPA sequence issues
- R7.1.3: Variant relationship loops

### Informational (Nice to Fix)
- R1.2.1: ID format recommendations
- R8.1.2: Missing hierarchical relationships
- R10.2.1: Missing field documentation

## Implementation Notes

1. **Test-Driven Development**: Each validation rule must have corresponding unit tests
2. **Progressive Enhancement**: Client-side validation enhances UX, server-side ensures data integrity
3. **Dynamic Loading**: All dropdown options and validation constraints load from LIFT ranges
4. **Internationalization**: Error messages must support multiple languages
5. **Performance**: Validation must not significantly impact form responsiveness

## Next Steps

1. Implement validation rule tests (Phase 1)
2. Create PySchematron schema files (Phase 1)
3. Build client-side validation service (Phase 2)
4. Integrate with form state management (Phase 2)
5. Add auto-save with validation feedback (Phase 3)
6. Implement conflict resolution UI (Phase 3)
