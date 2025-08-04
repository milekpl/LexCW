#!/usr/bin/env python3
"""Test date sorting in both directions."""

import requests

def test_date_sorting():
    try:
        # Test ascending date sort
        response = requests.get('http://localhost:5000/api/entries?sort_by=date_modified&sort_order=asc&limit=10')
        if response.status_code == 200:
            data = response.json()
            print('=== ASCENDING DATE SORT ===')
            print(f'Found {len(data.get("entries", []))} entries')
            for i, entry in enumerate(data.get('entries', [])[:10]):
                date_mod = entry.get('date_modified', 'NULL')
                lexical = entry.get('lexical_unit', {})
                if isinstance(lexical, dict) and 'forms' in lexical and lexical['forms']:
                    text = lexical['forms'][0].get('text', 'N/A')
                else:
                    text = 'N/A'
                print(f'{i+1}. {text} - {date_mod}')
        else:
            print(f'Error: {response.status_code}')
            
        # Test descending date sort
        response = requests.get('http://localhost:5000/api/entries?sort_by=date_modified&sort_order=desc&limit=10')
        if response.status_code == 200:
            data = response.json()
            print('\n=== DESCENDING DATE SORT ===')
            print(f'Found {len(data.get("entries", []))} entries')
            for i, entry in enumerate(data.get('entries', [])[:10]):
                date_mod = entry.get('date_modified', 'NULL')
                lexical = entry.get('lexical_unit', {})
                if isinstance(lexical, dict) and 'forms' in lexical and lexical['forms']:
                    text = lexical['forms'][0].get('text', 'N/A')
                else:
                    text = 'N/A'
                print(f'{i+1}. {text} - {date_mod}')

    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    test_date_sorting()
