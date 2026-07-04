"""
Unit tests for Subentry Discovery scan in DictionaryService.
"""

import pytest
from unittest.mock import MagicMock
from app.services.dictionary_service import DictionaryService


class TestSubentryDiscovery:

    def test_discover_subentries_basic(self):
        """Test that subentry discovery identifies orphaned phrase entries containing main headwords."""
        mock_connector = MagicMock()
        mock_connector.database = "dictionary"

        # Mock XQuery output returning 2 entries:
        # Entry 1: main entry "head" (stem, 0 rels)
        # Entry 2: orphaned phrase "lose one's head" (phrase, 0 rels)
        raw_xquery_output = (
            "entry_1|||head|||head|||n|||stem|||0|||1|||the head of a person|||head|||s1\n"
            "entry_2|||lose one's head|||lose one's head|||v|||phrase|||0|||1|||to become irrational or confused|||lose|||s2"
        )
        mock_connector.execute_query.return_value = raw_xquery_output

        service = DictionaryService(db_connector=mock_connector)
        result = service.discover_subentries(min_confidence=0.1)

        assert result is not None
        assert "candidates" in result
        candidates = result["candidates"]
        assert len(candidates) == 1

        c = candidates[0]
        assert c["scan_mode"] == "subentry"
        assert c["source"]["entry_id"] == "entry_1"
        assert c["source"]["headword"] == "head"
        assert c["target"]["entry_id"] == "entry_2"
        assert c["target"]["headword"] == "lose one's head"
        assert "head" in c["target"]["headword"].lower()

    def test_discover_subentries_ignores_linked(self):
        """Test that phrase entries with existing relation links are skipped."""
        mock_connector = MagicMock()
        mock_connector.database = "dictionary"

        # Entry 2 already has 1 relation (rel_count=1)
        raw_xquery_output = (
            "entry_1|||heart|||heart|||n|||stem|||0|||1|||human heart organ|||heart|||s1\n"
            "entry_2|||take to heart|||take to heart|||v|||phrase|||1|||1|||to take seriously|||take|||s2"
        )
        mock_connector.execute_query.return_value = raw_xquery_output

        service = DictionaryService(db_connector=mock_connector)
        result = service.discover_subentries(min_confidence=0.1)

        assert len(result["candidates"]) == 0
