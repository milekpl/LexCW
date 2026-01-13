import logging
from app import create_app


class FakeConn:
    def get_status(self):
        return {'connected': True, 'current_db': 'fake_db', 'configured_database': 'fake_db', 'aggressive_disconnect': False}


def test_per_request_basex_logging(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    app = create_app('testing')

    # Patch injector.get to return our fake connector
    monkeypatch.setattr(app, 'injector', app.injector)
    original_get = app.injector.get
    app.injector.get = lambda cls: FakeConn()

    with app.test_client() as client:
        client.get('/health')

    # Verify that a BaseX status log entry was emitted
    assert any('BaseX status at request start' in rec.message for rec in caplog.records)

    # Restore original injector.get
    app.injector.get = original_get