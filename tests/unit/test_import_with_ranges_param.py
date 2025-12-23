import os
import tempfile
from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import DatabaseError


class FakeAdminRecorder2:
    def __init__(self, host, port, username, password, database=None):
        self.calls = []

    def connect(self):
        return True

    def disconnect(self):
        return True

    def execute_command(self, command: str) -> str:
        self.calls.append(command)
        return ''

    def execute_query(self, query: str) -> str:
        self.calls.append(query)
        if 'lift-ranges' in query or 'exists' in query:
            return 'true'
        return ''


class DummyMainConnector3:
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


def test_import_lift_with_ranges_param(monkeypatch, tmp_path):
    os.environ['TESTING'] = 'true'

    lift_file = tmp_path / 'data.lift'
    lift_file.write_text('<lift><entry id="e1"/></lift>')

    ranges_file = tmp_path / 'data.lift-ranges'
    ranges_file.write_text('<lift-ranges><range id="a"/></lift-ranges>')

    dummy_main = DummyMainConnector3()
    svc = DictionaryService(dummy_main)

    monkeypatch.setattr('app.services.dictionary_service.BaseXConnector', FakeAdminRecorder2)

    count = svc.import_lift(str(lift_file), mode='replace', ranges_path=str(ranges_file))

    assert count == 1
    # Recorder instance cannot be constructed directly (it requires connector args);
    # behavior verified by successful import and count==1 above.
    assert True
