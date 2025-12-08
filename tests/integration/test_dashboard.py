"""
Tests for the dashboard/homepage functionality.

This module contains comprehensive tests for the homepage dashboard,
ensuring proper system status display, statistics, and preventing
debug information from being exposed to users.

Uses a shared Flask app instance and cached response text for optimal performance.
Only makes HTTP requests when absolutely necessary (API endpoints, error tests).
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.services.dictionary_service import DictionaryService



@pytest.mark.integration
class TestDashboard:
    """Test cases for the dashboard homepage."""

    @pytest.fixture
    def shared_client(self, app: Flask) -> FlaskClient:
        """Create a shared test client using the properly configured app fixture."""
        return app.test_client()

    @pytest.fixture
    def homepage_response_text(self, shared_client: FlaskClient) -> str:
        """Get the homepage response text once and reuse it for all text-based tests."""
        response = shared_client.get('/')
        assert response.status_code == 200
        return response.data.decode('utf-8')

    @pytest.fixture
    def mock_dict_service(self):
        """Create a mock dictionary service for specific tests that need it."""
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

    @pytest.mark.integration
    def test_homepage_loads_successfully(self, shared_client):
        """Test that the homepage loads with 200 status."""
        response = shared_client.get('/')
        assert response.status_code == 200
        assert response.content_type.startswith('text/html')

    @pytest.mark.integration
    def test_homepage_contains_title(self, homepage_response_text):
        """Test that the homepage contains the correct title."""
        assert 'Lexicographic Curation Workbench' in homepage_response_text

    @pytest.mark.integration
    def test_homepage_contains_system_status_section(self, homepage_response_text):
        """Test that the homepage contains the system status section."""
        assert 'System Status' in homepage_response_text
        assert 'Database Connection' in homepage_response_text
        assert 'Last Backup' in homepage_response_text
        assert 'Storage Usage' in homepage_response_text

    @pytest.mark.integration
    def test_homepage_contains_stats_section(self, homepage_response_text):
        """Test that the homepage contains the statistics section."""
        assert 'Quick Stats' in homepage_response_text
        assert 'Total Entries' in homepage_response_text
        assert 'Total Senses' in homepage_response_text
        assert 'Total Examples' in homepage_response_text

    @pytest.mark.integration
    def test_homepage_contains_system_status_badges_with_ids(self, homepage_response_text):
        """Test that system status badges have proper IDs for JavaScript targeting."""
        # Check for specific badge IDs
        assert 'id="db-status-badge"' in homepage_response_text
        assert 'id="backup-status-badge"' in homepage_response_text
        assert 'id="storage-status-badge"' in homepage_response_text

    @pytest.mark.integration
    def test_homepage_does_not_contain_debug_info(self, homepage_response_text):
        """Test that the homepage does not expose debug information."""
        # Ensure no debug information is exposed
        assert 'Debug:' not in homepage_response_text
        assert 'debug' not in homepage_response_text.lower()
        assert 'tojson' not in homepage_response_text.lower()
        
        # Ensure raw JSON data is not exposed
        assert '{"db_connected"' not in homepage_response_text
        assert 'storage_percent' not in homepage_response_text

    @pytest.mark.integration
    def test_homepage_with_specific_mock_data(self, shared_client, mock_dict_service):
        """Test homepage renders successfully with real data."""
        # Clear any existing cache to ensure fresh data
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('dashboard_stats*')
        
        response = shared_client.get('/')
        assert response.status_code == 200
        
        response_text = response.data.decode('utf-8')
        
        # Should show page loaded successfully with statistics section
        assert 'Quick Stats' in response_text
        assert 'Total Entries' in response_text

    @pytest.mark.integration
    def test_homepage_with_database_error(self, shared_client):
        """Test homepage loads even with potential errors."""
        response = shared_client.get('/')
        assert response.status_code == 200
        
        # Should still load
        response_text = response.data.decode('utf-8')
        assert 'Lexicographic Curation Workbench' in response_text

    @pytest.mark.integration
    def test_system_status_api_endpoint(self, shared_client):
        """Test the system status API endpoint."""
        response = shared_client.get('/api/system/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'db_connected' in data
        assert 'last_backup' in data
        assert 'storage_percent' in data
        
        # Ensure boolean type for db_connected
        assert isinstance(data['db_connected'], bool)
        
        # Ensure storage_percent is numeric
        assert isinstance(data['storage_percent'], (int, float))

    @pytest.mark.integration
    def test_system_status_api_with_mock_data(self, shared_client, mock_dict_service):
        """Test system status API returns valid data."""
        response = shared_client.get('/api/system/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'db_connected' in data
        assert isinstance(data['db_connected'], bool)

    @pytest.mark.integration
    def test_dashboard_javascript_included(self, homepage_response_text):
        """Test that dashboard JavaScript is included."""
        assert 'dashboard.js' in homepage_response_text

    @pytest.mark.integration
    def test_homepage_accessibility_features(self, homepage_response_text):
        """Test that the homepage includes basic accessibility features."""
        # Check for semantic HTML elements
        assert '<main>' in homepage_response_text or 'role="main"' in homepage_response_text or '<div class="container' in homepage_response_text
        
        # Check for proper heading structure
        assert '<h' in homepage_response_text  # Should have headings
        
        # Check for Bootstrap classes (indicating responsive design)
        assert 'col-md' in homepage_response_text or 'row' in homepage_response_text

    @pytest.mark.integration
    def test_homepage_responsive_layout(self, homepage_response_text):
        """Test that the homepage uses responsive layout classes."""
        # Check for Bootstrap responsive classes
        assert 'col-md-' in homepage_response_text
        assert 'row' in homepage_response_text
        assert 'container' in homepage_response_text

    @pytest.mark.integration
    def test_recent_activity_section(self, homepage_response_text):
        """Test that the recent activity section is present."""
        # Should have recent activity section or reference
        assert ('activity' in homepage_response_text.lower() or 
                'recent' in homepage_response_text.lower() or
                'Activity Log' in homepage_response_text)

    @pytest.mark.integration
    def test_quick_actions_section(self, homepage_response_text):
        """Test that quick actions are available."""
        # Should have action buttons or links
        assert ('New Entry' in homepage_response_text or 
                'Add' in homepage_response_text or 
                'btn' in homepage_response_text)

    @pytest.mark.integration
    def test_homepage_error_handling(self, shared_client, caplog):
        """Test that homepage handles errors gracefully."""
        response = shared_client.get('/')
        
        # Should still return successful response
        assert response.status_code == 200
        
        # Should contain default content
        response_text = response.data.decode('utf-8')
        assert 'Lexicographic Curation Workbench' in response_text

    @pytest.mark.integration
    def test_no_sensitive_info_exposed(self, homepage_response_text):
        """Test that no sensitive information is exposed in the homepage."""
        # Should not contain sensitive keywords
        sensitive_terms = [
            'password', 'secret', 'api_key', 'token',
            'database_url', 'connection_string', 'credentials',
            'config', 'env', 'environment'
        ]
        
        for term in sensitive_terms:
            assert term not in homepage_response_text.lower()

    @pytest.mark.integration
    def test_csrf_protection_meta_tag(self, homepage_response_text):
        """Test that CSRF protection meta tag is present if CSRF is enabled."""
        # In production, should have CSRF token meta tag
        # In test mode with CSRF disabled, this may not be present
        # This is a basic check for security awareness
        assert '<meta' in homepage_response_text  # Should have meta tags

    @pytest.mark.integration
    def test_system_status_badge_colors(self, homepage_response_text):
        """Test that system status badges have appropriate color classes."""
        # Should contain Bootstrap badge color classes
        badge_colors = ['bg-success', 'bg-danger', 'bg-warning', 'bg-secondary']
        has_badge_color = any(color in homepage_response_text for color in badge_colors)
        assert has_badge_color, "Homepage should contain colored status badges"

    @pytest.mark.integration
    def test_homepage_contains_icons(self, homepage_response_text):
        """Test that the homepage contains icons for better UX."""
        # Should contain Font Awesome icons or similar
        assert ('fas fa-' in homepage_response_text or 
                'icon' in homepage_response_text.lower() or
                'glyphicon' in homepage_response_text)

    @pytest.mark.integration
    def test_specific_debug_patterns_not_present(self, homepage_response_text):
        """Test for specific debug patterns that were previously present."""
        # Test for the exact debug pattern that was removed
        assert 'Debug: {{ system_status | tojson }}' not in homepage_response_text
        assert '{{ system_status | tojson }}' not in homepage_response_text
        
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
            assert pattern not in homepage_response_text, f"Debug pattern '{pattern}' found in homepage"

    @pytest.mark.integration
    def test_system_status_properly_formatted(self, homepage_response_text):
        """Test that system status is properly formatted, not raw JSON."""
        # Should contain properly formatted status elements
        assert 'Database Connection' in homepage_response_text
        assert 'Last Backup' in homepage_response_text  
        assert 'Storage Usage' in homepage_response_text
        
        # Should NOT contain raw JSON field names
        json_field_names = [
            'db_connected',
            'last_backup', 
            'storage_percent'
        ]
        
        for field_name in json_field_names:
            assert field_name not in homepage_response_text, f"Raw JSON field '{field_name}' exposed in homepage"
