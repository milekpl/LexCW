import os
import sys
import json
import pytest
from flask import Flask
from unittest.mock import Mock

# Add project root to sys.path to ensure correct module resolution for patching
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app
from app.services.dictionary_service import DictionaryService


@pytest.mark.integration
class TestDropDatabaseIntegration:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        # Set TESTING env var before create_app to prevent premature BaseX connection attempt
        os.environ['TESTING'] = 'true'
        os.environ['FLASK_ENV'] = 'testing'

        self.app = create_app(config_name='testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        yield
        self.app_context.pop()

    def test_drop_database_content_success(self):
        """Test successful dropping of database content via API."""
        with self.app.app_context():
            # Mock the dictionary service
            mock_dict_service = Mock()
            self.app.dict_service = mock_dict_service

            # Make the API call
            response = self.client.post('/settings/drop-database',
                                      content_type='application/json',
                                      data=json.dumps({'action': 'drop'}))

            # Check response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'message' in data

            # Verify the service method was called
            mock_dict_service.drop_database_content.assert_called_once()

    def test_drop_database_content_service_unavailable(self):
        """Test drop database when service is unavailable."""
        with self.app.app_context():
            # Remove dict_service if it exists
            if hasattr(self.app, 'dict_service'):
                delattr(self.app, 'dict_service')
            if hasattr(self.app, 'injector'):
                # Mock injector to raise exception
                original_injector = self.app.injector
                self.app.injector = Mock()
                self.app.injector.get.side_effect = Exception("Service unavailable")

                try:
                    # Make the API call
                    response = self.client.post('/settings/drop-database',
                                              content_type='application/json')

                    # Check response
                    assert response.status_code == 500
                    data = json.loads(response.data)
                    assert data['success'] is False
                    assert 'error' in data
                finally:
                    self.app.injector = original_injector

    def test_drop_database_content_service_error(self):
        """Test drop database when service raises an error."""
        with self.app.app_context():
            # Mock the dictionary service to raise an error
            mock_dict_service = Mock()
            mock_dict_service.drop_database_content.side_effect = Exception("Database error")
            self.app.dict_service = mock_dict_service

            # Make the API call
            response = self.client.post('/settings/drop-database',
                                      content_type='application/json')

            # Check response
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data

    def test_drop_database_content_method_get_not_allowed(self):
        """Test that GET requests to drop-database are not allowed."""
        response = self.client.get('/settings/drop-database')

        # Should return 405 Method Not Allowed
        assert response.status_code == 405


if __name__ == '__main__':
    pytest.main([__file__, '-v'])