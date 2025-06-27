"""
Real Integration Tests for API Endpoints
Tests API endpoints with actual database operations using real data.
"""
import os
import sys
import pytest
import tempfile
import json
import uuid
from flask import Flask
from unittest.mock import patch

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.entry import Entry
from app.models.sense import Sense
from app.services.dictionary_service import DictionaryService


class TestAPIIntegration:
    """Real integration tests for API endpoints."""
    
    @pytest.fixture(scope="class")
    def app(self):
        """Create Flask app for testing."""
        app = create_app(config_name='testing')
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        return app
    
    @pytest.fixture(scope="class") 
    def client(self, app):
        """Create test client."""
        return app.test_client()
        
    @pytest.fixture(scope="class")
    def dict_service(self, app):
        """Get dictionary service instance."""
        with app.app_context():
            return app.dict_service
    
    def test_api_entries_get_list(self, client, dict_service):
        """Test GET /api/entries - list entries."""
        # First create some test entries
        entry1 = Entry(
            id="api_test_1",
            lexical_unit={"en": "api_test1", "pl": "test_api1"},
            senses=[
                Sense(
                    id="api_sense_1",
                    gloss="API test gloss",
                    definition="API test definition"
                )
            ]
        )
        dict_service.create_entry(entry1)
        
        # Test API endpoint
        response = client.get('/api/entries')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'entries' in data
        assert isinstance(data['entries'], list)
        assert len(data['entries']) >= 1
        
        # Find our test entry
        test_entry = None
        for entry in data['entries']:
            if entry['id'] == 'api_test_1':
                test_entry = entry
                break
        
        assert test_entry is not None
        assert test_entry['lexical_unit']['en'] == 'api_test1'
        
    def test_api_entries_get_single(self, client, dict_service):
        """Test GET /api/entries/<id> - get single entry."""
        # Create test entry
        entry = Entry(
            id="api_single_test",
            lexical_unit={"en": "single_test", "pl": "pojedynczy_test"},
            senses=[
                Sense(
                    id="single_sense",
                    gloss="Single test gloss",
                    definition="Single test definition"
                )
            ]
        )
        dict_service.create_entry(entry)
        
        # Test API endpoint
        response = client.get('/api/entries/api_single_test')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['id'] == 'api_single_test'
        assert data['lexical_unit']['en'] == 'single_test'
        assert len(data['senses']) == 1
        assert data['senses'][0]['gloss'] == 'Single test gloss'
        
    def test_api_entries_create(self, client):
        """Test POST /api/entries - create new entry."""
        new_entry_data = {
            "id": "api_create_test",
            "lexical_unit": {
                "en": "create_test",
                "pl": "test_tworzenia"
            },
            "senses": [
                {
                    "id": "create_sense_1",
                    "gloss": "Create test gloss",
                    "definition": "Create test definition"
                }
            ]
        }
        
        response = client.post('/api/entries', 
                             data=json.dumps(new_entry_data),
                             content_type='application/json')
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['entry_id'] == 'api_create_test'
        
        # Verify entry was created by getting it back
        get_response = client.get('/api/entries/api_create_test')
        assert get_response.status_code == 200
        
    def test_api_entries_update(self, client, dict_service):
        """Test PUT /api/entries/<id> - update entry."""
        # Create entry to update
        entry = Entry(
            id="api_update_test",
            lexical_unit={"en": "update_original", "pl": "oryginalny"},
            senses=[
                Sense(
                    id="update_sense",
                    gloss="Original gloss",
                    definition="Original definition"
                )
            ]
        )
        dict_service.create_entry(entry)
        
        # Update data
        update_data = {
            "id": "api_update_test",
            "lexical_unit": {
                "en": "update_modified",
                "pl": "zmodyfikowany"
            },
            "senses": [
                {
                    "id": "update_sense",
                    "gloss": "Modified gloss",
                    "definition": "Modified definition"
                }
            ]
        }
        
        response = client.put('/api/entries/api_update_test',
                            data=json.dumps(update_data),
                            content_type='application/json')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify update by getting the entry back
        get_response = client.get('/api/entries/api_update_test')
        assert get_response.status_code == 200
        
        updated_entry = json.loads(get_response.data)
        assert updated_entry['lexical_unit']['en'] == 'update_modified'
        
    def test_api_entries_delete(self, client, dict_service):
        """Test DELETE /api/entries/<id> - delete entry."""
        # Create entry to delete
        entry = Entry(
            id="api_delete_test",
            lexical_unit={"en": "delete_test", "pl": "test_usuwania"},
            senses=[
                Sense(
                    id="delete_sense",
                    gloss="Delete test gloss",
                    definition="Delete test definition"
                )
            ]
        )
        dict_service.create_entry(entry)
        
        # Verify entry exists
        get_response = client.get('/api/entries/api_delete_test')
        assert get_response.status_code == 200
        
        # Delete the entry
        delete_response = client.delete('/api/entries/api_delete_test')
        assert delete_response.status_code == 200
        
        data = json.loads(delete_response.data)
        assert data['success'] is True
        
        # Verify entry is deleted
        get_response_after = client.get('/api/entries/api_delete_test')
        assert get_response_after.status_code == 404
        
    def test_api_search(self, client, dict_service):
        """Test GET /api/search - search entries."""
        # Create searchable entries
        entry1 = Entry(
            id="search_test_1",
            lexical_unit={"en": "searchable_word", "pl": "słowo_do_wyszukania"},
            senses=[
                Sense(
                    id="search_sense_1",
                    gloss="Searchable gloss",
                    definition="Searchable definition"
                )
            ]
        )
        dict_service.create_entry(entry1)
        
        # Test search
        response = client.get('/api/search?q=searchable')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'results' in data
        assert 'total' in data
        assert isinstance(data['results'], list)
        assert data['total'] >= 1
        
        # Find our test entry in results
        found = False
        for result in data['results']:
            if result['id'] == 'search_test_1':
                found = True
                break
        assert found, "Test entry not found in search results"
        
    def test_api_export_lift(self, client):
        """Test GET /api/export/lift - export LIFT format."""
        response = client.get('/api/export/lift')
        assert response.status_code == 200
        assert response.content_type == 'application/xml; charset=utf-8'
        
        # Check that response contains valid XML
        xml_content = response.data.decode('utf-8')
        assert '<?xml version=' in xml_content
        assert '<lift' in xml_content
        
    def test_api_validation_check(self, client):
        """Test POST /api/validation/check - validate entry data."""
        valid_entry_data = {
            "id": "validation_test",
            "lexical_unit": {
                "en": "valid_word",
                "pl": "poprawne_słowo"
            },
            "senses": [
                {
                    "id": "valid_sense",
                    "gloss": "Valid gloss",
                    "definition": "Valid definition"
                }
            ]
        }
        
        response = client.post('/api/validation/check',
                             data=json.dumps(valid_entry_data),
                             content_type='application/json')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'valid' in data
        assert 'errors' in data
        
    def test_api_error_handling(self, client):
        """Test API error handling."""
        # Test 404 for non-existent entry
        response = client.get('/api/entries/non_existent_entry_xyz')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        
        # Test invalid JSON in POST
        response = client.post('/api/entries',
                             data='invalid json',
                             content_type='application/json')
        assert response.status_code == 400
        
        # Test missing required fields
        response = client.post('/api/entries',
                             data=json.dumps({"invalid": "data"}),
                             content_type='application/json')
        assert response.status_code == 400


class TestExporterIntegration:
    """Integration tests for export functionality with real data."""
    
    @pytest.fixture(scope="class")
    def app(self):
        """Create Flask app for testing."""
        app = create_app(config_name='testing')
        app.config['TESTING'] = True
        return app
        
    @pytest.fixture(scope="class")
    def dict_service(self, app):
        """Get dictionary service instance."""
        with app.app_context():
            return app.dict_service
    
    def test_kindle_exporter_integration(self, dict_service):
        """Test Kindle export with real data."""
        from app.exporters.kindle_exporter import KindleExporter
        
        # Create test entry
        entry = Entry(
            id="kindle_export_test",
            lexical_unit={"en": "kindle_word", "pl": "słowo_kindle"},
            senses=[
                Sense(
                    id="kindle_sense",
                    gloss="Kindle test gloss",
                    definition="Kindle test definition"
                )
            ]
        )
        dict_service.create_entry(entry)
        
        # Test export
        exporter = KindleExporter(dict_service)
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
            try:
                exporter.export(temp_file.name, title="Test Dictionary")
                
                # Verify file was created and has content
                assert os.path.exists(temp_file.name)
                with open(temp_file.name, 'r', encoding='utf-8') as f:
                    content = f.read()
                    assert len(content) > 0
                    assert 'kindle_word' in content
                    assert 'Test Dictionary' in content
                    
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    def test_sqlite_exporter_integration(self, dict_service):
        """Test SQLite export with real data."""
        from app.exporters.sqlite_exporter import SQLiteExporter
        
        # Create test entry  
        entry = Entry(
            id="sqlite_export_test",
            lexical_unit={"en": "sqlite_word", "pl": "słowo_sqlite"},
            senses=[
                Sense(
                    id="sqlite_sense",
                    gloss="SQLite test gloss",
                    definition="SQLite test definition"
                )
            ]
        )
        dict_service.create_entry(entry)
        
        # Test export
        exporter = SQLiteExporter(dict_service)
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            try:
                exporter.export(temp_file.name)
                
                # Verify file was created
                assert os.path.exists(temp_file.name)
                assert os.path.getsize(temp_file.name) > 0
                
                # Test that it's a valid SQLite file
                import sqlite3
                conn = sqlite3.connect(temp_file.name)
                cursor = conn.cursor()
                
                # Check tables exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                assert len(tables) > 0
                
                conn.close()
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)


class TestEnhancedParserIntegration:
    """Integration tests for enhanced LIFT parser with real data."""
    
    @pytest.fixture(scope="class")
    def sample_lift_content(self):
        """Sample LIFT content for testing."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.15">
    <entry id="enhanced_parser_test">
        <lexical-unit>
            <form lang="en"><text>enhanced_test</text></form>
            <form lang="pl"><text>ulepszony_test</text></form>
        </lexical-unit>
        <sense id="enhanced_sense_1">
            <gloss lang="en"><text>Enhanced test gloss</text></gloss>
            <definition>
                <form lang="en"><text>Enhanced test definition</text></form>
            </definition>
            <grammatical-info value="Noun"/>
            <example>
                <form lang="en"><text>This is an enhanced example.</text></form>
                <translation>
                    <form lang="pl"><text>To jest ulepszony przykład.</text></form>
                </translation>
            </example>
        </sense>
    </entry>
</lift>'''
    
    def test_enhanced_lift_parser_parsing(self, sample_lift_content):
        """Test enhanced LIFT parser with real content."""
        from app.parsers.enhanced_lift_parser import EnhancedLiftParser
        
        parser = EnhancedLiftParser()
        
        # Create temporary file with LIFT content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(sample_lift_content)
            temp_path = temp_file.name
        
        try:
            # Parse the file
            entries = parser.parse_file(temp_path)
            
            assert len(entries) == 1
            entry = entries[0]
            
            assert entry.id == "enhanced_parser_test"
            assert entry.lexical_unit["en"] == "enhanced_test" 
            assert entry.lexical_unit["pl"] == "ulepszony_test"
            
            assert len(entry.senses) == 1
            sense = entry.senses[0]
            
            assert sense.id == "enhanced_sense_1"
            assert sense.gloss == "Enhanced test gloss"
            assert sense.definition == "Enhanced test definition"
            assert sense.grammatical_info == "Noun"
            
            # Check examples
            assert len(sense.examples) == 1
            example = sense.examples[0]
            assert "This is an enhanced example." in str(example)
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
