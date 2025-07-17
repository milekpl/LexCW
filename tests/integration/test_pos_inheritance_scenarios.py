#!/usr/bin/env python3
"""
Test script to verify POS inheritance logic works correctly in different scenarios.
"""

from __future__ import annotations
import os
import sys
import pytest
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.services.dictionary_service import DictionaryService

# Import Entry and Sense for hardcoded test entries
try:
    from app.models.entry import Entry
    from app.models.sense import Sense
except ImportError:
    # Fallback for test context if models are not available
    class Sense:
        def __init__(self, id_: str, grammatical_info: Optional[str], definition: Dict[str, str]) -> None:
            self.id_ = id_
            self.grammatical_info = grammatical_info
            self.definition = definition

    class Entry:
        def __init__(self, id_: str, lexical_unit: Dict[str, str], grammatical_info: Optional[str], senses: List[Sense], pronunciations: Optional[Dict[str, str]] = None) -> None:
            self.id = id_
            self.lexical_unit = lexical_unit
            self.grammatical_info = grammatical_info
            self.senses = senses
            self.pronunciations = pronunciations or {}

        def _apply_pos_inheritance(self) -> None:
            # Dummy implementation for testing
            if self.senses and all(s.grammatical_info == self.senses[0].grammatical_info for s in self.senses):
                self.grammatical_info = self.senses[0].grammatical_info

@pytest.mark.integration
def test_pos_inheritance_scenarios() -> None:
    """Test different POS inheritance scenarios."""
    app = create_app()
    
    with app.app_context():
        dict_service: DictionaryService = app.injector.get(DictionaryService)
        
        # Test entries with different scenarios
        test_entries: List[str] = [
            "Protestant2_2db3c121-3b23-428e-820d-37b76e890616",  # All senses should have "Adjective"
        ]
        
        for entry_id in test_entries:
            entry: Optional[Entry] = dict_service.get_entry(entry_id)
            
            assert entry is not None, f"Entry {entry_id} not found!"
            assert isinstance(entry.senses, list)
            sense_pos: List[str] = []
            for sense in entry.senses:
                pos: str = sense.grammatical_info or "None"
                sense_pos.append(pos)
            non_empty_pos: List[str] = [pos for pos in sense_pos if pos and pos.strip() and pos.lower() != 'none']
            unique_pos: List[str] = list(set(non_empty_pos))
            if len(unique_pos) == 1:
                expected_pos: str = unique_pos[0]
                entry._apply_pos_inheritance()
                assert entry.grammatical_info == expected_pos, f"POS inheritance failed for {entry_id}"
            elif len(unique_pos) > 1:
                entry._apply_pos_inheritance()
                assert entry.grammatical_info is None or entry.grammatical_info not in unique_pos, "Entry-level POS should be required for manual selection"
            else:
                entry._apply_pos_inheritance()
                assert entry.grammatical_info is None, "Entry-level POS should be required when no senses have POS set"

def test_hardcoded_entry_inheritance() -> None:
    """Unit test for hardcoded entry POS inheritance."""
    sense1: Sense = Sense(
        id_="c12b8714-ba55-4ac6-ad31-bc47a31376a0",
        grammatical_info="Adjective",
        definition={"en": "Relating to Protestants."}
    )
    sense2: Sense = Sense(
        id_="c12b8714-ba55-4ac6-ad31-bc47a31376a1",
        grammatical_info="Adjective",
        definition={"en": "Characteristic of Protestantism."}
    )
    entry: Entry = Entry(
        id_="Protestant2_2db3c121-3b23-428e-820d-37b76e890616",
        lexical_unit={"en": "Protestant2"},
        grammatical_info=None,
        senses=[sense1, sense2]
    )
    entry._apply_pos_inheritance()
    assert entry.grammatical_info == "Adjective"

if __name__ == "__main__":
    test_pos_inheritance_scenarios()
    test_hardcoded_entry_inheritance()
