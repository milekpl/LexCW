"""
Unit test for testing the Flask app's search endpoint with a live BaseX server.

This test ensures that the search functionality works correctly in the live Flask app,
not just in isolated tests of the dictionary service.
"""

import unittest
import os
import sys
import uuid
import tempfile

import pytest

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import url_for
from app import create_app
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService


@pytest.fixture(scope="function")
def test_db_name():
    """Generate a unique test database name for each test."""
    return f"test_flask_search_{str(uuid.uuid4()).replace('-', '_')}"

@pytest.fixture(scope="function")
def flask_app_with_test_db(test_db_name):
    """Create a Flask app with isolated test database."""
    # Create an admin connector to set up test database
    admin_connector = BaseXConnector(
        host='localhost',
        port=1984,
        username='admin',
        password='admin'
    )
    admin_connector.connect()
    
    # Clean up any existing test database
    try:
        if test_db_name in (admin_connector.execute_command("LIST") or ""):
            admin_connector.execute_command(f"DROP DB {test_db_name}")
    except Exception:
        pass
    
    # Create the test database
    admin_connector.execute_command(f"CREATE DB {test_db_name}")
    admin_connector.disconnect()
    
    # Create a Flask app for testing with isolated database
    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'SERVER_NAME': 'test.example.com',
        'BASEX_HOST': 'localhost',
        'BASEX_PORT': 1984,
        'BASEX_USERNAME': 'admin',
        'BASEX_PASSWORD': 'admin',
        'BASEX_DATABASE': test_db_name,
    })
    
    # Create a test client
    client = app.test_client()
    
    # Create a context for url_for
    app_context = app.app_context()
    app_context.push()
    
    # Create a BaseX connector for the test database
    connector = BaseXConnector(
        host='localhost',
        port=1984,
        username='admin',
        password='admin',
        database=test_db_name
    )
    
    # Create a dictionary service
    dict_service = DictionaryService(connector)
    
    # Initialize with minimal test data
    minimal_lift = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.15">
    <entry id="test_entry_1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="test_sense_1">
            <gloss lang="en"><text>test entry</text></gloss>
        </sense>
    </entry>
</lift>'''
    
    # Create temporary LIFT file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False) as f:
        f.write(minimal_lift)
        temp_lift_path = f.name
    
    try:
        dict_service.initialize_database(temp_lift_path)
    finally:
        # Cleanup temp file
        if os.path.exists(temp_lift_path):
            os.unlink(temp_lift_path)
    
    yield app, client, dict_service, app_context
    
    # Clean up
    try:
        connector.disconnect()
        admin_connector.connect()
        admin_connector.execute_command(f"DROP DB {test_db_name}")
        admin_connector.disconnect()
        app_context.pop()
    except Exception:
        pass


class TestFlaskSearchEndpoint:
    """Test case for the Flask app's search endpoint."""

    @pytest.mark.integration
    def test_search_endpoint_with_results(self, flask_app_with_test_db):
        """Test the search endpoint with a query that should return results."""
        app, client, dict_service, app_context = flask_app_with_test_db
        
        # First verify directly with the dictionary service
        entries, total = dict_service.search_entries("test")
        print(f"Direct API search found {total} entries")
        
        # Then test the Flask endpoint
        with app.test_request_context():
            url = url_for('main.search', q='test')
        
        response = client.get(url)
        assert response.status_code == 200, f"Search endpoint returned {response.status_code}"
        
        # Check if the response contains search results
        html_content = response.data.decode('utf-8')
        assert 'class="search-results"' in html_content, "Search results section not found in HTML"
        
        # Check if it shows the number of results (containers exist for JS)
        if total > 0:
            assert 'id="search-results"' in html_content, "Search results container not found"
            assert 'id="results-count"' in html_content, "Results count container not found"
    
    @pytest.mark.integration
    def test_search_endpoint_empty_query(self, flask_app_with_test_db):
        """Test the search endpoint with an empty query."""
        app, client, dict_service, app_context = flask_app_with_test_db
        
        with app.test_request_context():
            url = url_for('main.search')
        
        response = client.get(url)
        assert response.status_code == 200, "Empty search should return 200 status"
        
        # Empty search should render the template without results
        html_content = response.data.decode('utf-8')
        assert 'id="search-form"' in html_content, "Search form not found in HTML"
    
    @pytest.mark.integration
    def test_search_endpoint_pagination(self, flask_app_with_test_db):
        """Test the search endpoint with pagination."""
        app, client, dict_service, app_context = flask_app_with_test_db
        
        # First verify we have enough entries for pagination
        _, total = dict_service.search_entries("test")
        
        if total > 5:  # Only test pagination if we have enough entries
            with app.test_request_context():
                url = url_for('main.search', q='test', page=2, per_page=5)
            
            response = client.get(url)
            assert response.status_code == 200, "Paginated search should return 200 status"
            
            # Check for pagination controls containers (they exist for JS population)
            html_content = response.data.decode('utf-8')
            assert 'id="search-pagination"' in html_content, "Pagination container not found in HTML"
            assert 'id="results-pagination"' in html_content, "Results pagination container not found in HTML"
    
    @pytest.mark.integration
    def test_direct_api_search(self, flask_app_with_test_db):
        """Test the dictionary service search function directly."""
        app, client, dict_service, app_context = flask_app_with_test_db
        
        # This is useful to compare with the endpoint results
        entries, total = dict_service.search_entries("test")
        assert entries is not None, "Entries should not be None"
        assert isinstance(total, int), "Total should be an integer"
        
        print(f"Direct API found {total} entries for 'test'")
        if entries:
            for i, entry in enumerate(entries[:5]):  # Print first 5 entries
                print(f"Entry {i+1}: {entry.id} - {entry.lexical_unit}")


if __name__ == "__main__":
    unittest.main()
