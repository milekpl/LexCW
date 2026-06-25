"""
Unified Search Service

Consolidates search functionality from:
- app/services/dictionary_service.py::search_entries()
- app/services/xml_entry_service.py::search_entries()
- app/api/search.py::search_entries()
- app/api/xml_entries.py::search_entries()

Provides a single, consistent search interface regardless of the underlying
storage backend (BaseX XML, PostgreSQL, or other future backends).
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass

from app.services.dictionary_service import DictionaryService
from app.services.xml_entry_service import XMLEntryService

logger = logging.getLogger(__name__)


@dataclass
class SearchQuery:
    """Standardized search query parameters."""
    text: str = ""
    fields: Optional[List[str]] = None
    pos: Optional[str] = None
    exact_match: bool = False
    case_sensitive: bool = False
    limit: int = 50
    offset: int = 0
    project_id: Optional[int] = None
    advanced_filters: Optional[Dict[str, Any]] = None


@dataclass  
class SearchResults:
    """Standardized search results."""
    entries: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int
    query: str
    backend: str  # Which backend was used


class SearchService:
    """
    Unified search service with pluggable backends.
    
    Eliminates the duplication between:
    - DictionaryService.search_entries() (rich XQuery-based)
    - XMLEntryService.search_entries() (simpler XML-based)
    
    Both are consolidated behind a single interface with consistent
    parameter handling and return format.
    """
    
    def __init__(
        self,
        dictionary_service: Optional[DictionaryService] = None,
        xml_service: Optional[XMLEntryService] = None,
        default_backend: str = "auto"
    ):
        """
        Initialize the search service.
        
        Args:
            dictionary_service: Optional DictionaryService for rich searches
            xml_service: Optional XMLEntryService for simple XML searches  
            default_backend: Default backend to use ('auto', 'dictionary', 'xml')
        """
        self.dictionary_service = dictionary_service
        self.xml_service = xml_service
        self.default_backend = default_backend
        
    def search(
        self,
        query: Union[str, SearchQuery],
        backend: Optional[str] = None,
        **kwargs
    ) -> SearchResults:
        """
        Execute a search with the specified or auto-detected backend.
        
        Args:
            query: Search query text or SearchQuery object
            backend: Backend to use ('auto', 'dictionary', 'xml')
            **kwargs: Additional search parameters if query is a string
            
        Returns:
            SearchResults with standardized format
            
        Raises:
            ValueError: If no suitable backend is available
            SearchError: If search execution fails
        """
        # Normalize query to SearchQuery object
        if isinstance(query, str):
            query = SearchQuery(text=query, **kwargs)
        
        # Determine which backend to use
        selected_backend = backend or self.default_backend
        
        if selected_backend == "auto":
            selected_backend = self._select_backend(query)
        
        # Execute search with selected backend
        if selected_backend == "dictionary":
            return self._search_with_dictionary(query)
        elif selected_backend == "xml":
            return self._search_with_xml(query)
        else:
            raise ValueError(f"Unknown backend: {selected_backend}")
    
    def _select_backend(self, query: SearchQuery) -> str:
        """
        Auto-select the best backend based on query characteristics.
        
        Strategy:
        - Use 'dictionary' for rich queries (filters, POS, multiple fields)
        - Use 'xml' for simple text-only queries
        """
        # Use dictionary service if we have advanced features
        if (query.advanced_filters or 
            query.pos or 
            query.fields or
            query.exact_match or
            query.case_sensitive):
            if self.dictionary_service:
                return "dictionary"
        
        # Default to XML service for simple queries if available
        if self.xml_service:
            return "xml"
        
        # Fallback to dictionary if XML not available
        if self.dictionary_service:
            return "dictionary"
        
        raise ValueError("No search backend available")
    
    def _search_with_dictionary(self, query: SearchQuery) -> SearchResults:
        """
        Execute search using DictionaryService (rich XQuery-based).
        
        This provides the most feature-complete search with support for:
        - Multiple field search
        - Part of speech filtering
        - Exact/partial matching
        - Case sensitivity
        - Advanced filters
        """
        if not self.dictionary_service:
            raise ValueError("DictionaryService not available")
        
        try:
            # Execute search using DictionaryService
            entries, total = self.dictionary_service.search_entries(
                query=query.text,
                project_id=query.project_id,
                fields=query.fields,
                limit=query.limit,
                offset=query.offset,
                pos=query.pos,
                exact_match=query.exact_match,
                case_sensitive=query.case_sensitive,
                advanced_filters=query.advanced_filters
            )
            
            # Convert Entry objects to dicts for consistent format
            entry_dicts = [
                entry.to_dict() if hasattr(entry, 'to_dict') else entry
                for entry in entries
            ]
            
            return SearchResults(
                entries=entry_dicts,
                total=total,
                limit=query.limit,
                offset=query.offset,
                query=query.text,
                backend="dictionary"
            )
            
        except Exception as e:
            logger.error(f"Dictionary search failed: {e}")
            raise SearchError(f"Search failed: {e}") from e
    
    def _search_with_xml(self, query: SearchQuery) -> SearchResults:
        """
        Execute search using XMLEntryService (simpler XML-based).
        
        This is optimized for simple text queries on lexical units.
        """
        if not self.xml_service:
            raise ValueError("XMLEntryService not available")
        
        try:
            # Execute search using XMLEntryService
            results = self.xml_service.search_entries(
                query_text=query.text,
                limit=query.limit,
                offset=query.offset
            )
            
            # XMLEntryService returns a dict with different structure
            # Normalize it to SearchResults format
            return SearchResults(
                entries=results.get('entries', []),
                total=results.get('total', 0),
                limit=results.get('limit', query.limit),
                offset=results.get('offset', query.offset),
                query=query.text,
                backend="xml"
            )
            
        except Exception as e:
            logger.error(f"XML search failed: {e}")
            raise SearchError(f"Search failed: {e}") from e
    
    def search_simple(
        self,
        text: str,
        limit: int = 50,
        offset: int = 0,
        project_id: Optional[int] = None
    ) -> SearchResults:
        """
        Simple search with minimal parameters.
        
        Convenience method for the most common search use case.
        """
        query = SearchQuery(
            text=text,
            limit=limit,
            offset=offset,
            project_id=project_id
        )
        return self.search(query)
    
    def search_advanced(
        self,
        text: str,
        fields: List[str],
        pos: Optional[str] = None,
        exact_match: bool = False,
        case_sensitive: bool = False,
        limit: int = 50,
        offset: int = 0,
        project_id: Optional[int] = None,
        advanced_filters: Optional[Dict[str, Any]] = None
    ) -> SearchResults:
        """
        Advanced search with all available filters.
        
        Forces use of the dictionary backend for rich search capabilities.
        """
        query = SearchQuery(
            text=text,
            fields=fields,
            pos=pos,
            exact_match=exact_match,
            case_sensitive=case_sensitive,
            limit=limit,
            offset=offset,
            project_id=project_id,
            advanced_filters=advanced_filters
        )
        return self.search(query, backend="dictionary")


class SearchError(Exception):
    """Exception raised when a search operation fails."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        self.message = message
        self.cause = cause
        super().__init__(message)
    
    def __str__(self):
        if self.cause:
            return f"{self.message} (Caused by: {self.cause})"
        return self.message


# Convenience factory function
def get_search_service(
    dictionary_service: Optional[DictionaryService] = None,
    xml_service: Optional[XMLEntryService] = None
) -> SearchService:
    """
    Get a SearchService instance with auto-configured backends.
    
    Args:
        dictionary_service: Optional pre-configured DictionaryService
        xml_service: Optional pre-configured XMLEntryService
        
    Returns:
        Configured SearchService instance
    """
    # Auto-configure services if not provided
    if dictionary_service is None:
        try:
            from flask import current_app
            connector = current_app.injector.get(DictionaryService).db_connector
            dictionary_service = DictionaryService(connector)
        except Exception:
            dictionary_service = None
    
    if xml_service is None:
        try:
            from flask import current_app
            xml_service = XMLEntryService(
                host=current_app.config.get('BASEX_HOST', 'localhost'),
                port=current_app.config.get('BASEX_PORT', 1984),
                username=current_app.config.get('BASEX_USERNAME', 'admin'),
                password=current_app.config.get('BASEX_PASSWORD', 'admin'),
                database=current_app.config.get('BASEX_DATABASE', 'dictionary')
            )
        except Exception:
            xml_service = None
    
    return SearchService(
        dictionary_service=dictionary_service,
        xml_service=xml_service
    )
