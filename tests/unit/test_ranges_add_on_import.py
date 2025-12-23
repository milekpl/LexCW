import os
import tempfile
from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import DatabaseError


RECORDERS = []

class FakeAdminRecorder:
    def __init__(self, host, port, username, password, database=None):
        self.calls = []
        self._open = False
        # register instance for inspection
        RECORDERS.append(self)

    def connect(self):
        return True

    def disconnect(self):
        return True

    def execute_command(self, command: str) -> str:
        self.calls.append(command)
        # Simulate LIST showing DB exists
        if command == 'LIST':
            return 'dictionary\n'
        if command.startswith('CREATE DB '):
            return ''
        if command.startswith('OPEN '):
            self._open = True
            return ''
        if command.startswith('ADD '):
            return ''
        if command.startswith('DROP DB '):
            return ''
        return ''

    def execute_query(self, query: str) -> str:
        # Record verification queries and allow simulating different responses
        self.calls.append(query)
        # If query contains 'first-fails' return empty to simulate parse failure or false
        if 'first-fails' in query:
            return ''
        if 'lift-ranges' in query or 'exists' in query:
            return 'true'
        return ''


class DummyMainConnector2:
    def __init__(self):
        self.database = 'dictionary'
        self.connected = True
        self.host = 'localhost'
        self.port = 1984
        self.username = 'admin'
        self.password = 'admin'

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    def execute_query(self, query: str) -> str:
        return '1'

    def execute_command(self, command: str) -> str:
        # For this test, main connector should not be used for ADD when admin succeeds
        return ''


def test_import_lift_adds_ranges(monkeypatch, tmp_path):
    os.environ['TESTING'] = 'true'

    # Create LIFT file and companion ranges file in same directory
    lift_file = tmp_path / 'data.lift'
    lift_file.write_text('<lift><entry id="e1"/></lift>')

    ranges_file = tmp_path / 'data.lift-ranges'
    ranges_file.write_text('<lift-ranges></lift-ranges>')

    dummy_main = DummyMainConnector2()
    svc = DictionaryService(dummy_main)

    # Patch BaseXConnector used inside the DictionaryService to our recorder
    monkeypatch.setattr('app.services.dictionary_service.BaseXConnector', FakeAdminRecorder)

    count = svc.import_lift(str(lift_file), mode='replace')

    # Ensure entries were counted
    assert count == 1

    # Validate that admin connector recorded an ADD command
    assert len(RECORDERS) > 0
    recorder = RECORDERS[-1]
    assert any('OPEN' in c for c in recorder.calls), f"Expected OPEN in calls, got {recorder.calls}"
    assert any('ADD' in c for c in recorder.calls), f"Expected ADD in calls, got {recorder.calls}"


def test_verification_fallback(monkeypatch, tmp_path):
    os.environ['TESTING'] = 'true'

    lift_file = tmp_path / 'data2.lift'
    lift_file.write_text('<lift><entry id="e1"/></lift>')

    ranges_file = tmp_path / 'data2.lift-ranges'
    ranges_file.write_text('<lift-ranges></lift-ranges>')

    dummy_main = DummyMainConnector2()
    svc = DictionaryService(dummy_main)

    # Patch such that first verification query returns empty, second returns true
    def custom_execute_query(self, query: str) -> str:
        # Record the attempted verification query
        self.calls.append(query)
        # Simulate first query failing (empty) and second returning true
        if "exists(collection('dictionary')//lift-ranges)" in query:
            return ''
        if "local-name()" in query:
            return 'true'
        return ''

    monkeypatch.setattr('app.services.dictionary_service.BaseXConnector', FakeAdminRecorder)
    # Patch the execute_query on recorder instances via monkeypatching the class method
    monkeypatch.setattr(FakeAdminRecorder, 'execute_query', custom_execute_query)

    count = svc.import_lift(str(lift_file), mode='replace')
    assert count == 1
    # Ensure recorder logged the verification queries (calls is appended in execute_query wrapper)
    recorder = RECORDERS[-1]
    assert any('exists(collection' in c for c in recorder.calls) or any('local-name' in c for c in recorder.calls)


def test_import_uses_header_filename(monkeypatch, tmp_path):
    os.environ['TESTING'] = 'true'

    # Create LIFT file with header that references a ranges filename (without path)
    lift_file = tmp_path / 'sample.lift'
    lift_file.write_text('''<lift><header><ranges><range id="dialect" href="sample.lift-ranges"/></ranges></header><entry id="e1"/></lift>")''')

    ranges_file = tmp_path / 'sample.lift-ranges'
    ranges_file.write_text('<lift-ranges></lift-ranges>')

    dummy_main = DummyMainConnector2()
    svc = DictionaryService(dummy_main)

    monkeypatch.setattr('app.services.dictionary_service.BaseXConnector', FakeAdminRecorder)

    count = svc.import_lift(str(lift_file), mode='replace')

    assert count == 1
    recorder = RECORDERS[-1]
    # Expect that the ADD used the filename from the header, not 'ranges.xml'
    assert any('ADD TO sample.lift-ranges' in c for c in recorder.calls), f"Expected ADD TO sample.lift-ranges in calls, got {recorder.calls}"
    assert not any('ranges.xml' in c for c in recorder.calls), "Should not use ranges.xml anywhere"

