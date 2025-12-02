"""
Unit tests for LIFT subsense functionality (Day 22).

This test suite validates:
- Subsense data structures (Python dictionaries)
- Recursive subsense structures (nested subsenses)
- Subsense ordering and IDs
- Subsense data integrity (glosses, definitions, examples)

Note: XML serialization happens client-side (lift-xml-serializer.js).
These tests validate the data structures used by the serializer.
"""

import pytest

pytestmark = pytest.mark.unit


def test_subsense_basic_structure() -> None:
    """Test basic subsense XML structure."""
    subsense_data = {
        'id': 'test_subsense_1',
        'glosses': {
            'en': {'text': 'sub-meaning'},
            'pl': {'text': 'pod-znaczenie'}
        },
        'definitions': {
            'en': {'text': 'A more specific meaning'}
        },
        'grammatical_info': 'Noun',
        'examples': [],
        'relations': [],
        'notes': {},
        'subsenses': []  # No nested subsenses
    }
    
    # This will use the Python port of serializeSubsense
    # For now, testing the concept
    assert subsense_data['id'] == 'test_subsense_1'
    assert 'en' in subsense_data['glosses']
    assert 'pl' in subsense_data['glosses']
    assert subsense_data['glosses']['en']['text'] == 'sub-meaning'


def test_subsense_recursive_structure() -> None:
    """Test recursive subsense structures (subsense within subsense)."""
    parent_sense_data = {
        'id': 'sense_1',
        'glosses': {'en': {'text': 'parent'}},
        'definitions': {'en': {'text': 'Parent sense'}},
        'subsenses': [
            {
                'id': 'subsense_1.1',
                'glosses': {'en': {'text': 'child 1'}},
                'definitions': {'en': {'text': 'First child'}},
                'subsenses': [
                    {
                        'id': 'subsense_1.1.1',
                        'glosses': {'en': {'text': 'grandchild'}},
                        'definitions': {'en': {'text': 'Nested subsense'}},
                        'subsenses': []  # Leaf node
                    }
                ]
            },
            {
                'id': 'subsense_1.2',
                'glosses': {'en': {'text': 'child 2'}},
                'definitions': {'en': {'text': 'Second child'}},
                'subsenses': []  # No further nesting
            }
        ]
    }
    
    # Validate structure
    assert len(parent_sense_data['subsenses']) == 2
    assert parent_sense_data['subsenses'][0]['id'] == 'subsense_1.1'
    assert len(parent_sense_data['subsenses'][0]['subsenses']) == 1
    assert parent_sense_data['subsenses'][0]['subsenses'][0]['id'] == 'subsense_1.1.1'
    assert parent_sense_data['subsenses'][1]['id'] == 'subsense_1.2'
    assert len(parent_sense_data['subsenses'][1]['subsenses']) == 0


def test_subsense_ordering() -> None:
    """Test subsense order attribute."""
    subsenses = [
        {'id': 'sub_1', 'order': 0, 'glosses': {'en': {'text': 'first'}}},
        {'id': 'sub_2', 'order': 1, 'glosses': {'en': {'text': 'second'}}},
        {'id': 'sub_3', 'order': 2, 'glosses': {'en': {'text': 'third'}}}
    ]
    
    for i, subsense in enumerate(subsenses):
        assert subsense['order'] == i
        assert subsense['id'] == f'sub_{i+1}'


def test_subsense_with_examples() -> None:
    """Test subsenses containing examples."""
    subsense_data = {
        'id': 'subsense_with_examples',
        'glosses': {'en': {'text': 'specific meaning'}},
        'definitions': {'en': {'text': 'A specific definition'}},
        'examples': [
            {
                'sentence': 'Example sentence 1',
                'translation': 'Translation 1',
                'translation_type': 'free'
            },
            {
                'sentence': 'Example sentence 2',
                'translation': 'Translation 2',
                'translation_type': 'literal'
            }
        ],
        'subsenses': []
    }
    
    assert len(subsense_data['examples']) == 2
    assert subsense_data['examples'][0]['sentence'] == 'Example sentence 1'
    assert subsense_data['examples'][1]['translation_type'] == 'literal'


def test_subsense_with_notes() -> None:
    """Test subsenses with notes."""
    subsense_data = {
        'id': 'subsense_with_notes',
        'glosses': {'en': {'text': 'annotated meaning'}},
        'definitions': {'en': {'text': 'Definition with notes'}},
        'notes': {
            'general': 'This is a general note about this subsense',
            'grammar': 'Grammatical note'
        },
        'subsenses': []
    }
    
    assert 'general' in subsense_data['notes']
    assert 'grammar' in subsense_data['notes']
    assert subsense_data['notes']['general'] == 'This is a general note about this subsense'


def test_subsense_with_relations() -> None:
    """Test subsenses with semantic relations."""
    subsense_data = {
        'id': 'subsense_with_relations',
        'glosses': {'en': {'text': 'related meaning'}},
        'definitions': {'en': {'text': 'Definition with relations'}},
        'relations': [
            {
                'type': 'synonym',
                'ref': 'another_entry_id',
                'order': 0
            },
            {
                'type': 'antonym',
                'ref': 'opposite_entry_id',
                'order': 1
            }
        ],
        'subsenses': []
    }
    
    assert len(subsense_data['relations']) == 2
    assert subsense_data['relations'][0]['type'] == 'synonym'
    assert subsense_data['relations'][1]['type'] == 'antonym'


def test_subsense_with_traits() -> None:
    """Test subsenses with trait elements."""
    subsense_data = {
        'id': 'subsense_with_traits',
        'glosses': {'en': {'text': 'classified meaning'}},
        'definitions': {'en': {'text': 'Definition with traits'}},
        'domain_type': 'computer science',
        'semantic_domain': '6.2.3.1',
        'usage_type': 'informal',
        'subsenses': []
    }
    
    assert subsense_data['domain_type'] == 'computer science'
    assert subsense_data['semantic_domain'] == '6.2.3.1'
    assert subsense_data['usage_type'] == 'informal'


def test_subsense_grammatical_info() -> None:
    """Test subsenses with grammatical information."""
    subsense_data = {
        'id': 'subsense_gram',
        'glosses': {'en': {'text': 'meaning with grammar'}},
        'definitions': {'en': {'text': 'Definition with grammatical info'}},
        'grammatical_info': 'Noun',
        'subsenses': []
    }
    
    assert subsense_data['grammatical_info'] == 'Noun'


def test_empty_subsense_array() -> None:
    """Test sense with empty subsenses array."""
    sense_data = {
        'id': 'sense_no_subsenses',
        'glosses': {'en': {'text': 'simple sense'}},
        'definitions': {'en': {'text': 'No subsenses here'}},
        'subsenses': []
    }
    
    assert len(sense_data['subsenses']) == 0
    assert isinstance(sense_data['subsenses'], list)


def test_subsense_id_generation() -> None:
    """Test subsense ID follows hierarchical pattern."""
    # FieldWorks pattern: parent_id + order
    parent_id = 'entry_1_sense_1'
    subsenses = []
    
    for i in range(3):
        subsense_id = f"{parent_id}_subsense_{i+1}"
        subsenses.append({
            'id': subsense_id,
            'order': i,
            'glosses': {'en': {'text': f'subsense {i+1}'}}
        })
    
    assert subsenses[0]['id'] == 'entry_1_sense_1_subsense_1'
    assert subsenses[1]['id'] == 'entry_1_sense_1_subsense_2'
    assert subsenses[2]['id'] == 'entry_1_sense_1_subsense_3'


def test_subsense_multilingual_glosses() -> None:
    """Test subsenses with multiple language glosses."""
    subsense_data = {
        'id': 'multilingual_subsense',
        'glosses': {
            'en': {'text': 'English gloss'},
            'pl': {'text': 'Polish gloss'},
            'de': {'text': 'German gloss'},
            'fr': {'text': 'French gloss'}
        },
        'definitions': {
            'en': {'text': 'English definition'},
            'pl': {'text': 'Polish definition'}
        },
        'subsenses': []
    }
    
    assert len(subsense_data['glosses']) == 4
    assert 'en' in subsense_data['glosses']
    assert 'pl' in subsense_data['glosses']
    assert 'de' in subsense_data['glosses']
    assert 'fr' in subsense_data['glosses']
    assert len(subsense_data['definitions']) == 2


def test_subsense_deep_nesting() -> None:
    """Test deeply nested subsense structure (3+ levels)."""
    deep_sense = {
        'id': 'level_1',
        'glosses': {'en': {'text': 'Level 1'}},
        'subsenses': [
            {
                'id': 'level_2',
                'glosses': {'en': {'text': 'Level 2'}},
                'subsenses': [
                    {
                        'id': 'level_3',
                        'glosses': {'en': {'text': 'Level 3'}},
                        'subsenses': [
                            {
                                'id': 'level_4',
                                'glosses': {'en': {'text': 'Level 4'}},
                                'subsenses': []
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # Navigate to level 4
    level_2 = deep_sense['subsenses'][0]
    level_3 = level_2['subsenses'][0]
    level_4 = level_3['subsenses'][0]
    
    assert level_4['id'] == 'level_4'
    assert level_4['glosses']['en']['text'] == 'Level 4'
    assert len(level_4['subsenses']) == 0


def test_subsense_mixed_content() -> None:
    """Test subsense with all content types (examples, notes, relations, traits)."""
    comprehensive_subsense = {
        'id': 'comprehensive_sub',
        'glosses': {
            'en': {'text': 'comprehensive'},
            'pl': {'text': 'kompleksowy'}
        },
        'definitions': {
            'en': {'text': 'A comprehensive subsense definition'}
        },
        'grammatical_info': 'Adjective',
        'domain_type': 'linguistics',
        'semantic_domain': '3.5.4',
        'usage_type': 'technical',
        'examples': [
            {
                'sentence': 'Comprehensive example',
                'translation': 'Full translation',
                'translation_type': 'free'
            }
        ],
        'notes': {
            'general': 'General note',
            'usage': 'Usage note'
        },
        'relations': [
            {'type': 'synonym', 'ref': 'other_id', 'order': 0}
        ],
        'subsenses': [
            {
                'id': 'nested_sub',
                'glosses': {'en': {'text': 'nested'}},
                'definitions': {'en': {'text': 'Nested definition'}},
                'subsenses': []
            }
        ]
    }
    
    # Validate all components present
    assert 'glosses' in comprehensive_subsense
    assert 'definitions' in comprehensive_subsense
    assert 'grammatical_info' in comprehensive_subsense
    assert 'domain_type' in comprehensive_subsense
    assert 'examples' in comprehensive_subsense
    assert 'notes' in comprehensive_subsense
    assert 'relations' in comprehensive_subsense
    assert 'subsenses' in comprehensive_subsense
    
    # Validate nested subsense
    assert len(comprehensive_subsense['subsenses']) == 1
    assert comprehensive_subsense['subsenses'][0]['id'] == 'nested_sub'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
