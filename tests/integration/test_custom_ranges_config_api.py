"""Integration tests for the custom_ranges.json config API."""
from __future__ import annotations

import json
import os
import pytest
from app.services.ranges_service import RangesService


@pytest.mark.integration
def test_add_custom_range_via_api(client, app):
    service: RangesService = client.application.injector.get(RangesService)

    payload = {
        'id': 'test-fieldworks-trait',
        'label': 'Test FieldWorks Trait',
        'description': 'Temporary trait for testing'
    }

    cfg_path = os.path.join(app.root_path, 'config', 'custom_ranges.json')

    # Ensure id not present
    with open(cfg_path, 'r', encoding='utf-8') as f:
        original = json.load(f)
    if payload['id'] in original:
        del original[payload['id']]
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(original, f, indent=2, ensure_ascii=False)

    try:
        resp = client.post('/api/ranges-editor/config', json=payload)
        assert resp.status_code in (200, 201)

        # Reloaded into memory - fetch ranges
        ranges = service.get_all_ranges()
        assert payload['id'] in ranges
        assert ranges[payload['id']].get('provided_by_config') is True

    finally:
        # Cleanup: remove from config file and reload
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        if payload['id'] in cfg:
            del cfg[payload['id']]
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        # Trigger service reload
        try:
            from app.services.ranges_service import reload_custom_ranges_config
            reload_custom_ranges_config()
        except Exception:
            pass


@pytest.mark.integration
def test_post_existing_config_returns_400(client, app):
    cfg_path = os.path.join(app.root_path, 'config', 'custom_ranges.json')
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    # Pick an existing key
    existing = next(iter(cfg.keys()))

    resp = client.post('/api/ranges-editor/config', json={'id': existing, 'label': 'X'})
    assert resp.status_code == 400
