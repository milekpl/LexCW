import os
import tempfile
import logging
from app.services.dictionary_service import DictionaryService


class FakeAdminWithSessions:
    def __init__(self, host, port, username, password, database=None):
        self.calls = []
        self.drop_calls = 0

    def connect(self):
        return True

    def disconnect(self):
        return True

    def execute_command(self, command: str) -> str:
        self.calls.append(command)
        if command.startswith('LIST'):
            return 'dictionary\n'
        if command.startswith('DROP DB '):
            self.drop_calls += 1
            raise Exception("Command execution failed: Database 'dictionary' is opened by another process.")
        if command == 'SHOW SESSIONS':
            # Return a fake session listing
            return '  id: 1234 user: admin host: 127.0.0.1 db: dictionary\n'
        return ''


class DummyMainConnector:
    def __init__(self):
        self.database = 'dictionary'
        self.host = 'localhost'
        self.port = 1984
        self.username = 'admin'
        self.password = 'admin'

    def connect(self):
        pass

    def disconnect(self):
        pass

    def is_connected(self):
        return True

    def execute_query(self, query: str) -> str:
        return '1'

    def execute_command(self, command: str) -> str:
        return ''


def test_drop_logs_sessions(monkeypatch, caplog, tmp_path):
    import pytest
    os.environ['TESTING'] = 'true'
    caplog.set_level(logging.WARNING)

    # Prepare a minimal lift file
    lift_file = tmp_path / 'data.lift'
    lift_file.write_text('<lift><entry id="e1"/></lift>')

    # The constructor signature of BaseXConnector expects host, port, username, password
    fake_admin = FakeAdminWithSessions('localhost', 1984, 'admin', 'admin')
    dummy_main = DummyMainConnector()
    svc = DictionaryService(dummy_main)

    # Patch BaseXConnector to our fake admin factory
    monkeypatch.setattr('app.services.dictionary_service.BaseXConnector', lambda **kwargs: fake_admin)

    with pytest.raises(Exception):
        svc.import_lift(str(lift_file), mode='replace')

    # Verify that SHOW SESSIONS was attempted and logged
    assert any('SHOW SESSIONS' in c for c in fake_admin.calls)
    assert any('Found sessions' in rec.message for rec in caplog.records)