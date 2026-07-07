import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app

app = create_app()

with app.app_context():
    client = app.test_client()
    res = client.post(
        '/api/validation/batch',
        json={'project_id': 1, 'validate_all': True, 'entries': []},
        headers={'Content-Type': 'application/json', 'X-CSRFToken': 'test'}
    )
    print("Status code:", res.status_code)
    data = res.get_json()
    print("Total entries:", data.get('total_entries'))
    print("Valid entries:", data.get('valid_entries'))
    print("Invalid entries:", data.get('invalid_entries'))
    print("Total issues:", data.get('total_issues'))
    print("Results length:", len(data.get('results', [])))
    for r in data.get('results', []):
        print(" - Invalid entry:", r.get('entry_id'), r.get('errors'))
