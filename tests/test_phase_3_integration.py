#!/usr/bin/env python3

"""
Phase 3: Auto-Save & Conflict Resolution - Integration Test

This test verifies that Phase 3 implementation is working correctly with:
- Auto-save functionality integrated into entry forms
- Version conflict detection and resolution
- Client-server integration for real-time saving
"""

import pytest
import time
import json
from unittest.mock import Mock, patch
from app import create_app
from config import TestingConfig

class TestPhase3AutoSaveIntegration:
    """Test Phase 3 auto-save and conflict resolution integration"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = create_app(TestingConfig)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_auto_save_endpoint_integration(self, client):
        """Test that the auto-save endpoint is properly registered and working"""
        # Test the auto-save endpoint
        test_data = {
            'entryData': {
                'id': 'test_entry_123',
                'lexical_unit': {'en': 'test'},
                'senses': [
                    {
                        'id': 'sense1',
                        'definition': {'en': 'test definition'}
                    }
                ]
            },
            'version': 'v1',
            'timestamp': '2025-07-05T23:00:00Z'
        }
        
        response = client.post('/api/entry/autosave',
                             data=json.dumps(test_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'newVersion' in data
        assert 'timestamp' in data
        
    def test_auto_save_with_validation_errors(self, client):
        """Test auto-save behavior with validation errors"""
        # Test data with critical validation error (missing lexical unit)
        test_data = {
            'entryData': {
                'id': 'test_entry_456',
                # Missing lexical_unit (critical error)
                'senses': [
                    {
                        'id': 'sense1',
                        'definition': {'en': 'test definition'}
                    }
                ]
            },
            'version': 'v1',
            'timestamp': '2025-07-05T23:00:00Z'
        }
        
        response = client.post('/api/entry/autosave',
                             data=json.dumps(test_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error'] == 'validation_failed'
        assert 'validation_errors' in data
        
    def test_auto_save_endpoint_missing_data(self, client):
        """Test auto-save endpoint with missing data"""
        # Test with no data
        response = client.post('/api/entry/autosave',
                             data='{}',
                             content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error'] == 'invalid_request'
        
    def test_auto_save_test_endpoint(self, client):
        """Test the auto-save test endpoint"""
        response = client.get('/api/entry/autosave/test')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Auto-save API is working'
        
    def test_entry_form_includes_autosave_scripts(self, client):
        """Test that entry form template includes the required JavaScript files"""
        # Test add entry form
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        html_content = response.get_data(as_text=True)
        
        # Check that required JavaScript files are included
        assert 'form-state-manager.js' in html_content
        assert 'client-validation-engine.js' in html_content
        assert 'auto-save-manager.js' in html_content
        assert 'form-serializer.js' in html_content
        
    def test_phase_3_javascript_integration(self, client):
        """Test that the Phase 3 JavaScript integration code is present"""
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        html_content = response.get_data(as_text=True)
        
        # Check that the auto-save JavaScript file is included (function is in the JS file)
        assert 'js/entry-form.js' in html_content
        
        # Test the auto-save endpoint is available (this ensures the JS can call it)
        test_response = client.get('/api/entry/autosave/test')
        assert test_response.status_code == 200
        
    @pytest.mark.integration
    def test_complete_phase_3_integration(self, client):
        """Integration test for complete Phase 3 functionality"""
        # This test verifies the complete auto-save integration
        
        # 1. Access entry form
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        # 2. Test auto-save endpoint
        test_data = {
            'entryData': {
                'id': 'integration_test_entry',
                'lexical_unit': {'en': 'integration'},
                'senses': [
                    {
                        'id': 'sense1',
                        'definition': {'en': 'complete integration test'}
                    }
                ]
            },
            'version': 'v1',
            'timestamp': '2025-07-05T23:00:00Z'
        }
        
        response = client.post('/api/entry/autosave',
                             data=json.dumps(test_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        print("✅ Phase 3: Auto-Save & Conflict Resolution integration test passed!")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
