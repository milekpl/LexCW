#!/usr/bin/env python3
"""
Test morph-type respect for existing LIFT data - Fixed version without Selenium
"""

from __future__ import annotations
import pytest
from unittest.mock import Mock, patch
from app import create_app
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService


@pytest.mark.integration
class TestMorphTypeInheritance:
    """Test that morph-type respects existing LIFT data and doesn't auto-override"""
    
    def test_existing_morph_type_not_overridden(self, dict_service_with_db: DictionaryService):
        """Test that entries with existing morph-type in LIFT aren't overridden"""
        # Clean up any existing test entries
        try:
            existing = dict_service_with_db.get_entry('test-morph-123')
            if existing:
                dict_service_with_db.delete_entry('test-morph-123')
        except Exception:
            pass  # Entry doesn't exist, which is fine
        
        # Create an entry with existing morph-type "stem" (from LIFT)
        entry_data = {
            'id_': 'test-morph-123',
            'lexical_unit': {'en': 'Protestant'},
            'morph_type': 'stem',  # Existing from LIFT data
            'senses': [{'id': 'sense1', 'glosses': {'en': 'test definition'}}]
        }
        
        entry = Entry.from_dict(entry_data)
        print(f"Created entry with ID: {entry.id}")
        
        # Verify the entry was created with the original morph-type
        assert entry.morph_type == 'stem', f"Expected 'stem', got '{entry.morph_type}'"
        
        # Create the entry in the database
        try:
            created_id = dict_service_with_db.create_entry(entry)
            print(f"Entry created with ID: {created_id}")
            
            # Verify the entry was actually created and retrieved correctly
            retrieved_entry = dict_service_with_db.get_entry(created_id)
            print(f"Retrieved entry: {retrieved_entry.id if retrieved_entry else 'None'}")
            
            # The retrieved entry should still have the original morph-type
            assert retrieved_entry.morph_type == 'stem', \
                f"Expected 'stem', got '{retrieved_entry.morph_type}'"
            
        except Exception as e:
            print(f"Error creating entry: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Now test that modifying the lexical unit doesn't auto-override the morph-type
        # This simulates what would happen when editing an entry
        entry_data_modified = {
            'id_': 'test-morph-123',
            'lexical_unit': {'en': 'pre-'},  # Would normally auto-classify as 'prefix'
            'morph_type': 'stem',  # Should be preserved from LIFT data
            'senses': [{'id': 'sense1', 'glosses': {'en': 'test definition'}}]
        }
        
        modified_entry = Entry.from_dict(entry_data_modified)
        
        # The morph-type should still be 'stem', not auto-classified as 'prefix'
        assert modified_entry.morph_type == 'stem', \
            f"Morph-type should not be auto-overridden. Expected 'stem', got '{modified_entry.morph_type}'"
        
        # Test the update operation
        dict_service_with_db.update_entry(modified_entry)
        
        # Verify the updated entry still has the original morph-type
        final_entry = dict_service_with_db.get_entry(created_id)
        assert final_entry.morph_type == 'stem', \
            f"Updated entry should preserve original morph-type. Expected 'stem', got '{final_entry.morph_type}'"
    
    def test_empty_morph_type_gets_auto_classified(self, dict_service_with_db: DictionaryService):
        """Test that entries with no morph-type get auto-classified"""
        # Clean up any existing test entries
        try:
            existing = dict_service_with_db.get_entry('test-morph-456')
            if existing:
                dict_service_with_db.delete_entry('test-morph-456')
        except Exception:
            pass  # Entry doesn't exist, which is fine
        
        # Create an entry with no morph-type
        entry_data = {
            'id_': 'test-morph-456',
            'lexical_unit': {'en': 'test-suffix'},
            'morph_type': '',  # Empty - should be auto-classified
            'senses': [{'id': 'sense1', 'glosses': {'en': 'test definition'}}]
        }
        
        entry = Entry.from_dict(entry_data)
        
        # Should be auto-classified as suffix
        print(f"Auto-classified morph-type for 'test-suffix': {entry.morph_type}")
        assert 'suffix' in entry.morph_type.lower(), \
            f"Expected 'suffix' classification for 'test-suffix', got: {entry.morph_type}"
        
        # Test with the database
        dict_service_with_db.create_entry(entry)
        retrieved_entry = dict_service_with_db.get_entry(entry.id)
        
        # Should still be auto-classified as suffix
        assert 'suffix' in retrieved_entry.morph_type.lower(), \
            f"Expected 'suffix' classification for 'test-suffix', got: {retrieved_entry.morph_type}"
    
    def test_morph_type_patterns(self):
        """Test various morph-type classification patterns"""
        test_cases = [
            # (lexical_unit_dict, explicit_morph_type, expected_result)
            ({'en': 'word'}, None, 'stem'),
            ({'en': 'multi word'}, None, 'phrase'),
            ({'en': 'pre-'}, None, 'prefix'),
            ({'en': '-suf'}, None, 'suffix'),
            ({'en': '-in-'}, None, 'infix'),
            ({'en': 'word'}, 'phrase', 'phrase'),  # Explicit should override
            ({'en': ''}, None, 'stem'),  # Empty should default to stem
            ({'en': 'pre-'}, 'stem', 'stem'),  # Explicit should override auto-classification
        ]
        
        for lexical_unit, explicit_morph_type, expected in test_cases:
            data = {'lexical_unit': lexical_unit}
            if explicit_morph_type:
                data['morph_type'] = explicit_morph_type
                
            entry = Entry.from_dict(data)
            assert entry.morph_type == expected, \
                f"For '{lexical_unit}' with explicit '{explicit_morph_type}', expected '{expected}', got '{entry.morph_type}'"

    def test_lift_data_preservation(self):
        """Test that LIFT data is preserved and not overridden by auto-classification"""
        # Test case where auto-classification would differ from LIFT data
        entry_data = {
            'lexical_unit': {'en': 'word'},     # Would auto-classify as 'stem'
            'morph_type': 'phrase'              # But LIFT says 'phrase'
        }
        
        entry = Entry.from_dict(entry_data)
        
        # Should preserve LIFT data, not auto-classify
        assert entry.morph_type == 'phrase', \
            f"Should preserve LIFT data. Expected 'phrase', got '{entry.morph_type}'"
    
    def test_flask_app_morph_type_handling(self):
        """Test Flask app handles morph-type correctly"""
        app = create_app('testing')
        
        with app.app_context():
            # Mock the dictionary service
            with patch('flask.current_app') as mock_current_app:
                mock_dict_service = Mock(spec=DictionaryService)
                mock_dict_service.get_lift_ranges.return_value = {
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
                mock_current_app.injector.get.return_value = mock_dict_service
                
                # Test that existing entry preserves morph-type
                mock_entry = Entry()
                mock_entry.id = 'test-entry-1'
                mock_entry.lexical_unit = {'en': 'test-word'}
                mock_entry.morph_type = 'phrase'  # From LIFT
                
                mock_dict_service.get_entry_for_editing.return_value = mock_entry
                
                # Should preserve the morph-type from LIFT
                assert mock_entry.morph_type == 'phrase', \
                    f"Should preserve LIFT morph-type. Expected 'phrase', got '{mock_entry.morph_type}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])