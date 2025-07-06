"""
Test that invalid entries are always editable and viewable.

This is a critical requirement: lexicographers must be able to edit
entries with validation errors to fix them. Validation should guide,
not block editing.
"""

import pytest
from unittest.mock import Mock, patch
from app import create_app
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.models.sense import Sense


class TestInvalidEntryEditability:
    """Test that invalid entries can always be edited and viewed."""

    @pytest.fixture
    def app(self):
        """Create test app."""
        return create_app('testing')

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_get_entry_for_editing_bypasses_validation(self, app):
        """Test that get_entry_for_editing bypasses validation."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            
            # Mock the database response with invalid entry XML
            invalid_entry_xml = '''
            <entry id="invalid_entry" dateCreated="2023-01-01T00:00:00Z">
                <lexical-unit>
                    <form lang="en"><text>Invalid Entry</text></form>
                </lexical-unit>
                <sense id="invalid_sense">
                    <!-- This sense has no definition or gloss - it's invalid -->
                </sense>
            </entry>
            '''
            
            with patch.object(dict_service.db_connector, 'execute_query') as mock_query:
                mock_query.return_value = invalid_entry_xml
                
                # This should NOT raise ValidationError
                entry = dict_service.get_entry_for_editing("invalid_entry")
                
                # Verify entry was parsed
                assert entry is not None
                assert entry.id == "invalid_entry"
                assert entry.lexical_unit == {"en": "Invalid Entry"}
                assert len(entry.senses) == 1

    def test_view_entry_route_uses_non_validating_method(self, app, client):
        """Test that the view entry route uses get_entry_for_editing method."""
        with app.app_context():
            with patch.object(DictionaryService, 'get_entry_for_editing') as mock_get:
                # Configure mock to raise NotFoundError to avoid template rendering issues
                from app.utils.exceptions import NotFoundError
                mock_get.side_effect = NotFoundError("Entry not found")
                
                response = client.get('/entries/invalid_test')
                
                # Should call get_entry_for_editing (not get_entry)
                mock_get.assert_called_once_with("invalid_test")
                # Should redirect to entries list due to NotFoundError
                assert response.status_code == 302

    def test_edit_entry_route_uses_non_validating_method(self, app, client):
        """Test that the edit entry route uses get_entry_for_editing method."""
        with app.app_context():
            with patch.object(DictionaryService, 'get_entry_for_editing') as mock_get:
                # Configure mock to raise NotFoundError to avoid template rendering issues
                from app.utils.exceptions import NotFoundError
                mock_get.side_effect = NotFoundError("Entry not found")
                
                response = client.get('/entries/invalid_test/edit')
                
                # Should call get_entry_for_editing (not get_entry)
                mock_get.assert_called_with("invalid_test")
                # Should redirect to entries list due to NotFoundError
                assert response.status_code == 302

    def test_search_includes_invalid_entries(self, app):
        """Test that search results include invalid entries."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            
            # The search_entries method should already use non-validating parser
            # This is a regression test to ensure this behavior is maintained
            
            # Mock database response with both valid and invalid entries
            search_result_xml = '''
            <entry id="valid_entry">
                <lexical-unit>
                    <form lang="en"><text>Valid Entry</text></form>
                </lexical-unit>
                <sense id="valid_sense">
                    <definition>
                        <form lang="en"><text>A valid definition</text></form>
                    </definition>
                </sense>
            </entry>
            <entry id="invalid_entry">
                <lexical-unit>
                    <form lang="en"><text>Invalid Entry</text></form>
                </lexical-unit>
                <sense id="invalid_sense">
                    <!-- No definition or gloss - invalid -->
                </sense>
            </entry>
            '''
            
            with patch.object(dict_service.db_connector, 'execute_query') as mock_query:
                # First call returns count, second returns entries
                mock_query.side_effect = ["2", search_result_xml]
                
                entries, total = dict_service.search_entries("entry")
                
                # Both entries should be returned, including the invalid one
                assert total == 2
                assert len(entries) == 2
                
                entry_ids = [entry.id for entry in entries]
                assert "valid_entry" in entry_ids
                assert "invalid_entry" in entry_ids

    def test_validation_errors_shown_as_guidance_not_blockers(self, app):
        """Test that validation errors are shown as guidance, not blockers."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            
            # Create an entry that would fail validation
            invalid_entry = Entry(
                id_="test_invalid",
                lexical_unit={"en": "Test"},
                senses=[Sense(
                    id_="sense1",
                    # No definition or gloss - invalid!
                )]
            )
            
            # Mock database to return this entry
            with patch.object(dict_service.db_connector, 'execute_query') as mock_query:
                mock_query.return_value = '''
                <entry id="test_invalid">
                    <lexical-unit>
                        <form lang="en"><text>Test</text></form>
                    </lexical-unit>
                    <sense id="sense1">
                        <!-- No definition or gloss -->
                    </sense>
                </entry>
                '''
                
                # Should be able to get entry for editing despite validation errors
                entry = dict_service.get_entry_for_editing("test_invalid")
                assert entry is not None
                
                # Validation errors should be detectable but not blocking
                from app.services.validation_engine import ValidationEngine
                validation_engine = ValidationEngine()
                result = validation_engine.validate_entry(entry)
                
                # Entry should be invalid but still loadable
                assert not result.is_valid
                assert len(result.errors) > 0
                # The specific error we expect
                assert any("Sense must have definition, gloss, or be a variant reference" in error.message 
                          for error in result.errors)


if __name__ == "__main__":
    pytest.main([__file__])
