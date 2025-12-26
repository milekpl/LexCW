from app import create_app

app = create_app('testing')
app.testing = True
with app.test_client() as c:
    resp = c.get('/api/ranges')
    print('Status:', resp.status_code)
    try:
        data = resp.get_json()
    except Exception as e:
        print('Failed to parse JSON:', e)
        print(resp.data[:1000])
        exit(1)
    print('Keys:', sorted(list(data.get('data', data.get('ranges', {})).keys())))
    # check specific ranges
    for rid in ['usage-type', 'domain-type', 'grammatical-info']:
        r = c.get(f'/api/ranges/{rid}')
        print(rid, '->', r.status_code, r.get_json())
