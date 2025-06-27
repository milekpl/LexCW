#!/usr/bin/env python3
import json
from app import create_app

app = create_app('testing')
with app.test_client() as client:
    response = client.post('/api/entries', data=json.dumps({
        'id': 'test_redirect',
        'lexical_unit': {'en': 'test'}
    }), content_type='application/json')
    print(f'Status: {response.status_code}')
    print(f'Location: {response.headers.get("Location", "None")}')
    
    # Try with trailing slash
    response2 = client.post('/api/entries/', data=json.dumps({
        'id': 'test_redirect2',
        'lexical_unit': {'en': 'test'}
    }), content_type='application/json')
    print(f'Status with slash: {response2.status_code}')
