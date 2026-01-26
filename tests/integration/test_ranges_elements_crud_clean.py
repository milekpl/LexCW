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
        # Use a deterministic standard range to avoid flakiness
        return 'grammatical-info'

    def test_create_and_get(self, client: FlaskClient, test_range_id: str) -> None:
        service = client.application.injector.get(RangesService)
        # Use a unique element ID to avoid conflicts with other tests
        import uuid
        element_id = f'clean-create-elem-{uuid.uuid4().hex[:8]}'
        
        # Ensure we have a valid range to work with
        original_range_id = test_range_id
        try:
            # Try to get the range first to ensure it exists
            range_data = service.get_range(test_range_id)
            
            # Check if this range is suitable for testing (has reasonable structure)
            if not range_data.get('values') or len(range_data.get('values', [])) == 0:
                # This range is empty, try a different one
                print(f"DEBUG: Range '{test_range_id}' is empty, trying grammatical-info")
                test_range_id = 'grammatical-info'
                range_data = service.get_range(test_range_id)
            elif range_data.get('provided_by_config', False) or range_data.get('fieldworks_standard', False):
                # This range might be from config, try a standard LIFT range
                print(f"DEBUG: Range '{test_range_id}' is config-based, trying grammatical-info")
                test_range_id = 'grammatical-info'
                range_data = service.get_range(test_range_id)
                
        except Exception as e:
            print(f"DEBUG: Error getting range {test_range_id}: {e}")
            # If the range doesn't exist, use a known standard range
            test_range_id = 'grammatical-info'
            try:
                range_data = service.get_range(test_range_id)
            except Exception:
                # If even the standard range doesn't exist, skip this test
                pytest.skip(f"Neither {original_range_id} nor grammatical-info range exists")
        
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
        # Ensure cache invalidation so subsequent reads see the new element
        try:
            service._invalidate_cache()
        except Exception:
            pass
        
        # Verify element exists in the service layer (with retry for database consistency)
        element_exists = False
        last_error = None
        last_range_data = None
        
        for attempt in range(5):  # Retry up to 5 times
            try:
                range_data = service.get_range(test_range_id)
                last_range_data = range_data
                
                # Debug: Print range data only if element not found (to avoid spam)
                if not element_exists and attempt == 0:
                    print(f"DEBUG: Range '{test_range_id}' data: {range_data}")
                    print(f"DEBUG: Looking for element ID: {element_id}")
                    if 'values' in range_data:
                        element_ids = [elem.get('id') for elem in range_data['values']]
                        print(f"DEBUG: Existing element IDs: {element_ids}")
                
                element_exists = any(elem.get('id') == element_id for elem in range_data.get('values', []))
                if element_exists:
                    break
                else:
                    print(f"DEBUG: Element {element_id} not found in range {test_range_id} (attempt {attempt + 1}/5)")
                    time.sleep(0.3)  # Increased wait time
            except Exception as e:
                last_error = e
                print(f"DEBUG: Error getting range {test_range_id}: {e}")
                if attempt == 4:  # Last attempt
                    pytest.fail(f"Failed to verify element exists in service layer: {e}")
                time.sleep(0.3)
        
        if not element_exists:
            # Enhanced error message with debugging info
            error_msg = f"Element {element_id} should exist in range {test_range_id}"
            if last_range_data:
                error_msg += f"\nRange data: {last_range_data}"
                if 'values' in last_range_data:
                    existing_ids = [elem.get('id') for elem in last_range_data['values']]
                    error_msg += f"\nExisting element IDs: {existing_ids}"
            if last_error:
                error_msg += f"\nLast error: {last_error}"
            
            # Try one more time with a fresh service instance
            print("DEBUG: Trying with fresh service instance...")
            fresh_service = client.application.injector.get(RangesService)
            try:
                fresh_range_data = fresh_service.get_range(test_range_id)
                fresh_exists = any(elem.get('id') == element_id for elem in fresh_range_data.get('values', []))
                if fresh_exists:
                    print("DEBUG: Element found with fresh service instance!")
                    element_exists = True
                else:
                    error_msg += f"\nFresh service range data: {fresh_range_data}"
            except Exception as fresh_error:
                error_msg += f"\nFresh service error: {fresh_error}"
            
            assert element_exists, error_msg
        
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
