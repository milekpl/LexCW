#!/usr/bin/env python3
"""
Fixed validation rules tests - addressing the core issues:
1. Proper validation modes (save vs delete vs draft)
2. Correct test data format
3. Proper test expectations
"""

import pytest
from app.models.entry import Entry
from app.models.sense import Sense
from app.services.validation_engine import ValidationEngine
from app.utils.exceptions import ValidationError


class TestValidationModes:
    """Test validation modes and their behavior."""
    
    def test_save_entry_without_senses_in_draft_mode(self):
        """Test that entries can be saved without senses in draft mode."""
        # Create an entry without senses
        entry = Entry(
            id_="test_entry",
            lexical_unit={"pl": "test"},
            senses=[]
        )
        
        # Should fail in save mode
        with pytest.raises(ValidationError):
            entry.validate("save")
        
        # Should pass in draft mode
        assert entry.validate("draft") is True
    
    def test_delete_entry_bypasses_validation(self):
        """Test that deletion doesn't require validation."""
        # Create an invalid entry
        entry = Entry(
            id_="test_entry",
            lexical_unit={"pl": "test"},
            senses=[]
        )
        
        # Validation should not be called during deletion
        # This simulates the deletion workflow
        assert entry.validate("delete") is True
    
    def test_progressive_validation_workflow(self):
        """Test the progressive validation workflow."""
        # Step 1: Create entry without senses (draft mode)
        entry = Entry(
            id_="test_entry",
            lexical_unit={"pl": "test"},
            senses=[]
        )
        assert entry.validate("draft") is True
        
        # Step 2: Add a sense with proper structure
        sense = Sense(
            id_="sense1",
            gloss={"pl": {"text": "test gloss"}}
        )
        entry.add_sense(sense)
        
        # Step 3: Now should pass full validation
        assert entry.validate("save") is True


class TestEntryValidationRulesFixed:
    """Fixed entry validation rules tests."""
    
    def test_r1_1_1_entry_id_required(self):
        """Test R1.1.1: Entry ID is required."""
        with pytest.raises(ValidationError) as exc_info:
            entry = Entry(id_=None, lexical_unit={"pl": "test"}, senses=[Sense(id_="sense1", gloss={"pl": {"text": "test"}})])
            entry.validate("save")
        assert "Entry ID is required" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            entry = Entry(id_="", lexical_unit={"pl": "test"}, senses=[Sense(id_="sense1", gloss={"pl": {"text": "test"}})])
            entry.validate("save")
        assert "Entry ID is required" in str(exc_info.value)

    def test_r1_1_2_lexical_unit_required(self):
        """Test R1.1.2: Lexical unit is required."""
        with pytest.raises(ValidationError) as exc_info:
            entry = Entry(
                id_="test_entry", 
                lexical_unit={}, 
                senses=[Sense(id_="sense1", gloss={"pl": {"text": "test"}})]
            )
            entry.validate("save")
        assert "Lexical unit is required" in str(exc_info.value)

    def test_r1_1_3_at_least_one_sense_required_save_mode(self):
        """Test R1.1.3: At least one sense is required in save mode."""
        with pytest.raises(ValidationError) as exc_info:
            entry = Entry(id_="test_entry", lexical_unit={"pl": "test"}, senses=[])
            entry.validate("save")
        assert "At least one sense is required" in str(exc_info.value)

    def test_r1_1_3_sense_not_required_draft_mode(self):
        """Test R1.1.3: Senses not required in draft mode."""
        entry = Entry(id_="test_entry", lexical_unit={"pl": "test"}, senses=[])
        assert entry.validate("draft") is True

    def test_r1_2_1_entry_id_format_validation(self):
        """Test R1.2.1: Entry ID must be a valid string matching pattern."""
        # Test valid IDs
        valid_ids = ["test_entry", "entry-123", "ENTRY_1", "entry123"]
        for valid_id in valid_ids:
            entry = Entry(
                id_=valid_id,
                lexical_unit={"pl": "test"},
                senses=[Sense(id_="sense1", gloss={"pl": {"text": "test"}})],
            )
            assert entry.validate("save") is True

        # Test invalid IDs
        invalid_ids = ["test entry", "entry@123", "entry#1", "entry.1", "entry/1"]
        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                entry = Entry(
                    id_=invalid_id,
                    lexical_unit={"pl": "test"},
                    senses=[Sense(id_="sense1", gloss={"pl": {"text": "test"}})],
                )
                entry.validate("save")
            assert "Invalid entry ID format" in str(exc_info.value)

    def test_r1_2_2_lexical_unit_format_validation(self):
        """Test R1.2.2: Lexical unit must be a valid object."""
        # Test valid lexical units
        valid_units = [{"pl": "test"}, {"en": "test", "pl": "test"}]
        for valid_unit in valid_units:
            entry = Entry(
                id_="test_entry",
                lexical_unit=valid_unit,
                senses=[Sense(id_="sense1", gloss={"pl": {"text": "test"}})],
            )
            assert entry.validate("save") is True

        # Test invalid lexical units
        with pytest.raises(ValidationError) as exc_info:
            entry = Entry(
                id_="test_entry",
                lexical_unit={"pl": ""},  # Empty value
                senses=[Sense(id_="sense1", gloss={"pl": {"text": "test"}})],
            )
            entry.validate("save")
        assert "lexical unit" in str(exc_info.value).lower() or "cannot be empty" in str(exc_info.value).lower()


class TestSenseValidationRulesFixed:
    """Fixed sense validation rules tests."""
    
    def test_r2_1_1_sense_id_required(self):
        """Test R2.1.1: Sense ID is required."""
        with pytest.raises(ValidationError) as exc_info:
            entry = Entry(
                id_="test_entry",
                lexical_unit={"pl": "test"},
                senses=[Sense(id_=None, gloss={"pl": {"text": "test"}})]
            )
            entry.validate("save")
        assert "Sense ID is required" in str(exc_info.value)

    def test_r2_1_2_sense_definition_or_gloss_required(self):
        """Test R2.1.2: Sense definition OR gloss is required."""
        # Test with gloss only
        entry = Entry(
            id_="test_entry",
            lexical_unit={"pl": "test"},
            senses=[Sense(id_="sense1", gloss={"pl": {"text": "test gloss"}})]
        )
        assert entry.validate("save") is True

        # Test with definition only
        entry = Entry(
            id_="test_entry",
            lexical_unit={"pl": "test"},
            senses=[Sense(id_="sense1", definition={"pl": {"text": "test definition"}})]
        )
        assert entry.validate("save") is True

        # Test with neither
        with pytest.raises(ValidationError) as exc_info:
            entry = Entry(
                id_="test_entry",
                lexical_unit={"pl": "test"},
                senses=[Sense(id_="sense1")]
            )
            entry.validate("save")
        assert "definition" in str(exc_info.value).lower() or "gloss" in str(exc_info.value).lower()

    def test_r2_2_1_definition_content_validation(self):
        """Test R2.2.1: Definition content must be non-empty."""
        # Test valid definition
        entry = Entry(
            id_="test_entry",
            lexical_unit={"pl": "test"},
            senses=[Sense(id_="sense1", definition={"pl": {"text": "valid definition"}})]
        )
        assert entry.validate("save") is True

        # Test empty definition
        with pytest.raises(ValidationError) as exc_info:
            entry = Entry(
                id_="test_entry",
                lexical_unit={"pl": "test"},
                senses=[Sense(id_="sense1", definition={"pl": {"text": ""}})]
            )
            entry.validate("save")
        assert "definition" in str(exc_info.value).lower()

    def test_r2_2_2_gloss_content_validation(self):
        """Test R2.2.2: Gloss content must be non-empty."""
        # Test valid gloss
        entry = Entry(
            id_="test_entry",
            lexical_unit={"pl": "test"},
            senses=[Sense(id_="sense1", gloss={"pl": {"text": "valid gloss"}})]
        )
        assert entry.validate("save") is True

        # Test empty gloss
        with pytest.raises(ValidationError) as exc_info:
            entry = Entry(
                id_="test_entry",
                lexical_unit={"pl": "test"},
                senses=[Sense(id_="sense1", gloss={"pl": {"text": ""}})]
            )
            entry.validate("save")
        assert "gloss" in str(exc_info.value).lower()


class TestValidationEngineDirectly:
    """Test the validation engine directly to ensure it works properly."""
    
    def test_validation_engine_with_proper_data(self):
        """Test the validation engine with properly formatted data."""
        engine = ValidationEngine()
        
        # Test with valid data
        valid_data = {
            "id": "test_entry",
            "lexical_unit": {"pl": "test"},
            "senses": [
                {
                    "id": "sense1",
                    "gloss": {"pl": {"text": "test gloss"}}
                }
            ]
        }
        result = engine.validate_json(valid_data, "save")
        assert result.is_valid is True
        
        # Test with invalid ID
        invalid_data = {
            "id": "test entry",  # Invalid (contains space)
            "lexical_unit": {"pl": "test"},
            "senses": [
                {
                    "id": "sense1",
                    "gloss": {"pl": {"text": "test gloss"}}
                }
            ]
        }
        result = engine.validate_json(invalid_data, "save")
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("Invalid entry ID format" in error.message for error in result.errors)

    def test_validation_modes_in_engine(self):
        """Test validation modes in the engine."""
        engine = ValidationEngine()
        
        # Data without senses
        data_no_senses = {
            "id": "test_entry",
            "lexical_unit": {"pl": "test"},
            "senses": []
        }
        
        # Should fail in save mode
        result = engine.validate_json(data_no_senses, "save")
        assert result.is_valid is False
        assert any("At least one sense is required" in error.message for error in result.errors)
        
        # Should pass in draft mode
        result = engine.validate_json(data_no_senses, "draft")
        assert result.is_valid is True
        
        # Should pass in delete mode
        result = engine.validate_json(data_no_senses, "delete")
        assert result.is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])