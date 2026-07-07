import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app

app = create_app()

with app.app_context():
    client = app.test_client()
    r = client.get('/api/projects/1/validation-rules?include_defaults=true')
    print("Response status code:", r.status_code)
    d = r.get_json()
    print("D source:", d.get('source'))
    print("D count:", d.get('count'))
    rules = d.get('rules', [])
    print("Rules list length:", len(rules))
    if isinstance(rules, list) and len(rules) > 0:
        print("First rule:", rules[0])
