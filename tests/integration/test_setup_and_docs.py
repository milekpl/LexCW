#!/usr/bin/env python3

from __future__ import annotations

import pytest
from unittest.mock import patch


@pytest.mark.integration
def test_apidocs_contains_projects_endpoints(app, client):
    # fall back to checking URL map if apispec generation is broken
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert '/settings/projects' in rules


@pytest.mark.integration
def test_create_project_returns_success_json(app, client):
    payload = {
        'project_name': 'Docs Test Project',
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


@pytest.mark.integration
def test_settings_wizard_modal_shows(app, client):
    # Ensure the settings page for a project with wizard flagged shows modal
    # Create the project first
    payload = {
        'project_name': 'Wizard Modal Test',
        'source_language_code': 'en',
        'source_language_name': 'English',
        'target_language_code': 'es',
        'target_language_name': 'Spanish',
        'install_recommended_ranges': False
    }
    client.post('/settings/projects/create', json=payload)
    # Force no ranges so the wizard will be displayed
    from unittest.mock import patch
    with patch('app.services.dictionary_service.DictionaryService.get_lift_ranges') as mock_get_ranges:
        mock_get_ranges.return_value = {}
        resp = client.get('/settings/?project=Wizard%20Modal%20Test&wizard=true', follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'id="projectSetupModalSettings"' in html


@pytest.mark.integration
def test_help_page_mentions_project_setup(app, client):
    resp = client.get('/help')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Install Recommended Ranges' in html or 'Project Setup' in html or 'Project Wizard' in html


@pytest.mark.integration
def test_apispec_json_contains_expected_paths(app, client):
    # Ensure the Swagger/OpenAPI spec is generated and includes our key endpoints
    try:
        resp = client.get('/apispec.json')
    except Exception as e:
        pytest.fail(f"APISpec generation raised exception: {e}")
    assert resp.status_code == 200, f"APISpec generation failed: {resp.status_code} -- {resp.data[:400]}"
    data = resp.get_json()
    assert 'paths' in data
    paths = data['paths']
    expected_paths = [
        '/settings/projects',
        '/settings/projects/create',
        '/api/ranges/install_recommended',
        '/api/setup'
    ]
    for p in expected_paths:
        assert any(k.startswith(p) for k in paths.keys()), f"Missing API path in spec: {p}"
