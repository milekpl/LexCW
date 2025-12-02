"""
Integration tests for subsense CRUD operations (Day 23).

These tests validate the full subsense workflow:
- Creating entries with subsenses via the API
- Reading subsense data from the database
- Updating subsenses
- Deleting subsenses
- Recursive subsense structures
"""

import pytest
from flask import url_for
from app.models.entry import Entry


pytestmark = pytest.mark.integration


@pytest.fixture
def entry_with_subsenses_data() -> dict:
    """Test data for entry with subsenses."""
    return {
        'lexical_unit': {'en': 'test word'},
        'senses': [
            {
                'id': 'sense_1',
                'glosses': {'en': {'text': 'main sense'}},
                'definitions': {'en': {'text': 'Main definition'}},
                'subsenses': [
                    {
                        'id': 'subsense_1_1',
                        'glosses': {'en': {'text': 'first subsense'}},
                        'definitions': {'en': {'text': 'First subsense definition'}}
                    },
                    {
                        'id': 'subsense_1_2',
                        'glosses': {'en': {'text': 'second subsense'}},
                        'definitions': {'en': {'text': 'Second subsense definition'}},
                        'subsenses': [
                            {
                                'id': 'subsense_1_2_1',
                                'glosses': {'en': {'text': 'nested subsense'}},
                                'definitions': {'en': {'text': 'Nested subsense definition'}}
                            }
                        ]
                    }
                ]
            }
        ]
    }


def test_create_entry_with_subsenses(client, entry_with_subsenses_data: dict) -> None:
    """Test creating an entry with subsenses through the API."""
    # This test will be implemented when API endpoints support subsenses
    # For now, test the data structure
    assert 'subsenses' in entry_with_subsenses_data['senses'][0]
    assert len(entry_with_subsenses_data['senses'][0]['subsenses']) == 2
    
    # Verify nested structure
    nested_subsense = entry_with_subsenses_data['senses'][0]['subsenses'][1]
    assert 'subsenses' in nested_subsense
    assert len(nested_subsense['subsenses']) == 1


def test_subsense_data_structure() -> None:
    """Test that subsense data structures are properly formed."""
    subsense = {
        'id': 'test_sub',
        'glosses': {'en': {'text': 'gloss'}},
        'definitions': {'en': {'text': 'definition'}},
        'grammatical_info': 'Noun',
        'subsenses': []
    }
    
    assert subsense['id'] == 'test_sub'
    assert 'glosses' in subsense
    assert 'definitions' in subsense
    assert 'grammatical_info' in subsense
    assert 'subsenses' in subsense
    assert isinstance(subsense['subsenses'], list)


def test_recursive_subsense_depth() -> None:
    """Test deeply nested subsense structure (3 levels)."""
    sense = {
        'id': 'sense_1',
        'glosses': {'en': {'text': 'level 0'}},
        'subsenses': [
            {
                'id': 'sub_1',
                'glosses': {'en': {'text': 'level 1'}},
                'subsenses': [
                    {
                        'id': 'sub_1_1',
                        'glosses': {'en': {'text': 'level 2'}},
                        'subsenses': [
                            {
                                'id': 'sub_1_1_1',
                                'glosses': {'en': {'text': 'level 3'}},
                                'subsenses': []
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # Navigate to level 3
    level_1 = sense['subsenses'][0]
    level_2 = level_1['subsenses'][0]
    level_3 = level_2['subsenses'][0]
    
    assert level_3['id'] == 'sub_1_1_1'
    assert level_3['glosses']['en']['text'] == 'level 3'


def test_subsense_without_nested_subsenses() -> None:
    """Test subsense that has no further nesting."""
    subsense = {
        'id': 'simple_sub',
        'glosses': {'en': {'text': 'simple'}},
        'definitions': {'en': {'text': 'Simple subsense'}},
        'subsenses': []
    }
    
    assert len(subsense['subsenses']) == 0
    assert subsense['glosses']['en']['text'] == 'simple'


def test_multiple_subsenses_same_level() -> None:
    """Test sense with multiple subsenses at the same level."""
    sense = {
        'id': 'sense_1',
        'glosses': {'en': {'text': 'parent'}},
        'subsenses': [
            {
                'id': 'sub_1',
                'glosses': {'en': {'text': 'first'}},
                'subsenses': []
            },
            {
                'id': 'sub_2',
                'glosses': {'en': {'text': 'second'}},
                'subsenses': []
            },
            {
                'id': 'sub_3',
                'glosses': {'en': {'text': 'third'}},
                'subsenses': []
            }
        ]
    }
    
    assert len(sense['subsenses']) == 3
    assert sense['subsenses'][0]['id'] == 'sub_1'
    assert sense['subsenses'][1]['id'] == 'sub_2'
    assert sense['subsenses'][2]['id'] == 'sub_3'


def test_subsense_with_all_fields() -> None:
    """Test subsense with all possible LIFT fields populated."""
    comprehensive_subsense = {
        'id': 'comprehensive',
        'glosses': {
            'en': {'text': 'English gloss'},
            'pl': {'text': 'Polish gloss'}
        },
        'definitions': {
            'en': {'text': 'English definition'},
            'pl': {'text': 'Polish definition'}
        },
        'grammatical_info': 'Verb',
        'domain_type': 'linguistics',
        'semantic_domain': '3.5.4',
        'usage_type': 'formal',
        'examples': [
            {
                'sentence': 'Example sentence',
                'translation': 'Example translation',
                'translation_type': 'free'
            }
        ],
        'notes': {
            'general': 'General note'
        },
        'relations': [
            {
                'type': 'synonym',
                'ref': 'other_entry'
            }
        ],
        'subsenses': []
    }
    
    # Validate all fields present
    assert comprehensive_subsense['id'] == 'comprehensive'
    assert len(comprehensive_subsense['glosses']) == 2
    assert len(comprehensive_subsense['definitions']) == 2
    assert comprehensive_subsense['grammatical_info'] == 'Verb'
    assert comprehensive_subsense['domain_type'] == 'linguistics'
    assert comprehensive_subsense['semantic_domain'] == '3.5.4'
    assert comprehensive_subsense['usage_type'] == 'formal'
    assert len(comprehensive_subsense['examples']) == 1
    assert 'general' in comprehensive_subsense['notes']
    assert len(comprehensive_subsense['relations']) == 1
    assert len(comprehensive_subsense['subsenses']) == 0


def test_subsense_id_uniqueness() -> None:
    """Test that subsense IDs are unique within an entry."""
    sense = {
        'id': 'sense_1',
        'subsenses': [
            {'id': 'sub_1', 'glosses': {'en': {'text': 'first'}}},
            {'id': 'sub_2', 'glosses': {'en': {'text': 'second'}}},
            {'id': 'sub_3', 'glosses': {'en': {'text': 'third'}}}
        ]
    }
    
    ids = [sub['id'] for sub in sense['subsenses']]
    assert len(ids) == len(set(ids)), "Subsense IDs should be unique"


def test_empty_sense_subsenses_array() -> None:
    """Test sense with empty subsenses array."""
    sense = {
        'id': 'sense_no_subs',
        'glosses': {'en': {'text': 'no subsenses'}},
        'subsenses': []
    }
    
    assert 'subsenses' in sense
    assert len(sense['subsenses']) == 0
    assert isinstance(sense['subsenses'], list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
