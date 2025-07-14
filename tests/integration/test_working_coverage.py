"""
Working Coverage Tests for Core Stable Components

This module contains working tests to increase coverage on database connectors,
search integration, and parser modules.
"""
from __future__ import annotations

import pytest
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.models.sense import Sense

def test_dictionary_service_with_real_basex(dict_service_with_db: DictionaryService) -> None:
    """Integration: Test DictionaryService with a real, isolated BaseX database."""
    # Add an entry
    entry = Entry(
        id_="coverage_test",
        lexical_unit={"en": "test", "pl": "test"},
        senses=[
            Sense(
                id_="sense_1",
                glosses={"en": {"text": "test gloss"}},
                definitions={"en": {"text": "test definition"}}
            )
        ]
    )
    dict_service_with_db.create_entry(entry)
    # Retrieve the entry
    retrieved = dict_service_with_db.get_entry("coverage_test")
    assert retrieved.id == "coverage_test"
    # Search for the entry
    results, total = dict_service_with_db.search_entries("test")
    assert any(e.id == "coverage_test" for e in results)
    assert total >= 1
    # Count entries
    count = dict_service_with_db.get_entry_count()
    assert count >= 1
    # Delete the entry
    dict_service_with_db.delete_entry("coverage_test")
    with pytest.raises(Exception):
        dict_service_with_db.get_entry("coverage_test")
    print("DictionaryService with real BaseX: OK")

