"""
Integration test to reproduce and fix the string-as-list bug.

When usage_type is a string instead of a list, iterating over it
creates individual character traits instead of a single value trait.
"""

import pytest
from app.models.entry import Entry
from app.models.sense import Sense
from app.services.dictionary_service import DictionaryService


@pytest.mark.integration
def test_usage_type_string_incorrectly_split_into_characters(
    dict_service_with_db: DictionaryService
) -> None:
    """
    Regression test: usage_type as string should be converted to list.
    
    Previously, when usage_type was accidentally set as a string,
    it would be iterated character-by-character during serialization.
    Now the Sense model defensively converts strings to single-element lists.
    """
    # Create entry with usage_type as STRING (defensive code should handle this)
    entry_with_string = Entry(
        id_='bug_test_string_usage',
        lexical_unit={'en': 'test'},
        senses=[
            Sense(
                definitions={'en': {'text': 'test'}},
                usage_type='przestarzale'  # STRING - model should convert to ['przestarzale']
            )
        ]
    )
    
    # Save to database
    dict_service_with_db.create_entry(entry_with_string, skip_validation=True)
    
    # Retrieve and check - should be converted to list with single element
    retrieved = dict_service_with_db.get_entry('bug_test_string_usage')
    
    # Fixed: string should be converted to single-element list
    print(f"Retrieved usage_type: {retrieved.senses[0].usage_type}")
    assert retrieved.senses[0].usage_type == ['przestarzale'], \
        f"Expected ['przestarzale'], got {retrieved.senses[0].usage_type}"
    
    # Cleanup
    dict_service_with_db.delete_entry('bug_test_string_usage')


@pytest.mark.integration
def test_usage_type_as_list_works_correctly(
    dict_service_with_db: DictionaryService
) -> None:
    """
    Test that usage_type as a list works correctly.
    
    This is the correct implementation.
    """
    # Create entry with usage_type as LIST (correct)
    entry_correct = Entry(
        id_='correct_test_list_usage',
        lexical_unit={'en': 'test'},
        senses=[
            Sense(
                definitions={'en': {'text': 'test'}},
                usage_type=['przestarzale']  # LIST - CORRECT
            )
        ]
    )
    
    # Save to database
    dict_service_with_db.create_entry(entry_correct, skip_validation=True)
    
    # Retrieve and check
    retrieved = dict_service_with_db.get_entry('correct_test_list_usage')
    
    # Correct: list with single value
    print(f"Retrieved usage_type: {retrieved.senses[0].usage_type}")
    assert retrieved.senses[0].usage_type == ['przestarzale']
    
    # Cleanup
    dict_service_with_db.delete_entry('correct_test_list_usage')
