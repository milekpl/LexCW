import os
import tempfile
import time
from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import DatabaseError


class FakeAdmin:
    def __init__(self, host, port, username, password, database=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.connected = False
        self._drop_attempts = 0

    def connect(self):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False

    def execute_command(self, command: str) -> str:
        # LIST indicates the DB exists
        if command == "LIST":
            return "dictionary\n"
        if command.startswith("DROP DB "):
            self._drop_attempts += 1
            # simulate 'opened by another process' twice then succeed
            if self._drop_attempts < 3:
                raise DatabaseError("Command execution failed: Database 'dictionary' is opened by another process.")
            return ""
        if command.startswith("CREATE DB "):
            return ""
        return ""


class DummyMainConnector:
    def __init__(self):
        self.database = "dictionary"
        self.disconnected = False
        self.connected = True
        # Provide BaseX connection info expected by DictionaryService
        self.host = "localhost"
        self.port = 1984
        self.username = "admin"
        self.password = "admin"

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.disconnected = True
        self.connected = False

    def is_connected(self):
        return self.connected

    def execute_query(self, query: str) -> str:
        # Return a single entry count for post-import counting
        return "1"

    def execute_command(self, command: str) -> str:
        # Accept ADD TO ranges.xml and other commands used by DictionaryService
        if command.startswith('ADD TO') or command.startswith('ADD '):
            return ""
        if command == 'LIST':
            return f"{self.database}\n"
        return ""


def test_import_lift_replace_retries_drop(monkeypatch, tmp_path):
    os.environ['TESTING'] = 'true'

    # Create a minimal LIFT file
    lift_file = tmp_path / "test.lift"
    lift_file.write_text("<lift><entry id='e1'></entry></lift>")

    dummy_main = DummyMainConnector()
    svc = DictionaryService(dummy_main)

    # Patch BaseXConnector used inside the DictionaryService to our FakeAdmin
    monkeypatch.setattr("app.services.dictionary_service.BaseXConnector", FakeAdmin)

    total = svc.import_lift(str(lift_file), mode='replace')

    assert total == 1
    assert dummy_main.disconnected is True


def test_import_lift_replace_drop_fails(monkeypatch, tmp_path):
    os.environ['TESTING'] = 'true'

    # Create a minimal LIFT file
    lift_file = tmp_path / "test2.lift"
    lift_file.write_text("<lift><entry id='e1'></entry></lift>")

    class FakeAdminAlwaysFail(FakeAdmin):
        def execute_command(self, command: str) -> str:
            if command == "LIST":
                return "dictionary\n"
            if command.startswith("DROP DB "):
                raise DatabaseError("Command execution failed: Database 'dictionary' is opened by another process.")
            if command.startswith("CREATE DB "):
                return ""
            return ""

    dummy_main = DummyMainConnector()
    svc = DictionaryService(dummy_main)

    monkeypatch.setattr("app.services.dictionary_service.BaseXConnector", FakeAdminAlwaysFail)

    import pytest

    with pytest.raises(DatabaseError):
        svc.import_lift(str(lift_file), mode='replace')


def test_initialize_database_retries_drop(monkeypatch, tmp_path):
    os.environ['TESTING'] = 'true'

    # Create a minimal LIFT file
    lift_file = tmp_path / "init.lift"
    lift_file.write_text("<lift><entry id='e1'></entry></lift>")

    class FakeAdminDropRetry(FakeAdmin):
        def execute_command(self, command: str) -> str:
            if command == "LIST":
                return "dictionary\n"
            if command.startswith("DROP DB "):
                # fail twice then succeed
                self._drop_attempts += 1
                if self._drop_attempts < 3:
                    raise DatabaseError("Command execution failed: Database 'dictionary' is opened by another process.")
                return ""
            if command.startswith("CREATE DB "):
                return ""
            if command.startswith("ADD ") or command.startswith("ADD TO"):
                return ""
            return ""

    dummy_main = DummyMainConnector()
    svc = DictionaryService(dummy_main)

    monkeypatch.setattr("app.services.dictionary_service.BaseXConnector", FakeAdminDropRetry)

    # Should not raise
    svc.initialize_database(str(lift_file))


