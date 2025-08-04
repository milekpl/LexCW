#!/usr/bin/env python3
"""Test the API to see date_modified values."""

import requests
import json

def test_api():
    try:
        response = requests.get('http://localhost:5000/api/entries?sort_by=date_modified&sort_order=asc&limit=10')
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print(f'Total entries: {data.get("total", 0)}')
            
            for i, entry in enumerate(data.get('entries', [])[:10]):
                entry_id = entry.get('id', 'N/A')
                date_modified = entry.get('date_modified', 'N/A')
                lexical_unit = entry.get('lexical_unit', {})
                if isinstance(lexical_unit, dict) and 'forms' in lexical_unit:
                    main_form = lexical_unit['forms'][0].get('text', 'N/A') if lexical_unit['forms'] else 'N/A'
                else:
                    main_form = 'N/A'
                print(f'Entry {i+1}: {main_form} (ID: {entry_id}) - date_modified: {date_modified}')
        else:
            print(f'Response: {response.text[:200]}')
            
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    test_api()
