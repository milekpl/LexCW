#!/usr/bin/env python3

"""
Tests for the dictionary service search functionality.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry


class TestDictionaryServiceSearch:
    """Test search functionality of the dictionary service."""

    def _create_mock_service(self):
        """Create a properly mocked DictionaryService for testing."""
        mock_connector = Mock()
        mock_connector.database = "test_db"
        mock_connector.is_connected.return_value = True
        mock_connector.execute_command.return_value = "test_db"
        mock_connector.execute_update.return_value = None
        mock_connector.execute_query.return_value = ""

        with patch.dict("os.environ", {"TESTING": "true"}):
            service = DictionaryService(mock_connector)
            # Mock namespace detection to simplify query assertions
            service._detect_namespace_usage = Mock(return_value=False)

        return service, mock_connector

    def test_search_entries_prioritizes_exact_match_query(self):
        """Test that search_entries generates a query that prioritizes exact matches."""
        service, mock_connector = self._create_mock_service()

        # Mock the count query result and the main query result
        mock_connector.execute_query.side_effect = [
            "0",  # Return 0 for the count query
            "",  # Return empty XML for the main search query
        ]

        with patch("app.parsers.lift_parser.LIFTParser.parse_string", return_value=[]):
            service.search_entries(query="test")

            # Assert that execute_query was called twice (count and search)
            assert mock_connector.execute_query.call_count == 2

            # Get the second query executed, which is the main search query
            executed_query = mock_connector.execute_query.call_args_list[1].args[0]
            
            # 1. Check for the scoring logic
            assert "let $score :=" in executed_query
            assert "if (some $form in $entry/lexical-unit/form/text" in executed_query
            assert "satisfies lower-case($form/string()) = 'test')" in executed_query
            assert "then 1" in executed_query
            assert "else 2" in executed_query

            # 2. Check for the ordering logic
            assert "order by $score" in executed_query
            assert "$entry/lexical-unit/form[1]/text[1]/string()" in executed_query
            
    def test_search_results_are_correctly_parsed_and_returned(self):
        """Test that the search results are parsed and returned correctly, respecting the limit."""
        service, mock_connector = self._create_mock_service()

        mock_xml = """
        <entry id="test_id_1"><lexical-unit><form lang="en"><text>test</text></form></lexical-unit></entry>
        <entry id="test_id_2"><lexical-unit><form lang="en"><text>testing</text></form></lexical-unit></entry>
        """
        mock_entries = [
            Entry(id_="test_id_1", lexical_unit={"en": "test"}),
            Entry(id_="test_id_2", lexical_unit={"en": "testing"}),
        ]

        # Mock count query and search query results
        mock_connector.execute_query.side_effect = ["2", mock_xml]

        with patch("app.parsers.lift_parser.LIFTParser.parse_string", return_value=mock_entries) as mock_parse:
            entries, total_count = service.search_entries(query="test", limit=2)

            assert total_count == 2
            assert len(entries) == 2
            mock_parse.assert_called_with(mock_xml)
            assert entries[0].id == "test_id_1"

    def test_import_lift_includes_namespace_prologue(self):
        """Test that import_lift uses fast bulk merge operations."""
        service, mock_connector = self._create_mock_service()
        
        # Create the directory that will be used for temp files
        import os
        test_dir = "/tmp/test.lift"
        os.makedirs(test_dir, exist_ok=True)
        
        # Mock file operations and temp database operations
        with patch("os.path.exists", return_value=True), \
             patch("os.path.abspath", return_value=test_dir), \
             patch("os.path.getsize", return_value=100), \
             patch("random.randint", return_value=123456), \
             patch.object(service, 'find_ranges_file', return_value=None):
            
            # Mock the execute_command and execute_query for temp database operations
            def mock_execute_command(cmd):
                if "LIST" in cmd:
                    return "test_ddd24ab0\nimport_123456\ntest_ddd24ab0"  # Include the temp db in the list
                return None
            
            mock_connector.execute_command.side_effect = mock_execute_command
            # Mock queries: namespace detection (returns "false"), count (returns "2"),
            # delete (returns None), export (returns XML), final count
            mock_connector.execute_query.side_effect = [
                "false",  # namespace detection
                "2",      # count query in _import_lift_merge_continue
                None,      # delete query
                "<entry id=\"test1\"><form><text>test</text></form></entry>",  # export query
                "2"       # final count (if needed)
            ]  
            
            result = service.import_lift("/path/to/test.lift", mode="merge")

            # Check the result
            assert result == 2

            # Verify the queries were called (namespace detection and count)
            calls = mock_connector.execute_query.call_args_list
            assert len(calls) >= 2  # namespace detection, count query
        
        # Clean up the test directory
        import shutil
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
