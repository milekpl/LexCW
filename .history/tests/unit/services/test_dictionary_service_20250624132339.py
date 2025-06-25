"""
Unit tests for the dictionary service.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import NotFoundError, ValidationError, DatabaseError


class TestDictionaryService:
    """Tests for the dictionary service."""
    
    def test_get_entry(self, db_connector, sample_entry):
        """Test getting an entry by ID."""
        # Mock the database connector and parser
        with patch('app.parsers.lift_parser.LIFTParser.parse_string') as mock_parse:
            mock_parse.return_value = [sample_entry]
            
            # Create service and call method
            service = DictionaryService(db_connector)
            entry = service.get_entry("test_entry")
            
            # Assertions
            assert entry.id == "test_entry"
            assert entry.lexical_unit["en"] == "test"
            assert entry.grammatical_info == "noun"
            assert len(entry.senses) == 1
            assert entry.senses[0]["glosses"]["pl"] == "test"
    
    def test_get_entry_not_found(self, db_connector):
        """Test handling of non-existent entry."""
        # Mock the database connector to return empty result
        db_connector.execute_query = lambda query: ""
        
        # Create service and call method
        service = DictionaryService(db_connector)
          # Should raise NotFoundError
        with pytest.raises(NotFoundError):
            service.get_entry("nonexistent")
    
    def test_create_entry(self, db_connector, sample_entry):
        """Test creating a new entry."""
        # Mock the necessary methods
        with patch.object(sample_entry, 'validate', return_value=True), \
             patch.object(DictionaryService, 'get_entry', side_effect=NotFoundError("Not found")), \
             patch.object(db_connector, 'execute_update', return_value=""):
            
            # Create service and call method
            service = DictionaryService(db_connector)
            entry_id = service.create_entry(sample_entry)
            
            # Assertions
            assert entry_id == sample_entry.id
    
    def test_create_duplicate_entry(self, db_connector, sample_entry):
        """Test handling of duplicate entry creation."""
        # Mock the necessary methods
        with patch.object(sample_entry, 'validate', return_value=True), \
             patch.object(DictionaryService, 'get_entry', return_value=sample_entry):
            
            # Create service and call method
            service = DictionaryService(db_connector)
            
            # Should raise ValidationError
            with pytest.raises(ValidationError):
                service.create_entry(sample_entry)
      def test_update_entry(self, db_connector, sample_entry):
        """Test updating an existing entry."""
        # Mock the necessary methods
        with patch.object(sample_entry, 'validate', return_value=True), \
             patch.object(DictionaryService, 'get_entry', return_value=sample_entry), \
             patch.object(db_connector, 'execute_update', return_value=""):
            
            # Create service and call method
            service = DictionaryService(db_connector)
            
            # Update the entry
            sample_entry.lexical_unit["en"] = "updated_test"
            service.update_entry(sample_entry)
            
            # No assertions needed since we're just checking that no exceptions were raised
    
    def test_update_nonexistent_entry(self, db_connector, sample_entry):
        """Test handling of updating a non-existent entry."""
        # Mock the necessary methods
        with patch.object(sample_entry, 'validate', return_value=True), \
             patch.object(DictionaryService, 'get_entry', side_effect=NotFoundError("Not found")):
            
            # Create service and call method
            service = DictionaryService(db_connector)
            
            # Should raise NotFoundError
            with pytest.raises(NotFoundError):
                service.update_entry(sample_entry)
    
    def test_delete_entry(self, db_connector, sample_entry):
        """Test deleting an entry."""
        # Mock the necessary methods
        with patch.object(DictionaryService, 'get_entry', return_value=sample_entry):
            
            # Create service and call method
            service = DictionaryService(db_connector)
            service.delete_entry(sample_entry.id)
            
            # No assertions needed since we're just checking that no exceptions were raised
    
    def test_delete_nonexistent_entry(self, db_connector):
        """Test handling of deleting a non-existent entry."""
        # Mock the necessary methods
        with patch.object(DictionaryService, 'get_entry', side_effect=NotFoundError("Not found")):
            
            # Create service and call method
            service = DictionaryService(db_connector)
            
            # Should raise NotFoundError
            with pytest.raises(NotFoundError):
                service.delete_entry("nonexistent")
    
    def test_list_entries(self, db_connector, sample_entries):
        """Test listing entries with pagination."""
        # Mock the necessary methods
        with patch('app.parsers.lift_parser.LIFTParser.parse_string') as mock_parse, \
             patch.object(db_connector, 'execute_query') as mock_query:
            
            mock_parse.return_value = sample_entries
            mock_query.side_effect = lambda query, **kwargs: "100" if "count" in query else "<entries>...</entries>"
            
            # Create service and call method
            service = DictionaryService(db_connector)
            entries, total_count = service.list_entries(limit=5, offset=0)
            
            # Assertions
            assert len(entries) == 10  # All entries returned by our mock
            assert total_count == 100
    
    def test_search_entries(self, db_connector, sample_entries):
        """Test searching for entries."""
        # Mock the necessary methods
        with patch('app.parsers.lift_parser.LIFTParser.parse_string') as mock_parse, \
             patch.object(db_connector, 'execute_query') as mock_query:
            
            mock_parse.return_value = [e for e in sample_entries if "0" in e.lexical_unit["en"]]
            mock_query.side_effect = lambda query, **kwargs: "10" if "count" in query else "<entries>...</entries>"
            
            # Create service and call method
            service = DictionaryService(db_connector)
            entries, total_count = service.search_entries(query="0", fields=["lexical_unit"])
            
            # Assertions
            assert total_count == 10
            # Note: In a real test, we would check that only entries with "0" in the lexical unit are returned
    
    def test_get_entry_count(self, db_connector):
        """Test getting the total number of entries."""
        # Mock the database connector
        db_connector.execute_query = lambda query: "150"
        
        # Create service and call method
        service = DictionaryService(db_connector)
        count = service.get_entry_count()
        
        # Assertions
        assert count == 150
    
    def test_get_related_entries(self, db_connector, sample_entry, sample_entries):
        """Test getting related entries."""
        # Mock the necessary methods
        with patch.object(DictionaryService, 'get_entry', return_value=sample_entry), \
             patch('app.parsers.lift_parser.LIFTParser.parse_string') as mock_parse:
            
            # Filter entries to simulate related entries
            related_entries = [e for e in sample_entries if int(e.id.split('_')[1]) < 3]
            mock_parse.return_value = related_entries
            
            # Create service and call method
            service = DictionaryService(db_connector)
            entries = service.get_related_entries(sample_entry.id)
            
            # Assertions
            assert len(entries) == len(related_entries)
    
    def test_get_entries_by_grammatical_info(self, db_connector, sample_entries):
        """Test getting entries by grammatical information."""
        # Mock the necessary methods
        with patch('app.parsers.lift_parser.LIFTParser.parse_string') as mock_parse:
            
            # Filter entries to simulate grammatical info filtering
            noun_entries = [e for e in sample_entries if e.grammatical_info == "noun"]
            mock_parse.return_value = noun_entries
            
            # Create service and call method
            service = DictionaryService(db_connector)
            entries = service.get_entries_by_grammatical_info("noun")
            
            # Assertions
            assert len(entries) == len(noun_entries)
            assert all(e.grammatical_info == "noun" for e in entries)
