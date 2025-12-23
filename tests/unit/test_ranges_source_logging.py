import os
import tempfile
import re
import logging
from app.services.dictionary_service import DictionaryService


class FakeConnectorWithDocURI:
    def __init__(self):
        self.database = 'dictionary'
        self.host = 'localhost'
        self.port = 1984
        self.username = 'admin'
        self.password = 'admin'

    def is_connected(self):
        return True

    def execute_query(self, query: str) -> str:
        # If asking for ranges, return a small ranges document
        if 'collection' in query and 'lift-ranges' in query and 'for $r in' not in query:
            return '<lift-ranges></lift-ranges>'
        # If asking for document-uri, return a URI
        if query.strip().startswith('for $r in') and 'document-uri' in query:
            return 'xmldb:/db/dictionary/ranges.xml\n'
        return ''


def test_ranges_source_is_logged(caplog, tmp_path):
    os.environ['TESTING'] = 'true'
    caplog.set_level(logging.DEBUG)

    conn = FakeConnectorWithDocURI()
    svc = DictionaryService(conn)

    # Monkeypatch the db_connector to our fake
    svc.db_connector = conn

    _ = svc.get_lift_ranges()

    # Check logs contain the source filename 'ranges.xml'
    found = any('ranges.xml' in rec.message for rec in caplog.records)
    assert found, f"Expected 'ranges.xml' in logs, got: {[r.message for r in caplog.records]}"