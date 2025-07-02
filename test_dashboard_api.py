"""
Test script to check dashboard API functionality
"""
from app import create_app

app = create_app()

with app.test_client() as client:
    response = client.get('/api/dashboard/stats')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.get_json()
        print(f"Response data keys: {list(data.keys())}")
        print(f"Success: {data.get('success', 'N/A')}")
    else:
        print(f"Error: {response.data.decode()}")
