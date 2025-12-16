"""
End-to-end test for variant type selection functionality.
Tests that the selected variant type is properly stored in the XML output as a trait.
"""

import pytest
import tempfile
import os
from pathlib import Path
from app import create_app
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector
import xml.etree.ElementTree as ET


def test_variant_type_selection_stored_as_trait():
    """Test that when user selects a variant type, it's stored as a trait in the XML."""
    
    # Create a test app with testing configuration
    app = create_app('testing')
    
    with app.app_context():
        # Get the dictionary service
        dict_service = app.injector.get(DictionaryService)
        
        # Create a test entry with variant relations
        entry_data = {
            'id': 'test_entry_123',
            'lexical_unit': {'en': 'test word'},
            'grammatical_info': 'Noun',
            'variant_relations': [
                {
                    'ref': 'variant_entry_456',
                    'variant_type': 'spelling variant',
                    'type': '_component-lexeme',
                    'order': 0
                }
            ]
        }
        
        entry = Entry.from_dict(entry_data)
        
        # Create the entry in the database
        entry_id = dict_service.create_entry(entry)
        
        # Retrieve the entry to ensure it was properly saved
        retrieved_entry = dict_service.get_entry(entry_id)
        assert retrieved_entry.id == entry_id
        
        # Get the XML representation
        entry_xml_str = dict_service._prepare_entry_xml(retrieved_entry)
        
        # Parse the XML to verify the trait is present
        root = ET.fromstring(entry_xml_str)
        
        # Find all relations 
        relations = root.findall('.//relation')
        variant_relations = [rel for rel in relations if rel.get('type') == '_component-lexeme']
        
        assert len(variant_relations) == 1, f"Expected 1 variant relation, found {len(variant_relations)}"
        
        variant_relation = variant_relations[0]
        
        # Find the trait with name="variant-type"
        traits = variant_relation.findall('.//trait[@name="variant-type"]')
        assert len(traits) == 1, f"Expected 1 variant-type trait, found {len(traits)}"
        
        variant_trait = traits[0]
        assert variant_trait.get('value') == 'spelling variant', \
            f"Expected variant-type trait value 'spelling variant', got '{variant_trait.get('value')}'"
            
        print("✓ Test passed: Variant type is properly stored as a trait in the XML")
        
        # Clean up: delete the test entry
        try:
            dict_service.delete_entry(entry_id)
        except:
            pass  # Entry might not exist if test failed early


def test_multiple_variant_types():
    """Test that multiple variant types are stored correctly."""
    
    # Create a test app with testing configuration
    app = create_app('testing')
    
    with app.app_context():
        # Get the dictionary service
        dict_service = app.injector.get(DictionaryService)
        
        # Create a test entry with multiple variants
        entry_data = {
            'id': 'test_entry_multi_123',
            'lexical_unit': {'en': 'run'},
            'grammatical_info': 'Verb',
            'variant_relations': [
                {
                    'ref': 'variant_entry_456',
                    'variant_type': 'inflection',
                    'type': '_component-lexeme',
                    'order': 0
                },
                {
                    'ref': 'variant_entry_789',
                    'variant_type': 'dialectal variant',
                    'type': '_component-lexeme',
                    'order': 1
                }
            ]
        }
        
        entry = Entry.from_dict(entry_data)
        
        # Create the entry in the database
        entry_id = dict_service.create_entry(entry)
        
        # Retrieve and check XML
        retrieved_entry = dict_service.get_entry(entry_id)
        entry_xml_str = dict_service._prepare_entry_xml(retrieved_entry)
        root = ET.fromstring(entry_xml_str)
        
        # Find all variant relations
        relations = root.findall('.//relation')
        variant_relations = [rel for rel in relations if rel.get('type') == '_component-lexeme']
        
        assert len(variant_relations) == 2, f"Expected 2 variant relations, found {len(variant_relations)}"
        
        # Check that both have the correct variant-type traits
        variant_values = []
        for rel in variant_relations:
            traits = rel.findall('.//trait[@name="variant-type"]')
            assert len(traits) == 1, "Each variant relation should have exactly one variant-type trait"
            variant_values.append(traits[0].get('value'))
        
        assert 'inflection' in variant_values
        assert 'dialectal variant' in variant_values
        
        print("✓ Test passed: Multiple variant types are properly stored")
        
        # Clean up
        try:
            dict_service.delete_entry(entry_id)
        except:
            pass


if __name__ == "__main__":
    test_variant_type_selection_stored_as_trait()
    test_multiple_variant_types()
    print("All tests passed!")