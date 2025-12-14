import pytest
from flask import url_for
from app import create_app

@pytest.fixture
def client():
    app = create_app('testing')
    app.config['SERVER_NAME'] = 'localhost'
    with app.test_client() as client:
        yield client

def test_tools_page(client):
    response = client.get('/tools')
    assert response.status_code == 200
    assert b'<h1 class="mt-4">Tools</h1>' in response.data
    assert b'<a href="/tools/clear-cache"' in response.data

def test_clear_cache(client):
    response = client.get('/tools/clear-cache', follow_redirects=True)
    assert response.status_code == 200
    assert b'Cache cleared successfully.' in response.data
