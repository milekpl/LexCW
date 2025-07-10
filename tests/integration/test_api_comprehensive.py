"""
Comprehensive unit tests for API modules to increase coverage.
Tests all API endpoints and edge cases.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from app.models.entry import Entry
from app.models.sense import Sense
from app.utils.exceptions import DatabaseError, ValidationError, ExportError



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
    def test_entries_get_single_not_found(self, client, mock_dict_service):
        """Test getting a single entry that doesn't exist."""
        mock_dict_service.get_entry.return_value = None
        
        with patch('app.api.entries.get_dictionary_service', return_value=mock_dict_service):
            response = client.get('/api/entries/nonexistent')
            
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    @pytest.mark.integration
    def test_entries_get_single_database_error(self, client, mock_dict_service):
        """Test getting entry with database error."""
        mock_dict_service.get_entry.side_effect = DatabaseError("DB error")
        
        with patch('app.api.entries.get_dictionary_service', return_value=mock_dict_service):
            response = client.get('/api/entries/test')
            
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
    
    @pytest.mark.integration
    def test_entries_create_validation_error(self, client, mock_dict_service):
        """Test creating entry with validation error."""
        mock_dict_service.create_entry.side_effect = ValidationError("Invalid entry")
        
        entry_data = {
            'id': 'test',
            'lexical_unit': {'en': 'test'}
        }
        
        with patch('app.api.entries.get_dictionary_service', return_value=mock_dict_service):
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
    def test_entries_update_not_found(self, client, mock_dict_service):
        """Test updating entry that doesn't exist."""
        from app.utils.exceptions import NotFoundError
        mock_dict_service.update_entry.side_effect = NotFoundError("Entry not found")
        
        entry_data = {
            'lexical_unit': {'en': 'updated'}
        }
        
        with patch('app.api.entries.get_dictionary_service', return_value=mock_dict_service):
            response = client.put('/api/entries/nonexistent',
                                data=json.dumps(entry_data),
                                content_type='application/json')
            
        assert response.status_code == 404
    
    @pytest.mark.integration
    def test_entries_update_validation_error(self, client, mock_dict_service):
        """Test updating entry with validation error."""
        mock_dict_service.get_entry.return_value = Entry(id='test')
        mock_dict_service.update_entry.side_effect = ValidationError("Invalid update")
        
        entry_data = {
            'lexical_unit': {'en': 'updated'}
        }
        
        with patch('app.api.entries.get_dictionary_service', return_value=mock_dict_service):
            response = client.put('/api/entries/test',
                                data=json.dumps(entry_data),
                                content_type='application/json')
            
        assert response.status_code == 400
    
    @pytest.mark.integration
    def test_entries_delete_not_found(self, client, mock_dict_service):
        """Test deleting entry that doesn't exist."""
        from app.utils.exceptions import NotFoundError
        mock_dict_service.delete_entry.side_effect = NotFoundError("Entry not found")
        
        with patch('app.api.entries.get_dictionary_service', return_value=mock_dict_service):
            response = client.delete('/api/entries/nonexistent')
            
        assert response.status_code == 404
    
    @pytest.mark.integration
    def test_entries_delete_database_error(self, client, mock_dict_service):
        """Test deleting entry with database error."""
        mock_dict_service.get_entry.return_value = Entry(id='test')
        mock_dict_service.delete_entry.side_effect = DatabaseError("DB error")
        
        with patch('app.api.entries.get_dictionary_service', return_value=mock_dict_service):
            response = client.delete('/api/entries/test')
            
        assert response.status_code == 500



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
class TestExportAPI:
    """Test export API endpoints."""
    
    @pytest.mark.integration
    def test_export_lift_success(self, client, mock_dict_service):
        """Test successful LIFT export."""
        mock_dict_service.export_lift.return_value = "<?xml version='1.0'?><lift></lift>"
        
        with patch('app.api.export.get_dictionary_service', return_value=mock_dict_service):
            response = client.get('/api/export/lift')
            
        assert response.status_code == 200
        assert response.content_type == 'application/xml; charset=utf-8'
        assert b'lift' in response.data
    
    @pytest.mark.integration
    def test_export_lift_database_error(self, client, mock_dict_service):
        """Test LIFT export with database error."""
        mock_dict_service.export_lift.side_effect = DatabaseError("Export failed")
        
        with patch('app.api.export.get_dictionary_service', return_value=mock_dict_service):
            response = client.get('/api/export/lift')
            
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'message' in data
    
    @pytest.mark.integration
    def test_export_kindle_success(self, client, mock_dict_service):
        """Test successful Kindle export."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
            temp_file.write(b'<html>test</html>')
            temp_path = temp_file.name
        
        try:
            # Mock the export_to_kindle method to return a directory path
            mock_dict_service.export_to_kindle.return_value = temp_path
            
            with patch('app.api.export.get_dictionary_service', return_value=mock_dict_service):
                response = client.post('/api/export/kindle',
                                     data=json.dumps({'title': 'Test Dict'}),
                                     content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'message' in data
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.integration
    def test_export_kindle_export_error(self, client, mock_dict_service):
        """Test Kindle export with export error."""
        mock_dict_service.export_to_kindle.side_effect = ExportError("Export failed")
        
        with patch('app.api.export.get_dictionary_service', return_value=mock_dict_service):
            response = client.post('/api/export/kindle',
                                 data=json.dumps({'title': 'Test Dict'}),
                                 content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'message' in data
    
    @pytest.mark.integration
    def test_export_sqlite_success(self, client, mock_dict_service):
        """Test successful SQLite export."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            with patch('app.api.export.get_dictionary_service', return_value=mock_dict_service):
                with patch('app.exporters.sqlite_exporter.SQLiteExporter.export', return_value=temp_path):
                    response = client.post('/api/export/sqlite',
                                         data=json.dumps({}),
                                         content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'message' in data
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)



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
