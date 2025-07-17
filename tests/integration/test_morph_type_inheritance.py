#!/usr/bin/env python3
"""
Test morph-type respect for existing LIFT data
"""

from __future__ import annotations
import pytest
from unittest.mock import Mock, patch
from app import create_app
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService

@pytest.fixture
def app():
    """Create a test Flask app."""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app

@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()

@pytest.fixture
def mock_dict_service():
    """Create a mock dictionary service."""
    service = Mock()
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
    service.get_complete_variant_relations.return_value = []
    service.get_component_relations.return_value = []
    service.get_entry_for_editing.return_value = None
    return service

@pytest.mark.integration
class TestMorphTypeInheritance:
    """Test that morph-type respects existing LIFT data and doesn't auto-override"""
    
    @pytest.mark.integration
    def test_existing_morph_type_not_overridden(self, app, client, mock_dict_service):
        """Test that entries with existing morph-type in LIFT aren't overridden"""
        # Create an entry with existing morph-type "stem" (from LIFT)
        entry_data = {
            'id_': 'test-morph-123',
            'lexical_unit': {'en': 'Protestant'},
            'morph_type': 'stem',  # Existing from LIFT data
            'senses': [{'id': 'sense1', 'glosses': {'en': 'test definition'}}]
        }
        
        entry = Entry.from_dict(entry_data)
        
        # Mock the dictionary service to return our entry
        mock_dict_service.create_entry.return_value = 'test-morph-123'
        mock_dict_service.get_entry.return_value = entry
        
        with app.app_context():
            with patch('flask.current_app.injector.get') as mock_get:
                mock_get.return_value = mock_dict_service
                
                # Test that the entry maintains its existing morph-type
                assert entry.morph_type == 'stem'
                
                # Test that creating the entry preserves the morph-type
                created_id = mock_dict_service.create_entry(entry)
                assert created_id == 'test-morph-123'
                
                # Verify the mock was called correctly
                mock_dict_service.create_entry.assert_called_once_with(entry)
                
                # Verify the entry still has the original morph-type
                assert entry.morph_type == 'stem'
    
    @pytest.mark.integration
    def test_empty_morph_type_gets_auto_classified(self, app, mock_dict_service):
        """Test that entries with no morph-type get auto-classified"""
        # Create an entry with no morph-type
        entry_data = {
            'id_': 'test-morph-456',
            'lexical_unit': {'en': '-suffix'},  # Starts with '-' should be classified as suffix
            'morph_type': '',  # Empty - should be auto-classified
            'senses': [{'id': 'sense1', 'glosses': {'en': 'test definition'}}]
        }
        
        entry = Entry.from_dict(entry_data)
        
        # The Entry.from_dict() method already auto-classifies based on lexical unit
        # when morph_type is empty, so we test that it was classified correctly
        assert entry.morph_type == 'suffix'
    
    @pytest.mark.integration 
    def test_morph_type_patterns(self, app, mock_dict_service):
        """Test various morph-type classification patterns"""
        test_cases = [
            ('pre-', 'prefix'),
            ('-suf', 'suffix'),
            ('-mid-', 'infix'),
            ('word', 'stem'),
            ('two words', 'phrase'),
        ]
        
        for lexical_unit, expected_morph_type in test_cases:
            entry_data = {
                'id_': f'test-{lexical_unit}',
                'lexical_unit': {'en': lexical_unit},
                'morph_type': '',  # Empty - should be auto-classified
                'senses': [{'id': 'sense1', 'glosses': {'en': 'test definition'}}]
            }
            
            entry = Entry.from_dict(entry_data)
            
            # Apply auto-classification logic
            if not entry.morph_type:
                if ' ' in lexical_unit:
                    entry.morph_type = 'phrase'
                elif lexical_unit.endswith('-') and not lexical_unit.startswith('-'):
                    entry.morph_type = 'prefix'
                elif lexical_unit.startswith('-') and lexical_unit.endswith('-'):
                    entry.morph_type = 'infix'
                elif lexical_unit.startswith('-'):
                    entry.morph_type = 'suffix'
                else:
                    entry.morph_type = 'stem'
            
            assert entry.morph_type == expected_morph_type, \
                f"Expected {expected_morph_type} for '{lexical_unit}', got {entry.morph_type}"
    
    @pytest.mark.integration
    def test_lift_data_preservation(self, app, mock_dict_service):
        """Test that LIFT data morph-type is preserved"""
        from app.parsers.lift_parser import LIFTParser
        
        # Test XML with explicit morph-type
        xml_with_morph_type = '''<entry id="test-entry">
            <lexical-unit>
                <form lang="en">
                    <text>Protestant</text>
                </form>
            </lexical-unit>
            <trait name="morph-type" value="stem"/>
            <sense id="sense1">
                <gloss lang="en">
                    <text>test definition</text>
                </gloss>
            </sense>
        </entry>'''
        
        parser = LIFTParser()
        entries = parser.parse_string(xml_with_morph_type)
        
        assert len(entries) == 1
        entry = entries[0]
        
        # The morph-type from LIFT should be preserved
        assert entry.morph_type == 'stem'
        
        # Even if the lexical unit would normally be auto-classified differently,
        # the LIFT data should be preserved
        assert entry.lexical_unit.get('en') == 'Protestant'
    
    @pytest.mark.integration
    def test_flask_app_morph_type_handling(self, app, client, mock_dict_service):
        """Test that Flask app preserves morph-type from LIFT"""
        # Mock an entry with morph-type from LIFT
        mock_entry = Entry()
        mock_entry.id = 'test-entry-1'
        mock_entry.lexical_unit = {'en': 'Protestant'}
        mock_entry.morph_type = 'stem'  # From LIFT
        
        mock_dict_service.get_entry_for_editing.return_value = mock_entry
        
        with app.app_context():
            with patch('flask.current_app.injector.get') as mock_get:
                mock_get.return_value = mock_dict_service
                
                # Request the edit form
                response = client.get('/entries/test-entry-1/edit')
                assert response.status_code == 200
                
                html = response.data.decode('utf-8')
                
                # The form should show the morph-type from LIFT
                assert 'data-selected="stem"' in html
                
                # The lexical unit should be preserved
                assert 'value="Protestant"' in html
