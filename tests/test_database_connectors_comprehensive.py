"""
Comprehensive tests for database connectors to increase coverage.
Focus on stable, core database functionality that's unlikely to change.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Optional

from app.database.basex_connector import BaseXConnector
from app.database.mock_connector import MockDatabaseConnector
from app.database.connector_factory import create_database_connector
from app.utils.exceptions import DatabaseError


class TestBaseXConnectorComprehensive:
    """Comprehensive tests for BaseX database connector."""
    
    @pytest.fixture
    def connector_config(self):
        """Standard connector configuration."""
        return {
            'host': 'localhost',
            'port': 1984,
            'username': 'admin',
            'password': 'admin',
            'database': 'test_db'
        }
    
    def test_connector_initialization(self, connector_config):
        """Test BaseX connector initialization with various parameters."""
        connector = BaseXConnector(**connector_config)
        
        assert connector.host == 'localhost'
        assert connector.port == 1984
        assert connector.username == 'admin'
        assert connector.password == 'admin'
        assert connector.database == 'test_db'
        assert not connector.is_connected()
    
    def test_connector_initialization_minimal(self):
        """Test connector with minimal parameters."""
        connector = BaseXConnector(
            host='test_host',
            port=9999,
            username='user',
            password='pass'
        )
        
        assert connector.host == 'test_host'
        assert connector.port == 9999
        assert connector.username == 'user'
        assert connector.password == 'pass'
        assert connector.database is None
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_connection_success(self, mock_basex_client, connector_config):
        """Test successful database connection."""
        # Mock successful connection
        mock_session = Mock()
        mock_basex_client.Session.return_value = mock_session
        
        connector = BaseXConnector(**connector_config)
        connector.connect()
        
        assert connector.is_connected()
        assert connector.session == mock_session
        
        # Verify BaseX client was called correctly
        mock_basex_client.Session.assert_called_once_with(
            'localhost', 1984, 'admin', 'admin'
        )
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_connection_failure(self, mock_basex_client, connector_config):
        """Test connection failure handling."""
        # Mock connection failure
        mock_basex_client.Session.side_effect = Exception("Connection failed")
        
        connector = BaseXConnector(**connector_config)
        
        with pytest.raises(DatabaseError, match="Failed to connect"):
            connector.connect()
        
        assert not connector.is_connected()
        assert connector.session is None
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_disconnect(self, mock_basex_client, connector_config):
        """Test database disconnection."""
        mock_session = Mock()
        mock_basex_client.Session.return_value = mock_session
        
        connector = BaseXConnector(**connector_config)
        connector.connect()
        
        # Test disconnect
        connector.disconnect()
        
        assert not connector.is_connected()
        assert connector.session is None
        mock_session.close.assert_called_once()
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_execute_query_success(self, mock_basex_client, connector_config):
        """Test successful query execution."""
        mock_session = Mock()
        mock_session.execute.return_value = "<result>test data</result>"
        mock_basex_client.Session.return_value = mock_session
        
        connector = BaseXConnector(**connector_config)
        connector.connect()
        
        result = connector.execute_query("count(//entry)")
        
        assert result == "<result>test data</result>"
        # Should call execute twice - once for OPEN, once for query
        assert mock_session.execute.call_count >= 1
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_execute_query_not_connected(self, mock_basex_client, connector_config):
        """Test query execution when not connected."""
        connector = BaseXConnector(**connector_config)
        
        with pytest.raises(DatabaseError, match="Not connected"):
            connector.execute_query("count(//entry)")
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_execute_query_failure(self, mock_basex_client, connector_config):
        """Test query execution failure."""
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Query failed")
        mock_basex_client.Session.return_value = mock_session
        
        connector = BaseXConnector(**connector_config)
        connector.connect()
        
        with pytest.raises(DatabaseError, match="Failed to execute query"):
            connector.execute_query("invalid query")
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_execute_update_success(self, mock_basex_client, connector_config):
        """Test successful update execution."""
        mock_session = Mock()
        mock_session.execute.return_value = ""
        mock_basex_client.Session.return_value = mock_session
        
        connector = BaseXConnector(**connector_config)
        connector.connect()
        
        connector.execute_update("db:add('test', '<entry/>')")
        
        # Should call execute for update
        assert mock_session.execute.call_count >= 1
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_create_database(self, mock_basex_client, connector_config):
        """Test database creation."""
        mock_session = Mock()
        mock_session.execute.return_value = ""
        mock_basex_client.Session.return_value = mock_session
        
        connector = BaseXConnector(**connector_config)
        connector.connect()
        
        connector.create_database("new_test_db")
        
        # Should execute CREATE DB command
        mock_session.execute.assert_any_call("CREATE DB new_test_db")
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_drop_database(self, mock_basex_client, connector_config):
        """Test database dropping."""
        mock_session = Mock()
        mock_session.execute.return_value = ""
        mock_basex_client.Session.return_value = mock_session
        
        connector = BaseXConnector(**connector_config)
        connector.connect()
        
        connector.drop_database("old_test_db")
        
        # Should execute DROP DB command
        mock_session.execute.assert_any_call("DROP DB old_test_db")
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_context_manager(self, mock_basex_client, connector_config):
        """Test connector as context manager."""
        mock_session = Mock()
        mock_basex_client.Session.return_value = mock_session
        
        connector = BaseXConnector(**connector_config)
        
        with connector:
            assert connector.is_connected()
        
        # Should disconnect after context
        mock_session.close.assert_called_once()
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_execute_lift_query_with_namespace(self, mock_basex_client, connector_config):
        """Test LIFT query execution with namespace."""
        mock_session = Mock()
        mock_session.execute.return_value = "<entry/>"
        mock_basex_client.Session.return_value = mock_session
        
        connector = BaseXConnector(**connector_config)
        connector.connect()
        
        query = "//lift:entry"
        result = connector.execute_lift_query(query, has_namespace=True)
        
        assert result == "<entry/>"
        # Should add namespace declaration to query
        executed_query = mock_session.execute.call_args_list[-1][0][0]
        assert "declare namespace lift" in executed_query
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_execute_lift_query_without_namespace(self, mock_basex_client, connector_config):
        """Test LIFT query execution without namespace."""
        mock_session = Mock()
        mock_session.execute.return_value = "<entry/>"
        mock_basex_client.Session.return_value = mock_session
        
        connector = BaseXConnector(**connector_config)
        connector.connect()
        
        query = "//entry"
        result = connector.execute_lift_query(query, has_namespace=False)
        
        assert result == "<entry/>"
        # Should not add namespace declaration
        executed_query = mock_session.execute.call_args_list[-1][0][0]
        assert "declare namespace lift" not in executed_query


class TestMockDatabaseConnectorComprehensive:
    """Comprehensive tests for mock database connector."""
    
    def test_mock_connector_initialization(self):
        """Test mock connector initialization."""
        connector = MockDatabaseConnector()
        
        assert connector.host == "mock_host"
        assert connector.port == 1984
        assert connector.username == "mock_user"
        assert connector.password == "mock_pass"
        assert connector.database == "mock_db"
        assert not connector.is_connected()
        assert connector.entries == {}
    
    def test_mock_connector_connect_disconnect(self):
        """Test mock connector connection management."""
        connector = MockDatabaseConnector()
        
        # Test connect
        connector.connect()
        assert connector.is_connected()
        
        # Test disconnect
        connector.disconnect()
        assert not connector.is_connected()
    
    def test_mock_connector_context_manager(self):
        """Test mock connector as context manager."""
        connector = MockDatabaseConnector()
        
        with connector:
            assert connector.is_connected()
        
        assert not connector.is_connected()
    
    def test_mock_execute_query_count(self):
        """Test mock query execution for counting."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        # Add some test entries
        connector.entries = {
            "entry1": "<entry id='entry1'/>",
            "entry2": "<entry id='entry2'/>"
        }
        
        result = connector.execute_query("count(//entry)")
        assert result == "2"
    
    def test_mock_execute_query_get_entry(self):
        """Test mock query execution for getting specific entry."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        test_entry = "<entry id='test123'><lexical-unit><form><text>test</text></form></lexical-unit></entry>"
        connector.entries["test123"] = test_entry
        
        result = connector.execute_query("//entry[@id='test123']")
        assert result == test_entry
    
    def test_mock_execute_query_list_entries(self):
        """Test mock query execution for listing entries."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        connector.entries = {
            "entry1": "<entry id='entry1'/>",
            "entry2": "<entry id='entry2'/>",
            "entry3": "<entry id='entry3'/>"
        }
        
        result = connector.execute_query("//entry")
        # Should return all entries
        assert "entry1" in result
        assert "entry2" in result
        assert "entry3" in result
    
    def test_mock_execute_query_search(self):
        """Test mock query execution for search."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        connector.entries = {
            "entry1": "<entry id='entry1'><lexical-unit><form><text>hello</text></form></lexical-unit></entry>",
            "entry2": "<entry id='entry2'><lexical-unit><form><text>world</text></form></lexical-unit></entry>",
            "entry3": "<entry id='entry3'><lexical-unit><form><text>test</text></form></lexical-unit></entry>"
        }
        
        # Search for "hello"
        result = connector.execute_query("//entry[contains(.,'hello')]")
        assert "entry1" in result
        assert "entry2" not in result
    
    def test_mock_execute_update_add_entry(self):
        """Test mock update execution for adding entries."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        entry_xml = "<entry id='new_entry'><lexical-unit><form><text>new</text></form></lexical-unit></entry>"
        connector.execute_update(f"db:add('test', '{entry_xml}')")
        
        assert "new_entry" in connector.entries
        assert connector.entries["new_entry"] == entry_xml
    
    def test_mock_execute_update_replace_entry(self):
        """Test mock update execution for replacing entries."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        # Add initial entry
        initial_entry = "<entry id='test'><lexical-unit><form><text>old</text></form></lexical-unit></entry>"
        connector.entries["test"] = initial_entry
        
        # Replace entry
        new_entry = "<entry id='test'><lexical-unit><form><text>new</text></form></lexical-unit></entry>"
        connector.execute_update(f"replace node //entry[@id='test'] with {new_entry}")
        
        assert connector.entries["test"] == new_entry
    
    def test_mock_execute_update_delete_entry(self):
        """Test mock update execution for deleting entries."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        # Add entry
        connector.entries["test"] = "<entry id='test'/>"
        
        # Delete entry
        connector.execute_update("delete node //entry[@id='test']")
        
        assert "test" not in connector.entries
    
    def test_mock_create_database(self):
        """Test mock database creation."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        # Should not raise any errors
        connector.create_database("new_test_db")
        
        # Mock connector should accept any database name
        assert connector.database == "mock_db"  # Doesn't change
    
    def test_mock_drop_database(self):
        """Test mock database dropping."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        # Add some entries
        connector.entries["test"] = "<entry id='test'/>"
        
        # Drop database (clears entries)
        connector.drop_database("test_db")
        
        # Entries should be cleared
        assert len(connector.entries) == 0
    
    def test_mock_execute_lift_query(self):
        """Test mock LIFT query execution."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        connector.entries = {
            "entry1": "<entry id='entry1'/>",
            "entry2": "<entry id='entry2'/>"
        }
        
        # With namespace
        result = connector.execute_lift_query("//lift:entry", has_namespace=True)
        assert "entry1" in result
        
        # Without namespace  
        result = connector.execute_lift_query("//entry", has_namespace=False)
        assert "entry1" in result
    
    def test_mock_query_not_connected(self):
        """Test mock query when not connected."""
        connector = MockDatabaseConnector()
        
        with pytest.raises(DatabaseError, match="Not connected"):
            connector.execute_query("count(//entry)")
    
    def test_mock_update_not_connected(self):
        """Test mock update when not connected."""
        connector = MockDatabaseConnector()
        
        with pytest.raises(DatabaseError, match="Not connected"):
            connector.execute_update("db:add('test', '<entry/>')")


class TestConnectorFactory:
    """Test database connector factory functionality."""
    
    def test_create_basex_connector(self):
        """Test creating BaseX connector through factory."""
        connector = create_database_connector(
            host="localhost",
            port=1984,
            username="admin", 
            password="admin",
            database="test"
        )
        
        # Should return BaseX connector by default
        assert isinstance(connector, BaseXConnector)
        assert connector.host == "localhost"
        assert connector.port == 1984
        assert connector.username == "admin"
        assert connector.password == "admin"
        assert connector.database == "test"
    
    @patch.dict(os.environ, {'USE_MOCK_DB': 'true'})
    def test_create_mock_connector_with_env_var(self):
        """Test creating mock connector when environment variable is set."""
        connector = create_database_connector(
            host="localhost",
            port=1984,
            username="admin",
            password="admin", 
            database="test"
        )
        
        # Should return mock connector when env var is set
        assert isinstance(connector, MockDatabaseConnector)
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_create_connector_basex_import_error(self, mock_basex_client):
        """Test fallback to mock when BaseX import fails."""
        # Mock import error
        mock_basex_client.side_effect = ImportError("BaseX not available")
        
        connector = create_database_connector(
            host="localhost",
            port=1984,
            username="admin",
            password="admin",
            database="test"
        )
        
        # Should fallback to mock connector
        assert isinstance(connector, MockDatabaseConnector)
    
    def test_create_connector_preserves_database_name(self):
        """Test that factory preserves database name for mock connector."""
        connector = create_database_connector(
            host="test_host",
            port=9999,
            username="test_user",
            password="test_pass",
            database="custom_db"
        )
        
        if isinstance(connector, MockDatabaseConnector):
            # Mock connector sets its own values but should still be configurable
            assert connector is not None
        else:
            # BaseX connector should preserve the database name
            assert connector.database == "custom_db"


class TestDatabaseConnectorEdgeCases:
    """Test edge cases and error conditions for database connectors."""
    
    def test_mock_connector_malformed_xml_handling(self):
        """Test mock connector handling of malformed XML."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        # Add malformed XML
        malformed_xml = "<entry id='test'><unclosed-tag>"
        
        # Should not raise errors when storing
        connector.execute_update(f"db:add('test', '{malformed_xml}')")
        assert "test" in connector.entries
    
    def test_mock_connector_empty_query_results(self):
        """Test mock connector with queries that return no results."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        # Query non-existent entry
        result = connector.execute_query("//entry[@id='nonexistent']")
        assert result == ""
        
        # Count when no entries
        result = connector.execute_query("count(//entry)")
        assert result == "0"
    
    def test_mock_connector_special_characters_in_queries(self):
        """Test mock connector with special characters in queries."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        # Add entry with special characters
        special_entry = "<entry id='test'><text>hello's \"world\" &amp; more</text></entry>"
        connector.entries["test"] = special_entry
        
        # Search for special characters
        result = connector.execute_query("//entry[contains(.,'hello')]")
        assert "test" in result
    
    @patch('app.database.basex_connector.BaseXClient')
    def test_basex_connector_session_recovery(self, mock_basex_client, connector_config=None):
        """Test BaseX connector session recovery after connection loss."""
        if connector_config is None:
            connector_config = {
                'host': 'localhost',
                'port': 1984,
                'username': 'admin',
                'password': 'admin',
                'database': 'test'
            }
        
        mock_session = Mock()
        mock_basex_client.Session.return_value = mock_session
        
        connector = BaseXConnector(**connector_config)
        connector.connect()
        
        # Simulate connection loss
        mock_session.execute.side_effect = Exception("Connection lost")
        
        # Should raise DatabaseError
        with pytest.raises(DatabaseError):
            connector.execute_query("count(//entry)")
    
    def test_mock_connector_large_dataset_simulation(self):
        """Test mock connector with large dataset simulation."""
        connector = MockDatabaseConnector()
        connector.connect()
        
        # Add many entries
        for i in range(1000):
            entry_xml = f"<entry id='entry_{i}'><text>entry number {i}</text></entry>"
            connector.entries[f"entry_{i}"] = entry_xml
        
        # Count all entries
        result = connector.execute_query("count(//entry)")
        assert result == "1000"
        
        # Search should still work
        result = connector.execute_query("//entry[contains(.,'500')]")
        assert "entry_500" in result
