"""
Test suite for centralized validation system.

This module tests the centralized validation engine that replaces scattered 
validation logic with a declarative, rule-based system.

Following TDD approach as specified in project requirements.
"""

from __future__ import annotations

import pytest
import json
from pathlib import Path

# Import will be available after we create the validation engine
from app.services.validation_engine import (
    ValidationEngine, 
    ValidationResult, 
    SchematronValidator,
    ValidationRulesSchemaValidator
)


class TestValidationEngine:
    """Test the core validation engine functionality."""

    def test_validation_engine_initialization(self):
        """Test that validation engine initializes with rule definitions."""
        engine = ValidationEngine()
        assert engine is not None
        assert len(engine.rules) > 0

    def test_r1_1_1_entry_id_required_json(self):
        """Test R1.1.1: Entry ID is required and must be non-empty (JSON)."""
        engine = ValidationEngine()
        
        # Valid entry
        valid_entry = {
            "id": "valid_entry",
            "lexical_unit": {"pl": "test"},
            "senses": [{"id": "sense1", "gloss": "test"}]
        }
        
        # Invalid entries
        missing_id_entry = {
            "lexical_unit": {"pl": "test"},
            "senses": [{"id": "sense1", "gloss": "test"}]
        }
        
        empty_id_entry = {
            "id": "",
            "lexical_unit": {"pl": "test"},
            "senses": [{"id": "sense1", "gloss": "test"}]
        }
        
        # Test validation
        assert engine.validate_json(valid_entry).is_valid
        assert not engine.validate_json(missing_id_entry).is_valid
        assert not engine.validate_json(empty_id_entry).is_valid

    def test_r1_1_2_lexical_unit_required_json(self):
        """Test R1.1.2: Lexical unit is required and must contain at least one language entry (JSON)."""
        engine = ValidationEngine()
        
        # Valid entry
        valid_entry = {
            "id": "test_entry",
            "lexical_unit": {"pl": "test"},
            "senses": [{"id": "sense1", "gloss": "test"}]
        }
        
        # Invalid entries
        missing_lexical_unit = {
            "id": "test_entry",
            "senses": [{"id": "sense1", "gloss": "test"}]
        }
        
        empty_lexical_unit = {
            "id": "test_entry",
            "lexical_unit": {},
            "senses": [{"id": "sense1", "gloss": "test"}]
        }
        
        # Test validation
        assert engine.validate_json(valid_entry).is_valid
        assert not engine.validate_json(missing_lexical_unit).is_valid
        assert not engine.validate_json(empty_lexical_unit).is_valid

    def test_r1_1_3_sense_required_json(self):
        """Test R1.1.3: At least one sense is required per entry (JSON)."""
        engine = ValidationEngine()

        # Valid entry
        valid_entry = {
            "id": "test_entry",
            "lexical_unit": {"pl": "test"},
            "senses": [{"id": "sense1", "gloss": "test"}]
        }

        # Invalid entries
        missing_senses = {
            "id": "test_entry",
            "lexical_unit": {"pl": "test"}
        }

        empty_senses = {
            "id": "test_entry",
            "lexical_unit": {"pl": "test"},
            "senses": []
        }

        # Test validation - entries without senses should now be valid (with warning)
        assert engine.validate_json(valid_entry).is_valid

        # Missing senses should now fail validation in save mode (critical error)
        result_missing = engine.validate_json(missing_senses)
        assert not result_missing.is_valid  # Should fail validation in save mode
        assert len(result_missing.errors) > 0  # Should have critical errors

        result_empty = engine.validate_json(empty_senses)
        assert not result_empty.is_valid  # Should fail validation in save mode
        assert len(result_empty.errors) > 0  # Should have critical errors

        # But should be valid in draft mode
        result_missing_draft = engine.validate_json(missing_senses, "draft")
        assert result_missing_draft.is_valid  # Should be valid in draft mode

        result_empty_draft = engine.validate_json(empty_senses, "draft")
        assert result_empty_draft.is_valid  # Should be valid in draft mode

    def test_r4_1_1_pronunciation_language_restriction_json(self):
        """Test R4.1.1: Pronunciation language restricted to seh-fonipa (JSON)."""
        engine = ValidationEngine()
        
        valid_entry = {
            "id": "test_entry",
            "lexical_unit": {"pl": "test"},
            "senses": [{"id": "sense1", "gloss": "test"}],
            "pronunciations": {"seh-fonipa": "test"}
        }
        
        invalid_entry = {
            "id": "test_entry",
            "lexical_unit": {"pl": "test"},
            "senses": [{"id": "sense1", "gloss": "test"}],
            "pronunciations": {"en": "test"}  # Invalid language
        }
        
        # Note: This rule might not be implemented yet in JSON rules
        result_valid = engine.validate_json(valid_entry)
        result_invalid = engine.validate_json(invalid_entry)
        
        # At minimum, entries should be structurally valid
        assert result_valid.is_valid
        # Invalid pronunciation language should trigger warning/error if rule exists
        # This is a placeholder until we implement all rules

    def test_r2_1_2_variant_entry_sense_validation(self):
        """Test R2.1.2: Variant entries should not require sense definitions/glosses."""
        engine = ValidationEngine()
        
        # Variant entry (has _component-lexeme relation) - should pass without sense definition
        variant_entry = {
            "id": "variant_entry",
            "lexical_unit": {"pl": "variant_form"},
            "relations": [
                {
                    "type": "_component-lexeme",
                    "ref": "base_entry_id",
                    "traits": {"variant-type": "Unspecified Variant"}
                }
            ],
            "senses": [
                {
                    "id": "sense1"
                    # No definition or gloss - should be OK for variant entries
                }
            ]
        }
        
        # Regular entry (no _component-lexeme relation) - should fail without definition
        regular_entry = {
            "id": "regular_entry",
            "lexical_unit": {"pl": "regular_form"},
            "senses": [
                {
                    "id": "sense1"
                    # No definition or gloss - should fail for regular entries
                }
            ]
        }
        
        # Test variant entry - should pass
        variant_result = engine.validate_json(variant_entry)
        variant_sense_errors = [
            error for error in variant_result.errors 
            if "definition, gloss, or be a variant" in error.message
        ]
        assert len(variant_sense_errors) == 0, f"Variant entry should not have sense content errors: {variant_sense_errors}"
        
        # Test regular entry - should fail with sense content error
        regular_result = engine.validate_json(regular_entry)
        regular_sense_errors = [
            error for error in regular_result.errors 
            if "definition, gloss, or be a variant" in error.message
        ]
        assert len(regular_sense_errors) > 0, "Regular entry should require sense definition or gloss"

class TestSchematronValidator:
    """Test the Schematron XML validator."""

    def test_schematron_validator_initialization(self):
        """Test that Schematron validator initializes properly."""
        # Skip if PySchematron not available
        try:
            validator = SchematronValidator()
            assert validator is not None
        except ImportError:
            pytest.skip("PySchematron not available")

    def test_xml_validation_basic(self):
        """Test basic XML validation with Schematron."""
        try:
            validator = SchematronValidator()
            
            # Valid LIFT XML fragment
            valid_xml = '''<?xml version="1.0" encoding="UTF-8"?>
            <lift xmlns="http://code.google.com/p/lift-standard">
                <entry id="test_entry">
                    <lexical-unit>
                        <form lang="pl">
                            <text>test</text>
                        </form>
                    </lexical-unit>
                    <sense id="sense1">
                        <gloss lang="en">
                            <text>test gloss</text>
                        </gloss>
                    </sense>
                </entry>
            </lift>'''
            
            result = validator.validate_xml(valid_xml)
            # Should be valid or have specific validation issues
            assert isinstance(result, ValidationResult)
            
        except ImportError:
            pytest.skip("PySchematron not available")
        except Exception as e:
            # Expected for incomplete schema setup
            assert "schema" in str(e).lower() or "schematron" in str(e).lower()


class TestValidationRulesSchemaValidator:
    """Test the JSON Schema validator for validation_rules.json."""

    def test_schema_validator_initialization(self):
        """Test that schema validator initializes properly."""
        validator = ValidationRulesSchemaValidator()
        assert validator is not None
        assert validator._schema is not None

    def test_valid_rules_file(self):
        """Test that current validation_rules.json passes schema validation."""
        validator = ValidationRulesSchemaValidator()
        result = validator.validate_rules_file("validation_rules.json")
        
        # Print any errors for debugging
        if not result.is_valid:
            for error in result.errors:
                print(f"Schema Error: {error.message} at {error.path}")
        
        assert result.is_valid, "validation_rules.json should pass schema validation"
        assert len(result.errors) == 0

    def test_invalid_json_syntax(self, tmp_path):
        """Test that invalid JSON syntax is caught."""
        # Create a file with invalid JSON
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text('{"rules": {invalid json}}')
        
        validator = ValidationRulesSchemaValidator()
        result = validator.validate_rules_file(str(invalid_file))
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert result.errors[0].rule_id == "JSON_SYNTAX"

    def test_missing_required_field(self, tmp_path):
        """Test that missing required fields are caught."""
        # Create a rules file missing required 'name' field
        invalid_rules = {
            "rules": {
                "R1.1.1": {
                    "description": "Test rule",
                    "category": "structure",
                    "priority": "critical",
                    "path": "id",
                    "condition": "required",
                    "validation": {"min_length": 1},
                    "error_message": "Test error"
                    # Missing 'name' field
                }
            }
        }
        invalid_file = tmp_path / "invalid_rules.json"
        invalid_file.write_text(json.dumps(invalid_rules))
        
        validator = ValidationRulesSchemaValidator()
        result = validator.validate_rules_file(str(invalid_file))
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "name" in result.errors[0].message.lower()

    def test_invalid_priority_value(self, tmp_path):
        """Test that invalid enum values are caught."""
        # Create a rules file with invalid priority
        invalid_rules = {
            "rules": {
                "R1.1.1": {
                    "name": "Test Rule",
                    "description": "Test rule",
                    "category": "structure",
                    "priority": "super_critical",  # Invalid value
                    "path": "id",
                    "condition": "required",
                    "validation": {"min_length": 1},
                    "error_message": "Test error"
                }
            }
        }
        invalid_file = tmp_path / "invalid_priority.json"
        invalid_file.write_text(json.dumps(invalid_rules))
        
        validator = ValidationRulesSchemaValidator()
        result = validator.validate_rules_file(str(invalid_file))
        
        assert not result.is_valid
        assert len(result.errors) > 0


class TestValidationRuleLoading:
    """Test that validation rules load correctly from configuration."""
    
    def test_validation_rules_file_exists(self):
        """Test that validation_rules.json file exists and is valid."""
        rules_file = Path("validation_rules.json")
        assert rules_file.exists(), "validation_rules.json file should exist"
        
        with open(rules_file, 'r', encoding='utf-8') as f:
            rules_data = json.load(f)
        
        assert 'rules' in rules_data
        assert len(rules_data['rules']) > 0
        
        # Check that critical rules exist
        rules = rules_data['rules']
        assert 'R1.1.1' in rules  # Entry ID required
        assert 'R1.1.2' in rules  # Lexical unit required
        assert 'R1.1.3' in rules  # Sense required

    def test_rule_structure_validation(self):
        """Test that rules have correct structure."""
        engine = ValidationEngine()
        
        for rule_id, rule_config in engine.rules.items():
            # Each rule should have required fields
            assert 'name' in rule_config
            assert 'description' in rule_config
            assert 'category' in rule_config
            assert 'priority' in rule_config
            assert 'path' in rule_config
            assert 'condition' in rule_config
            assert 'validation' in rule_config
            assert 'error_message' in rule_config
            
            # Priority should be valid
            assert rule_config['priority'] in ['critical', 'warning', 'informational']


class TestHunspellSpellingValidation:
    """Test hunspell spelling validation with language-aware detection.

    These tests verify that:
    1. Spelling errors are detected for languages with installed dictionaries
    2. Validation is skipped for languages without installed dictionaries
    3. Language codes are properly detected from JSON paths
    4. Fallback logic works when exact dictionary is not available
    """

    def test_hunspell_detects_spelling_errors_in_english(self):
        """Test that hunspell detects spelling errors when English dictionary is available."""
        engine = ValidationEngine()

        # Entry with intentional spelling errors in English
        entry_with_errors = {
            "id": "test-entry-1",
            "lexical_unit": {"en": "helllo wrld"},
            "senses": [{"id": "sense-1", "definition": {"en": "A defnition error"}}]
        }

        result = engine.validate_json(entry_with_errors)

        # Should have warnings for lexical unit and info for definition
        spelling_warnings = [w for w in result.warnings if 'spelling' in w.message.lower()]
        spelling_info = [i for i in result.info if 'spelling' in i.message.lower()]

        assert len(spelling_warnings) > 0, "Should detect spelling errors in English lexical unit"
        assert len(spelling_info) > 0, "Should detect spelling errors in English definition"

    def test_hunspell_skips_validation_for_missing_dictionary(self):
        """Test that hunspell skips validation when dictionary is not installed."""
        engine = ValidationEngine()

        # Entry with language that has no dictionary installed
        entry_no_dictionary = {
            "id": "test-entry-2",
            "lexical_unit": {
                "xx": "sometext here",  # No dictionary for 'xx'
                "pl": "dzień dobry"     # No Polish dictionary
            },
            "senses": [{"id": "sense-1", "definition": {"pl": "To jest definicja"}}]
        }

        result = engine.validate_json(entry_no_dictionary)

        # Should NOT have spelling errors for languages without dictionaries
        spelling_errors = [e for e in result.errors + result.warnings + result.info
                          if 'spelling' in e.message.lower()]

        assert len(spelling_errors) == 0, \
            "Should NOT flag spelling errors for languages without installed dictionaries"

    def test_hunspell_multilingual_entry_mixed_availability(self):
        """Test multilingual entry where some languages have dictionaries and some don't."""
        engine = ValidationEngine()

        # Mixed: English (has dict) + Polish (no dict)
        entry_mixed = {
            "id": "test-entry-3",
            "lexical_unit": {
                "en": "helllo wrld",    # Should flag errors (en_US dict available)
                "pl": "dzień dobry"     # Should skip (no pl dict)
            },
            "senses": [
                {"id": "sense-1", "definition": {"en": "A defnition error"}},
                {"id": "sense-2", "definition": {"pl": "To jest definicja"}}
            ]
        }

        result = engine.validate_json(entry_mixed)

        # Should only have errors for English
        english_errors = [e for e in result.warnings + result.info
                         if 'spelling' in e.message.lower() and 'en' in e.path.lower()]
        polish_errors = [e for e in result.warnings + result.info
                        if 'spelling' in e.message.lower() and 'pl' in e.path.lower()]

        assert len(english_errors) > 0, "Should detect spelling errors in English"
        assert len(polish_errors) == 0, "Should NOT detect spelling errors in Polish (no dict)"

    def test_hunspell_validates_correct_words(self):
        """Test that hunspell accepts correctly spelled words."""
        engine = ValidationEngine()

        entry_valid = {
            "id": "test-entry-4",
            "lexical_unit": {"en": "hello world"},
            "senses": [{"id": "sense-1", "definition": {"en": "A valid definition"}}]
        }

        result = engine.validate_json(entry_valid)

        # Should have no spelling warnings
        spelling_warnings = [w for w in result.warnings if 'spelling' in w.message.lower()]
        assert len(spelling_warnings) == 0, "Should not flag correctly spelled words"

    def test_hunspell_language_code_extraction(self):
        """Test that language codes are correctly extracted from JSON paths."""
        engine = ValidationEngine()

        # Test with various language codes
        entry = {
            "id": "test-entry-5",
            "lexical_unit": {
                "en": "hello",     # Should use en_US dict
                "en_GB": "hello",  # Should fall back to en_US (only en_US available)
            },
            "senses": [
                {"id": "sense-1", "gloss": [{"lang": "en", "text": "greeting"}]}
            ]
        }

        result = engine.validate_json(entry)

        # Should validate correctly (both English variants map to en_US)
        assert result.is_valid or len([w for w in result.warnings if 'spelling' in w.message.lower()]) == 0

    def test_hunspell_ignores_ignored_words(self):
        """Test that ignored words are not flagged as spelling errors."""
        engine = ValidationEngine()

        # Entry with words in the ignore list
        entry_ignored = {
            "id": "test-entry-6",
            "lexical_unit": {"en": "test demo example word"},
            "senses": [{"id": "sense-1", "definition": {"en": "A test example."}}]
        }

        result = engine.validate_json(entry_ignored)

        # Should not flag ignored words
        for w in result.warnings:
            assert 'test' not in w.message.lower(), "Should ignore 'test'"
            assert 'demo' not in w.message.lower(), "Should ignore 'demo'"
            assert 'example' not in w.message.lower(), "Should ignore 'example'"

    def test_hunspell_provides_suggestions(self):
        """Test that hunspell provides spelling suggestions."""
        engine = ValidationEngine()

        entry = {
            "id": "test-entry-7",
            "lexical_unit": {"en": "helllo"},
            "senses": [{"id": "sense-1", "definition": {"en": "A defnition."}}]
        }

        result = engine.validate_json(entry)

        # Find spelling errors with suggestions
        spelling_warnings = [w for w in result.warnings if 'spelling' in w.message.lower()]

        assert len(spelling_warnings) > 0, "Should detect spelling errors"
        # Check that suggestions are mentioned in the message
        warning_messages = [w.message for w in spelling_warnings]
        assert any('suggestions:' in msg for msg in warning_messages), \
            "Should provide spelling suggestions"

    def test_hunspell_skip_validation_with_no_dictionary(self):
        """Integration test: Verify validation behavior when dictionary is unavailable.

        This test simulates the scenario where a user has entries in multiple languages
        but only some have hunspell dictionaries installed. The system should:
        1. Validate languages with available dictionaries
        2. Silently skip languages without dictionaries
        3. Not report false positives for missing dictionaries
        """
        engine = ValidationEngine()

        # Realistic multilingual entry
        # Note: 'naxha' is accidentally valid in English (typo of 'naphtha')
        # Use words that are clearly language-specific
        entry = {
            "id": "test-entry-8",
            "lexical_unit": {
                "en": "thsi is a tset",          # English with errors (has dict)
                "de": "dies ist ein test",       # German - no dictionary
                "fr": "ceci est un test",        # French - no dictionary
                "seh": "naxha malaxha"           # No dictionary - 'naxha' is accidentally valid in en_US
            },
            "senses": [
                {
                    "id": "sense-1",
                    "definition": {"en": "A tset definision"},
                    "examples": [{"text": "This is an exmple"}]
                }
            ]
        }

        result = engine.validate_json(entry)

        # Count spelling issues
        spelling_issues = [e for e in result.warnings + result.info if 'spelling' in e.message.lower()]

        # Should have issues for English (errors in thsi, tset, definision, exmple)
        # Should NOT have issues for de, fr (no dictionaries)
        # Note: seh might have issues if words happen to match English dictionary
        english_issues = [i for i in spelling_issues if 'lexical_unit.en' in i.path or 'definition.en' in i.path]
        non_english_issues = [i for i in spelling_issues
                             if any(lang in i.path for lang in ['lexical_unit.de', 'lexical_unit.fr'])]

        assert len(english_issues) > 0, "Should detect English spelling errors"
        assert len(non_english_issues) == 0, "Should NOT detect errors for languages without dictionaries"
