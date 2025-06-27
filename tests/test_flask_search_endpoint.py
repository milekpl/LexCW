"""
Unit test for testing the Flask app's search endpoint with a live BaseX server.

This test ensures that the search functionality works correctly in the live Flask app,
not just in isolated tests of the dictionary service.
"""

import unittest
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import url_for
from app import create_app
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService


class FlaskSearchEndpointTest(unittest.TestCase):
    """Test case for the Flask app's search endpoint."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment once before all tests."""
        # Configure Flask app for testing
        os.environ['BASEX_DATABASE'] = 'dictionary'  # Use the same database as the app
        
        # Create a Flask app for testing
        cls.app = create_app('testing')
        cls.app.config.update({
            'TESTING': True,
            'SERVER_NAME': 'test.example.com',
            'BASEX_HOST': 'localhost',
            'BASEX_PORT': 1984,
            'BASEX_USERNAME': 'admin',
            'BASEX_PASSWORD': 'admin',
            'BASEX_DATABASE': 'dictionary',
        })
        
        # Create a test client
        cls.client = cls.app.test_client()
        
        # Create a context for url_for
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Create a BaseX connector directly
        cls.connector = BaseXConnector(
            host='localhost',
            port=1984,
            username='admin',
            password='admin',
            database='dictionary'
        )
        
        # Create a dictionary service
        cls.dict_service = DictionaryService(cls.connector)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        cls.app_context.pop()
    
    def test_search_endpoint_with_results(self):
        """Test the search endpoint with a query that should return results."""
        # First verify directly with the dictionary service
        entries, total = self.dict_service.search_entries("test")
        print(f"Direct API search found {total} entries")
        
        # Then test the Flask endpoint
        with self.app.test_request_context():
            url = url_for('main.search', q='test')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, f"Search endpoint returned {response.status_code}")
        
        # Check if the response contains search results
        html_content = response.data.decode('utf-8')
        self.assertIn('class="search-results"', html_content, "Search results section not found in HTML")
        
        # Check if it shows the number of results (containers exist for JS)
        if total > 0:
            self.assertIn('id="search-results"', html_content, "Search results container not found")
            self.assertIn('id="results-count"', html_content, "Results count container not found")
    
    def test_search_endpoint_empty_query(self):
        """Test the search endpoint with an empty query."""
        with self.app.test_request_context():
            url = url_for('main.search')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, "Empty search should return 200 status")
        
        # Empty search should render the template without results
        html_content = response.data.decode('utf-8')
        self.assertIn('id="search-form"', html_content, "Search form not found in HTML")
    
    def test_search_endpoint_pagination(self):
        """Test the search endpoint with pagination."""
        # First verify we have enough entries for pagination
        _, total = self.dict_service.search_entries("test")
        
        if total > 5:  # Only test pagination if we have enough entries
            with self.app.test_request_context():
                url = url_for('main.search', q='test', page=2, per_page=5)
            
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, "Paginated search should return 200 status")
            
            # Check for pagination controls containers (they exist for JS population)
            html_content = response.data.decode('utf-8')
            self.assertIn('id="search-pagination"', html_content, "Pagination container not found in HTML")
            self.assertIn('id="results-pagination"', html_content, "Results pagination container not found in HTML")
    
    def test_direct_api_search(self):
        """Test the dictionary service search function directly."""
        # This is useful to compare with the endpoint results
        entries, total = self.dict_service.search_entries("test")
        self.assertIsNotNone(entries, "Entries should not be None")
        self.assertIsInstance(total, int, "Total should be an integer")
        
        print(f"Direct API found {total} entries for 'test'")
        if entries:
            for i, entry in enumerate(entries[:5]):  # Print first 5 entries
                print(f"Entry {i+1}: {entry.id} - {entry.lexical_unit}")


if __name__ == "__main__":
    unittest.main()
