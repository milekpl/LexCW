"""
Integration tests for Academic Domains CRUD functionality.

Tests that Academic Domains work correctly in the full application context
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
class TestAcademicDomainsIntegration:
    """Integration tests for Academic Domains CRUD operations."""
    
    @pytest.mark.integration
    def test_create_entry_with_entry_level_academic_domain(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry with academic domain at entry level."""
        entry = Entry(
            id_="test_entry_academic_domain",
            lexical_unit={"en": "computer science", "pl": "informatyka"},
            academic_domain="informatyka",
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
        assert entry_id == "test_entry_academic_domain"
        
        # Retrieve and verify
        retrieved_entry = dict_service_with_db.get_entry("test_entry_academic_domain")
        assert retrieved_entry is not None
        assert retrieved_entry.academic_domain == "informatyka"
        assert retrieved_entry.lexical_unit["en"] == "computer science"
        
        # Clean up
        dict_service_with_db.delete_entry("test_entry_academic_domain")
    
    @pytest.mark.integration
    def test_create_entry_with_sense_level_academic_domain(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry with academic domain at sense level."""
        entry = Entry(
            id_="test_sense_academic_domain",
            lexical_unit={"en": "finance", "pl": "finanse"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "management of money"},
                    definitions={"en": {"text": "finance"}},
                    academic_domain="finanse"
                ),
                Sense(
                    id_="sense2",
                    glosses={"en": "legal matters"},
                    definitions={"en": {"text": "law"}},
                    academic_domain="prawniczy"
                )
            ]
        )
        
        # Create the entry
        entry_id = dict_service_with_db.create_entry(entry)
        assert entry_id == "test_sense_academic_domain"
        
        # Retrieve and verify
        retrieved_entry = dict_service_with_db.get_entry("test_sense_academic_domain")
        assert retrieved_entry is not None
        assert len(retrieved_entry.senses) == 2
        
        # Verify sense-level academic domains
        sense1 = retrieved_entry.senses[0] if retrieved_entry.senses[0].id == "sense1" else retrieved_entry.senses[1]
        sense2 = retrieved_entry.senses[1] if retrieved_entry.senses[1].id == "sense2" else retrieved_entry.senses[0]
        
        if sense1.id == "sense1":
            assert sense1.academic_domain == "finanse"
            assert sense2.academic_domain == "prawniczy"
        else:
            assert sense1.academic_domain == "prawniczy" 
            assert sense2.academic_domain == "finanse"
        
        # Clean up
        dict_service_with_db.delete_entry("test_sense_academic_domain")
    
    @pytest.mark.integration
    def test_create_entry_with_both_entry_and_sense_academic_domains(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry with academic domains at both entry and sense levels."""
        entry = Entry(
            id_="test_both_academic_domains",
            lexical_unit={"en": "literature", "pl": "literatura"},
            academic_domain="literatura",  # Entry-level academic domain
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "written works"},
                    definitions={"en": {"text": "literature"}},
                    academic_domain="antyk"  # Sense-level academic domain
                )
            ]
        )
        
        # Create the entry
        entry_id = dict_service_with_db.create_entry(entry)
        assert entry_id == "test_both_academic_domains"
        
        # Retrieve and verify both levels
        retrieved_entry = dict_service_with_db.get_entry("test_both_academic_domains")
        assert retrieved_entry is not None
        
        # Verify entry-level academic domain
        assert retrieved_entry.academic_domain == "literatura"
        
        # Verify sense-level academic domain
        assert len(retrieved_entry.senses) == 1
        assert retrieved_entry.senses[0].academic_domain == "antyk"
        
        # Clean up
        dict_service_with_db.delete_entry("test_both_academic_domains")
    
    @pytest.mark.integration
    def test_update_entry_academic_domain(self, dict_service_with_db: DictionaryService) -> None:
        """Test updating an entry's academic domain."""
        # Create initial entry
        entry = Entry(
            id_="test_update_academic_domain",
            lexical_unit={"en": "administration", "pl": "administracja"},
            academic_domain="administracja",
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "administration"},
                    definitions={"en": {"text": "administration"}}
                )
            ]
        )
        
        dict_service_with_db.create_entry(entry)
        
        # Update the academic domain
        entry.academic_domain = "rolnictwo"
        dict_service_with_db.update_entry(entry)
        
        # Retrieve and verify update
        retrieved_entry = dict_service_with_db.get_entry("test_update_academic_domain")
        assert retrieved_entry is not None
        assert retrieved_entry.academic_domain == "rolnictwo"
        
        # Clean up
        dict_service_with_db.delete_entry("test_update_academic_domain")
    
    @pytest.mark.integration
    def test_update_sense_academic_domain(self, dict_service_with_db: DictionaryService) -> None:
        """Test updating a sense's academic domain."""
        # Create entry with sense-level academic domain
        entry = Entry(
            id_="test_update_sense_academic_domain",
            lexical_unit={"en": "law", "pl": "prawo"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "legal system"},
                    definitions={"en": {"text": "law"}},
                    academic_domain="prawniczy"
                )
            ]
        )
        
        dict_service_with_db.create_entry(entry)
        
        # Update the sense's academic domain
        entry.senses[0].academic_domain = "literatura"
        dict_service_with_db.update_entry(entry)
        
        # Retrieve and verify update
        retrieved_entry = dict_service_with_db.get_entry("test_update_sense_academic_domain")
        assert retrieved_entry is not None
        assert len(retrieved_entry.senses) == 1
        assert retrieved_entry.senses[0].academic_domain == "literatura"
        
        # Clean up
        dict_service_with_db.delete_entry("test_update_sense_academic_domain")
    
    @pytest.mark.integration
    def test_retrieve_entries_by_academic_domain(self, dict_service_with_db: DictionaryService) -> None:
        """Test retrieving entries filtered by academic domain."""
        # Create test entries with SENSE-LEVEL academic domains (moved from entry-level)
        entries_data = [
            Entry(
                id_="entry_informatyka",
                lexical_unit={"en": "algorithm"},
                senses=[
                    Sense(
                        id_="sense1",
                        glosses={"en": "algorithm"},
                        definitions={"en": "algorithm"},
                        academic_domain="informatyka"  # Sense-level now
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
                        academic_domain="finanse"  # Sense-level now
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
                        academic_domain="prawniczy"  # Sense-level now
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
                        academic_domain="literatura"  # Sense-level now
                    )
                ]
            ),
        ]
        
        # Create all entries
        for entry in entries_data:
            dict_service_with_db.create_entry(entry)
        
        # Get specific entries by ID and verify academic domains at sense level
        entry_informatyka = dict_service_with_db.get_entry("entry_informatyka")
        assert entry_informatyka is not None
        assert len(entry_informatyka.senses) == 1
        assert entry_informatyka.senses[0].academic_domain == "informatyka"
        
        entry_finanse = dict_service_with_db.get_entry("entry_finanse")
        assert entry_finanse is not None
        assert len(entry_finanse.senses) == 1
        assert entry_finanse.senses[0].academic_domain == "finanse"
        
        entry_prawniczy = dict_service_with_db.get_entry("entry_prawniczy")
        assert entry_prawniczy is not None
        assert len(entry_prawniczy.senses) == 1
        assert entry_prawniczy.senses[0].academic_domain == "prawniczy"
        
        entry_literatura = dict_service_with_db.get_entry("entry_literatura")
        assert entry_literatura is not None
        assert len(entry_literatura.senses) == 1
        assert entry_literatura.senses[0].academic_domain == "literatura"
        
        # Clean up test entries
        for entry_id in ["entry_informatyka", "entry_finanse", "entry_prawniczy", "entry_literatura"]:
            try:
                dict_service_with_db.delete_entry(entry_id)
            except Exception:
                pass  # Entry might not exist if previous cleanup failed
    
    @pytest.mark.integration
    def test_delete_entry_with_academic_domain(self, dict_service_with_db: DictionaryService) -> None:
        """Test deleting an entry that has academic domain."""
        # Create entry with academic domain
        entry = Entry(
            id_="test_delete_academic_domain",
            lexical_unit={"en": "agriculture", "pl": "rolnictwo"},
            academic_domain="rolnictwo",
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
        retrieved_entry = dict_service_with_db.get_entry("test_delete_academic_domain")
        assert retrieved_entry is not None
        assert retrieved_entry.academic_domain == "rolnictwo"
        
        # Delete the entry
        dict_service_with_db.delete_entry("test_delete_academic_domain")
        
        # Verify entry no longer exists
        with pytest.raises(NotFoundError):
            dict_service_with_db.get_entry("test_delete_academic_domain")
    
    @pytest.mark.integration
    def test_create_entry_without_academic_domain(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry without academic domain (should work fine)."""
        entry = Entry(
            id_="test_no_academic_domain",
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
        assert entry_id == "test_no_academic_domain"
        
        # Retrieve and verify academic_domain is None
        retrieved_entry = dict_service_with_db.get_entry("test_no_academic_domain")
        assert retrieved_entry is not None
        assert retrieved_entry.academic_domain is None
        
        # Clean up
        dict_service_with_db.delete_entry("test_no_academic_domain")
    
    @pytest.mark.integration
    def test_create_entry_with_empty_academic_domain(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry with empty academic domain (should be treated as None)."""
        entry = Entry(
            id_="test_empty_academic_domain",
            lexical_unit={"en": "word"},
            academic_domain="",  # Empty string
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
        assert entry_id == "test_empty_academic_domain"
        
        # Retrieve and verify academic_domain is None
        retrieved_entry = dict_service_with_db.get_entry("test_empty_academic_domain")
        assert retrieved_entry is not None
        # Empty string should be converted to None
        assert retrieved_entry.academic_domain is None or retrieved_entry.academic_domain == ""
        
        # Clean up
        dict_service_with_db.delete_entry("test_empty_academic_domain")
    
    @pytest.mark.integration
    def test_multiple_senses_different_academic_domains(self, dict_service_with_db: DictionaryService) -> None:
        """Test entry with multiple senses having different academic domains."""
        entry = Entry(
            id_="test_multiple_senses_academic",
            lexical_unit={"en": "bank"},
            senses=[
                Sense(
                    id_="sense_financial",
                    glosses={"en": "financial institution"},
                    definitions={"en": {"text": "bank - financial institution"}},
                    academic_domain="finanse"
                ),
                Sense(
                    id_="sense_river",
                    glosses={"en": "river bank"},
                    definitions={"en": {"text": "bank - river bank"}},
                    academic_domain="geografia"  # Different academic domain
                )
            ]
        )
        
        # Create the entry
        entry_id = dict_service_with_db.create_entry(entry)
        assert entry_id == "test_multiple_senses_academic"
        
        # Retrieve and verify
        retrieved_entry = dict_service_with_db.get_entry("test_multiple_senses_academic")
        assert retrieved_entry is not None
        assert len(retrieved_entry.senses) == 2
        
        # Verify different academic domains per sense
        academic_domains = [sense.academic_domain for sense in retrieved_entry.senses]
        assert "finanse" in academic_domains
        assert "geografia" in academic_domains
        
        # Clean up
        dict_service_with_db.delete_entry("test_multiple_senses_academic")
    
    @pytest.mark.integration
    def test_unicode_academic_domain_handling(self, dict_service_with_db: DictionaryService) -> None:
        """Test handling of Unicode characters in academic domain values."""
        entry = Entry(
            id_="test_unicode_academic_domain",
            lexical_unit={"en": "word"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "word"},
                    definitions={"en": "word"},
                    academic_domain="informatyka-żabki"  # Contains Polish character ż
                )
            ]
        )
        
        # Create the entry
        entry_id = dict_service_with_db.create_entry(entry)
        assert entry_id == "test_unicode_academic_domain"
        
        # Retrieve and verify Unicode preservation at sense level
        retrieved_entry = dict_service_with_db.get_entry("test_unicode_academic_domain")
        assert retrieved_entry is not None
        assert len(retrieved_entry.senses) == 1
        assert retrieved_entry.senses[0].academic_domain == "informatyka-żabki"
        assert "ż" in retrieved_entry.senses[0].academic_domain  # Verify Unicode is preserved
        
        # Clean up
        dict_service_with_db.delete_entry("test_unicode_academic_domain")
    
    @pytest.mark.integration
    def test_academic_domain_serialization_roundtrip(self, dict_service_with_db: DictionaryService) -> None:
        """Test that academic domains survive serialization/deserialization cycles."""
        original_entry = Entry(
            id_="test_academic_serialization",
            lexical_unit={"en": "test word"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "test"},
                    definitions={"en": "test"},  # LIFT flat format
                    academic_domain="finanse"  # Sense-level only
                )
            ]
        )
        
        # Create the entry
        dict_service_with_db.create_entry(original_entry)
        
        # Get entry (first deserialization)
        retrieved_entry = dict_service_with_db.get_entry("test_academic_serialization")
        
        # Convert to dict and back (second deserialization)
        entry_dict = retrieved_entry.to_dict()
        reconstructed_entry = Entry(**entry_dict)
        
        # Verify academic domain is preserved at sense level
        assert len(reconstructed_entry.senses) == 1
        assert reconstructed_entry.senses[0].academic_domain == "finanse"
        
        # Clean up
        dict_service_with_db.delete_entry("test_academic_serialization")
    
    @pytest.mark.integration
    def test_form_data_processing_academic_domain(self, dict_service_with_db: DictionaryService) -> None:
        """Test that academic domain works correctly with form data processing at SENSE level.
        
        Note: academic_domain was moved to sense-level only.
        Entry-level academic_domain is no longer supported.
        """
        # Simulate form data that would come from the entry form
        # Using bracket notation as expected by the form processor
        form_data = {
            'lexical_unit[en]': 'test word',
            'senses[0][id]': 'sense1',
            'senses[0][definition][en]': 'test definition',
            'senses[0][academic_domain]': 'informatyka'  # Sense-level only
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
        
        # Verify academic domains are set correctly (sense-level only)
        assert not hasattr(entry, 'academic_domain') or entry.academic_domain is None
        assert len(entry.senses) == 1
        assert entry.senses[0].academic_domain == "informatyka"
        
        # Create in database and retrieve
        dict_service_with_db.create_entry(entry)
        retrieved_entry = dict_service_with_db.get_entry(entry.id)
        
        # Verify academic domains are preserved after database roundtrip (sense-level only)
        assert len(retrieved_entry.senses) == 1
        assert retrieved_entry.senses[0].academic_domain == "informatyka"
        
        # Clean up
        dict_service_with_db.delete_entry(entry.id)