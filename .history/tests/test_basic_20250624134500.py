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
                "gloss": {"form": {"text": "A test entry"}}
            }]
        )        
        assert entry.id == "test_entry_1"
        assert entry.lexical_unit == {"en": "test"}
        assert len(entry.senses) == 1
        assert entry.senses[0]["id"] == "sense_1"
    
    def test_entry_validation(self):
        """Test entry validation."""
        # Valid entry
        entry = Entry(
            id_="test_entry_1",
            lexical_unit={"en": "test"},
            senses=[{
                "id": "sense_1",
                "gloss": {"form": {"text": "A test entry"}}
            }]
        )
        
        assert entry.validate() == True
        
        # Invalid entry - no lexical unit
        entry_no_lexical_unit = Entry(
            id_="test_entry_2",
            senses=[{
                "id": "sense_1",
                "gloss": {"form": {"text": "A test entry"}}
            }]
        )
        
        with pytest.raises(ValidationError):
            entry_no_lexical_unit.validate()
        
        # Invalid entry - sense without ID
        entry_invalid_sense = Entry(
            id_="test_entry_3",
            lexical_unit={"en": "test"},
            senses=[{
                "gloss": {"form": {"text": "A test entry"}}
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
        assert entry.senses[0]["id"] == "sense_1"
    
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
        assert connector.session is None
    
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
        assert connector.session == mock_session_instance
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
        self.mock_connector.execute_query.assert_called_once()
    
    def test_get_ranges(self):
        """Test getting ranges data."""
        ranges = self.service.get_ranges()
        
        assert isinstance(ranges, dict)
        assert "ranges" in ranges


class TestFlaskApp:
    """Test the Flask application."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = create_app('testing')
        self.client = self.app.test_client()    
    def test_app_creation(self):
        """Test creating the Flask app."""
        assert self.app is not None
        assert self.app.config['TESTING'] == True
    
    def test_index_route(self):
        """Test the index route."""
        response = self.client.get('/')
        
        assert response.status_code == 200
        # Index route returns HTML, not JSON
        assert b'Dictionary Writing System' in response.data or b'Dashboard' in response.data
    
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
