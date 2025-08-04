#!/usr/bin/env python3
import requests

response = requests.get('http://localhost:5000/api/entries?limit=5')
print(f'Status: {response.status_code}')

if response.status_code == 200:
    data = response.json()
    print(f'Total entries: {data.get("total", 0)}')
    print(f'Returned entries: {len(data.get("entries", []))}')
else:
    print(f'Error: {response.text[:100]}')
