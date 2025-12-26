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
        
        # Ensure we have a valid range to work with
        try:
            # Try to get the range first to ensure it exists
            range_data = service.get_range(test_range_id)
        except Exception:
            # If the range doesn't exist, use a known standard range
            test_range_id = 'grammatical-info'
            try:
                range_data = service.get_range(test_range_id)
            except Exception:
                # If even the standard range doesn't exist, skip this test
                pytest.skip(f"Neither {test_range_id} nor grammatical-info range exists")
        
        # Clean up if element already exists
        try:
            service.delete_range_element(test_range_id, element_id)
        except Exception:
            pass
            
        # Create the element
        guid = service.create_range_element(test_range_id, {
            'id': element_id,
            'labels': {'en': 'Clean element'},
            'descriptions': {'en': 'desc'}
        })
        assert guid, "Element creation should return a GUID"
        
        # Verify element exists in the service layer
        try:
            range_data = service.get_range(test_range_id)
            element_exists = any(elem.get('id') == element_id for elem in range_data.get('values', []))
            assert element_exists, f"Element {element_id} should exist in range {test_range_id}"
        except Exception as e:
            pytest.fail(f"Failed to verify element exists in service layer: {e}")
        
        # Retry GET briefly in case of transient latency between create and read
        resp = None
        for attempt in range(5):  # Increased from 3 to 5 attempts
            resp = client.get(f'/api/ranges-editor/{test_range_id}/elements/{element_id}')
            if resp.status_code == 200:
                break
            elif resp.status_code == 404:
                # Element not found via API, wait and retry
                time.sleep(0.2)  # Increased from 0.1 to 0.2 seconds
            else:
                # Other error, log and break
                self.logger.warning(f"API returned status {resp.status_code} on attempt {attempt + 1}")
                time.sleep(0.2)
        
        # If still not found, check if there's a database consistency issue
        if resp is None or resp.status_code != 200:
            try:
                # Check if element exists in the database but API can't find it
                range_data = service.get_range(test_range_id)
                element_exists = any(elem.get('id') == element_id for elem in range_data.get('values', []))
                if element_exists:
                    pytest.fail(f"Element {element_id} exists in service layer but not accessible via API. Status: {resp.status_code if resp else 'None'}")
                else:
                    pytest.fail(f"Element {element_id} was not created successfully in the database")
            except Exception as e:
                pytest.fail(f"Failed to verify element state: {e}")
        
        # Verify API response contains expected data
        assert resp is not None and resp.status_code == 200, f"Expected 200, got {resp.status_code if resp else 'None'}"
        
        try:
            result = resp.get_json()
            assert result['success'] is True, "API should return success=True"
            element_data = result['data']
            assert element_data['id'] == element_id, f"Expected element ID {element_id}, got {element_data.get('id')}"
            assert element_data['labels']['en'] == 'Clean element', f"Expected 'Clean element', got {element_data.get('labels', {}).get('en')}"
        except Exception as e:
            pytest.fail(f"API response validation failed: {e}")
        
        # Cleanup
        try:
            service.delete_range_element(test_range_id, element_id)
        except Exception:
            pass
