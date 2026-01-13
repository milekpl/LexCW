import os
from app.database.basex_connector import BaseXConnector


def test_get_status_disconnected(monkeypatch):
    # Ensure TEST_DB_NAME env var does not leak into this test
    monkeypatch.delenv('TEST_DB_NAME', raising=False)
    conn = BaseXConnector('localhost', 1984, 'admin', 'admin', database='db')

    # Default disconnected state
    status = conn.get_status()
    assert isinstance(status, dict)
    assert status['connected'] is False
    assert status['current_db'] is None
    # configured_database should reflect connector.database (no TEST_DB_NAME set)
    assert status['configured_database'] == 'db'


def test_get_status_connected(monkeypatch):
    conn = BaseXConnector('localhost', 1984, 'admin', 'admin', database='db')

    # Simulate an active session and current DB
    conn._session = object()
    conn._current_db = 'test_db'

    # Allow runtime override via TEST_DB_NAME
    monkeypatch.setenv('TEST_DB_NAME', 'override_db')

    status = conn.get_status()
    assert status['connected'] is True
    assert status['current_db'] == 'test_db'
    assert status['configured_database'] == 'override_db'