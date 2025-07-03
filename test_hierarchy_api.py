#!/usr/bin/env python3
"""Test hierarchical ranges API with cache clearing"""

import requests

# First clear the cache
clear_response = requests.post('http://127.0.0.1:5000/api/ranges/clear-cache')
print(f'Cache clear response: {clear_response.status_code}')

# Test the semantic domain range
response = requests.get('http://127.0.0.1:5000/api/ranges/semantic-domain-ddp4')
if response.status_code == 200:
    data = response.json()
    if data['success'] and 'values' in data['data']:
        values = data['data']['values']
        print(f'Semantic domain has {len(values)} values')
        # Look for items with parents
        with_parents = [v for v in values if v.get('parent')]
        print(f'Items with parents: {len(with_parents)}')
        if with_parents:
            print('Sample hierarchical items:')
            for item in with_parents[:3]:
                print(f'  {item["id"]} (parent: {item["parent"]})')
        else:
            print('Sample items (checking for parent field):')
            for item in values[:3]:
                print(f'  {item["id"]} - parent: {item.get("parent", "MISSING")}')
else:
    print(f'API call failed: {response.status_code}')
