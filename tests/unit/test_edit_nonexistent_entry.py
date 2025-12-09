"""
Unit tests for editing non-existent entries with relations.

Tests the scenario where:
1. An entry doesn't exist in the database
2. A user tries to edit it via the /entries/{id}/edit route
3. The entry should be created instead of throwing an error
4. Relations to non-existent targets should be allowed
"""

from __future__ import annotations

import pytest
from app.models.entry import Entry
from app.models.sense import Sense


@pytest.mark.unit
class TestEditNonexistentEntry:
    """Test suite for editing non-existent entries."""

    def test_create_entry_from_dict_with_relation_to_nonexistent_target(self) -> None:
        """
        Test that an entry can be created with a relation to a non-existent target.
        
        This is the key requirement: relations should allow UUID refs even if
        the target entry doesn't exist yet.
        """
        # Create entry data with a relation that references a non-existent UUID
        entry_dict = {
            'id': 'test_relation_pqr',
            'lexical_unit': {'pl': 'słowo z relacją'},
            'grammatical_info': '',
            'senses': [
                {
                    'id': 'sense1',
                    'definition': {'pl': 'Definicja z relacją'},
                    'relations': [
                        {
                            'type': 'Porównaj',
                            'ref': 'aaaee4d6-8239-43e3-819c-c246932b0ae0'  # Non-existent UUID
                        }
                    ]
                }
            ]
        }
        
        # This should NOT raise an error
        entry = Entry.from_dict(entry_dict)
        
        # Verify the entry was created correctly
        assert entry.id == 'test_relation_pqr'
        assert entry.lexical_unit == {'pl': 'słowo z relacją'}
        assert len(entry.senses) == 1
        assert len(entry.senses[0].relations) == 1
        assert entry.senses[0].relations[0]['ref'] == 'aaaee4d6-8239-43e3-819c-c246932b0ae0'
        assert entry.senses[0].relations[0]['type'] == 'Porównaj'

    def test_entry_with_relation_preserves_all_data(self) -> None:
        """
        Test that converting entry to dict and back preserves relation data.
        """
        # Create entry with relation
        entry_dict = {
            'id': 'test_entry_123',
            'lexical_unit': {'en': 'test word'},
            'senses': [
                {
                    'id': 'sense1',
                    'definition': {'en': 'A test word'},
                    'relations': [
                        {
                            'type': 'synonym',
                            'ref': 'non-existent-uuid'
                        }
                    ]
                }
            ]
        }
        
        entry = Entry.from_dict(entry_dict)
        result_dict = entry.to_dict()
        
        # Verify relation is preserved in round-trip
        assert 'senses' in result_dict
        assert len(result_dict['senses']) > 0
        assert 'relations' in result_dict['senses'][0]
        assert len(result_dict['senses'][0]['relations']) > 0
        assert result_dict['senses'][0]['relations'][0]['ref'] == 'non-existent-uuid'

    def test_entry_empty_constructor(self) -> None:
        """
        Test that Entry can be instantiated with just an ID (for new entries).
        """
        entry = Entry(id_='new_entry_id')
        
        assert entry.id == 'new_entry_id'
        assert entry.lexical_unit == {}
        assert entry.senses == []
        assert entry.notes == {}

    def test_entry_preserves_sense_relation_structure(self) -> None:
        """
        Test that sense relations maintain their structure through dict conversion.
        """
        sense = Sense(
            id_='sense1',
            definition={'pl': 'test definition'}
        )
        # Add a relation
        sense.relations.append({
            'type': 'Porównaj',
            'ref': 'target-uuid-that-may-not-exist'
        })
        
        # Convert to dict
        sense_dict = sense.to_dict()
        
        # Verify structure
        assert sense_dict['id'] == 'sense1'
        assert 'relations' in sense_dict
        assert len(sense_dict['relations']) == 1
        assert sense_dict['relations'][0]['type'] == 'Porównaj'
        assert sense_dict['relations'][0]['ref'] == 'target-uuid-that-may-not-exist'
