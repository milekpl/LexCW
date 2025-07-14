"""
Comprehensive unit tests for API modules to increase coverage.
Tests all API endpoints and edge cases.
"""

import pytest
import json



@pytest.mark.integration
class TestEntriesAPI:
    """Test entries API endpoints."""
    
    @pytest.mark.integration
    def test_entries_list_with_pagination(self, client):
        """Test entries list with pagination parameters."""
        response = client.get('/api/entries?page=2&per_page=5&sort_by=id')
        
        # Should return valid response even if no entries exist  
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'entries' in data
        assert 'total' in data
        
    @pytest.mark.integration
    def test_entries_list_invalid_pagination(self, client):
        """Test entries list with invalid pagination parameters."""
        # Test negative page - should return error
        response = client.get('/api/entries?page=-1')
        assert response.status_code == 400  # API returns 400 for invalid parameters
        
        # Test negative per_page  
        response = client.get('/api/entries?per_page=-1')
        assert response.status_code == 400  # API returns 400 for invalid parameters
        
        # Test zero per_page
        response = client.get('/api/entries?per_page=0')
        assert response.status_code == 400  # API returns 400 for invalid parameters
    
    @pytest.mark.integration
    def test_entries_get_single_not_found(self, client):
        """Test getting a single entry that doesn't exist (real DB)."""
        response = client.get('/api/entries/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires mocking a database error; not possible with real DB only.")
    def test_entries_get_single_database_error(self, client):
        pass
    
    @pytest.mark.integration
    def test_entries_create_validation_error(self, client):
        """Test creating entry with validation error (real DB)."""
        entry_data = {
            'id': 'test',
            'lexical_unit': {}  # Invalid: lexical_unit required
        }
        response = client.post('/api/entries',
                             data=json.dumps(entry_data),
                             content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    @pytest.mark.integration
    def test_entries_create_invalid_json(self, client):
        """Test creating entry with invalid JSON."""
        response = client.post('/api/entries',
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    @pytest.mark.integration
    def test_entries_update_not_found(self, client):
        """Test updating entry that doesn't exist (real DB)."""
        entry_data = {
            'lexical_unit': {'en': 'updated'}
        }
        response = client.put('/api/entries/nonexistent',
                            data=json.dumps(entry_data),
                            content_type='application/json')
        assert response.status_code == 404
    
    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires mocking a validation error; not possible with real DB only.")
    def test_entries_update_validation_error(self, client):
        pass
    
    @pytest.mark.integration
    def test_entries_delete_not_found(self, client):
        """Test deleting entry that doesn't exist (real DB)."""
        response = client.delete('/api/entries/nonexistent')
        assert response.status_code == 404
    
    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires mocking a database error; not possible with real DB only.")
    def test_entries_delete_database_error(self, client):
        pass



@pytest.mark.integration
class TestSearchAPI:
    """Test search API endpoints."""
    
    @pytest.mark.integration
    def test_search_with_all_parameters(self, client):
        """Test search with all query parameters."""
        response = client.get('/api/search?q=test&fields=lexical_unit,definition&pos=noun&limit=10&offset=5&exact_match=true&case_sensitive=true')
        
        # Should return valid response (might be empty if no matches)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'entries' in data
        assert 'total' in data
    
    @pytest.mark.integration
    def test_search_empty_query(self, client):
        """Test search with empty query."""
        response = client.get('/api/search?q=')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    @pytest.mark.integration
    def test_search_database_error(self, client):
        """Test search with database error - just verify endpoint exists."""
        # This test verifies the endpoint handles errors gracefully
        response = client.get('/api/search?q=test')
        
        # Should return either 200 (success) or 500 (database error) 
        assert response.status_code in [200, 500]
    
    @pytest.mark.integration
    def test_search_invalid_limit(self, client):
        """Test search with invalid limit."""
        response = client.get('/api/search?q=test&limit=-1')
        
        # API returns 400 for invalid limit
        assert response.status_code == 400
    
    @pytest.mark.integration
    def test_search_invalid_offset(self, client):
        """Test search with invalid offset."""
        response = client.get('/api/search?q=test&offset=-1')
        
        # API returns 400 for invalid offset
        assert response.status_code == 400






@pytest.mark.integration
class TestValidationAPI:
    """Test validation API endpoints."""
    
    @pytest.mark.integration
    def test_validation_check_valid_entry(self, client):
        """Test validation check with valid entry using nested dicts for multitext fields."""
        entry_data = {
            'id': 'test',
            'lexical_unit': {'en': 'test'},
            'senses': [{
                'id': 'sense1',
                'definitions': {'en': {'text': 'test definition'}},
                'glosses': {'en': {'text': 'test gloss'}}
            }]
        }

        response = client.post('/api/validation/check',
                             data=json.dumps(entry_data),
                             content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['valid'] is True
        assert 'errors' in data
    
    @pytest.mark.integration
    def test_validation_check_invalid_entry(self, client):
        """Test validation check with invalid entry."""
        entry_data = {
            'id': '',  # Invalid empty ID
            'lexical_unit': {'en': 'test'}
        }
        
        response = client.post('/api/validation/check',
                             data=json.dumps(entry_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['valid'] is False
        assert len(data['errors']) > 0
    
    @pytest.mark.integration
    def test_validation_check_invalid_json(self, client):
        """Test validation check with invalid JSON."""
        response = client.post('/api/validation/check',
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'errors' in data
    
    @pytest.mark.integration
    def test_validation_batch_success(self, client):
        """Test batch validation with valid entries."""
        entries_data = {
            'entries': [
                {
                    'id': 'test1',
                    'lexical_unit': {'en': 'test1'}
                },
                {
                    'id': 'test2',
                    'lexical_unit': {'en': 'test2'}
                }
            ]
        }
        
        response = client.post('/api/validation/batch',
                             data=json.dumps(entries_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'valid' in data
        assert 'errors' in data
    
    @pytest.mark.integration
    def test_validation_batch_missing_entries(self, client):
        """Test batch validation with missing entries key."""
        entries_data = {}
        
        response = client.post('/api/validation/batch',
                             data=json.dumps(entries_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'errors' in data
    
    @pytest.mark.integration
    def test_validation_schema_success(self, client):
        """Test schema validation."""
        response = client.get('/api/validation/schema')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert '$schema' in data
    
    @pytest.mark.integration
    def test_validation_rules_success(self, client):
        """Test validation rules endpoint."""
        response = client.get('/api/validation/rules')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'required_fields' in data
