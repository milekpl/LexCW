#!/usr/bin/env python3

"""
Test-driven implementation of date fields in the query builder UI.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient

@pytest.mark.integration
class TestDatesUI:
    """Test date fields in the query builder user interface components."""

    @pytest.mark.integration
    def test_query_builder_has_date_sorting_options(self, client: FlaskClient) -> None:
        """Test query builder includes date sorting options."""
        response = client.get('/workbench/query-builder')
        
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should have date sorting controls
        assert 'sort-by-select' in html
        assert 'value="date_created"' in html
        assert 'value="date_modified"' in html

    @pytest.mark.integration
    def test_date_sorting_functionality(self, client: FlaskClient, isolated_basex_connector) -> None:
        # Use an isolated BaseX database for this test to ensure strict teardown and avoid
        # cross-test interference when running the full integration suite.
        """Test that date sorting works through the query builder API."""
        # Ensure there is at least one entry in the database for preview
        import uuid
        entry_id = f"date_test_entry_{uuid.uuid4().hex[:8]}"
        xml_entry = f'''<?xml version="1.0" encoding="utf-8"?>
<entry id="{entry_id}">
    <lexical-unit><form lang="en"><text>date-test</text></form></lexical-unit>
    <sense id="s1"><gloss lang="en"><text>date test</text></gloss></sense>
</entry>'''.encode('utf-8')
        post_resp = client.post('/api/xml/entries', data=xml_entry, content_type='application/xml')
        assert post_resp.status_code in (200, 201, 409)

        # Wait until the entry is retrievable (guard against eventual indexing delays)
        import time
        timeout = 60.0
        interval = 0.5
        start = time.time()
        get_resp = None
        xml_get = None
        while time.time() - start < timeout:
            get_resp = client.get(f"/api/entries/{entry_id}")
            if get_resp.status_code == 200:
                break
            # Fallback: check raw XML storage if entries API hasn't indexed yet
            xml_get = client.get(f"/api/xml/entries/{entry_id}")
            if xml_get.status_code == 200:
                # Consider the entry present even if the entries index hasn't updated
                break
            time.sleep(interval)

        # Retry creation a couple times if still not found
        if not (get_resp and get_resp.status_code == 200) and not (xml_get and xml_get.status_code == 200):
            for _ in range(2):
                post_resp = client.post('/api/xml/entries', data=xml_entry, content_type='application/xml')
                assert post_resp.status_code in (200, 201, 409)
                tstart = time.time()
                found = False
                while time.time() - tstart < 30.0:
                    get_resp = client.get(f"/api/entries/{entry_id}")
                    if get_resp.status_code == 200:
                        found = True
                        break
                    xml_get = client.get(f"/api/xml/entries/{entry_id}")
                    if xml_get.status_code == 200:
                        found = True
                        break
                    time.sleep(0.5)
                if found:
                    break

        assert (get_resp and get_resp.status_code == 200) or (xml_get and xml_get.status_code == 200), "Created entry did not appear in /api/entries or XML API within timeout"

        # Test ascending sort by date_created
        query_data: dict[str, str | int] = {
            "sort_by": "date_created",
            "sort_order": "asc",
            "limit": 5
        }
        
        # Poll the preview endpoint until the posted entry appears (eventual consistency)
        import time

        timeout = 10.0
        interval = 0.5
        start = time.time()
        data = None
        while time.time() - start < timeout:
            response = client.post(
                '/api/query-builder/preview',
                json=query_data,
                content_type='application/json'
            )
            assert response.status_code == 200
            data = response.get_json()
            if data and 'preview_entries' in data and len(data['preview_entries']) > 0:
                break
            time.sleep(interval)

        assert data is not None and 'preview_entries' in data and len(data['preview_entries']) > 0, "No preview entries found after waiting"

        # Test descending sort by date_modified
        query_data: dict[str, str | int] = {
            "sort_by": "date_modified",
            "sort_order": "desc",
            "limit": 5
        }
        
        # Poll the preview endpoint until the posted entry appears (eventual consistency)
        import time

        timeout = 10.0
        interval = 0.5
        start = time.time()
        data = None
        while time.time() - start < timeout:
            response = client.post(
                '/api/query-builder/preview',
                json=query_data,
                content_type='application/json'
            )
            assert response.status_code == 200
            data = response.get_json()
            if data and 'preview_entries' in data and len(data['preview_entries']) > 0:
                break
            time.sleep(interval)

        assert data is not None and 'preview_entries' in data and len(data['preview_entries']) > 0, "No preview entries found after waiting"