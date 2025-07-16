#!/usr/bin/env python3
"""
Integration tests for etymology UI functionality.
Tests etymology editing with real database and API integration.
"""

import pytest
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService


class TestEtymologyAPISupport:
    """Test API support for etymology management."""

    @pytest.mark.integration
    def test_api_entry_creation_with_etymologies(self, basex_test_connector):
        """Test creating entries with etymologies via API."""
        dict_service = DictionaryService(basex_test_connector)
        entry_data = {
            "lexical_unit": {"en": "water"},
            "senses": [
                {
                    "id": "sense-1",
                    "definition": {"en": "transparent liquid"}
                }
            ],
            "etymologies": [
                {
                    "type": "inheritance",
                    "source": "Old English", 
                    "form": {"lang": "ang", "text": "wæter"},
                    "gloss": {"lang": "en", "text": "water"}
                }
            ]
        }
        entry = Entry.from_dict(entry_data)
        result_id = dict_service.create_entry(entry)
        assert result_id is not None
        assert len(entry.etymologies) == 1
        assert entry.etymologies[0].type == "inheritance"

    @pytest.mark.integration
    def test_api_entry_update_with_etymologies(self, basex_test_connector):
        """Test updating entry etymologies via API."""
        dict_service = DictionaryService(basex_test_connector)
        # Create entry
        entry = Entry(
            lexical_unit={"en": "book"}, 
            senses=[{"id": "sense-1", "definition": {"en": "printed work"}}]
        )
        entry_id = dict_service.create_entry(entry)
        # Get the entry from database to ensure we have the correct object
        entry = dict_service.get_entry(entry_id)
        # Update with etymologies
        entry.add_etymology(
            etymology_type="borrowing",
            source="Old French",
            form_lang="fro", 
            form_text="livre",
            gloss_lang="en",
            gloss_text="book"
        )
        entry.add_etymology(
            etymology_type="inheritance", 
            source="Latin",
            form_lang="la",
            form_text="liber", 
            gloss_lang="en",
            gloss_text="book, writing"
        )
        dict_service.update_entry(entry)
        # Verify update
        updated_entry = dict_service.get_entry(entry_id)
        assert len(updated_entry.etymologies) == 2


class TestEtymologyRangesIntegration:
    """Test integration with LIFT ranges for etymology types."""
    @pytest.mark.integration
    def test_etymology_types_from_ranges(self, basex_test_connector):
        """Test that etymology types can be retrieved from ranges."""
        dict_service = DictionaryService(basex_test_connector)
        ranges = dict_service.get_ranges()
        assert isinstance(ranges, dict)


class TestEtymologyLifecycle:
    """Test complete etymology lifecycle operations."""
    @pytest.mark.integration
    def test_add_etymology_to_existing_entry(self, basex_test_connector):
        """Test adding an etymology to an existing entry."""
        dict_service = DictionaryService(basex_test_connector)
        entry = Entry(
            lexical_unit={"en": "house"}, 
            senses=[{"id": "sense-1", "definition": {"en": "dwelling place"}}]
        )
        entry_id = dict_service.create_entry(entry)
        entry = dict_service.get_entry(entry_id)
        entry.add_etymology(
            etymology_type="inheritance",
            source="Old English",
            form_lang="ang",
            form_text="hūs", 
            gloss_lang="en",
            gloss_text="house"
        )
        dict_service.update_entry(entry)
        updated = dict_service.get_entry(entry_id)
        assert len(updated.etymologies) == 1
        assert updated.etymologies[0].type == "inheritance"
        assert updated.etymologies[0].source == "Old English"
    @pytest.mark.integration
    def test_remove_etymology_from_entry(self, basex_test_connector):
        """Test removing an etymology from an entry."""
        dict_service = DictionaryService(basex_test_connector)
        entry = Entry(
            lexical_unit={"en": "test"}, 
            senses=[{"id": "sense-1", "definition": {"en": "test word"}}],
            etymologies=[
                {
                    "type": "inheritance",
                    "source": "keep_source",
                    "form": {"lang": "en", "text": "keep_form"},
                    "gloss": {"lang": "en", "text": "keep_gloss"}
                },
                {
                    "type": "borrowing", 
                    "source": "remove_source",
                    "form": {"lang": "en", "text": "remove_form"},
                    "gloss": {"lang": "en", "text": "remove_gloss"}
                }
            ]
        )
        entry_id = dict_service.create_entry(entry)
        entry = dict_service.get_entry(entry_id)
        entry.etymologies = [e for e in entry.etymologies if e.source != "remove_source"]
        dict_service.update_entry(entry)
        updated = dict_service.get_entry(entry_id)
        assert len(updated.etymologies) == 1
        assert updated.etymologies[0].source == "keep_source"
    @pytest.mark.integration
    def test_modify_etymology_in_entry(self, basex_test_connector):
        """Test modifying an existing etymology."""
        dict_service = DictionaryService(basex_test_connector)
        entry = Entry(
            lexical_unit={"en": "test"},
            senses=[{"id": "sense_1", "definition": {"en": "test definition"}}],
            etymologies=[{
                "type": "borrowing",
                "source": "old_source", 
                "form": {"lang": "en", "text": "old_form"},
                "gloss": {"lang": "en", "text": "old_gloss"}
            }]
        )
        entry_id = dict_service.create_entry(entry)
        entry = dict_service.get_entry(entry_id)
        entry.etymologies[0].type = "inheritance"
        entry.etymologies[0].source = "new_source"
        # Get first form/gloss language and update text
        form_lang = list(entry.etymologies[0].form.keys())[0]
        gloss_lang = list(entry.etymologies[0].gloss.keys())[0]
        entry.etymologies[0].form[form_lang]["text"] = "new_form"
        entry.etymologies[0].gloss[gloss_lang]["text"] = "new_gloss"
        dict_service.update_entry(entry)
        updated = dict_service.get_entry(entry_id)
        assert len(updated.etymologies) == 1
        assert updated.etymologies[0].type == "inheritance"
        assert updated.etymologies[0].source == "new_source"
        assert updated.etymologies[0].form[form_lang]["text"] == "new_form"
        assert updated.etymologies[0].gloss[gloss_lang]["text"] == "new_gloss", f"Gloss mismatch: {updated.etymologies[0].gloss}"

