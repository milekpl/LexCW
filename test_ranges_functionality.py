#!/usr/bin/env python3
"""Test script to verify LIFT ranges functionality"""

from app import create_app, injector
from app.services.dictionary_service import DictionaryService

def test_ranges():
    app = create_app()
    with app.app_context():
        # Get dictionary service using the injector
        dict_service = injector.get(DictionaryService)
        
        # Test ranges
        ranges = dict_service.get_ranges()
        print('LIFT Ranges loaded:', len(ranges))
        
        for range_id, range_data in ranges.items():
            print(f'\n{range_id}: {len(range_data.get("values", []))} items')
            for value in range_data.get('values', [])[:3]:
                print(f'  - {value.get("id", "N/A")}: {value.get("value", "N/A")} ({value.get("abbrev", "N/A")})')
            if len(range_data.get('values', [])) > 3:
                print(f'  ... and {len(range_data.get("values", [])) - 3} more')

def test_api():
    """Test the ranges API endpoints"""
    app = create_app()
    client = app.test_client()
    
    with app.app_context():
        # Test all ranges
        response = client.get('/api/ranges')
        print(f'\nAPI /api/ranges status: {response.status_code}')
        if response.status_code == 200:
            data = response.get_json()
            print(f'Success: {data.get("success")}')
            ranges = data.get('data', {})
            print(f'Ranges returned: {len(ranges)}')
        
        # Test variant types specifically
        response = client.get('/api/ranges/variant-types')
        print(f'\nAPI /api/ranges/variant-types status: {response.status_code}')
        if response.status_code == 200:
            data = response.get_json()
            print(f'Success: {data.get("success")}')
            if data.get('data'):
                values = data['data'].get('values', [])
                print(f'Variant types available: {len(values)}')
                for vt in values[:3]:
                    print(f'  - {vt.get("value", "N/A")} ({vt.get("abbrev", "N/A")})')
        
        # Test grammatical-info endpoint  
        response = client.get('/api/ranges/grammatical-info')
        print(f'\nAPI /api/ranges/grammatical-info status: {response.status_code}')
        if response.status_code == 200:
            data = response.get_json()
            print(f'Success: {data.get("success")}')
            if data.get('data'):
                values = data['data'].get('values', [])
                print(f'Grammatical categories available: {len(values)}')
                for gi in values[:3]:
                    print(f'  - {gi.get("value", "N/A")} ({gi.get("abbrev", "N/A")})')
        
        # Test relation-types endpoint
        response = client.get('/api/ranges/relation-types')
        print(f'\nAPI /api/ranges/relation-types status: {response.status_code}')
        if response.status_code == 200:
            data = response.get_json()
            print(f'Success: {data.get("success")}')
            if data.get('data'):
                values = data['data'].get('values', [])
                print(f'Relation types available: {len(values)}')
                for rt in values[:3]:
                    print(f'  - {rt.get("value", "N/A")} ({rt.get("abbrev", "N/A")})')

if __name__ == '__main__':
    test_ranges()
    test_api()
