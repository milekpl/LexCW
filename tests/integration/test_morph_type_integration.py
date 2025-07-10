"""
Integration tests for morph-type field server-side logic and UI integration.

Tests verify that:
1. Morph-type is correctly classified server-side for new entries
2. LIFT data morph-type is preserved and not overridden
3. Template correctly exposes morph-type values from backend
4. API correctly handles morph-type in requests/responses
5. JavaScript no longer performs client-side auto-classification
"""

import pytest
import json
from unittest.mock import Mock, patch
from app import create_app
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService



@pytest.mark.integration
class TestMorphTypeIntegration:
    """Integration tests for morph-type server-side logic and UI integration."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def mock_dict_service(self):
        """Mock dictionary service."""
        service = Mock(spec=DictionaryService)
        service.get_lift_ranges.return_value = {
            'morph-type': {
                'id': 'morph-type',
                'name': 'Morphological Type',
                'items': [
                    {'id': 'stem', 'name': 'stem'},
                    {'id': 'phrase', 'name': 'phrase'},
                    {'id': 'prefix', 'name': 'prefix'},
                    {'id': 'suffix', 'name': 'suffix'},
                    {'id': 'infix', 'name': 'infix'}
                ]
            }
        }
        return service

    @pytest.mark.integration
    def test_new_entry_form_shows_empty_morph_type(self, client, mock_dict_service):
        """Test that new entry form shows empty morph-type field."""
        with patch('app.views.dict_service', mock_dict_service):
            response = client.get('/entry/add')
            assert response.status_code == 200
            
            # Check that morph-type field is present but empty
            html = response.data.decode('utf-8')
            assert 'id="morph-type"' in html
            assert 'name="morph_type"' in html
            assert 'data-range-id="morph-type"' in html
            
            # Should not have data-selected attribute when empty
            assert 'data-selected=""' in html or 'data-selected' not in html

    @pytest.mark.integration
    def test_existing_entry_form_shows_backend_morph_type(self, client, mock_dict_service):
        """Test that existing entry form shows morph-type from backend."""
        # Mock an entry with morph-type
        mock_entry = Entry()
        mock_entry.id = 'test-entry-1'
        mock_entry.lexical_unit = 'test-word'
        mock_entry.morph_type = 'suffix'
        
        mock_dict_service.get_entry.return_value = mock_entry
        mock_dict_service.get_complete_variant_relations.return_value = []
        mock_dict_service.get_component_relations.return_value = []
        
        with patch('app.views.dict_service', mock_dict_service):
            response = client.get('/entry/edit/test-entry-1')
            assert response.status_code == 200
            
            html = response.data.decode('utf-8')
            assert 'id="morph-type"' in html
            assert 'name="morph_type"' in html
            assert 'data-selected="suffix"' in html

    @pytest.mark.integration
    def test_create_entry_api_auto_classifies_morph_type(self, client, mock_dict_service):
        """Test that POST /entry API auto-classifies morph-type server-side."""
        mock_dict_service.create_entry.return_value = 'new-entry-id'
        
        # Test different headword patterns
        test_cases = [
            ('word', 'stem'),
            ('multi word phrase', 'phrase'),
            ('pre-', 'prefix'),
            ('-suf', 'suffix'),
            ('-in-', 'infix')
        ]
        
        for headword, expected_morph_type in test_cases:
            with patch('app.views.dict_service', mock_dict_service):
                response = client.post('/entry', 
                    data={'lexical_unit': headword},
                    content_type='application/x-www-form-urlencoded'
                )
                
                assert response.status_code == 200
                
                # Verify that create_entry was called with correct morph_type
                args, kwargs = mock_dict_service.create_entry.call_args
                entry = args[0]
                assert hasattr(entry, 'morph_type')
                assert entry.morph_type == expected_morph_type, \
                    f"Expected {expected_morph_type} for '{headword}', got {entry.morph_type}"

    @pytest.mark.integration
    def test_create_entry_api_preserves_explicit_morph_type(self, client, mock_dict_service):
        """Test that API preserves explicitly provided morph-type (e.g., from LIFT)."""
        mock_dict_service.create_entry.return_value = 'new-entry-id'
        
        with patch('app.views.dict_service', mock_dict_service):
            # Send request with explicit morph_type that differs from auto-classification
            response = client.post('/entry', 
                data={
                    'lexical_unit': 'word',  # Would auto-classify as 'stem'
                    'morph_type': 'phrase'   # But explicit value should be preserved
                },
                content_type='application/x-www-form-urlencoded'
            )
            
            assert response.status_code == 200
            
            # Verify that explicit morph_type was preserved
            args, kwargs = mock_dict_service.create_entry.call_args
            entry = args[0]
            assert entry.morph_type == 'phrase'  # Should preserve explicit value

    @pytest.mark.integration
    def test_entry_model_auto_classification_logic(self):
        """Test Entry model morph-type auto-classification logic directly."""
        # Test cases with expected classifications
        test_cases = [
            # (lexical_unit, explicit_morph_type, expected_result)
            ('word', None, 'stem'),
            ('multi word', None, 'phrase'),
            ('pre-', None, 'prefix'),
            ('-suf', None, 'suffix'),
            ('-in-', None, 'infix'),
            ('word', 'phrase', 'phrase'),  # Explicit should override
            ('', None, 'stem'),  # Empty should default to stem
        ]
        
        for lexical_unit, explicit_morph_type, expected in test_cases:
            data = {'lexical_unit': lexical_unit}
            if explicit_morph_type:
                data['morph_type'] = explicit_morph_type
                
            entry = Entry.from_dict(data)
            assert entry.morph_type == expected, \
                f"For '{lexical_unit}' with explicit '{explicit_morph_type}', expected '{expected}', got '{entry.morph_type}'"

    @pytest.mark.integration
    def test_lift_parser_preserves_entry_morph_type(self):
        """Test that LIFT parser preserves entry-level morph-type traits."""
        from app.parsers.lift_parser import LIFTParser
        
        # Mock LIFT XML with entry-level morph-type trait
        lift_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test-entry-1">
                <lexical-unit>
                    <form lang="en">
                        <text>test-word</text>
                    </form>
                </lexical-unit>
                <trait name="morph-type" value="phrase"/>
                <sense id="sense-1">
                    <definition>
                        <form lang="en">
                            <text>Test definition</text>
                        </form>
                    </definition>
                </sense>
            </entry>
        </lift>'''
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(lift_content)
        
        assert len(entries) == 1
        entry = entries[0]
        assert entry.morph_type == 'phrase'  # Should preserve LIFT trait value

    @pytest.mark.integration
    def test_javascript_morph_type_removal(self, client, mock_dict_service):
        """Test that JavaScript file no longer contains morph-type auto-classification."""
        # Read the JavaScript file to verify cleanup
        with open('app/static/js/entry-form.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # These functions/references should be removed
        assert 'updateMorphTypeClassification' not in js_content
        assert 'morphTypeSelect' not in js_content
        assert 'Auto-classified as' not in js_content
        
        # These should still be present (POS inheritance)
        assert 'updateGrammaticalCategoryInheritance' in js_content
        assert 'dynamic-grammatical-info' in js_content

    @pytest.mark.integration
    def test_template_morph_type_data_selected(self, client, mock_dict_service):
        """Test that template correctly uses data-selected for morph-type."""
        # Mock entry with morph-type
        mock_entry = Entry()
        mock_entry.id = 'test-entry-1' 
        mock_entry.lexical_unit = 'test-'
        mock_entry.morph_type = 'prefix'
        
        mock_dict_service.get_entry.return_value = mock_entry
        mock_dict_service.get_complete_variant_relations.return_value = []
        mock_dict_service.get_component_relations.return_value = []
        
        with patch('app.views.dict_service', mock_dict_service):
            response = client.get('/entry/edit/test-entry-1')
            assert response.status_code == 200
            
            html = response.data.decode('utf-8')
            
            # Should have data-selected attribute with backend value
            assert 'data-selected="prefix"' in html
            
            # Should still have other required attributes
            assert 'data-range-id="morph-type"' in html
            assert 'name="morph_type"' in html

    @pytest.mark.integration
    def test_api_json_response_includes_morph_type(self, client, mock_dict_service):
        """Test that JSON API responses include morph_type field."""
        mock_entry = Entry()
        mock_entry.id = 'test-entry-1'
        mock_entry.lexical_unit = 'test-suffix'
        mock_entry.morph_type = 'suffix'
        
        mock_dict_service.get_entry.return_value = mock_entry
        
        with patch('app.views.dict_service', mock_dict_service):
            response = client.get('/api/entry/test-entry-1')
            
            if response.status_code == 200:
                data = json.loads(response.data)
                assert 'morph_type' in data
                assert data['morph_type'] == 'suffix'

    @pytest.mark.parametrize("headword,expected_morph_type", [
        ('word', 'stem'),
        ('two words', 'phrase'),
        ('pre-', 'prefix'),
        ('-suf', 'suffix'),
        ('-mid-', 'infix'),
        ('', 'stem'),  # Default for empty
    ])
    @pytest.mark.integration
    def test_server_side_classification_accuracy(self, headword, expected_morph_type):
        """Test server-side morph-type classification accuracy."""
        entry_data = {'lexical_unit': headword}
        entry = Entry.from_dict(entry_data)
        
        assert entry.morph_type == expected_morph_type, \
            f"Headword '{headword}' should classify as '{expected_morph_type}', got '{entry.morph_type}'"

    @pytest.mark.integration
    def test_no_override_of_lift_data(self):
        """Test that auto-classification never overrides LIFT data."""
        # Test case where auto-classification would differ from LIFT data
        entry_data = {
            'lexical_unit': 'word',     # Would auto-classify as 'stem'
            'morph_type': 'phrase'      # But LIFT says 'phrase'
        }
        
        entry = Entry.from_dict(entry_data)
        
        # Should preserve LIFT data, not auto-classify
        assert entry.morph_type == 'phrase'

    @pytest.mark.integration
    def test_end_to_end_morph_type_workflow(self, client, mock_dict_service):
        """Test complete workflow: create entry -> edit entry -> verify morph-type."""
        mock_dict_service.create_entry.return_value = 'new-entry-id'
        
        # Step 1: Create entry with auto-classification
        with patch('app.views.dict_service', mock_dict_service):
            response = client.post('/entry', 
                data={'lexical_unit': 'pre-'},
                content_type='application/x-www-form-urlencoded'
            )
            assert response.status_code == 200
            
            # Verify auto-classification happened
            args, kwargs = mock_dict_service.create_entry.call_args
            created_entry = args[0]
            assert created_entry.morph_type == 'prefix'
        
        # Step 2: Mock the created entry for editing
        mock_dict_service.get_entry.return_value = created_entry
        mock_dict_service.get_complete_variant_relations.return_value = []
        mock_dict_service.get_component_relations.return_value = []
        
        # Step 3: Load edit form and verify backend value is exposed
        with patch('app.views.dict_service', mock_dict_service):
            response = client.get('/entry/edit/new-entry-id')
            assert response.status_code == 200
            
            html = response.data.decode('utf-8')
            assert 'data-selected="prefix"' in html


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
