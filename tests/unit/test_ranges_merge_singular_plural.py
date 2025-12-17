"""Unit tests for merging singular/plural range IDs."""
from app.services.ranges_service import RangesService
from app.database.mock_connector import MockDatabaseConnector
from unittest.mock import Mock


def test_merge_singular_plural_pairs():
    mock_connector = MockDatabaseConnector()
    service = RangesService(mock_connector)
    # Provide ranges XML directly from the mock connector to simulate parsed ranges
    ranges_xml = (
        '<ranges>'
        '<range id="variant-type">'
        '<range-element id="a" />'
        '<range-element id="b" />'
        '</range>'
        '<range id="variant-type">'
        '<range-element id="c" />'
        '</range>'
        '</ranges>'
    )
    mock_connector.execute_query = lambda q: ranges_xml

    # Sanity check: ensure our mock returns the XML we set
    assert mock_connector.execute_query('query') == ranges_xml

    # Mock the parser to return parsed ranges so we don't depend on XML parsing here
    service.ranges_parser.parse_string = Mock(return_value={
        'variant-type': {'id': 'variant-type', 'values': [{'id': 'a'}, {'id': 'b'}], 'labels': {}, 'descriptions': {}},
        'variant-type': {'id': 'variant-type', 'values': [{'id': 'c'}], 'labels': {}, 'descriptions': {}},
    })

    merged = service.get_all_ranges()

    # Only one key should remain (preferred one has more values? here plural has 1, singular has 2 -> singular kept)
    keys = list(merged.keys())
    assert ('variant-type' in keys) ^ ('variant-type' in keys)  # exactly one present

    # The remaining should have all unique values
    remaining = merged.get('variant-type') or merged.get('variant-type')
    ids = {v.get('id') for v in remaining['values']}
    assert ids == {'a', 'b', 'c'}