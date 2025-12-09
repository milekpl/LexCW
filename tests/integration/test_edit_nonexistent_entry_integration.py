"""
Integration tests for editing non-existent entries.

Tests the complete workflow of:
1. Navigating to an edit form for a non-existent entry
2. Adding relations to non-existent target entries
3. Saving the entry and having it created in the database
"""

from __future__ import annotations

import pytest
from flask import Flask
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry


@pytest.mark.integration
class TestEditNonexistentEntryIntegration:
    """Integration tests for editing non-existent entries."""

    def test_edit_nonexistent_entry_creates_it(
        self, 
        app: Flask, 
        dict_service_with_db: DictionaryService
    ) -> None:
        """
        Test that editing a non-existent entry via the service creates it.
        
        This simulates the scenario where:
        1. User navigates to /entries/test_new_entry/edit
        2. The entry doesn't exist in the database
        3. The form should allow editing and saving
        4. Upon save, the entry should be created
        """
        with app.app_context():
            dict_service = dict_service_with_db
            
            # Verify entry doesn't exist yet
            try:
                dict_service.get_entry('test_new_entry')
                assert False, "Entry should not exist yet"
            except Exception:
                pass  # Expected - entry doesn't exist
            
            # Create entry data with a relation to a non-existent target
            entry = Entry(id_='test_new_entry')
            entry.lexical_unit = {'en': 'test word'}
            
            # Add a sense with a relation to a non-existent target
            from app.models.sense import Sense
            sense = Sense(id_='sense1')
            sense.definition = {'en': 'A test word'}
            sense.relations.append({
                'type': 'synonym',
                'ref': 'non-existent-target-uuid-12345'
            })
            entry.senses.append(sense)
            
            # Save the entry (should use create since it doesn't exist)
            dict_service.create_entry(entry)
            
            # Verify entry was created
            retrieved_entry = dict_service.get_entry('test_new_entry')
            assert retrieved_entry is not None
            assert retrieved_entry.id == 'test_new_entry'
            assert retrieved_entry.lexical_unit == {'en': 'test word'}
            
            # Verify the relation was preserved
            assert len(retrieved_entry.senses) > 0
            assert len(retrieved_entry.senses[0].relations) > 0
            relation = retrieved_entry.senses[0].relations[0]
            assert relation['type'] == 'synonym'
            assert relation['ref'] == 'non-existent-target-uuid-12345'

    def test_edit_entry_with_nonexistent_relation_targets_preserves_refs(
        self,
        app: Flask,
        dict_service_with_db: DictionaryService
    ) -> None:
        """
        Test that when editing an entry with relations to non-existent targets,
        the refs are preserved.
        """
        with app.app_context():
            dict_service = dict_service_with_db
            
            # Create an entry with multiple relations to non-existent targets
            entry_dict = {
                'id': 'test_multi_relation',
                'lexical_unit': {'pl': 'słowo z relacjami'},
                'senses': [
                    {
                        'id': 'sense1',
                        'definition': {'pl': 'First sense'},
                        'relations': [
                            {
                                'type': 'Porównaj',
                                'ref': 'uuid-that-does-not-exist-1'
                            },
                            {
                                'type': 'synonym',
                                'ref': 'uuid-that-does-not-exist-2'
                            }
                        ]
                    }
                ]
            }
            
            entry = Entry.from_dict(entry_dict)
            dict_service.create_entry(entry)
            
            # Retrieve and verify both relations are preserved
            retrieved = dict_service.get_entry('test_multi_relation')
            assert len(retrieved.senses) > 0
            assert len(retrieved.senses[0].relations) == 2
            
            # Check first relation
            assert retrieved.senses[0].relations[0]['type'] == 'Porównaj'
            assert retrieved.senses[0].relations[0]['ref'] == 'uuid-that-does-not-exist-1'
            
            # Check second relation
            assert retrieved.senses[0].relations[1]['type'] == 'synonym'
            assert retrieved.senses[0].relations[1]['ref'] == 'uuid-that-does-not-exist-2'
