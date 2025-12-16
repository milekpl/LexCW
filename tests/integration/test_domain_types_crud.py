"""
Integration tests for Domain Types CRUD functionality.

Tests that Domain Types work correctly in the full application context
including entry creation, retrieval, updating, and deletion at both 
entry-level and sense-level.
"""

from __future__ import annotations

import pytest
from app.models.entry import Entry
from app.models.sense import Sense
from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import NotFoundError


@pytest.mark.integration
class TestDomainTypesIntegration:
    """Integration tests for Domain Types CRUD operations."""
    
    @pytest.mark.integration
    def test_create_entry_with_entry_level_domain_type(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry with domain type at entry level."""
        entry = Entry(
            id_="test_entry_domain_type",
            lexical_unit={"en": "computer science", "pl": "informatyka"},
            domain_type="informatyka",
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "the study of computers"},
                    definitions={"en": {"text": "computer science"}}
                )
            ]
        )
        
        # Create the entry
        entry_id = dict_service_with_db.create_entry(entry)
        assert entry_id == "test_entry_domain_type"
        
        # Retrieve and verify
        retrieved_entry = dict_service_with_db.get_entry("test_entry_domain_type")
        assert retrieved_entry is not None
        assert retrieved_entry.domain_type == "informatyka"
        assert retrieved_entry.lexical_unit["en"] == "computer science"
        
        # Clean up
        dict_service_with_db.delete_entry("test_entry_domain_type")
    
    @pytest.mark.integration
    def test_create_entry_with_sense_level_domain_type(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry with domain type at sense level."""
        entry = Entry(
            id_="test_sense_domain_type",
            lexical_unit={"en": "finance", "pl": "finanse"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "management of money"},
                    definitions={"en": {"text": "finance"}},
                    domain_type="finanse"
                ),
                Sense(
                    id_="sense2",
                    glosses={"en": "legal matters"},
                    definitions={"en": {"text": "law"}},
                    domain_type="prawniczy"
                )
            ]
        )
        
        # Create the entry
        entry_id = dict_service_with_db.create_entry(entry)
        assert entry_id == "test_sense_domain_type"
        
        # Retrieve and verify
        retrieved_entry = dict_service_with_db.get_entry("test_sense_domain_type")
        assert retrieved_entry is not None
        assert len(retrieved_entry.senses) == 2
        
        # Verify sense-level domain types
        sense1 = retrieved_entry.senses[0] if retrieved_entry.senses[0].id == "sense1" else retrieved_entry.senses[1]
        sense2 = retrieved_entry.senses[1] if retrieved_entry.senses[1].id == "sense2" else retrieved_entry.senses[0]
        
        if sense1.id == "sense1":
            assert sense1.domain_type == "finanse"
            assert sense2.domain_type == "prawniczy"
        else:
            assert sense1.domain_type == "prawniczy" 
            assert sense2.domain_type == "finanse"
        
        # Clean up
        dict_service_with_db.delete_entry("test_sense_domain_type")
    
    @pytest.mark.integration
    def test_create_entry_with_both_entry_and_sense_domain_types(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry with domain types at both entry and sense levels."""
        entry = Entry(
            id_="test_both_domain_types",
            lexical_unit={"en": "literature", "pl": "literatura"},
            domain_type="literatura",  # Entry-level domain type
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "written works"},
                    definitions={"en": {"text": "literature"}},
                    domain_type="antyk"  # Sense-level domain type
                )
            ]
        )
        
        # Create the entry
        entry_id = dict_service_with_db.create_entry(entry)
        assert entry_id == "test_both_domain_types"
        
        # Retrieve and verify both levels
        retrieved_entry = dict_service_with_db.get_entry("test_both_domain_types")
        assert retrieved_entry is not None
        
        # Verify entry-level domain type
        assert retrieved_entry.domain_type == "literatura"
        
        # Verify sense-level domain type
        assert len(retrieved_entry.senses) == 1
        assert retrieved_entry.senses[0].domain_type == "antyk"
        
        # Clean up
        dict_service_with_db.delete_entry("test_both_domain_types")
    
    @pytest.mark.integration
    def test_update_entry_domain_type(self, dict_service_with_db: DictionaryService) -> None:
        """Test updating an entry's domain type."""
        # Create initial entry
        entry = Entry(
            id_="test_update_domain_type",
            lexical_unit={"en": "administration", "pl": "administracja"},
            domain_type="administracja",
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "administration"},
                    definitions={"en": {"text": "administration"}}
                )
            ]
        )
        
        dict_service_with_db.create_entry(entry)
        
        # Update the domain type
        entry.domain_type = "rolnictwo"
        dict_service_with_db.update_entry(entry)
        
        # Retrieve and verify update
        retrieved_entry = dict_service_with_db.get_entry("test_update_domain_type")
        assert retrieved_entry is not None
        assert retrieved_entry.domain_type == "rolnictwo"
        
        # Clean up
        dict_service_with_db.delete_entry("test_update_domain_type")
    
    @pytest.mark.integration
    def test_update_sense_domain_type(self, dict_service_with_db: DictionaryService) -> None:
        """Test updating a sense's domain type."""
        # Create entry with sense-level domain type
        entry = Entry(
            id_="test_update_sense_domain_type",
            lexical_unit={"en": "law", "pl": "prawo"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "legal system"},
                    definitions={"en": {"text": "law"}},
                    domain_type="prawniczy"
                )
            ]
        )
        
        dict_service_with_db.create_entry(entry)
        
        # Update the sense's domain type
        entry.senses[0].domain_type = "literatura"
        dict_service_with_db.update_entry(entry)
        
        # Retrieve and verify update
        retrieved_entry = dict_service_with_db.get_entry("test_update_sense_domain_type")
        assert retrieved_entry is not None
        assert len(retrieved_entry.senses) == 1
        assert retrieved_entry.senses[0].domain_type == "literatura"
        
        # Clean up
        dict_service_with_db.delete_entry("test_update_sense_domain_type")
    
    @pytest.mark.integration
    def test_retrieve_entries_by_domain_type(self, dict_service_with_db: DictionaryService) -> None:
        """Test retrieving entries filtered by domain type."""
        # Create test entries with SENSE-LEVEL domain types (moved from entry-level)
        entries_data = [
            Entry(
                id_="entry_informatyka",
                lexical_unit={"en": "algorithm"},
                senses=[
                    Sense(
                        id_="sense1",
                        glosses={"en": "algorithm"},
                        definitions={"en": "algorithm"},
                        domain_type="informatyka"  # Sense-level now
                    )
                ]
            ),
            Entry(
                id_="entry_finanse",
                lexical_unit={"en": "investment"},
                senses=[
                    Sense(
                        id_="sense1",
                        glosses={"en": "investment"},
                        definitions={"en": "investment"},
                        domain_type="finanse"  # Sense-level now
                    )
                ]
            ),
            Entry(
                id_="entry_prawniczy",
                lexical_unit={"en": "contract"},
                senses=[
                    Sense(
                        id_="sense1",
                        glosses={"en": "contract"},
                        definitions={"en": "contract"},
                        domain_type="prawniczy"  # Sense-level now
                    )
                ]
            ),
            Entry(
                id_="entry_literatura",
                lexical_unit={"en": "poem"},
                senses=[
                    Sense(
                        id_="sense1",
                        glosses={"en": "poem"},
                        definitions={"en": "poem"},
                        domain_type="literatura"  # Sense-level now
                    )
                ]
            ),
        ]
        
        # Create all entries
        for entry in entries_data:
            dict_service_with_db.create_entry(entry)
        
        # Get specific entries by ID and verify domain types at sense level
        entry_informatyka = dict_service_with_db.get_entry("entry_informatyka")
        assert entry_informatyka is not None
        assert len(entry_informatyka.senses) == 1
        assert entry_informatyka.senses[0].domain_type == "informatyka"
        
        entry_finanse = dict_service_with_db.get_entry("entry_finanse")
        assert entry_finanse is not None
        assert len(entry_finanse.senses) == 1
        assert entry_finanse.senses[0].domain_type == "finanse"
        
        entry_prawniczy = dict_service_with_db.get_entry("entry_prawniczy")
        assert entry_prawniczy is not None
        assert len(entry_prawniczy.senses) == 1
        assert entry_prawniczy.senses[0].domain_type == "prawniczy"
        
        entry_literatura = dict_service_with_db.get_entry("entry_literatura")
        assert entry_literatura is not None
        assert len(entry_literatura.senses) == 1
        assert entry_literatura.senses[0].domain_type == "literatura"
        
        # Clean up test entries
        for entry_id in ["entry_informatyka", "entry_finanse", "entry_prawniczy", "entry_literatura"]:
            try:
                dict_service_with_db.delete_entry(entry_id)
            except Exception:
                pass  # Entry might not exist if previous cleanup failed
    
    @pytest.mark.integration
    def test_delete_entry_with_domain_type(self, dict_service_with_db: DictionaryService) -> None:
        """Test deleting an entry that has domain type."""
        # Create entry with domain type
        entry = Entry(
            id_="test_delete_domain_type",
            lexical_unit={"en": "agriculture", "pl": "rolnictwo"},
            domain_type="rolnictwo",
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "agriculture"},
                    definitions={"en": {"text": "agriculture"}}
                )
            ]
        )
        
        dict_service_with_db.create_entry(entry)
        
        # Verify entry exists
        retrieved_entry = dict_service_with_db.get_entry("test_delete_domain_type")
        assert retrieved_entry is not None
        assert retrieved_entry.domain_type == "rolnictwo"
        
        # Delete the entry
        dict_service_with_db.delete_entry("test_delete_domain_type")
        
        # Verify entry no longer exists
        with pytest.raises(NotFoundError):
            dict_service_with_db.get_entry("test_delete_domain_type")
    
    @pytest.mark.integration
    def test_create_entry_without_domain_type(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry without domain type (should work fine)."""
        entry = Entry(
            id_="test_no_domain_type",
            lexical_unit={"en": "word"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "word"},
                    definitions={"en": {"text": "word"}}
                )
            ]
        )
        
        # Create the entry
        entry_id = dict_service_with_db.create_entry(entry)
        assert entry_id == "test_no_domain_type"
        
        # Retrieve and verify domain_type is None
        retrieved_entry = dict_service_with_db.get_entry("test_no_domain_type")
        assert retrieved_entry is not None
        assert retrieved_entry.domain_type is None
        
        # Clean up
        dict_service_with_db.delete_entry("test_no_domain_type")
    
    @pytest.mark.integration
    def test_create_entry_with_empty_domain_type(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry with empty domain type (should be treated as None)."""
        entry = Entry(
            id_="test_empty_domain_type",
            lexical_unit={"en": "word"},
            domain_type="",  # Empty string
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "word"},
                    definitions={"en": {"text": "word"}}
                )
            ]
        )
        
        # Create the entry
        entry_id = dict_service_with_db.create_entry(entry)
        assert entry_id == "test_empty_domain_type"
        
        # Retrieve and verify domain_type is None
        retrieved_entry = dict_service_with_db.get_entry("test_empty_domain_type")
        assert retrieved_entry is not None
        # Empty string should be converted to None
        assert retrieved_entry.domain_type is None or retrieved_entry.domain_type == ""
        
        # Clean up
        dict_service_with_db.delete_entry("test_empty_domain_type")
    
    @pytest.mark.integration
    def test_multiple_senses_different_domain_types(self, dict_service_with_db: DictionaryService) -> None:
        """Test entry with multiple senses having different domain types."""
        entry = Entry(
            id_="test_multiple_senses_domain_types",
            lexical_unit={"en": "bank"},
            senses=[
                Sense(
                    id_="sense_financial",
                    glosses={"en": "financial institution"},
                    definitions={"en": {"text": "bank - financial institution"}},
                    domain_type="finanse"
                ),
                Sense(
                    id_="sense_river",
                    glosses={"en": "river bank"},
                    definitions={"en": {"text": "bank - river bank"}},
                    domain_type="geografia"  # Different domain type
                )
            ]
        )
        
        # Create the entry
        entry_id = dict_service_with_db.create_entry(entry)
        assert entry_id == "test_multiple_senses_domain_types"
        
        # Retrieve and verify
        retrieved_entry = dict_service_with_db.get_entry("test_multiple_senses_domain_types")
        assert retrieved_entry is not None
        assert len(retrieved_entry.senses) == 2
        
        domain_types = [sense.domain_type for sense in retrieved_entry.senses]
        assert "finanse" in domain_types
        assert "geografia" in domain_types
        
        # Clean up
        dict_service_with_db.delete_entry("test_multiple_senses_domain_types")
    
    @pytest.mark.integration
    def test_unicode_domain_type_handling(self, dict_service_with_db: DictionaryService) -> None:
        """Test handling of Unicode characters in domain type values."""
        entry = Entry(
            id_="test_unicode_domain_type",
            lexical_unit={"en": "word"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "word"},
                    definitions={"en": "word"},
                    domain_type="informatyka-żabki"  # Contains Polish character ż
                )
            ]
        )
        
        # Create the entry
        entry_id = dict_service_with_db.create_entry(entry)
        assert entry_id == "test_unicode_domain_type"
        
        # Retrieve and verify Unicode preservation at sense level
        retrieved_entry = dict_service_with_db.get_entry("test_unicode_domain_type")
        assert retrieved_entry is not None
        assert len(retrieved_entry.senses) == 1
        assert retrieved_entry.senses[0].domain_type == "informatyka-żabki"
        assert 'ż' in (retrieved_entry.senses[0].domain_type or '')
        
        # Clean up
        dict_service_with_db.delete_entry("test_unicode_domain_type")
    
    @pytest.mark.integration
    def test_domain_type_serialization_roundtrip(self, dict_service_with_db: DictionaryService) -> None:
        """Test that domain types survive serialization/deserialization cycles."""
        original_entry = Entry(
            id_="test_domain_types_serialization",
            lexical_unit={"en": "test word"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "test"},
                    definitions={"en": "test"},  # LIFT flat format
                    domain_type="finanse"  # Sense-level only
                )
            ]
        )
        
        # Create the entry
        dict_service_with_db.create_entry(original_entry)
        
        # Get entry (first deserialization)
        retrieved_entry = dict_service_with_db.get_entry("test_domain_types_serialization")
        
        # Convert to dict and back (second deserialization)
        entry_dict = retrieved_entry.to_dict()
        reconstructed_entry = Entry(**entry_dict)
        
        # Verify domain type is preserved at sense level
        assert len(reconstructed_entry.senses) == 1
        assert reconstructed_entry.senses[0].domain_type == "finanse"
        
        # Clean up
        dict_service_with_db.delete_entry("test_domain_types_serialization")
    
    @pytest.mark.integration
    def test_form_data_processing_domain_type(self, dict_service_with_db: DictionaryService) -> None:
        """Test that domain type works correctly with form data processing at SENSE level.
        
        Note: domain_type was moved to sense-level only.
        Entry-level domain_type is no longer supported.
        """
        # Simulate form data that would come from the entry form
        # Using bracket notation as expected by the form processor
        form_data = {
            'lexical_unit[en]': 'test word',
            'senses[0][id]': 'sense1',
            'senses[0][definition][en]': 'test definition',
            'senses[0][domain_type]': 'informatyka'  # Sense-level only
        }
        
        from app.utils.multilingual_form_processor import (
            process_entry_form_data,
            process_senses_form_data
        )
        
        # Process form data (entry and senses separately)
        entry_data = process_entry_form_data(form_data)
        senses_data = process_senses_form_data(form_data)
        
        # Create entry from processed data
        entry = Entry(lexical_unit=entry_data['lexical_unit'])
        
        # Create senses from processed data
        if senses_data:
            from app.models.sense import Sense
            entry.senses = [Sense(**sense_data) for sense_data in senses_data]
        
        # Verify domain types are set correctly (sense-level only)
        assert entry.domain_type is None
        assert len(entry.senses) == 1
        assert entry.senses[0].domain_type == "informatyka"
        
        # Create in database and retrieve
        dict_service_with_db.create_entry(entry)
        retrieved_entry = dict_service_with_db.get_entry(entry.id)
        
        # Verify domain types are preserved after database roundtrip (sense-level only)
        assert len(retrieved_entry.senses) == 1
        assert retrieved_entry.senses[0].domain_type == "informatyka"
        
        # Clean up
        dict_service_with_db.delete_entry(entry.id)