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
        assert c["level"] == "entry"
        assert c["relation_type"] == "_component-lexeme"
        assert c["complex_form_type"] == "Phrase"
        assert c["source"]["entry_id"] == "entry_2"  # Phrase subentry
        assert c["source"]["headword"] == "lose one's head"
        assert c["target"]["entry_id"] == "entry_1"  # Main headword entry
        assert c["target"]["headword"] == "head"

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

    def test_discover_subentries_word_boundary(self):
        """Test that subentry discovery requires whole word boundary matches and rejects partial substrings."""
        mock_connector = MagicMock()
        mock_connector.database = "dictionary"

        # Entry 1: main entry "hag" (stem, 0 rels)
        # Entry 2: phrase "Copenhagen blue" (phrase, 0 rels) — contains "hag" inside "Copenhagen", but NOT as a word
        raw_xquery_output = (
            "entry_1|||hag|||hag|||n|||stem|||0|||1|||an ugly old woman|||hag|||s1\n"
            "entry_2|||Copenhagen blue|||Copenhagen blue|||n|||phrase|||0|||1|||a medium light shade of blue|||blue|||s2"
        )
        mock_connector.execute_query.return_value = raw_xquery_output

        service = DictionaryService(db_connector=mock_connector)
        result = service.discover_subentries(min_confidence=0.0)

        # Must NOT match hag inside Copenhagen blue!
        assert len(result["candidates"]) == 0

    def test_create_component_relation_entry_level(self):
        """Test that _create_relation creates an entry-level _component-lexeme relation with complex-form-type trait."""
        mock_connector = MagicMock()
        mock_connector.database = "dictionary"
        mock_connector.execute_update.return_value = None

        service = DictionaryService(db_connector=mock_connector)
        
        mock_entry_1 = MagicMock()
        mock_entry_1.id = "copenhagen_blue"
        mock_entry_1.headword = "Copenhagen blue"
        mock_entry_1.relations = []

        mock_entry_2 = MagicMock()
        mock_entry_2.id = "blue"
        mock_entry_2.headword = "blue"
        mock_entry_2.relations = []

        service.get_entry = MagicMock(side_effect=lambda eid, **kw: mock_entry_1 if eid == "copenhagen_blue" else mock_entry_2)

        res = service._create_relation(
            source_id="copenhagen_blue",
            target_id="blue",
            relation_type="_component-lexeme",
            level="entry",
            complex_form_type="Phrase",
        )

        assert res["level"] == "entry"
        assert res["source_entry_id"] == "copenhagen_blue"
        assert res["target_entry_id"] == "blue"
        assert res["relation_type"] == "_component-lexeme"
        assert res["complex_form_type"] == "Phrase"

        # Verify execute_update XQuery call
        mock_connector.execute_update.assert_called_once()
        query = mock_connector.execute_update.call_args[0][0]
        assert "insert node" in query
        assert "_component-lexeme" in query
        assert "complex-form-type" in query
        assert "Phrase" in query
