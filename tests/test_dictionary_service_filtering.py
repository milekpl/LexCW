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

    def _create_mock_service(self) -> Tuple[DictionaryService, Mock]:
        """Create a properly mocked DictionaryService for testing."""
        # Mock connector with all necessary methods
        mock_connector = Mock()
        mock_connector.database = "test_db"
        mock_connector.is_connected.return_value = True
        mock_connector.connect.return_value = None
        mock_connector.execute_command.return_value = "test_db"  # For database list check
        mock_connector.execute_update.return_value = None
        mock_connector.execute_query.return_value = ""  # Default empty - will be overridden by parse_string mock
        
        # Create service with testing environment
        with patch.dict('os.environ', {'TESTING': 'true'}):
            service = DictionaryService(mock_connector)
            
            return service, mock_connector

    def test_list_entries_with_sort_order_asc(self) -> None:
        """Test that list_entries supports ascending sort order."""
        service, mock_connector = self._create_mock_service()
        
        # Mock count method and parse_string method
        with patch.object(service, 'count_entries', return_value=2), \
             patch.object(service.lift_parser, 'parse_string') as mock_parse:
            
            mock_parse.return_value = [
                Entry(id_="entry1", lexical_unit={"en": "apple"},
                      senses=[{"id": "sense_1", "definition": {"en": "a fruit"}}]),
                Entry(id_="entry2", lexical_unit={"en": "banana"},
                      senses=[{"id": "sense_1", "definition": {"en": "another fruit"}}])
            ]
            
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
            mock_connector.execute_query.assert_called()

    def test_list_entries_with_sort_order_desc(self) -> None:
        """Test that list_entries supports descending sort order."""
        service, _ = self._create_mock_service()
        
        with patch.object(service, 'count_entries', return_value=2), \
             patch.object(service.lift_parser, 'parse_string') as mock_parse:
            
            mock_parse.return_value = [
                Entry(id_="entry2", lexical_unit={"en": "banana"},
                      senses=[{"id": "sense_1", "definition": {"en": "another fruit"}}]),
                Entry(id_="entry1", lexical_unit={"en": "apple"},
                      senses=[{"id": "sense_1", "definition": {"en": "a fruit"}}])
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
        service, _ = self._create_mock_service()
        
        with patch.object(service, '_count_entries_with_filter', return_value=1), \
             patch.object(service.lift_parser, 'parse_string') as mock_parse:
            
            mock_parse.return_value = [
                Entry(id_="entry1", lexical_unit={"en": "apple"}, 
                      senses=[{"id": "sense_1", "definition": {"en": "a fruit"}}])
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
            assert entries[0].id == "entry1"

    def test_list_entries_with_combined_filter_and_sort(self) -> None:
        """Test that list_entries supports both filtering and custom sorting."""
        service, _ = self._create_mock_service()
        
        with patch.object(service, '_count_entries_with_filter', return_value=2), \
             patch.object(service.lift_parser, 'parse_string') as mock_parse:
            
            mock_parse.return_value = [
                Entry(id_="entry3", lexical_unit={"en": "application"},
                      senses=[{"id": "sense_1", "definition": {"en": "a program"}}]),
                Entry(id_="entry1", lexical_unit={"en": "apple"},
                      senses=[{"id": "sense_1", "definition": {"en": "a fruit"}}])
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
        service, _ = self._create_mock_service()
        
        with patch.object(service, 'count_entries', return_value=1), \
             patch.object(service.lift_parser, 'parse_string') as mock_parse:
            
            mock_parse.return_value = [
                Entry(id_="entry1", lexical_unit={"en": "test"},
                      senses=[{"id": "sense_1", "definition": {"en": "a test word"}}])
            ]
            
            # Test without new parameters (backward compatibility)
            entries, total = service.list_entries(limit=10, offset=0, sort_by="lexical_unit")
            
            assert len(entries) == 1
            assert total == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
