import os
from app.database.basex_connector import BaseXConnector


def test_get_status_disconnected(monkeypatch):
    monkeypatch.delenv('TEST_DB_NAME', raising=False)
    conn = BaseXConnector('localhost', 1984, 'admin', 'admin', database='db')

    status = conn.get_status()
    assert isinstance(status, dict)
    assert status['connected'] is False
    assert status['configured_database'] == 'db'
    assert status['pool_size'] == 0


def test_get_status_connected(monkeypatch):
    conn = BaseXConnector('localhost', 1984, 'admin', 'admin', database='db')

    monkeypatch.setenv('TEST_DB_NAME', 'override_db')

    status = conn.get_status()
    assert status['connected'] is False  # not explicitly connected
    assert status['configured_database'] == 'override_db'
    assert status['pool_size'] == 0
