import pytest
from unittest.mock import Mock, patch

from app.services.dictionary_service import DictionaryService


def test_scan_handles_concatenated_entries_and_calls_importer(monkeypatch):
    # Prepare a mock DB connector that returns concatenated serialized entries
    mock_connector = Mock()
    mock_connector.database = 'test_db'
    # Simulate two serialized entry fragments with XML prolog and namespace
    frag1 = '<?xml version="1.0" encoding="UTF-8"?><entry id="e1"><lexical-unit></lexical-unit></entry>'
    frag2 = '<?xml version="1.0" encoding="UTF-8"?><entry id="e2"><lexical-unit></lexical-unit></entry>'
    mock_connector.execute_query.side_effect = lambda q: frag1 + frag2 if "string-join" in q else None

    service = DictionaryService(db_connector=mock_connector)

    # Patch the parser to return some undefined ranges
    class DummyParser:
        def identify_undefined_ranges(self, lift_xml, ranges_xml=None, list_xml=None):
            assert '<lift>' in lift_xml and '</lift>' in lift_xml
            return ({'custom-rel'}, {'custom-trait': {'a'}})

    # Patch the parser in its module path and the import service
    monkeypatch.setattr('app.parsers.undefined_ranges_parser.UndefinedRangesParser', lambda: DummyParser())

    # Patch the import service to capture calls
    mock_import = Mock()
    monkeypatch.setattr('app.services.lift_import_service.LIFTImportService', lambda db: mock_import)

    # Run scan (should not raise)
    service.scan_and_create_custom_ranges(project_id=1)

    # Verify importer was invoked
    assert mock_import.create_custom_ranges.called
