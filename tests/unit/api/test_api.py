"""
Unit tests for the API endpoints.
"""

import json
from unittest.mock import patch

from app.models.entry import Entry
from app.utils.exceptions import NotFoundError


class TestEntriesAPI:
    """Tests for the entries API endpoints."""
    
    def test_list_entries(self, client, sample_entries):
        """Test listing entries."""
        # Mock the dictionary service
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.list_entries.return_value = (sample_entries, len(sample_entries))
            
            # Make the request
            response = client.get('/api/entries/')
            
            # Parse response
            data = json.loads(response.data)
            
            # Assertions
            assert response.status_code == 200
            assert 'entries' in data
            assert 'total_count' in data
            assert data['total_count'] == len(sample_entries)
            assert len(data['entries']) == len(sample_entries)
    
    def test_get_entry(self, client, sample_entry):
        """Test getting an entry by ID."""
        # Mock the dictionary service
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.get_entry.return_value = sample_entry
            
            # Make the request
            response = client.get(f'/api/entries/{sample_entry.id}')
            
            # Parse response
            data = json.loads(response.data)
            
            # Assertions
            assert response.status_code == 200
            assert data['id'] == sample_entry.id
            assert data['lexical_unit'] == sample_entry.lexical_unit
    
    def test_get_entry_not_found(self, client):
        """Test getting a non-existent entry."""
        # Mock the dictionary service
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.get_entry.side_effect = NotFoundError("Entry not found")
            
            # Make the request
            response = client.get('/api/entries/nonexistent')
            
            # Parse response
            data = json.loads(response.data)
            
            # Assertions
            assert response.status_code == 404
            assert 'error' in data
    
    def test_create_entry(self, client, sample_entry):
        """Test creating a new entry."""
        # Mock the dictionary service
        with patch('app.api.entries.get_dictionary_service') as mock_get_service, \
             patch('app.api.entries.Entry.from_dict', return_value=sample_entry):
            
            mock_service = mock_get_service.return_value
            mock_service.create_entry.return_value = sample_entry.id
            
            # Make the request
            response = client.post('/api/entries/', json=sample_entry.to_dict())
            
            # Parse response
            data = json.loads(response.data)
            
            # Assertions
            assert response.status_code == 201
            assert 'id' in data
            assert data['id'] == sample_entry.id
    
    def test_update_entry(self, client, sample_entry):
        """Test updating an entry."""
        # Mock the dictionary service
        with patch('app.api.entries.get_dictionary_service') as mock_get_service, \
             patch('app.api.entries.Entry.from_dict', return_value=sample_entry):
            
            mock_service = mock_get_service.return_value
            mock_service.update_entry.return_value = None
            
            # Make the request
            response = client.put(f'/api/entries/{sample_entry.id}', json=sample_entry.to_dict())
            
            # Parse response
            data = json.loads(response.data)
            
            # Assertions
            assert response.status_code == 200
            assert 'success' in data
            assert data['success'] is True
    
    def test_delete_entry(self, client, sample_entry):
        """Test deleting an entry."""
        # Mock the dictionary service
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.delete_entry.return_value = None
            
            # Make the request
            response = client.delete(f'/api/entries/{sample_entry.id}')
            
            # Parse response
            data = json.loads(response.data)
            
            # Assertions
            assert response.status_code == 200
            assert 'success' in data
            assert data['success'] is True
    
    def test_get_related_entries(self, client, sample_entry, sample_entries):
        """Test getting related entries."""
        # Filter sample entries to use as related entries
        related_entries = sample_entries[:3]
        
        # Mock the dictionary service
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.get_related_entries.return_value = related_entries
            
            # Make the request
            response = client.get(f'/api/entries/{sample_entry.id}/related')
            
            # Parse response
            data = json.loads(response.data)
            
            # Assertions
            assert response.status_code == 200
            assert 'entries' in data
            assert 'count' in data
            assert data['count'] == len(related_entries)
            assert len(data['entries']) == len(related_entries)


class TestSearchAPI:
    """Tests for the search API endpoints."""
    
    def test_search_entries(self, client, sample_entries):
        """Test searching for entries."""
        # Filter sample entries to use as search results
        search_results = sample_entries[::2]  # Every other entry
        
        # Mock the dictionary service
        with patch('app.api.search.get_dictionary_service') as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.search_entries.return_value = (search_results, len(search_results))
            
            # Make the request
            response = client.get('/api/search/?q=test&fields=lexical_unit,glosses')
            
            # Parse response
            data = json.loads(response.data)
            
            # Assertions
            assert response.status_code == 200
            assert 'entries' in data
            assert 'total_count' in data
            assert 'query' in data
            assert 'fields' in data
            assert data['query'] == 'test'
            assert data['fields'] == ['lexical_unit', 'glosses']
            assert data['total_count'] == len(search_results)
            assert len(data['entries']) == len(search_results)
    
    def test_search_by_grammatical_info(self, client, sample_entries):
        """Test searching by grammatical information."""
        # Filter sample entries to use as search results
        noun_entries = [e for e in sample_entries if e.grammatical_info == "noun"]
        
        # Mock the dictionary service
        with patch('app.api.search.get_dictionary_service') as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.get_entries_by_grammatical_info.return_value = noun_entries
            
            # Make the request
            response = client.get('/api/search/grammatical?value=noun')
            
            # Parse response
            data = json.loads(response.data)
            
            # Assertions
            assert response.status_code == 200
            assert 'entries' in data
            assert 'count' in data
            assert 'grammatical_info' in data
            assert data['grammatical_info'] == 'noun'
            assert data['count'] == len(noun_entries)
            assert len(data['entries']) == len(noun_entries)
    
    def test_get_ranges(self, client):
        """Test getting ranges data."""
        # Sample ranges data
        ranges_data = {
            "grammatical-info": {
                "id": "grammatical-info",
                "values": [
                    {"id": "noun", "value": "noun"},
                    {"id": "verb", "value": "verb"}
                ]
            }
        }
        
        # Mock the dictionary service
        with patch('app.api.search.get_dictionary_service') as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.get_ranges.return_value = ranges_data
            
            # Make the request
            response = client.get('/api/search/ranges')
            
            # Parse response
            data = json.loads(response.data)
            
            # Assertions
            assert response.status_code == 200
            assert "grammatical-info" in data
            assert len(data["grammatical-info"]["values"]) == 2
    
    def test_get_range_values(self, client):
        """Test getting values for a specific range."""
        # Sample range values
        range_values = [
            {"id": "noun", "value": "noun"},
            {"id": "verb", "value": "verb"}
        ]
        
        # Mock the dictionary service
        with patch('app.api.search.get_dictionary_service') as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.get_range_values.return_value = range_values
            
            # Make the request
            response = client.get('/api/search/ranges/grammatical-info')
            
            # Parse response
            data = json.loads(response.data)
            
            # Assertions
            assert response.status_code == 200
            assert len(data) == 2
            assert data[0]["id"] == "noun"
            assert data[1]["id"] == "verb"
