import pytest

@pytest.mark.integration
def test_debug_ranges_endpoint(client):
    resp = client.get('/api/ranges')
    print('STATUS', resp.status_code)
    data = resp.get_json()
    ranges = data.get('data', data.get('ranges', {}))
    print('RANGES KEYS:', sorted(list(ranges.keys())))
    for rid in ['usage-type', 'domain-type', 'grammatical-info']:
        r = client.get(f'/api/ranges/{rid}')
        print(rid, '->', r.status_code, r.get_json())
    assert True
