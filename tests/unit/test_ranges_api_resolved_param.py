from __future__ import annotations

from unittest.mock import Mock
from flask import current_app


def test_ranges_endpoint_passes_resolved_flag_to_service(app):
    # Prepare a fake service
    fake_service = Mock()
    fake_service.get_ranges.return_value = {'foo': {'id': 'foo', 'values': []}}

    # Patch injector.get to return our fake service
    app.injector.get = lambda cls: fake_service

    with app.test_client() as client:
        resp = client.get('/api/ranges?resolved=true')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'foo' in data['data']
        # Ensure service was called with resolved=True
        fake_service.get_ranges.assert_called_with(resolved=True, force_reload=True)

    # Also test default behavior (no param => resolved False)
    with app.test_client() as client:
        resp = client.get('/api/ranges')
        assert resp.status_code == 200
        fake_service.get_ranges.assert_called_with(resolved=False, force_reload=True)
