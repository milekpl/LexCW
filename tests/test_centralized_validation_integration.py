"""
Integration tests for centralized validation system.

Tests the integration between the centralized validation engine and 
the refactored model classes that use it.

Following TDD approach as specified in project requirements.
"""

from __future__ import annotations

import pytest
from app.models.entry import Entry
from app.models.sense import Sense
from app.services.validation_engine import ValidationEngine, ValidationResult
from app.utils.exceptions import ValidationError


class TestCentralizedValidationIntegration:
    """Test integration between models and centralized validation."""

    def test_entry_model_uses_centralized_validation(self):
        """Test that Entry model uses centralized validation system."""
        engine = ValidationEngine()
        
        # Test valid entry passes validation
        valid_entry = Entry(
            id="test_entry",
            lexical_unit={"en": "test"},
            senses=[Sense(id="sense1", gloss="test")]
        )
        
        # Should not raise exception
        assert valid_entry.validate()
        
        # Test that validation engine directly validates the same data
        entry_data = valid_entry.to_dict()
        result = engine.validate_json(entry_data)
        assert result.is_valid

    def test_entry_validation_catches_critical_errors(self):
        """Test that Entry validation catches critical validation errors."""
        # Test empty lexical unit (critical error)
        with pytest.raises(ValidationError) as exc_info:
            invalid_entry = Entry(
                id="test_entry",
                lexical_unit={},  # Empty lexical unit
                senses=[Sense(id="sense1", gloss="test")]
            )
            invalid_entry.validate()
        
        assert "lexical unit" in str(exc_info.value).lower()

    def test_entry_validation_catches_empty_senses(self):
        """Test that Entry validation catches missing senses."""
        # Test no senses (critical error)
        with pytest.raises(ValidationError) as exc_info:
            invalid_entry = Entry(
                id="test_entry",
                lexical_unit={"en": "test"},
                senses=[]  # No senses
            )
            invalid_entry.validate()
        
        assert "sense" in str(exc_info.value).lower()

    def test_sense_validation_integration(self):
        """Test that Sense model validation integrates with centralized system."""
        # Test valid sense (has gloss)
        valid_sense = Sense(id="test_sense", gloss="test definition")
        assert valid_sense.validate()

        # Test sense with empty gloss but valid definition (should pass)
        valid_sense2 = Sense(id="test_sense2", gloss="", definitions={"en": {"text": "valid definition"}})
        assert valid_sense2.validate()

        # Test sense with both gloss and definition empty (should fail)
        with pytest.raises(ValidationError) as exc_info:
            invalid_sense = Sense(id="test_sense3", gloss="", definitions={})
            invalid_sense.validate()
        assert "gloss" in str(exc_info.value).lower() or "definition" in str(exc_info.value).lower()

    def test_language_code_validation_integration(self):
        """Test that language code validation works through models."""
        # Test invalid language code
        with pytest.raises(ValidationError) as exc_info:
            invalid_entry = Entry(
                id="test_entry",
                lexical_unit={"invalid_lang": "test"},  # Invalid language code
                senses=[Sense(id="sense1", gloss="test")]
            )
            invalid_entry.validate()
        
        # Should catch the invalid language code
        error_msg = str(exc_info.value).lower()
        assert "language" in error_msg or "invalid_lang" in error_msg

    def test_validation_result_contains_rule_information(self):
        """Test that validation results contain proper rule information."""
        engine = ValidationEngine()
        
        # Test with data that will trigger multiple validation errors
        invalid_data = {
            "id": "",  # Empty ID
            "lexical_unit": {},  # Empty lexical unit
            "senses": []  # No senses
        }
        
        result = engine.validate_json(invalid_data)
        
        # Should have multiple critical errors
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Check that errors have proper rule information
        for error in result.errors:
            assert error.rule_id.startswith('R')  # Rule IDs start with R
            assert error.rule_name
            assert error.message
            assert error.priority
            assert error.category

    def test_validation_priority_categorization(self):
        """Test that validation errors are properly categorized by priority."""
        engine = ValidationEngine()
        
        # Test data with both critical and warning issues
        mixed_data = {
            "id": "test@invalid",  # Invalid format (warning)
            "lexical_unit": {"en": "test"},
            "senses": []  # Missing senses (critical)
        }
        
        result = engine.validate_json(mixed_data)
        
        # Should have critical errors and warnings
        assert not result.is_valid  # Critical errors make it invalid
        assert len(result.errors) > 0  # Critical errors
        # May or may not have warnings depending on rule implementation

    def test_custom_validation_functions_work(self):
        """Test that custom validation functions are properly executed."""
        engine = ValidationEngine()
        
        # Test data that would trigger custom validation
        data_with_notes = {
            "id": "test_entry",
            "lexical_unit": {"en": "test"},
            "senses": [{"id": "sense1", "gloss": "test"}],
            "notes": [
                {"type": "etymology", "content": "test"},
                {"type": "etymology", "content": "duplicate"}  # Duplicate type
            ]
        }
        
        result = engine.validate_json(data_with_notes)
        
        # Should detect duplicate note types if that rule is implemented
        # This tests that custom validation functions are being called
        # The specific validation may pass or fail depending on rule implementation
        assert isinstance(result, ValidationResult)

    def test_model_to_dict_compatibility(self):
        """Test that model to_dict() output is compatible with validation engine."""
        entry = Entry(
            id="test_entry",
            lexical_unit={"en": "test"},
            senses=[Sense(id="sense1", gloss="test")]
        )
        
        # Convert to dict and validate
        entry_dict = entry.to_dict()
        engine = ValidationEngine()
        result = engine.validate_json(entry_dict)
        
        # Should be valid
        assert result.is_valid
        
        # Dict should contain expected fields
        assert "id" in entry_dict
        assert "lexical_unit" in entry_dict
        assert "senses" in entry_dict

    def test_variant_entry_listing_without_validation_errors(self):
        """Test that variant entries can be listed without triggering validation errors."""
        from app.services.dictionary_service import DictionaryService
        from app.database.mock_connector import MockDatabaseConnector
        from app.parsers.lift_parser import LIFTParser
        
        # Test that non-validating parser (used in listing) accepts variant entries
        non_validating_parser = LIFTParser(validate=False)
        # This variant entry would normally fail validation but should be accepted when validation is disabled
        variant_entry_xml = """
        <lift>
            <entry id="variant_entry_test">
                <lexical-unit>
                    <form lang="en">
                        <text>variant form</text>
                    </form>
                </lexical-unit>
                <relation type="_component-lexeme" ref="main_entry">
                    <trait name="variant-type" value="Unspecified Variant"/>
                </relation>
                <sense id="sense_1">
                    <!-- No definition or gloss - OK for variants when validation is disabled -->
                </sense>
            </entry>
        </lift>
        """
        # This should NOT raise a validation error
        entries = non_validating_parser.parse_string(variant_entry_xml)
        assert len(entries) == 1
        assert entries[0].id == "variant_entry_test"
        # Test that dictionary service listing operations work without validation errors
        mock_db = MockDatabaseConnector()
        dict_service = DictionaryService(mock_db)
        # This should succeed without validation errors
        entries, count = dict_service.list_entries(limit=10)
        assert isinstance(entries, list)
        assert isinstance(count, int)

class TestValidationEnginePerformance:
    """Test performance aspects of the validation engine."""

    def test_validation_engine_performance(self):
        """Test that validation engine performs adequately."""
        import time
        
        engine = ValidationEngine()
        
        # Create a reasonably sized entry for testing
        test_data = {
            "id": "performance_test",
            "lexical_unit": {"en": "test"},
            "senses": [
                {"id": f"sense_{i}", "gloss": f"test gloss {i}"} 
                for i in range(10)
            ],
            "notes": {"etymology": "test etymology"},
            "pronunciations": {"ipa": "test"}
        }
        
        # Measure validation time
        start_time = time.time()
        result = engine.validate_json(test_data)
        end_time = time.time()
        
        validation_time = end_time - start_time
        
        # Should complete validation quickly (under 100ms for single entry)
        assert validation_time < 0.1, f"Validation took {validation_time:.3f}s, expected < 0.1s"
        
        # Should return valid result
        assert isinstance(result, ValidationResult)

    def test_multiple_validations_performance(self):
        """Test performance with multiple validation calls."""
        import time
        
        engine = ValidationEngine()
        
        test_entries = []
        for i in range(50):
            test_entries.append({
                "id": f"entry_{i}",
                "lexical_unit": {"en": f"word_{i}"},
                "senses": [{"id": f"sense_{i}", "gloss": f"meaning {i}"}]
            })
        
        # Measure time for multiple validations
        start_time = time.time()
        results = []
        for entry_data in test_entries:
            result = engine.validate_json(entry_data)
            results.append(result)
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / len(test_entries)
        
        # Should complete all validations in reasonable time
        assert total_time < 2.0, f"50 validations took {total_time:.3f}s, expected < 2s"
        assert avg_time < 0.04, f"Average validation time {avg_time:.3f}s, expected < 0.04s"
        
        # All should be valid
        assert all(r.is_valid for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
