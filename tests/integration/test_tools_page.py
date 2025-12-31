import pytest

def test_tools_page(client):
    response = client.get('/tools')
    assert response.status_code == 200
    assert b'<h1 class="mt-4">' in response.data
    assert b'Tools' in response.data
    assert b'<a href="/tools/clear-cache"' in response.data

def test_clear_cache(client):
    response = client.get('/tools/clear-cache', follow_redirects=True)
    assert response.status_code == 200
    assert b'Cache cleared successfully.' in response.data
