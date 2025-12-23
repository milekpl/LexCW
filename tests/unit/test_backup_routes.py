"""Unit tests for backup routes.

Tests that the backup management routes are properly registered and accessible.
"""

from __future__ import annotations

import pytest
from flask import Flask, url_for, current_app


class TestBackupRoutes:
    """Test suite for backup route functionality."""

    def test_backup_management_route_exists(self, client):
        """Test that the backup management route is registered and accessible."""
        # Test that the route exists and returns a successful response
        response = client.get('/backup/management')
        assert response.status_code == 200
        assert b'Backup Management' in response.data

    def test_backup_management_url_for_works(self, app: Flask):
        """Test that url_for works correctly for backup management endpoint."""
        with app.app_context():
            # Configure SERVER_NAME to allow url_for to work
            app.config['SERVER_NAME'] = 'localhost:5000'
            # Test that url_for can generate the correct URL
            with app.test_request_context():
                url = url_for('backup.backup_management')
                assert url == '/backup/management'

    def test_backup_management_template_renders(self, client):
        """Test that the backup management template renders correctly."""
        response = client.get('/backup/management')
        assert response.status_code == 200
        # Check for key elements in the backup management page
        assert b'Backup Management' in response.data
        assert b'Create Backup' in response.data or b'Create' in response.data
        assert b'Backup History' in response.data or b'History' in response.data

    def test_backup_route_not_found(self, client):
        """Test that the old /backup/ route returns 404 (to verify the fix)."""
        # The old incorrect route should return 404
        response = client.get('/backup/')
        assert response.status_code == 404

    def test_backup_blueprint_registration(self, app: Flask):
        """Test that the backup blueprint is properly registered."""
        # Check that the backup blueprint exists
        assert 'backup' in app.blueprints
        backup_bp = app.blueprints['backup']
        assert backup_bp.name == 'backup'
        assert backup_bp.url_prefix == '/backup'

    def test_backup_management_route_methods(self, client):
        """Test that the backup management route only accepts GET requests."""
        # GET should work
        get_response = client.get('/backup/management')
        assert get_response.status_code == 200
        
        # POST should not be allowed
        post_response = client.post('/backup/management')
        assert post_response.status_code in [405, 404]  # Method Not Allowed or Not Found

    def test_backup_download_route_exists(self, client):
        """Test that the backup download route is registered."""
        # The download route should exist (though it may require authentication)
        # We just test that the route is registered, not that it works fully
        with client:
            response = client.get('/backup/download')
            # This might redirect or require auth, but the route should exist
            assert response.status_code in [200, 302, 401, 403]  # OK, Redirect, Unauthorized, or Forbidden
