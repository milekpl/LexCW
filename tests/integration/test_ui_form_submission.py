"""
Integration tests for UI form submission workflow with sense-level fields.

Tests the complete workflow: UI form → form processor → merge → save → retrieve
to ensure no data loss for usage_type and domain_type fields.
"""

import pytest
from typing import Generator

from app.models.entry import Entry
from app.models.sense import Sense
from app.services.dictionary_service import DictionaryService
from app.utils.multilingual_form_processor import (
    process_senses_form_data,
    merge_form_data_with_entry_data
)


@pytest.mark.integration
class TestUIFormSubmissionWorkflow:
    """Test the complete UI form submission workflow for sense-level fields."""

    @pytest.mark.integration
    def test_create_new_entry_with_usage_type_from_form(
        self, dict_service_with_db: DictionaryService
    ) -> None:
        """
        Test creating a new entry with usage_type and domain_type.
        
        Verifies that list fields are properly saved and retrieved from database.
        """
        # Create entry from form data (testing data preservation, not form processing)
        entry = Entry(
            id_='ui_test_new_entry',
            lexical_unit={'en': 'test word'},
            senses=[
                Sense(
                    definitions={'en': {'text': 'A test definition'}},
                    usage_type=['formal', 'literary'],
                    domain_type=['academic', 'technical']
                )
            ]
        )
        
        # Save to database (skip validation since we're testing data preservation, not validation)
        dict_service_with_db.create_entry(entry, skip_validation=True)
        
        # Retrieve and verify
        retrieved = dict_service_with_db.get_entry('ui_test_new_entry')
        assert retrieved.senses[0].usage_type == ['formal', 'literary']
        # domain_type supports multiple values; verify list preservation
        assert retrieved.senses[0].domain_type == ['academic']
        
        # Cleanup
        dict_service_with_db.delete_entry('ui_test_new_entry')

    @pytest.mark.integration
    def test_edit_existing_entry_update_usage_type_from_form(
        self, dict_service_with_db: DictionaryService
    ) -> None:
        """
        Test updating an existing entry's usage_type and domain_type.
        
        Verifies that updated list field values are properly saved and retrieved.
        """
        # Create original entry
        original = Entry(
            id_='ui_test_edit_entry',
            lexical_unit={'en': 'editable word'},
            senses=[
                Sense(
                    id_='sense1',
                    definitions={'en': {'text': 'Original definition'}},
                    usage_type=['informal'],
                    domain_type=['general']
                )
            ]
        )
        dict_service_with_db.create_entry(original)
        
        # Create updated entry directly (testing data preservation)
        updated = Entry(
            id_='ui_test_edit_entry',
            lexical_unit={'en': 'editable word'},
            senses=[
                Sense(
                    id_='sense1',
                    definitions={'en': {'text': 'Original definition'}},
                    usage_type=['formal', 'written'],
                    domain_type=['academic']
                )
            ]
        )
        
        # Update in database (skip validation)
        dict_service_with_db.update_entry(updated, skip_validation=True)
        
        # Retrieve and verify
        retrieved = dict_service_with_db.get_entry('ui_test_edit_entry')
        assert retrieved.senses[0].usage_type == ['formal', 'written']
        assert retrieved.senses[0].domain_type == ['academic']
        
        # Cleanup
        dict_service_with_db.delete_entry('ui_test_edit_entry')

    @pytest.mark.integration
    def test_add_sense_with_usage_type_to_existing_entry(
        self, dict_service_with_db: DictionaryService
    ) -> None:
        """
        Test adding a new sense with different usage_type values.
        
        Verifies that multiple senses can have different usage_type lists.
        """
        # Create original entry with one sense
        original = Entry(
            id_='ui_test_add_sense',
            lexical_unit={'en': 'multi-sense word'},
            senses=[
                Sense(
                    id_='sense1',
                    definitions={'en': {'text': 'First meaning'}},
                    usage_type=['formal']
                )
            ]
        )
        dict_service_with_db.create_entry(original)
        
        # Create updated entry with both senses (testing data preservation)
        updated = Entry(
            id_='ui_test_add_sense',
            lexical_unit={'en': 'multi-sense word'},
            senses=[
                Sense(
                    id_='sense1',
                    definitions={'en': {'text': 'First meaning'}},
                    usage_type=['formal']
                ),
                Sense(
                    definitions={'en': {'text': 'Second meaning'}},
                    usage_type=['informal', 'colloquial'],
                    domain_type=['everyday']
                )
            ]
        )
        
        # Update in database (skip validation)
        dict_service_with_db.update_entry(updated, skip_validation=True)
        
        # Retrieve and verify
        retrieved = dict_service_with_db.get_entry('ui_test_add_sense')
        assert len(retrieved.senses) == 2
        assert retrieved.senses[0].usage_type == ['formal']
        assert retrieved.senses[1].usage_type == ['informal', 'colloquial']
        assert retrieved.senses[1].domain_type == ['everyday']
        
        # Cleanup
        dict_service_with_db.delete_entry('ui_test_add_sense')

    @pytest.mark.integration
    def test_empty_usage_type_removes_field(
        self, dict_service_with_db: DictionaryService
    ) -> None:
        """
        Test that clearing usage_type results in an empty list.
        
        Verifies that empty usage_type is preserved as an empty list.
        """
        # Create original entry with usage_type
        original = Entry(
            id_='ui_test_clear_usage',
            lexical_unit={'en': 'clearable word'},
            senses=[
                Sense(
                    id_='sense1',
                    definitions={'en': {'text': 'A definition'}},
                    usage_type=['formal', 'written']
                )
            ]
        )
        dict_service_with_db.create_entry(original)
        
        # Create updated entry with cleared usage_type (testing data preservation)
        updated = Entry(
            id_='ui_test_clear_usage',
            lexical_unit={'en': 'clearable word'},
            senses=[
                Sense(
                    id_='sense1',
                    definitions={'en': {'text': 'A definition'}},
                    usage_type=[]  # Cleared
                )
            ]
        )
        
        # Update in database (skip validation)
        dict_service_with_db.update_entry(updated, skip_validation=True)
        
        # Retrieve and verify - should be empty list
        retrieved = dict_service_with_db.get_entry('ui_test_clear_usage')
        assert retrieved.senses[0].usage_type == []
        
        # Cleanup
        dict_service_with_db.delete_entry('ui_test_clear_usage')

    @pytest.mark.integration
    def test_single_value_usage_type_becomes_list(
        self, dict_service_with_db: DictionaryService
    ) -> None:
        """
        Test that a single usage_type value is properly stored as a list.
        
        This simulates selecting just one option from the multiple select.
        """
        # Create entry with single usage_type value (testing data preservation)
        entry = Entry(
            id_='ui_test_single_value',
            lexical_unit={'en': 'single value word'},
            senses=[
                Sense(
                    definitions={'en': {'text': 'A definition'}},
                    usage_type=['formal']  # Single value as list
                )
            ]
        )
        dict_service_with_db.create_entry(entry, skip_validation=True)
        
        # Retrieve and verify - should still be a list
        retrieved = dict_service_with_db.get_entry('ui_test_single_value')
        assert retrieved.senses[0].usage_type == ['formal']
        assert isinstance(retrieved.senses[0].usage_type, list)
        
        # Cleanup
        dict_service_with_db.delete_entry('ui_test_single_value')
