import pytest
from unittest.mock import Mock, patch

from app.services.dictionary_service import DictionaryService


def test_scan_handles_concatenated_entries_and_calls_importer(monkeypatch):
    # Prepare a mock DB connector that returns distinct relation and trait values
    mock_connector = Mock()
    mock_connector.database = 'test_db'

    def mock_query(q):
        if "relation" in q:
            return "custom-rel"
        if "trait" in q:
            return "custom-trait"
        return ""

    mock_connector.execute_query.side_effect = mock_query

    service = DictionaryService(db_connector=mock_connector)

    # Patch the parser to return some undefined ranges
    class DummyParser:
        def identify_undefined_ranges_from_sets(self, found_relations, found_traits, ranges_xml=None):
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
