import os
import logging
from app.services.dictionary_service import DictionaryService


class FakeConnectorEmptyRanges:
    def __init__(self):
        self.database = 'dictionary'
        self.host = 'localhost'
        self.port = 1984
        self.username = 'admin'
        self.password = 'admin'

    def is_connected(self):
        return True

    def execute_query(self, query: str) -> str:
        # When asked for ranges, return an empty ranges document
        if 'collection' in query and 'lift-ranges' in query:
            return '<lift-ranges></lift-ranges>'
        return ''


def test_truncated_ranges_sample_logged(caplog):
    os.environ['TESTING'] = 'true'
    caplog.set_level(logging.DEBUG)

    conn = FakeConnectorEmptyRanges()
    svc = DictionaryService(conn)
    svc.db_connector = conn

    _ = svc.get_lift_ranges()

    # Ensure a truncated sample was logged at DEBUG
    found = any('Ranges XML sample' in rec.message for rec in caplog.records)
    assert found, f"Expected 'Ranges XML sample' debug log, got: {[r.message for r in caplog.records]}"