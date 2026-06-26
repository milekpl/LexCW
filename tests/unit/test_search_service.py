"""
Unit tests for SearchService

Tests the unified search service that consolidates search functionality
from DictionaryService and XMLEntryService.
"""

import pytest
from unittest.mock import Mock, patch
from typing import List

from app.services.search_service import (
    SearchService, SearchQuery, SearchResults, SearchError, get_search_service
)
from app.services.dictionary_service import DictionaryService
from app.services.xml_entry_service import XMLEntryService


class TestSearchQueryDataClass:
    """Test SearchQuery dataclass"""

    def test_search_query_default_values(self):
        """SearchQuery should have sensible defaults."""
        query = SearchQuery()
        
        assert query.text == ""
        assert query.fields is None
        assert query.pos is None
        assert query.exact_match is False
        assert query.case_sensitive is False
        assert query.limit == 50
        assert query.offset == 0
        assert query.project_id is None
        assert query.advanced_filters is None

    def test_search_query_custom_values(self):
        """SearchQuery should accept custom values."""
        query = SearchQuery(
            text="test query",
            fields=["lexical_unit", "glosses"],
            pos="noun",
            exact_match=True,
            case_sensitive=True,
            limit=100,
            offset=10,
            project_id=123,
            advanced_filters={"grammatical_info": "verb"}
        )
        
        assert query.text == "test query"
        assert query.fields == ["lexical_unit", "glosses"]
        assert query.pos == "noun"
        assert query.exact_match is True
        assert query.case_sensitive is True
        assert query.limit == 100
        assert query.offset == 10
        assert query.project_id == 123
        assert query.advanced_filters == {"grammatical_info": "verb"}


class TestSearchResultsDataClass:
    """Test SearchResults dataclass"""

    def test_search_results_creation(self):
        """SearchResults should store results correctly."""
        entries = [
            {"id": "entry_1", "lexical_unit": {"en": "test"}},
            {"id": "entry_2", "lexical_unit": {"en": "example"}}
        ]
        results = SearchResults(
            entries=entries,
            total=100,
            limit=50,
            offset=0,
            query="test",
            backend="dictionary"
        )
        
        assert len(results.entries) == 2
        assert results.total == 100
        assert results.limit == 50
        assert results.offset == 0
        assert results.query == "test"
        assert results.backend == "dictionary"


class TestSearchServiceInitialization:
    """Test SearchService initialization and setup"""

    def test_service_initialization_with_both_backends(self):
        """SearchService should initialize with both backends."""
        mock_dict = Mock(spec=DictionaryService)
        mock_xml = Mock(spec=XMLEntryService)
        
        service = SearchService(
            dictionary_service=mock_dict,
            xml_service=mock_xml,
            default_backend="auto"
        )
        
        assert service.dictionary_service is mock_dict
        assert service.xml_service is mock_xml
        assert service.default_backend == "auto"

    def test_service_initialization_with_only_dictionary(self):
        """SearchService should work with only dictionary backend."""
        mock_dict = Mock(spec=DictionaryService)
        
        service = SearchService(dictionary_service=mock_dict)
        
        assert service.dictionary_service is mock_dict
        assert service.xml_service is None
        assert service.default_backend == "auto"

    def test_service_initialization_with_only_xml(self):
        """SearchService should work with only XML backend."""
        mock_xml = Mock(spec=XMLEntryService)
        
        service = SearchService(xml_service=mock_xml)
        
        assert service.dictionary_service is None
        assert service.xml_service is mock_xml
        assert service.default_backend == "auto"

    def test_service_initialization_with_no_backends(self):
        """SearchService should initialize but search will fail."""
        service = SearchService()
        
        assert service.dictionary_service is None
        assert service.xml_service is None


class TestBackendSelection:
    """Test auto-selection of search backends"""

    def test_auto_selects_dictionary_for_advanced_filters(self):
        """Should auto-select dictionary backend when advanced filters present."""
        mock_dict = Mock(spec=DictionaryService)
        mock_xml = Mock(spec=XMLEntryService)
        service = SearchService(mock_dict, mock_xml)
        
        query = SearchQuery(
            text="test",
            advanced_filters={"grammatical_info": "noun"}
        )
        
        backend = service._select_backend(query)
        assert backend == "dictionary"

    def test_auto_selects_dictionary_for_pos_filter(self):
        """Should auto-select dictionary backend when POS filter present."""
        mock_dict = Mock(spec=DictionaryService)
        mock_xml = Mock(spec=XMLEntryService)
        service = SearchService(mock_dict, mock_xml)
        
        query = SearchQuery(text="test", pos="verb")
        
        backend = service._select_backend(query)
        assert backend == "dictionary"

    def test_auto_selects_dictionary_for_multiple_fields(self):
        """Should auto-select dictionary backend when searching multiple fields."""
        mock_dict = Mock(spec=DictionaryService)
        mock_xml = Mock(spec=XMLEntryService)
        service = SearchService(mock_dict, mock_xml)
        
        query = SearchQuery(text="test", fields=["lexical_unit", "glosses", "definitions"])
        
        backend = service._select_backend(query)
        assert backend == "dictionary"

    def test_auto_selects_dictionary_for_exact_match(self):
        """Should auto-select dictionary backend for exact match."""
        mock_dict = Mock(spec=DictionaryService)
        mock_xml = Mock(spec=XMLEntryService)
        service = SearchService(mock_dict, mock_xml)
        
        query = SearchQuery(text="test", exact_match=True)
        
        backend = service._select_backend(query)
        assert backend == "dictionary"

    def test_auto_selects_dictionary_for_case_sensitive(self):
        """Should auto-select dictionary backend for case-sensitive search."""
        mock_dict = Mock(spec=DictionaryService)
        mock_xml = Mock(spec=XMLEntryService)
        service = SearchService(mock_dict, mock_xml)
        
        query = SearchQuery(text="Test", case_sensitive=True)
        
        backend = service._select_backend(query)
        assert backend == "dictionary"

    def test_auto_selects_xml_for_simple_query(self):
        """Should auto-select XML backend for simple text queries."""
        mock_dict = Mock(spec=DictionaryService)
        mock_xml = Mock(spec=XMLEntryService)
        service = SearchService(mock_dict, mock_xml)
        
        query = SearchQuery(text="simple query")
        
        backend = service._select_backend(query)
        assert backend == "xml"

    def test_auto_fallback_to_dictionary_when_xml_unavailable(self):
        """Should fallback to dictionary when XML not available."""
        mock_dict = Mock(spec=DictionaryService)
        service = SearchService(dictionary_service=mock_dict)  # No XML service
        
        query = SearchQuery(text="test")
        
        backend = service._select_backend(query)
        assert backend == "dictionary"

    def test_auto_raises_error_when_no_backends_available(self):
        """Should raise ValueError when no backends available."""
        service = SearchService()  # No backends
        
        query = SearchQuery(text="test")
        
        with pytest.raises(ValueError) as exc_info:
            service._select_backend(query)
        
        assert "No search backend available" in str(exc_info.value)


class TestDictionaryBackendSearch:
    """Test search using DictionaryService backend"""

    def test_dictionary_search_with_string_query(self):
        """Should handle string query and convert to SearchQuery."""
        mock_dict = Mock(spec=DictionaryService)
        
        # Mock return value
        mock_entry = Mock()
        mock_entry.to_dict.return_value = {"id": "entry_1", "lexical_unit": {"en": "test"}}
        mock_dict.search_entries.return_value = ([mock_entry], 100)
        
        service = SearchService(dictionary_service=mock_dict)
        
        results = service.search("test query")
        
        # Verify dictionary service was called
        mock_dict.search_entries.assert_called_once()
        call_kwargs = mock_dict.search_entries.call_args[1]
        assert call_kwargs['query'] == "test query"
        
        # Verify results format
        assert isinstance(results, SearchResults)
        assert results.backend == "dictionary"
        assert results.total == 100
        assert len(results.entries) == 1
        assert results.entries[0]["id"] == "entry_1"

    def test_dictionary_search_with_searchquery_object(self):
        """Should handle SearchQuery object directly."""
        mock_dict = Mock(spec=DictionaryService)
        mock_dict.search_entries.return_value = ([], 0)
        
        service = SearchService(dictionary_service=mock_dict)
        
        query = SearchQuery(
            text="test",
            fields=["lexical_unit", "glosses"],
            pos="noun",
            exact_match=True,
            case_sensitive=False,
            limit=25,
            offset=5,
            project_id=42
        )
        
        service.search(query)
        
        # Verify all parameters passed correctly
        call_kwargs = mock_dict.search_entries.call_args[1]
        assert call_kwargs['query'] == "test"
        assert call_kwargs['fields'] == ["lexical_unit", "glosses"]
        assert call_kwargs['pos'] == "noun"
        assert call_kwargs['exact_match'] is True
        assert call_kwargs['case_sensitive'] is False
        assert call_kwargs['limit'] == 25
        assert call_kwargs['offset'] == 5
        assert call_kwargs['project_id'] == 42

    def test_dictionary_search_handles_entries_without_to_dict(self):
        """Should handle entries that are already dicts."""
        mock_dict = Mock(spec=DictionaryService)
        # Entry is already a dict, no to_dict method
        mock_dict.search_entries.return_value = (
            [{"id": "entry_1", "lexical_unit": {"en": "test"}}],
            1
        )
        
        service = SearchService(dictionary_service=mock_dict)
        results = service.search("test")
        
        assert len(results.entries) == 1
        assert results.entries[0]["id"] == "entry_1"

    def test_dictionary_search_raises_error_on_failure(self):
        """Should wrap errors in SearchError."""
        mock_dict = Mock(spec=DictionaryService)
        mock_dict.search_entries.side_effect = Exception("Database connection failed")
        
        service = SearchService(dictionary_service=mock_dict)
        
        with pytest.raises(SearchError) as exc_info:
            service.search("test")
        
        assert "Database connection failed" in str(exc_info.value)


class TestXMLBackendSearch:
    """Test search using XMLEntryService backend"""

    def test_xml_search_with_simple_query(self):
        """Should handle simple XML search."""
        mock_xml = Mock(spec=XMLEntryService)
        mock_xml.search_entries.return_value = {
            "entries": [{"id": "entry_1", "lexical_units": ["test"]}],
            "total": 50,
            "limit": 50,
            "offset": 0,
            "count": 1
        }
        
        service = SearchService(xml_service=mock_xml)
        results = service.search("test", backend="xml")
        
        # Verify XML service was called
        mock_xml.search_entries.assert_called_once()
        call_kwargs = mock_xml.search_entries.call_args[1]
        assert call_kwargs['query_text'] == "test"
        
        # Verify results format
        assert isinstance(results, SearchResults)
        assert results.backend == "xml"
        assert results.total == 50
        assert len(results.entries) == 1

    def test_xml_search_normalizes_results_format(self):
        """Should normalize XML results to standard format."""
        mock_xml = Mock(spec=XMLEntryService)
        mock_xml.search_entries.return_value = {
            "entries": [{"id": "entry_1", "lexical_units": ["test"]}],
            "total": 100,
            "limit": 50,
            "offset": 0,
            "count": 1
        }
        
        service = SearchService(xml_service=mock_xml)
        query = SearchQuery(text="test", limit=50, offset=0)
        results = service.search(query, backend="xml")
        
        assert results.limit == 50
        assert results.offset == 0
        assert results.query == "test"

    def test_xml_search_handles_empty_results(self):
        """Should handle empty XML search results."""
        mock_xml = Mock(spec=XMLEntryService)
        mock_xml.search_entries.return_value = {
            "entries": [],
            "total": 0,
            "limit": 50,
            "offset": 0,
            "count": 0
        }
        
        service = SearchService(xml_service=mock_xml)
        results = service.search("nonexistent", backend="xml")
        
        assert results.entries == []
        assert results.total == 0
        assert results.backend == "xml"

    def test_xml_search_raises_error_on_failure(self):
        """Should wrap XML errors in SearchError."""
        mock_xml = Mock(spec=XMLEntryService)
        mock_xml.search_entries.side_effect = Exception("XML parsing error")
        
        service = SearchService(xml_service=mock_xml)
        
        with pytest.raises(SearchError) as exc_info:
            service.search("test", backend="xml")
        
        assert "XML parsing error" in str(exc_info.value)


class TestConvenienceMethods:
    """Test convenience search methods"""

    def test_search_simple_uses_auto_backend(self):
        """search_simple should use auto backend selection."""
        mock_dict = Mock(spec=DictionaryService)
        mock_dict.search_entries.return_value = ([], 0)
        
        service = SearchService(dictionary_service=mock_dict)
        
        results = service.search_simple("test", limit=100, offset=10, project_id=42)
        
        # Verify query was created correctly
        assert results.query == "test"
        assert results.limit == 100
        assert results.offset == 10
        
        # Verify dictionary service was called (auto-selected)
        call_kwargs = mock_dict.search_entries.call_args[1]
        assert call_kwargs['project_id'] == 42

    def test_search_advanced_forces_dictionary_backend(self):
        """search_advanced should force dictionary backend."""
        mock_dict = Mock(spec=DictionaryService)
        mock_dict.search_entries.return_value = ([], 0)
        mock_xml = Mock(spec=XMLEntryService)
        
        service = SearchService(dictionary_service=mock_dict, xml_service=mock_xml)
        
        results = service.search_advanced(
            text="test",
            fields=["lexical_unit", "glosses"],
            pos="noun",
            exact_match=True,
            case_sensitive=False,
            limit=25,
            offset=5,
            project_id=42,
            advanced_filters={"custom": "filter"}
        )
        
        # Verify backend was forced to dictionary
        assert results.backend == "dictionary"
        
        # Verify all parameters passed
        call_kwargs = mock_dict.search_entries.call_args[1]
        assert call_kwargs['fields'] == ["lexical_unit", "glosses"]
        assert call_kwargs['pos'] == "noun"
        assert call_kwargs['exact_match'] is True
        assert call_kwargs['advanced_filters'] == {"custom": "filter"}


class TestSearchErrorHandling:
    """Test error handling in search operations"""

    def test_search_error_class(self):
        """SearchError should store message and cause."""
        original_error = ValueError("Original error")
        error = SearchError("Search failed", cause=original_error)
        
        assert str(error) == "Search failed (Caused by: Original error)"
        assert error.message == "Search failed"
        assert error.cause is original_error

    def test_search_error_without_cause(self):
        """SearchError should work without cause."""
        error = SearchError("Simple error")
        
        assert str(error) == "Simple error"
        assert error.cause is None

    def test_explicit_backend_not_available(self):
        """Should raise error when explicit backend not available."""
        service = SearchService()  # No backends
        
        with pytest.raises(ValueError) as exc_info:
            service.search("test", backend="dictionary")
        
        assert "DictionaryService not available" in str(exc_info.value)


class TestGetSearchServiceFactory:
    """Test the get_search_service factory function"""

    def test_factory_with_preconfigured_services(self):
        """Should use provided services."""
        mock_dict = Mock(spec=DictionaryService)
        mock_xml = Mock(spec=XMLEntryService)
        
        service = get_search_service(mock_dict, mock_xml)
        
        assert service.dictionary_service is mock_dict
        assert service.xml_service is mock_xml

    def test_factory_with_only_dictionary(self):
        """Should work with only dictionary service."""
        mock_dict = Mock(spec=DictionaryService)
        
        service = get_search_service(mock_dict)
        
        assert service.dictionary_service is mock_dict
        assert service.xml_service is None

    def test_factory_auto_creates_services(self, mock_app):
        """Should auto-create services from Flask config."""
        from flask import current_app
        mock_connector = Mock()
        mock_dict_service = Mock()
        mock_dict_service.db_connector = mock_connector
        current_app.injector.get.return_value = mock_dict_service

        service = get_search_service()

        assert service is not None
        assert isinstance(service, SearchService)
        current_app.injector.get.assert_called_once_with(DictionaryService)
        assert service.dictionary_service is not None
