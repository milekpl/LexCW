#!/usr/bin/env python3

"""
Test for filter and sort_order support in dictionary service.
This follows TDD principles - writing tests first before implementing the feature.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
from typing import Tuple
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry


class TestDictionaryServiceFilteringSorting:
    """Test enhanced filtering and sorting functionality."""

    def _create_mock_service(self) -> Tuple[DictionaryService, Mock, Mock]:
        """Create a properly mocked DictionaryService for testing."""
        # Mock connector with all necessary methods
        mock_connector = Mock()
        mock_connector.database = "test_db"
        mock_connector.is_connected.return_value = True
        mock_connector.connect.return_value = None
        mock_connector.execute_command.return_value = "test_db"  # For database list check
        mock_connector.execute_update.return_value = None
        mock_connector.execute_lift_query.return_value = "<entry id='entry1'><lexical-unit><form><text>apple</text></form></lexical-unit></entry><entry id='entry2'><lexical-unit><form><text>banana</text></form></lexical-unit></entry>"
        
        # Create service and mock its dependencies
        with patch('app.services.dictionary_service.QueryBuilder'), \
             patch('app.services.dictionary_service.NamespaceManager'), \
             patch('app.services.dictionary_service.LiftParser') as mock_lift_parser:
            
            # Mock the lift parser
            mock_parser_instance = Mock()
            mock_lift_parser.return_value = mock_parser_instance
            mock_parser_instance.parse_string.return_value = [
                Entry(id_="entry1", lexical_unit={"en": "apple"}),
                Entry(id_="entry2", lexical_unit={"en": "banana"})
            ]
            
            service = DictionaryService(mock_connector)
            service.lift_parser = mock_parser_instance
            
            return service, mock_connector, mock_parser_instance

    def test_list_entries_with_sort_order_asc(self) -> None:
        """Test that list_entries supports ascending sort order."""
        service, mock_connector, mock_parser = self._create_mock_service()
        
        # Mock count method
        with patch.object(service, 'count_entries', return_value=2):
            # Test ascending sort order
            entries, total = service.list_entries(
                limit=10, 
                offset=0, 
                sort_by="lexical_unit", 
                sort_order="asc"
            )
            
            assert len(entries) == 2
            assert total == 2
            # Verify the query was called
            mock_connector.execute_lift_query.assert_called()

    def test_list_entries_with_sort_order_desc(self) -> None:
        """Test that list_entries supports descending sort order."""
        mock_connector = Mock()
        mock_connector.execute_query.return_value = [
            {'id': 'entry2', 'lexical_unit': 'banana'},
            {'id': 'entry1', 'lexical_unit': 'apple'},
        ]
        mock_connector.count_entries.return_value = 2
        
        service = DictionaryService(mock_connector)
        
        with patch.object(service, '_parse_entry_from_xml') as mock_parse:
            mock_parse.side_effect = [
                Entry(id_="entry2", lexical_unit={"en": "banana"}),
                Entry(id_="entry1", lexical_unit={"en": "apple"})
            ]
            
            # Test descending sort order
            entries, total = service.list_entries(
                limit=10, 
                offset=0, 
                sort_by="lexical_unit", 
                sort_order="desc"
            )
            
            assert len(entries) == 2
            assert total == 2

    def test_list_entries_with_filter_text(self) -> None:
        """Test that list_entries supports filtering by text."""
        mock_connector = Mock()
        mock_connector.execute_query.return_value = [
            {'id': 'entry1', 'lexical_unit': 'apple'},
        ]
        mock_connector.count_entries.return_value = 1
        
        service = DictionaryService(mock_connector)
        
        with patch.object(service, '_parse_entry_from_xml') as mock_parse:
            mock_parse.side_effect = [
                Entry(id_="entry1", lexical_unit={"en": "apple"})
            ]
            
            # Test text filtering
            entries, total = service.list_entries(
                limit=10, 
                offset=0, 
                sort_by="lexical_unit", 
                sort_order="asc",
                filter_text="app"
            )
            
            assert len(entries) == 1
            assert total == 1
            assert entries[0].id_ == "entry1"

    def test_list_entries_with_combined_filter_and_sort(self) -> None:
        """Test that list_entries supports both filtering and custom sorting."""
        mock_connector = Mock()
        mock_connector.execute_query.return_value = [
            {'id': 'entry3', 'lexical_unit': 'application'},
            {'id': 'entry1', 'lexical_unit': 'apple'},
        ]
        mock_connector.count_entries.return_value = 2
        
        service = DictionaryService(mock_connector)
        
        with patch.object(service, '_parse_entry_from_xml') as mock_parse:
            mock_parse.side_effect = [
                Entry(id_="entry3", lexical_unit={"en": "application"}),
                Entry(id_="entry1", lexical_unit={"en": "apple"})
            ]
            
            # Test combined filtering and sorting
            entries, total = service.list_entries(
                limit=10, 
                offset=0, 
                sort_by="lexical_unit", 
                sort_order="desc",
                filter_text="app"
            )
            
            assert len(entries) == 2
            assert total == 2

    def test_list_entries_backward_compatibility(self) -> None:
        """Test that list_entries maintains backward compatibility."""
        mock_connector = Mock()
        mock_connector.execute_query.return_value = [
            {'id': 'entry1', 'lexical_unit': 'test'},
        ]
        mock_connector.count_entries.return_value = 1
        
        service = DictionaryService(mock_connector)
        
        with patch.object(service, '_parse_entry_from_xml') as mock_parse:
            mock_parse.side_effect = [
                Entry(id_="entry1", lexical_unit={"en": "test"})
            ]
            
            # Test without new parameters (backward compatibility)
            entries, total = service.list_entries(limit=10, offset=0, sort_by="lexical_unit")
            
            assert len(entries) == 1
            assert total == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
