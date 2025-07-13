from __future__ import annotations
from typing import Any
import pytest
from flask import Flask
from app import create_app

@pytest.fixture
def client() -> Any:
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_clear_entries_cache(client: Any) -> None:
    """
    Test the /api/entries/clear-cache endpoint clears the cache and returns success.
    """
    response = client.post('/api/entries/clear-cache')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'cache' in data['message']
