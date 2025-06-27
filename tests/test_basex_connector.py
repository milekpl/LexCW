"""
Tests for the BaseX database connection and operations.
"""

import os
import pytest
from app.database.basex_connector import BaseXConnector
from app.utils.exceptions import DatabaseError

# Test connection parameters - these should work with a live BaseX server
HOST = "localhost"
PORT = 1984
USERNAME = "admin"
PASSWORD = "admin"
TEST_DB = "test_connection_db"


class TestBaseXConnector:
    """Test the BaseX connector functionality with a live server."""
    
    def test_connection(self):
        """Test that we can connect to a BaseX server."""
        connector = BaseXConnector(HOST, PORT, USERNAME, PASSWORD)
        
        # Connect to the server
        assert connector.connect() is True
        assert connector.is_connected() is True
        
        # Disconnect
        connector.disconnect()
        assert connector.is_connected() is False
    
    def test_wrong_credentials(self):
        """Test connection with wrong credentials."""
        connector = BaseXConnector(HOST, PORT, "wrong_user", "wrong_pass")
        
        # Should raise an exception
        with pytest.raises(DatabaseError):
            connector.connect()
        
        assert connector.is_connected() is False
    
    def test_execute_query(self):
        """Test executing a simple query."""
        connector = BaseXConnector(HOST, PORT, USERNAME, PASSWORD)
        connector.connect()
        
        try:
            # Simple XQuery to return a value
            result = connector.execute_query("xquery 1 + 1")
            assert result == "2"
            
            # Query to list all databases
            result = connector.execute_command("LIST")
            assert isinstance(result, str)
        finally:
            connector.disconnect()
    
    def test_create_and_drop_database(self):
        """Test creating and dropping a database."""
        connector = BaseXConnector(HOST, PORT, USERNAME, PASSWORD)
        connector.connect()
        
        try:
            # Check if test database exists and drop it if it does
            if TEST_DB in (connector.execute_command("LIST") or ""):
                connector.execute_update(f"DROP DB {TEST_DB}")
            
            # Create a new database
            connector.execute_update(f"CREATE DB {TEST_DB}")
            
            # Verify it exists
            assert TEST_DB in connector.execute_command("LIST")
            
            # Drop the database
            connector.execute_update(f"DROP DB {TEST_DB}")
            
            # Verify it no longer exists
            assert TEST_DB not in connector.execute_command("LIST")
        finally:
            # Clean up in case of test failure
            if TEST_DB in (connector.execute_command("LIST") or ""):
                connector.execute_update(f"DROP DB {TEST_DB}")
            connector.disconnect()
    
    def test_add_xml_to_database(self):
        """Test adding XML content to a database."""
        connector = BaseXConnector(HOST, PORT, USERNAME, PASSWORD)
        connector.connect()
        
        try:
            # Create a new database
            if TEST_DB in (connector.execute_command("LIST") or ""):
                connector.execute_update(f"DROP DB {TEST_DB}")
                
            connector.execute_update(f"CREATE DB {TEST_DB}")
            
            # Add some XML content
            xml_content = "<test><item>Test Item</item></test>"
            connector.execute_update(f'add to "test.xml" {xml_content}')
            
            # Query the content
            result = connector.execute_query(f"xquery doc('{TEST_DB}/test.xml')/test/item/text()")
            assert result == "Test Item"
        finally:
            # Clean up
            if TEST_DB in (connector.execute_command("LIST") or ""):
                connector.execute_update(f"DROP DB {TEST_DB}")
            connector.disconnect()
