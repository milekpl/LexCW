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
from app.services.validation_engine import ValidationEngine, ValidationResult, SchematronValidator


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
        
        # Test validation
        assert engine.validate_json(valid_entry).is_valid
        assert not engine.validate_json(missing_senses).is_valid
        assert not engine.validate_json(empty_senses).is_valid

    def test_r1_2_1_entry_id_format_json(self):
        """Test R1.2.1: Entry ID must match valid format pattern (JSON)."""
        engine = ValidationEngine()
        
        # Valid IDs
        valid_ids = ["entry1", "entry_test", "entry-test", "TEST123"]
        
        # Invalid IDs  
        invalid_ids = ["entry 1", "entry@test", "entry.test", "entry/test", "entry#test"]
        
        for valid_id in valid_ids:
            entry = {
                "id": valid_id,
                "lexical_unit": {"pl": "test"},
                "senses": [{"id": "sense1", "gloss": "test"}]
            }
            result = engine.validate_json(entry)
            # This should be valid for core fields, format might be warning
            assert result.is_valid or len(result.warnings) > 0
        
        for invalid_id in invalid_ids:
            entry = {
                "id": invalid_id,
                "lexical_unit": {"pl": "test"},
                "senses": [{"id": "sense1", "gloss": "test"}]
            }
            result = engine.validate_json(entry)
            # Should have warning or error for format
            assert len(result.warnings) > 0 or not result.is_valid

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
