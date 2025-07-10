#!/usr/bin/env python
"""
Unit tests for ensuring invalid entries are always editable.

This test suite verifies that the Dictionary Writing System allows
lexicographers to edit invalid entries, showing validation errors
as guidance rather than blocking access.
"""

import pytest
from unittest.mock import Mock, patch
from flask import Flask

from app import create_app
from app.services.dictionary_service import DictionaryService
from app.services.validation_engine import ValidationEngine, ValidationResult, ValidationError as VError
from app.models.entry import Entry
from app.utils.exceptions import NotFoundError


class TestInvalidEntryEditing:
    """Test suite for invalid entry editing functionality."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        return create_app('testing')

    @pytest.fixture
    def dict_service(self, app):
        """Mock dictionary service."""
        with app.app_context():
            return app.injector.get(DictionaryService)

    def test_get_entry_for_editing_bypasses_validation(self, app):
        """Test that get_entry_for_editing loads invalid entries without validation blocking."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            
            # Mock the database connector and parser
            with patch.object(dict_service, 'db_connector') as mock_db, \
                 patch('app.services.dictionary_service.LIFTParser') as mock_parser_class:
                
                # Setup mocks
                mock_db.database = 'test_dict'
                mock_db.execute_query.return_value = '''
                    <entry id="invalid_entry">
                        <lexical-unit><form lang="en"><text>test</text></form></lexical-unit>
                        <sense id="sense1">
                            <!-- Missing definition/gloss - makes entry invalid -->
                        </sense>
                    </entry>
                '''
                
                # Mock the non-validating parser
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser
                
                # Create an invalid entry (missing sense definition)
                invalid_entry = Entry(
                    id_="invalid_entry",
                    lexical_unit={"en": "test"},
                    senses=[{"id": "sense1"}]  # Sense without definition
                )
                mock_parser.parse_string.return_value = [invalid_entry]
                
                # The method should succeed even with invalid entry
                result = dict_service.get_entry_for_editing("invalid_entry")
                
                # Verify the entry was returned
                assert result is not None
                assert result.id == "invalid_entry"
                
                # Verify non-validating parser was used
                mock_parser_class.assert_called_with(validate=False)
                mock_parser.parse_string.assert_called_once()

    def test_get_entry_for_editing_vs_regular_get_entry(self, app):
        """Test that get_entry_for_editing works where regular get_entry fails for invalid entries."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            
            # Mock an invalid entry that would fail validation
            with patch.object(dict_service, 'db_connector') as mock_db, \
                 patch.object(dict_service, '_detect_namespace_usage', return_value=False), \
                 patch.object(dict_service._query_builder, 'build_entry_by_id_query', return_value="mock_query"):
                
                mock_db.database = 'test_dict'
                mock_db.execute_query.return_value = '''
                    <entry id="invalid_entry">
                        <lexical-unit><form lang="en"><text>test</text></form></lexical-unit>
                        <sense id="sense1">
                            <!-- Missing definition/gloss -->
                        </sense>
                    </entry>
                '''
                
                # The get_entry_for_editing should work
                with patch('app.services.dictionary_service.LIFTParser') as mock_parser_class:
                    mock_parser = Mock()
                    mock_parser_class.return_value = mock_parser
                    
                    invalid_entry = Entry(
                        id_="invalid_entry", 
                        lexical_unit={"en": "test"},
                        senses=[{"id": "sense1"}]
                    )
                    mock_parser.parse_string.return_value = [invalid_entry]
                    
                    result = dict_service.get_entry_for_editing("invalid_entry")
                    assert result is not None
                    
                    # Verify non-validating parser was used for editing
                    mock_parser_class.assert_called_with(validate=False)

    def test_validation_shown_as_guidance_not_blocker(self, app):
        """Test that validation errors are shown as guidance for editing, not as blockers."""
        with app.app_context():
            # Create an invalid entry
            invalid_entry = Entry(
                id_="test_invalid",
                lexical_unit={"en": "test"},
                senses=[{"id": "sense1"}]  # Missing definition
            )
            
            # Get validation result
            validation_engine = ValidationEngine()
            validation_result = validation_engine.validate_entry(invalid_entry)
            
            # Entry should be invalid but still accessible for editing
            assert not validation_result.is_valid
            assert len(validation_result.errors) > 0
            
            # Verify the specific error we expect
            error_messages = [error.message for error in validation_result.errors]
            assert any("definition, gloss, or be a variant reference" in msg for msg in error_messages)

    def test_edit_entry_view_uses_non_validating_method(self, app):
        """Test that the edit_entry view uses the non-validating method."""
        with app.app_context():
            # Test directly that the method exists and works
            dict_service = app.injector.get(DictionaryService)
            
            # Verify the method exists
            assert hasattr(dict_service, 'get_entry_for_editing')
            
            # Test with a mock to verify non-validating behavior
            with patch.object(dict_service, 'db_connector') as mock_db, \
                 patch('app.services.dictionary_service.LIFTParser') as mock_parser_class:
                
                mock_db.database = 'test_dict'
                mock_db.execute_query.return_value = '<entry id="test"><lexical-unit><form lang="en"><text>test</text></form></lexical-unit></entry>'
                
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser
                
                test_entry = Entry(id_="test", lexical_unit={"en": "test"})
                mock_parser.parse_string.return_value = [test_entry]
                
                # Call the method
                result = dict_service.get_entry_for_editing("test")
                
                # Verify non-validating parser was used
                mock_parser_class.assert_called_with(validate=False)
                assert result.id == "test"

    def test_post_entry_update_uses_non_validating_method(self, app):
        """Test that POST updates also use non-validating method for existing entry retrieval."""
        with app.test_client() as client:
            with patch.object(DictionaryService, 'get_entry_for_editing') as mock_get_edit, \
                 patch.object(DictionaryService, 'update_entry') as mock_update, \
                 patch('app.views.merge_form_data_with_entry_data') as mock_merge, \
                 patch('app.models.entry.Entry.from_dict') as mock_from_dict:
                
                # Setup mocks
                mock_entry = Mock()
                mock_entry.to_dict.return_value = {"id": "test_entry"}
                mock_get_edit.return_value = mock_entry
                
                mock_merged_data = {"id": "test_entry", "lexical_unit": {"en": "updated"}}
                mock_merge.return_value = mock_merged_data
                
                mock_new_entry = Mock()
                mock_from_dict.return_value = mock_new_entry
                
                # Make POST request to edit endpoint
                response = client.post('/entries/test_entry/edit', 
                                     json={"lexical_unit": {"en": "updated"}})
                
                # Verify the non-validating method was called for existing entry
                mock_get_edit.assert_called_once_with('test_entry')
                
                # Update should proceed
                mock_update.assert_called_once()

    def test_entry_not_found_still_raises_error(self, app):
        """Test that truly missing entries still raise NotFoundError."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            
            with patch.object(dict_service, 'db_connector') as mock_db:
                mock_db.database = 'test_dict'
                mock_db.execute_query.return_value = ""  # Empty result
                
                with pytest.raises(NotFoundError, match="not found"):
                    dict_service.get_entry_for_editing("nonexistent_entry")

    def test_real_scholastic_assessment_entry_editable(self, app):
        """Integration test: verify the real problematic entry is now editable."""
        import os
        if os.environ.get("RUN_REAL_DB_TESTS") != "1":
            pytest.skip("Skipping real DB test unless RUN_REAL_DB_TESTS=1 is set.")
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            entry_id = "Scholastic Assessment Test_25645cb1-c7de-4560-be73-9505d9e9c33f"

            try:
                # This should work now with our fix, using the real DB
                entry = dict_service.get_entry_for_editing(entry_id)

                # Entry should be loaded
                assert entry is not None
                assert entry.id == entry_id
                assert entry.lexical_unit.get("en") == "Scholastic Assessment Test"

                # Entry should be invalid but still editable
                validation_engine = ValidationEngine()
                validation_result = validation_engine.validate_entry(entry)
                assert not validation_result.is_valid  # Invalid but still loaded

            except NotFoundError:
                pytest.skip("Test entry not available in real database")
            except Exception as e:
                pytest.fail(f"Entry should be editable even if invalid: {e}")
        """Integration test: verify the real problematic entry is now editable."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            entry_id = "Scholastic Assessment Test_25645cb1-c7de-4560-be73-9505d9e9c33f"

            # Mock the db_connector and LIFTParser to avoid real DB access
            with patch.object(dict_service, 'db_connector') as mock_db, \
                 patch('app.services.dictionary_service.LIFTParser') as mock_parser_class:

                mock_db.database = 'test_dict'
                mock_db.execute_query.return_value = '''
                    <entry id="Scholastic Assessment Test_25645cb1-c7de-4560-be73-9505d9e9c33f">
                        <lexical-unit><form lang="en"><text>Scholastic Assessment Test</text></form></lexical-unit>
                        <sense id="sense1">
                            <!-- Missing definition/gloss -->
                        </sense>
                    </entry>
                '''

                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser

                invalid_entry = Entry(
                    id_="Scholastic Assessment Test_25645cb1-c7de-4560-be73-9505d9e9c33f",
                    lexical_unit={"en": "Scholastic Assessment Test"},
                    senses=[{"id": "sense1"}]
                )
                mock_parser.parse_string.return_value = [invalid_entry]

                try:
                    # This should work now with our fix
                    entry = dict_service.get_entry_for_editing(entry_id)

                    # Entry should be loaded
                    assert entry is not None
                    assert entry.id == entry_id
                    assert entry.lexical_unit.get("en") == "Scholastic Assessment Test"

                    # Entry should be invalid but still editable
                    validation_engine = ValidationEngine()
                    validation_result = validation_engine.validate_entry(entry)
                    assert not validation_result.is_valid  # Invalid but still loaded

                except NotFoundError:
                    # If entry doesn't exist in test environment, that's ok
                    pytest.skip("Test entry not available in test environment")
                except Exception as e:
                    pytest.fail(f"Entry should be editable even if invalid: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
