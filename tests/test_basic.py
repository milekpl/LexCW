"""
Unit tests for the Dictionary Writing System.

This module contains basic unit tests to verify the structure and functionality
of the dictionary application.
"""

import pytest
from unittest.mock import Mock, patch
from app import create_app
from app.models.entry import Entry
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError


class TestEntry:
    """Test the Entry model."""
    
    def test_entry_creation(self):
        """Test creating a basic entry."""
        entry = Entry(
            id_="test_entry_1",
            lexical_unit={"en": "test"},
            senses=[{
                "id": "sense_1",
                "gloss": "A test entry"  # Simple string, should be stored in 'en'
            }]
        )        
        assert entry.id == "test_entry_1"
        assert entry.lexical_unit == {"en": "test"}
        assert len(entry.senses) == 1
        # Test with actual Sense object, not dictionary
        assert entry.senses[0].id == "sense_1"
        assert entry.senses[0].gloss == "A test entry"  # Test the property
    
    def test_entry_validation(self):
        """Test entry validation."""
        # Valid entry
        entry = Entry(
            id_="test_entry_1",
            lexical_unit={"en": "test"},
            senses=[{
                "id": "sense_1",
                "gloss": "A test entry"
            }]
        )
        
        assert entry.validate()
        
        # Invalid entry - no lexical unit
        entry_no_lexical_unit = Entry(
            id_="test_entry_2",
            senses=[{
                "id": "sense_1",
                "gloss": "A test entry"
            }]
        )
        
        with pytest.raises(ValidationError):
            entry_no_lexical_unit.validate()
        
        # Invalid entry - sense without ID  
        entry_invalid_sense = Entry(
            id_="test_entry_3",
            lexical_unit={"en": "test"},
            senses=[{
                "id": "",  # Empty ID should fail validation
                "gloss": "A test entry"
            }]
        )
        
        with pytest.raises(ValidationError):
            entry_invalid_sense.validate()
    
    def test_entry_add_sense(self):
        """Test adding a sense to an entry."""
        entry = Entry(
            id_="test_entry_1",
            lexical_unit={"en": "test"}
        )
        
        sense = {
            "id": "sense_1",
            "gloss": {"form": {"text": "A test entry"}}
        }
        
        entry.add_sense(sense)
        
        assert len(entry.senses) == 1
        # After adding, the sense is converted to a Sense object
        assert entry.senses[0].id == "sense_1"
    
    def test_entry_add_pronunciation(self):
        """Test adding pronunciation to an entry."""
        entry = Entry(
            id_="test_entry_1",
            lexical_unit={"en": "test"}
        )
        
        entry.add_pronunciation("seh-fonipa", "test")
        
        assert entry.pronunciations["seh-fonipa"] == "test"


class TestBaseXConnector:
    """Test the BaseX connector."""
    
    def test_connector_initialization(self):
        """Test creating a BaseX connector."""
        connector = BaseXConnector(
            host="localhost",
            port=1984,
            username="admin",
            password="admin",
            database="test_db"
        )
        
        assert connector.host == "localhost"
        assert connector.port == 1984
        assert connector.username == "admin"
        assert connector.password == "admin"
        assert connector.database == "test_db"
        assert connector._session is None
    
    @patch('app.database.basex_connector.BaseXSession')
    def test_connector_connection(self, mock_session):
        """Test connecting to BaseX."""
        connector = BaseXConnector(
            host="localhost",
            port=1984,
            username="admin",
            password="admin"
        )
        
        # Mock the session
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        result = connector.connect()
        
        assert result == True
        assert connector._session == mock_session_instance
        mock_session.assert_called_once_with("localhost", 1984, "admin", "admin")
    
    def test_connector_context_manager(self):
        """Test using the connector as a context manager."""
        connector = BaseXConnector(
            host="localhost",
            port=1984,
            username="admin",
            password="admin"
        )
        
        with patch.object(connector, 'connect') as mock_connect:
            with patch.object(connector, 'disconnect') as mock_disconnect:
                mock_connect.return_value = True
                
                with connector:
                    pass
                
                mock_connect.assert_called_once()
                mock_disconnect.assert_called_once()


class TestDictionaryService:
    """Test the Dictionary service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connector = Mock(spec=BaseXConnector)
        self.mock_connector.database = "test_db"  # Add missing database attribute
        self.mock_connector.execute_query.return_value = "test_db"  # For LIST command in __init__
        self.service = DictionaryService(self.mock_connector)
    
    def test_service_initialization(self):
        """Test creating a dictionary service."""
        assert self.service.db_connector == self.mock_connector
        assert hasattr(self.service, 'lift_parser')
        assert hasattr(self.service, 'ranges_parser')
    
    def test_get_entry_count(self):
        """Test getting the entry count."""
        self.mock_connector.execute_query.return_value = "42"
        
        count = self.service.get_entry_count()
        
        assert count == 42
        # Should be called multiple times (namespace detection + actual count)
        assert self.mock_connector.execute_query.call_count >= 1
    
    def test_get_ranges(self):
        """Test getting ranges data."""
        # Mock empty ranges (typical when no ranges.xml is found)
        self.mock_connector.execute_query.return_value = None
        
        ranges = self.service.get_ranges()
        
        assert isinstance(ranges, dict)
        # Should return fallback ranges from sample LIFT ranges file when no ranges found in database
        assert len(ranges) > 0
        
        # Check that fallback ranges contain core categories from the sample LIFT ranges file
        # These are categories we know exist in the sample-lift-file.lift-ranges
        expected_core_categories = ['grammatical-info', 'etymology-type', 'usage-type']
        found_categories = 0
        for category in expected_core_categories:
            if category in ranges:
                found_categories += 1
                assert 'id' in ranges[category]
                assert 'values' in ranges[category]
        
        # Should find at least some of the expected core categories
        assert found_categories >= 1, f"Should find at least one core category from {expected_core_categories} in {list(ranges.keys())}"
        
        # Verify the ranges have proper structure consistent with LIFT ranges format
        for range_id, range_data in list(ranges.items())[:3]:  # Check first 3 ranges
            assert 'id' in range_data, f"Range {range_id} should have 'id' field"
            assert 'values' in range_data, f"Range {range_id} should have 'values' field"
            assert isinstance(range_data['values'], list), f"Range {range_id} values should be a list"


class TestFlaskApp:
    """Test the Flask application."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = create_app('testing')
        self.client = self.app.test_client()    
    def test_app_creation(self):
        """Test creating the Flask app."""
        assert self.app is not None
        assert self.app.config['TESTING']
    
    def test_index_route(self):
        """Test the index route."""
        response = self.client.get('/')
        
        assert response.status_code == 200
        # Index route returns HTML, not JSON
        assert b'Lexicographic Curation Workbench' in response.data or b'Dashboard' in response.data
    
    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
    
    def test_404_error(self):
        """Test 404 error handling."""
        response = self.client.get('/nonexistent')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'Not found'


if __name__ == '__main__':
    pytest.main([__file__])
