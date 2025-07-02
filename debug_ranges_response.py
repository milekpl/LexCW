#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
import json

app = create_app()
with app.test_client() as client:
    resp = client.get('/api/ranges/grammatical-info')
    data = resp.get_json()
    print("Response status:", resp.status_code)
    print("Response data:")
    print(json.dumps(data, indent=2))
    
    if data and 'data' in data:
        values = data['data'].get('values', [])
        print(f"\nNumber of values: {len(values)}")
        print("Value IDs:", [val.get('id') for val in values])
