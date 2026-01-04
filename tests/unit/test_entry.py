"""
Unit tests for Entry model.
"""

import pytest
from app.models.entry import Entry


def test_convert_trait():
    """Entry should support trait conversion."""
    entry = Entry(
        id='test-1',
        lexical_unit={'en': 'test'},
        traits={'part-of-speech': 'verb', 'transitivity': 'transitive'}
    )

    # Convert verb to phrasal-verb
    entry.convert_trait('part-of-speech', 'verb', 'phrasal-verb')

    assert entry.traits['part-of-speech'] == 'phrasal-verb'
    assert entry.traits['transitivity'] == 'transitive'  # Unchanged


def test_convert_trait_raises_on_missing_trait():
    """Entry should raise ValueError when trait type doesn't exist."""
    entry = Entry(
        id='test-1',
        lexical_unit={'en': 'test'},
        traits={'part-of-speech': 'verb'}
    )

    with pytest.raises(ValueError, match="Trait 'nonexistent-trait' does not have value 'verb'"):
        entry.convert_trait('nonexistent-trait', 'verb', 'new-value')


def test_convert_trait_raises_on_wrong_value():
    """Entry should raise ValueError when old_value doesn't match."""
    entry = Entry(
        id='test-1',
        lexical_unit={'en': 'test'},
        traits={'part-of-speech': 'verb'}
    )

    with pytest.raises(ValueError, match="Trait 'part-of-speech' does not have value 'noun'"):
        entry.convert_trait('part-of-speech', 'noun', 'verb')
