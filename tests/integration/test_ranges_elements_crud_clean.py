"""Integration tests for range elements CRUD operations (clean)."""

from __future__ import annotations

import pytest
import json
import time
from typing import Any
from flask import Flask
from flask.testing import FlaskClient

from app.services.ranges_service import RangesService


@pytest.mark.integration
class TestRangeElementsCRUDClean:
    """Clean test suite for ranges element CRUD using service methods."""

    @pytest.fixture
    def client(self, app: Flask) -> FlaskClient:
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def test_range_id(self, client: Flask) -> str:
        response = client.get('/api/ranges-editor/')
        if response.status_code == 200:
            data = json.loads(response.data)
            ranges = data.get('data', {})
            if ranges:
                return list(ranges.keys())[0]
        return 'grammatical-info'

    def test_create_and_get(self, client: FlaskClient, test_range_id: str) -> None:
        service = client.application.injector.get(RangesService)
        element_id = 'clean-create-elem'
        try:
            service.delete_range_element(test_range_id, element_id)
        except Exception:
            pass
        guid = service.create_range_element(test_range_id, {
            'id': element_id,
            'labels': {'en': 'Clean element'},
            'descriptions': {'en': 'desc'}
        })
        assert guid
        # Retry GET briefly in case of transient latency between create and read
        resp = None
        for _ in range(3):
            resp = client.get(f'/api/ranges-editor/{test_range_id}/elements/{element_id}')
            if resp.status_code == 200:
                break
            time.sleep(0.1)

        assert resp is not None and resp.status_code == 200
        # Cleanup
        service.delete_range_element(test_range_id, element_id)
