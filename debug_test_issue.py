#!/usr/bin/env python3
"""
Debug script to understand the failing test issue.
"""

import pytest
import json
import time
from flask import Flask
from flask.testing import FlaskClient
from app.services.ranges_service import RangesService


def test_debug_issue():
    """Debug the failing test issue."""
    # Create app and client
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        print("=== DEBUGGING TEST ISSUE ===")
        
        # Get a test range ID
        response = client.get('/api/ranges-editor/')
        print(f"GET /api/ranges-editor/ status: {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.data)
            ranges = data.get('data', {})
            print(f"Available ranges: {list(ranges.keys())}")
            
            if ranges:
                test_range_id = list(ranges.keys())[0]
                print(f"Using test range ID: {test_range_id}")
            else:
                test_range_id = 'grammatical-info'
                print(f"No ranges found, using default: {test_range_id}")
        else:
            test_range_id = 'grammatical-info'
            print(f"Failed to get ranges, using default: {test_range_id}")
        
        # Try to get the range
        response = client.get(f'/api/ranges-editor/{test_range_id}')
        print(f"GET /api/ranges-editor/{test_range_id} status: {response.status_code}")
        
        if response.status_code == 200:
            range_data = json.loads(response.data)
            print(f"Range data keys: {list(range_data.get('data', {}).keys())}")
            values = range_data.get('data', {}).get('values', [])
            print(f"Range has {len(values)} values")
        else:
            print(f"Failed to get range: {response.data}")
        
        # Create element using service
        service = client.application.injector.get(RangesService)
        element_id = 'debug-element'
        
        # Clean up if exists
        try:
            service.delete_range_element(test_range_id, element_id)
            print(f"Cleaned up existing element {element_id}")
        except Exception:
            pass
        
        # Create element
        try:
            guid = service.create_range_element(test_range_id, {
                'id': element_id,
                'labels': {'en': 'Debug element'},
                'descriptions': {'en': 'debug desc'}
            })
            print(f"Created element {element_id} with GUID: {guid}")
        except Exception as e:
            print(f"Failed to create element: {e}")
            return
        
        # Check if element exists in range
        try:
            range_data = service.get_range(test_range_id)
            values = range_data.get('values', [])
            element_exists = any(elem.get('id') == element_id for elem in values)
            print(f"Element exists in service range data: {element_exists}")
            if element_exists:
                for elem in values:
                    if elem.get('id') == element_id:
                        print(f"Element details: {elem}")
                        break
        except Exception as e:
            print(f"Failed to get range from service: {e}")
        
        # Try to get element via API
        print("\n=== TESTING API ENDPOINT ===")
        for attempt in range(5):
            print(f"Attempt {attempt + 1}:")
            resp = client.get(f'/api/ranges-editor/{test_range_id}/elements/{element_id}')
            print(f"GET /api/ranges-editor/{test_range_id}/elements/{element_id} status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = json.loads(resp.data)
                print(f"Success! Data: {data}")
                break
            elif resp.status_code == 404:
                print(f"404 Not Found - Element not accessible via API")
            else:
                print(f"Other error: {resp.data}")
            
            time.sleep(0.2)
        
        # List all elements in the range
        print("\n=== LISTING ALL ELEMENTS ===")
        resp = client.get(f'/api/ranges-editor/{test_range_id}/elements')
        print(f"GET /api/ranges-editor/{test_range_id}/elements status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = json.loads(resp.data)
            elements = data.get('data', [])
            print(f"Found {len(elements)} elements:")
            for elem in elements:
                print(f"  - {elem.get('id')}: {elem.get('labels', {})}")
        
        # Clean up
        try:
            service.delete_range_element(test_range_id, element_id)
            print(f"Cleaned up element {element_id}")
        except Exception:
            pass


if __name__ == "__main__":
    test_debug_issue()