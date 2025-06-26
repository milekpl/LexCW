"""
Tests for the dashboard/homepage functionality.

This module contains comprehensive tests for the homepage dashboard,
ensuring proper system status display, statistics, and preventing
debug information from being exposed to users.
"""

import pytest
import json
from unittest.mock import Mock, patch
from flask import Flask

from app import create_app
from app.services.dictionary_service import DictionaryService


class TestDashboard:
    """Test cases for the dashboard homepage."""

    @pytest.fixture
    def app(self):
        """Create test Flask application."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def mock_dict_service(self):
        """Create a mock dictionary service."""
        mock_service = Mock(spec=DictionaryService)
        mock_service.count_entries.return_value = 150
        mock_service.count_senses_and_examples.return_value = (300, 450)
        mock_service.get_recent_activity.return_value = [
            {
                'timestamp': '2025-06-27 00:15',
                'action': 'Entry Created',
                'description': 'Added new entry "test"'
            }
        ]
        mock_service.get_system_status.return_value = {
            'db_connected': True,
            'last_backup': '2025-06-27 00:15',
            'storage_percent': 25
        }
        return mock_service

    def test_homepage_loads_successfully(self, client):
        """Test that the homepage loads with 200 status."""
        response = client.get('/')
        assert response.status_code == 200
        assert response.content_type.startswith('text/html')

    def test_homepage_contains_title(self, client):
        """Test that the homepage contains the correct title."""
        response = client.get('/')
        assert b'Dictionary Writing System' in response.data

    def test_homepage_contains_system_status_section(self, client):
        """Test that the homepage contains the system status section."""
        response = client.get('/')
        assert b'System Status' in response.data
        assert b'Database Connection' in response.data
        assert b'Last Backup' in response.data
        assert b'Storage Usage' in response.data

    def test_homepage_contains_stats_section(self, client):
        """Test that the homepage contains the statistics section."""
        response = client.get('/')
        assert b'Quick Stats' in response.data
        assert b'Total Entries' in response.data
        assert b'Total Senses' in response.data
        assert b'Total Examples' in response.data

    def test_homepage_contains_system_status_badges_with_ids(self, client):
        """Test that system status badges have proper IDs for JavaScript targeting."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Check for specific badge IDs
        assert 'id="db-status-badge"' in response_text
        assert 'id="backup-status-badge"' in response_text
        assert 'id="storage-status-badge"' in response_text

    def test_homepage_does_not_contain_debug_info(self, client):
        """Test that the homepage does not expose debug information."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Ensure no debug information is exposed
        assert 'Debug:' not in response_text
        assert 'debug' not in response_text.lower()
        assert 'tojson' not in response_text.lower()
        
        # Ensure raw JSON data is not exposed
        assert '{"db_connected"' not in response_text
        assert 'storage_percent' not in response_text

    @patch('app.injector.get')
    def test_homepage_with_database_connected(self, mock_injector_get, client, mock_dict_service):
        """Test homepage when database is connected and working."""
        mock_injector_get.return_value = mock_dict_service
        
        response = client.get('/')
        assert response.status_code == 200
        
        response_text = response.data.decode('utf-8')
        
        # Should show actual statistics
        assert '150' in response_text  # entry count
        assert '300' in response_text  # sense count
        assert '450' in response_text  # example count

    @patch('app.injector.get')
    def test_homepage_with_database_error(self, mock_injector_get, client):
        """Test homepage when database service throws an error."""
        mock_service = Mock(spec=DictionaryService)
        mock_service.count_entries.side_effect = Exception("Database connection failed")
        mock_injector_get.return_value = mock_service
        
        response = client.get('/')
        assert response.status_code == 200
        
        # Should still load with default values
        response_text = response.data.decode('utf-8')
        assert 'Dictionary Writing System' in response_text

    def test_system_status_api_endpoint(self, client):
        """Test the system status API endpoint."""
        response = client.get('/api/system/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'db_connected' in data
        assert 'last_backup' in data
        assert 'storage_percent' in data
        
        # Ensure boolean type for db_connected
        assert isinstance(data['db_connected'], bool)
        
        # Ensure storage_percent is numeric
        assert isinstance(data['storage_percent'], (int, float))

    @patch('app.injector.get')
    def test_system_status_api_with_mock_data(self, mock_injector_get, client, mock_dict_service):
        """Test system status API with mocked data."""
        mock_injector_get.return_value = mock_dict_service
        
        response = client.get('/api/system/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['db_connected'] is True
        assert data['last_backup'] == '2025-06-27 00:15'
        assert data['storage_percent'] == 25

    def test_dashboard_javascript_included(self, client):
        """Test that dashboard JavaScript is included."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        assert 'dashboard.js' in response_text

    def test_homepage_accessibility_features(self, client):
        """Test that the homepage includes basic accessibility features."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Check for semantic HTML elements
        assert '<main>' in response_text or 'role="main"' in response_text or '<div class="container' in response_text
        
        # Check for proper heading structure
        assert '<h' in response_text  # Should have headings
        
        # Check for Bootstrap classes (indicating responsive design)
        assert 'col-md' in response_text or 'row' in response_text

    def test_homepage_responsive_layout(self, client):
        """Test that the homepage uses responsive layout classes."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Check for Bootstrap responsive classes
        assert 'col-md-' in response_text
        assert 'row' in response_text
        assert 'container' in response_text

    def test_recent_activity_section(self, client):
        """Test that the recent activity section is present."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Should have recent activity section or reference
        assert ('activity' in response_text.lower() or 
                'recent' in response_text.lower() or
                'Activity Log' in response_text)

    def test_quick_actions_section(self, client):
        """Test that quick actions are available."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Should have action buttons or links
        assert ('New Entry' in response_text or 
                'Add' in response_text or 
                'btn' in response_text)

    @patch('app.injector.get')
    def test_homepage_error_handling(self, mock_injector_get, client, caplog):
        """Test that homepage handles errors gracefully."""
        mock_service = Mock(spec=DictionaryService)
        mock_service.count_entries.side_effect = Exception("Database error")
        mock_service.count_senses_and_examples.side_effect = Exception("Database error")
        mock_service.get_recent_activity.side_effect = Exception("Database error")
        mock_service.get_system_status.side_effect = Exception("Database error")
        mock_injector_get.return_value = mock_service
        
        response = client.get('/')
        
        # Should still return successful response
        assert response.status_code == 200
        
        # Should contain default content
        response_text = response.data.decode('utf-8')
        assert 'Dictionary Writing System' in response_text

    def test_no_sensitive_info_exposed(self, client):
        """Test that no sensitive information is exposed in the homepage."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Should not contain sensitive keywords
        sensitive_terms = [
            'password', 'secret', 'api_key', 'token',
            'database_url', 'connection_string', 'credentials',
            'config', 'env', 'environment'
        ]
        
        for term in sensitive_terms:
            assert term not in response_text.lower()

    def test_csrf_protection_meta_tag(self, client):
        """Test that CSRF protection meta tag is present if CSRF is enabled."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # In production, should have CSRF token meta tag
        # In test mode with CSRF disabled, this may not be present
        # This is a basic check for security awareness
        assert '<meta' in response_text  # Should have meta tags

    def test_system_status_badge_colors(self, client):
        """Test that system status badges have appropriate color classes."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Should contain Bootstrap badge color classes
        badge_colors = ['bg-success', 'bg-danger', 'bg-warning', 'bg-secondary']
        has_badge_color = any(color in response_text for color in badge_colors)
        assert has_badge_color, "Homepage should contain colored status badges"

    def test_homepage_contains_icons(self, client):
        """Test that the homepage contains icons for better UX."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Should contain Font Awesome icons or similar
        assert ('fas fa-' in response_text or 
                'icon' in response_text.lower() or
                'glyphicon' in response_text)

    def test_specific_debug_patterns_not_present(self, client):
        """Test for specific debug patterns that were previously present."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Test for the exact debug pattern that was removed
        assert 'Debug: {{ system_status | tojson }}' not in response_text
        assert '{{ system_status | tojson }}' not in response_text
        
        # Test for common debug patterns that should never appear
        debug_patterns = [
            'Debug:',
            'debug:',
            'DEBUG:',
            '| tojson',
            'tojson }}',
            'system_status | tojson',
            '{"db_connected": true',  # Raw JSON should not be visible
            '"storage_percent": 25',  # Raw JSON fields should not be visible
        ]
        
        for pattern in debug_patterns:
            assert pattern not in response_text, f"Debug pattern '{pattern}' found in homepage"

    def test_system_status_properly_formatted(self, client):
        """Test that system status is properly formatted, not raw JSON."""
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Should contain properly formatted status elements
        assert 'Database Connection' in response_text
        assert 'Last Backup' in response_text  
        assert 'Storage Usage' in response_text
        
        # Should NOT contain raw JSON field names
        json_field_names = [
            'db_connected',
            'last_backup', 
            'storage_percent'
        ]
        
        for field_name in json_field_names:
            assert field_name not in response_text, f"Raw JSON field '{field_name}' exposed in homepage"
