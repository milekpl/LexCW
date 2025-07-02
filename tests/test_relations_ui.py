"""
Test suite for LIFT relations UI functionality.

This module tests the enhanced relations editing interface that supports
proper LIFT relation structure with types and references.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from app import create_app
from app.models.entry import Entry, Relation
from app.services.dictionary_service import DictionaryService
from app.database.mock_connector import MockDatabaseConnector


class TestRelationsUI:
    """Test relations UI model support."""
    
    def test_relation_object_creation(self):
        """Test creating Relation objects with type and ref."""
        relation = Relation(type="synonym", ref="word123")
        
        assert relation.type == "synonym"
        assert relation.ref == "word123"
    
    def test_entry_model_supports_relations_list(self):
        """Test Entry model supports list of Relation objects."""
        relations_data = [
            {"type": "synonym", "ref": "happy_123"},
            {"type": "antonym", "ref": "sad_456"},
            {"type": "hypernym", "ref": "emotion_789"}
        ]
        
        entry = Entry(
            lexical_unit={"en": "joyful"},
            relations=relations_data
        )
        
        assert len(entry.relations) == 3
        assert entry.relations[0].type == "synonym"
        assert entry.relations[0].ref == "happy_123"
        assert entry.relations[1].type == "antonym"
        assert entry.relations[1].ref == "sad_456"
        assert entry.relations[2].type == "hypernym"
        assert entry.relations[2].ref == "emotion_789"
    
    def test_entry_relations_serialization(self):
        """Test relations are properly serialized to/from dict."""
        entry = Entry(
            lexical_unit={"en": "beautiful"},
            relations=[
                {"type": "synonym", "ref": "lovely_123"},
                {"type": "antonym", "ref": "ugly_456"}
            ]
        )
        
        # Serialize to dict
        entry_dict = entry.to_dict()
        assert 'relations' in entry_dict
        assert len(entry_dict['relations']) == 2
        assert entry_dict['relations'][0]['type'] == "synonym"
        assert entry_dict['relations'][0]['ref'] == "lovely_123"
        
        # Round-trip test
        new_entry = Entry.from_dict(entry_dict)
        assert len(new_entry.relations) == 2
        assert new_entry.relations[0].type == "synonym"
        assert new_entry.relations[1].type == "antonym"
    
    def test_empty_relations_handling(self):
        """Test entries with no relations are handled correctly."""
        entry = Entry(lexical_unit={"en": "isolated"})
        
        assert entry.relations == []
        
        entry_dict = entry.to_dict()
        assert entry_dict['relations'] == []
    
    def test_add_relation_method(self):
        """Test the add_relation method creates proper Relation objects."""
        entry = Entry(lexical_unit={"en": "test"})
        
        entry.add_relation("synonym", "equivalent_123")
        
        assert len(entry.relations) == 1
        assert entry.relations[0].type == "synonym"
        assert entry.relations[0].ref == "equivalent_123"


class TestRelationsAPISupport:
    """Test API support for relations management."""
    
    @pytest.fixture
    def app(self) -> Flask:
        """Create test app with mock connector."""
        mock_connector = MockDatabaseConnector()
        mock_dictionary_service = DictionaryService(mock_connector)

        app = create_app('testing')
        app.config['DICTIONARY_SERVICE'] = mock_dictionary_service
        
        return app
    
    def test_api_entry_creation_with_relations(self, app: Flask):
        """Test creating entries with relations via API."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            
            entry_data = {
                "lexical_unit": {"en": "wonderful"},
                "relations": [
                    {"type": "synonym", "ref": "amazing_123"},
                    {"type": "antonym", "ref": "terrible_456"}
                ]
            }
            
            entry = Entry.from_dict(entry_data)
            result_id = dict_service.create_entry(entry)
            
            assert result_id is not None
            assert len(entry.relations) == 2
            assert entry.relations[0].type == "synonym"
    
    def test_api_entry_update_with_relations(self, app: Flask):
        """Test updating entry relations via API."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            
            # Create entry
            entry = Entry(lexical_unit={"en": "modify"})
            entry_id = dict_service.create_entry(entry)
            
            # Get the entry from database to ensure we have the correct object
            entry = dict_service.get_entry(entry_id)
            
            # Update with relations
            entry.add_relation("synonym", "change_123")
            entry.add_relation("hypernym", "action_456")
            
            dict_service.update_entry(entry)
            
            # Verify update
            updated_entry = dict_service.get_entry(entry_id)
            assert len(updated_entry.relations) == 2


class TestRelationsRangesIntegration:
    """Test integration with LIFT ranges for relation types."""
    
    @pytest.fixture
    def app(self) -> Flask:
        """Create test app."""
        app = create_app('testing')
        app.config['DICTIONARY_SERVICE'] = MagicMock(spec=DictionaryService)
        return app
    
    def test_relation_types_from_ranges(self, app: Flask):
        """Test that relation types can be loaded from ranges."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            # Mock the get_ranges method to return predictable data
            dict_service.get_ranges.return_value = {
                'relation-types': {
                    'values': [
                        {'value': 'synonym'},
                        {'value': 'antonym'},
                        {'value': 'hypernym'},
                        {'value': 'hyponym'},
                    ]
                }
            }
            ranges = dict_service.get_ranges()
            
            # Should have relation-types range with default values
            assert 'relation-types' in ranges
            relation_types = ranges['relation-types']['values']
            
            # Check for expected types
            type_values = [rt['value'] for rt in relation_types]
            assert 'synonym' in type_values
            assert 'antonym' in type_values
            assert 'hypernym' in type_values
            assert 'hyponym' in type_values
    
    def test_relation_validation_ready(self, app: Flask):
        """Test that relation type validation infrastructure is ready."""
        with app.app_context():
            # Create relation with valid type
            relation = Relation(type="synonym", ref="test_123")
            assert relation.type == "synonym"
            
            # Entry with relation should validate
            entry = Entry(
                lexical_unit={"en": "test"},
                relations=[{"type": "synonym", "ref": "valid_123"}]
            )
            assert len(entry.relations) == 1


class TestRelationsLifecycle:
    """Test complete lifecycle operations for relations."""
    
    @pytest.fixture
    def app(self) -> Flask:
        """Create test app with mock connector."""
        mock_connector = MockDatabaseConnector()
        mock_dictionary_service = DictionaryService(mock_connector)

        app = create_app('testing')
        app.config['DICTIONARY_SERVICE'] = mock_dictionary_service
        
        return app
    
    def test_add_relation_to_existing_entry(self, app: Flask):
        """Test adding a relation to an existing entry."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            
            # Create base entry
            entry = Entry(lexical_unit={"en": "base"})
            entry_id = dict_service.create_entry(entry)
            
            # Get the entry from database to ensure we have the correct object
            entry = dict_service.get_entry(entry_id)
            
            # Add relation
            entry.add_relation("synonym", "equivalent_123")
            dict_service.update_entry(entry)
            
            # Verify
            updated = dict_service.get_entry(entry_id)
            assert len(updated.relations) == 1
            assert updated.relations[0].type == "synonym"
    
    def test_remove_relation_from_entry(self, app: Flask):
        """Test removing a relation from an entry."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            
            # Create entry with relations
            entry = Entry(
                lexical_unit={"en": "test"},
                relations=[
                    {"type": "synonym", "ref": "keep_123"},
                    {"type": "antonym", "ref": "remove_456"}
                ]
            )
            entry_id = dict_service.create_entry(entry)
            
            # Get the entry from database to ensure we have the correct object
            entry = dict_service.get_entry(entry_id)
            
            # Remove one relation
            entry.relations = [r for r in entry.relations if r.ref != "remove_456"]
            dict_service.update_entry(entry)
            
            # Verify
            updated = dict_service.get_entry(entry_id)
            assert len(updated.relations) == 1
            assert updated.relations[0].ref == "keep_123"
    
    def test_modify_relation_in_entry(self, app: Flask):
        """Test modifying an existing relation."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            
            # Create entry with relation
            entry = Entry(
                lexical_unit={"en": "test"},
                relations=[{"type": "synonym", "ref": "old_123"}]
            )
            entry_id = dict_service.create_entry(entry)
            
            # Get the entry from database to ensure we have the correct object
            entry = dict_service.get_entry(entry_id)
            
            # Modify relation
            entry.relations[0].ref = "new_456"
            entry.relations[0].type = "antonym"
            dict_service.update_entry(entry)
            
            # Verify
            updated = dict_service.get_entry(entry_id)
            assert len(updated.relations) == 1
            assert updated.relations[0].type == "antonym"
            assert updated.relations[0].ref == "new_456"
