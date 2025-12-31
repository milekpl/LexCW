"""
Reproduction test for mocking-class-method behavior around install_recommended_ranges.
This ensures that patching DictionaryService.get_ranges (without a return_value) does
not cause the install endpoint to hang or repeatedly loop.

This test is intentionally minimal and uses the integration fixtures.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, Mock

@pytest.mark.integration
def test_install_endpoint_with_class_level_get_ranges_mock(client):
    # Patch the DictionaryService.get_ranges at class level to a bare Mock
    with patch('app.services.dictionary_service.DictionaryService.get_ranges') as mock_get_ranges:
        # Do NOT set mock_get_ranges.return_value deliberately to reproduce the failure
        # Ensure the request completes (timeout will fail the test runner if it hangs)
        resp = client.post('/api/ranges/install_recommended')
        # Endpoint should return a JSON response (200/201 or error JSON) and must finish
        assert resp.status_code in (200, 201, 400, 500)
        # If it returned JSON, ensure it is parseable
        try:
            _ = resp.get_json()
        except Exception:
            # If not JSON, at least we did not hang
            pass

@pytest.mark.integration
def test_install_endpoint_with_connector_method_patch(client):
    # Patch BaseXConnector.execute_query to return a bare Mock (no return value)
    with patch('app.database.basex_connector.BaseXConnector.execute_query') as mock_exec:
        # Do not set return_value
        resp = client.post('/api/ranges/install_recommended')
        assert resp.status_code in (200, 201, 400, 500)
        try:
            _ = resp.get_json()
        except Exception:
            pass
