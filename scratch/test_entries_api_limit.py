import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app

app = create_app()

with app.app_context():
    client = app.test_client()
    # Test limit=10
    r1 = client.get('/api/entries?project_id=1&limit=10')
    d1 = r1.get_json()
    print("D1 length:", len(d1.get('entries', [])))
    print("D1 total_count:", d1.get('total_count'))
    
    # Test limit=100
    r2 = client.get('/api/entries?project_id=1&limit=100')
    d2 = r2.get_json()
    print("D2 length:", len(d2.get('entries', [])))
    print("D2 total_count:", d2.get('total_count'))
    
    # Test limit=10000
    r3 = client.get('/api/entries?project_id=1&limit=10000')
    d3 = r3.get_json()
    print("D3 length:", len(d3.get('entries', [])))
    print("D3 total_count:", d3.get('total_count'))
