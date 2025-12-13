#!/usr/bin/env python3

from __future__ import annotations

import pytest
from unittest.mock import patch


@pytest.mark.integration
def test_install_recommended_ranges_endpoint(app, client):
    # Patch the service to avoid touching the real DB
    with patch('app.services.dictionary_service.DictionaryService.install_recommended_ranges') as mock_install:
        mock_install.return_value = {'grammatical-info': {'id': 'grammatical-info', 'values': []}}

        resp = client.post('/api/ranges/install_recommended')
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
    @pytest.mark.integration
    def test_create_project_and_wizard(client, app):
        # Create a new project via API and ensure it gets created
        payload = {
            'project_name': 'Wizard Test',
            'source_language_code': 'en',
            'source_language_name': 'English',
            'target_language_code': 'es',
            'target_language_name': 'Spanish',
            'install_recommended_ranges': False
        }
        resp = client.post('/settings/projects/create', json=payload)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True

        # Check projects page lists it
        resp2 = client.get('/settings/projects')
        html = resp2.data.decode('utf-8')
        assert 'Wizard Test' in html


@pytest.mark.integration
def test_entry_form_shows_ranges_missing_banner(app, client):
    # Simulate no ranges by patching get_ranges to return empty dict
    with patch('app.services.dictionary_service.DictionaryService.get_lift_ranges') as mock_get_ranges:
        mock_get_ranges.return_value = {}
        resp = client.get('/entries/add')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Ranges Not Configured' in html
        assert 'Install recommended ranges' in html or 'install-recommended-ranges-btn' in html


def test_install_recommended_when_ranges_exist(app, client):
    # Ensure installer doesn't overwrite existing ranges
    with patch('app.services.dictionary_service.DictionaryService.get_lift_ranges') as mock_get_ranges:
        mock_get_ranges.return_value = {'grammatical-info': {'id': 'grammatical-info', 'values': []}}
        resp = client.post('/api/ranges/install_recommended')
        assert resp.status_code == 500
        data = resp.get_json()
        assert data['success'] is False
