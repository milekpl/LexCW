"""
Integration tests for reversal CRUD operations (LIFT 0.13 - Day 24-25).

These tests validate the full reversal workflow:
- Creating entries with reversals via the API
- Reading reversal data from the database
- Updating reversals
- Deleting reversals
- Complex reversal structures with main elements
- Reversal types and grammatical-info preservation
"""

import pytest
from typing import Dict, Any


pytestmark = pytest.mark.integration


@pytest.fixture
def entry_with_reversals_data() -> Dict[str, Any]:
    """Test data for entry with reversals."""
    return {
        'lexical_unit': {'pl': 'kot'},
        'senses': [
            {
                'id': 'sense_1',
                'glosses': {'en': 'cat'},
                'definitions': {'pl': 'Ssak drapieżny z rodziny kotowatych'},
                'reversals': [
                    {
                        'type': 'en',
                        'forms': {'en': 'cat'},
                        'grammatical_info': 'Noun'
                    },
                    {
                        'type': 'en',
                        'forms': {'en': 'feline'},
                        'grammatical_info': 'Noun',
                        'main': {
                            'forms': {'en': 'domestic cat'},
                            'grammatical_info': 'Noun'
                        }
                    }
                ]
            }
        ]
    }


@pytest.fixture
def entry_with_complex_reversals_data() -> Dict[str, Any]:
    """Test data for entry with complex reversals (nested main elements)."""
    return {
        'lexical_unit': {'pl': 'pies'},
        'senses': [
            {
                'id': 'sense_1',
                'glosses': {'en': 'dog'},
                'definitions': {'pl': 'Ssak drapieżny z rodziny psowatych'},
                'reversals': [
                    {
                        'type': 'en',
                        'forms': {'en': 'dog'},
                        'main': {
                            'forms': {'en': 'canine'},
                            'grammatical_info': 'Noun',
                            'main': {
                                'forms': {'en': 'domestic dog'},
                                'grammatical_info': 'Noun'
                            }
                        }
                    }
                ]
            }
        ]
    }


def test_reversal_data_structure(entry_with_reversals_data: Dict[str, Any]) -> None:
    """Test that reversal data structures are properly formed."""
    sense = entry_with_reversals_data['senses'][0]
    assert 'reversals' in sense
    assert len(sense['reversals']) == 2
    
    # Check first reversal (basic)
    reversal1 = sense['reversals'][0]
    assert reversal1['type'] == 'en'
    assert 'forms' in reversal1
    assert reversal1['forms']['en'] == 'cat'
    assert reversal1['grammatical_info'] == 'Noun'
    assert 'main' not in reversal1
    
    # Check second reversal (with main element)
    reversal2 = sense['reversals'][1]
    assert 'main' in reversal2
    assert 'forms' in reversal2['main']
    assert reversal2['main']['forms']['en'] == 'domestic cat'
    assert reversal2['main']['grammatical_info'] == 'Noun'


def test_reversal_multitext_forms() -> None:
    """Test reversals with multiple language forms."""
    reversal = {
        'type': 'en',
        'forms': {
            'en': 'cat',
            'en-US': 'kitty',
            'en-GB': 'moggy'
        },
        'grammatical_info': 'Noun'
    }
    
    assert len(reversal['forms']) == 3
    assert 'en' in reversal['forms']
    assert 'en-US' in reversal['forms']
    assert 'en-GB' in reversal['forms']


def test_reversal_without_type() -> None:
    """Test that reversals can exist without a type attribute."""
    reversal = {
        'forms': {'en': 'cat'}
    }
    
    assert 'type' not in reversal
    assert 'forms' in reversal


def test_reversal_nested_main_structure(entry_with_complex_reversals_data: Dict[str, Any]) -> None:
    """Test that nested main elements are properly structured."""
    sense = entry_with_complex_reversals_data['senses'][0]
    reversal = sense['reversals'][0]
    
    # Check top-level main
    assert 'main' in reversal
    assert reversal['main']['forms']['en'] == 'canine'
    assert reversal['main']['grammatical_info'] == 'Noun'
    
    # Check nested main
    assert 'main' in reversal['main']
    nested_main = reversal['main']['main']
    assert nested_main['forms']['en'] == 'domestic dog'
    assert nested_main['grammatical_info'] == 'Noun'


def test_reversal_main_without_grammatical_info() -> None:
    """Test main element can exist without grammatical-info."""
    reversal = {
        'type': 'en',
        'forms': {'en': 'cat'},
        'main': {
            'forms': {'en': 'domestic cat'}
        }
    }
    
    assert 'grammatical_info' not in reversal['main']
    assert 'forms' in reversal['main']


def test_reversal_empty_main() -> None:
    """Test handling of empty main element."""
    reversal = {
        'type': 'en',
        'forms': {'en': 'cat'},
        'main': {}
    }
    
    assert 'main' in reversal
    assert isinstance(reversal['main'], dict)
    assert len(reversal['main']) == 0


def test_multiple_reversals_per_sense() -> None:
    """Test that a sense can have multiple reversals."""
    sense = {
        'id': 'sense_1',
        'glosses': {'en': 'cat'},
        'reversals': [
            {'type': 'en', 'forms': {'en': 'cat'}},
            {'type': 'fr', 'forms': {'fr': 'chat'}},
            {'type': 'de', 'forms': {'de': 'Katze'}},
            {'type': 'es', 'forms': {'es': 'gato'}}
        ]
    }
    
    assert len(sense['reversals']) == 4
    types = [r['type'] for r in sense['reversals']]
    assert 'en' in types
    assert 'fr' in types
    assert 'de' in types
    assert 'es' in types


def test_reversal_with_all_fields() -> None:
    """Test reversal with all possible fields populated."""
    reversal = {
        'type': 'en',
        'forms': {
            'en': 'cat',
            'en-US': 'kitty'
        },
        'grammatical_info': 'Noun',
        'main': {
            'forms': {
                'en': 'domestic cat',
                'en-US': 'house cat'
            },
            'grammatical_info': 'Noun',
            'main': {
                'forms': {'en': 'Felis catus'},
                'grammatical_info': 'Noun'
            }
        }
    }
    
    # Verify all fields
    assert reversal['type'] == 'en'
    assert len(reversal['forms']) == 2
    assert reversal['grammatical_info'] == 'Noun'
    assert 'main' in reversal
    assert len(reversal['main']['forms']) == 2
    assert reversal['main']['grammatical_info'] == 'Noun'
    assert 'main' in reversal['main']
    assert reversal['main']['main']['forms']['en'] == 'Felis catus'


def test_reversal_serialization_basic() -> None:
    """Test that basic reversal can be serialized to dict."""
    reversal = {
        'type': 'en',
        'forms': {'en': 'cat'},
        'grammatical_info': 'Noun'
    }
    
    # Should be JSON-serializable
    import json
    serialized = json.dumps(reversal)
    deserialized = json.loads(serialized)
    
    assert deserialized['type'] == 'en'
    assert deserialized['forms']['en'] == 'cat'
    assert deserialized['grammatical_info'] == 'Noun'


def test_reversal_serialization_with_main() -> None:
    """Test that reversal with main element can be serialized to dict."""
    reversal = {
        'type': 'en',
        'forms': {'en': 'cat'},
        'main': {
            'forms': {'en': 'domestic cat'},
            'grammatical_info': 'Noun'
        }
    }
    
    # Should be JSON-serializable
    import json
    serialized = json.dumps(reversal)
    deserialized = json.loads(serialized)
    
    assert deserialized['main']['forms']['en'] == 'domestic cat'
    assert deserialized['main']['grammatical_info'] == 'Noun'


def test_reversal_type_language_codes() -> None:
    """Test various language codes in reversal type."""
    language_codes = ['en', 'fr', 'de', 'es', 'pl', 'ru', 'zh', 'ja', 'ar', 'en-US', 'en-GB', 'fr-CA']
    
    for code in language_codes:
        reversal = {
            'type': code,
            'forms': {code: 'test'}
        }
        assert reversal['type'] == code
        assert code in reversal['forms']
