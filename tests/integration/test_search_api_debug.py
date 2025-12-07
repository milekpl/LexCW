"""
Test search functionality with actual API calls.
"""

import json
import pytest
from app.models.entry import Entry


@pytest.mark.integration
class TestSearchAPI:
    """Test search API functionality."""
    
    @pytest.mark.integration
    def test_search_api_basic(self, client):
        """Test basic search API functionality."""
        response = client.get('/api/search/?q=test&limit=5')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'query' in data
        assert 'entries' in data
        assert 'total' in data
        assert data['query'] == 'test'
        
    @pytest.mark.integration
    def test_search_with_notes_field(self, client):
        """Test search API with notes field specified."""
        response = client.get('/api/search/?q=EXAMPLE&fields=notes&limit=10')
        
        # Should not fail even if no results
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'query' in data
        assert 'entries' in data
        assert 'fields' in data
        assert 'notes' in data['fields']
        
    @pytest.mark.integration
    def test_search_with_multiple_fields(self, client):
        """Test search API with multiple fields including notes."""
        response = client.get('/api/search/?q=EXAMPLE&fields=lexical_unit,notes,definition&limit=10')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'query' in data
        assert 'entries' in data
        assert 'fields' in data
        assert 'notes' in data['fields']
        assert 'definition' in data['fields']
        
    @pytest.mark.integration
    def test_search_error_handling(self, client):
        """Test search API error handling."""
        # Empty query should return error
        response = client.get('/api/search/?q=')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        
    @pytest.mark.integration
    def test_search_debug_info(self, client):
        """Test search to see what's actually being searched."""
        response = client.get('/api/search/?q=house&fields=lexical_unit,notes&limit=5')
        
        print(f"Search response status: {response.status_code}")
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f"Search results: {data}")
            print(f"Fields searched: {data.get('fields', [])}")
            print(f"Total results: {data.get('total', 0)}")
            if data.get('entries'):
                print(f"First entry: {data['entries'][0]}")
                
        assert response.status_code == 200
