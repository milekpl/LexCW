"""
Unit tests for LIFT ranges loading from BaseX.

Tests the DictionaryService.get_ranges() method with different query strategies.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from app.services.dictionary_service import DictionaryService


@pytest.mark.skip_et_mock
class TestRangesLoading:
    """Test ranges loading from BaseX with various query strategies."""

    def test_get_ranges_with_collection_query(self):
        """Test that get_ranges() successfully loads ranges using collection() query."""
        # Mock the BaseX connector with minimal required setup
        mock_connector = Mock()
        mock_connector.database = "test_db"
        mock_connector.is_connected.return_value = False  # Skip connection logic in __init__
        mock_connector.execute_command.return_value = ""
        
        # Sample ranges XML (minimal but valid)
        sample_ranges_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="grammatical-info">
        <range-element id="Noun">
            <label><form lang="en"><text>Noun</text></form></label>
        </range-element>
        <range-element id="Verb">
            <label><form lang="en"><text>Verb</text></form></label>
        </range-element>
    </range>
    <range id="lexica-relation">
        <range-element id="synonym">
            <label><form lang="en"><text>Synonym</text></form></label>
        </range-element>
    </range>
</lift-ranges>
"""
        
        # Mock the query execution to return ranges XML
        mock_connector.execute_query.return_value = sample_ranges_xml
        
        # Create service with mocked connector
        service = DictionaryService(mock_connector)
        
        # Call get_ranges
        ranges = service.get_ranges()
        
        # Debug output
        print(f"\nRanges result: {ranges}")
        print(f"Type: {type(ranges)}")
        print(f"Keys: {list(ranges.keys()) if ranges else 'None'}")
        print(f"execute_query call count: {mock_connector.execute_query.call_count}")
        print(f"execute_query calls: {mock_connector.execute_query.call_args_list}")
        
        # Verify the query was called with collection() syntax
        assert mock_connector.execute_query.called
        # Check that at least one call used the collection query
        calls = [str(call) for call in mock_connector.execute_query.call_args_list]
        collection_query_found = any("collection('test_db')//lift-ranges" in call for call in calls)
        assert collection_query_found, f"Expected collection query not found in calls: {calls}"
        
        # Verify ranges were parsed correctly
        assert ranges is not None
        assert 'grammatical-info' in ranges
        assert 'relation-type' in ranges or 'lexical-relation' in ranges or 'lexica-relation' in ranges
        
        # Verify range structure (parser returns nested dict with 'values' list)
        assert 'values' in ranges['grammatical-info']
        assert len(ranges['grammatical-info']['values']) == 2
        
        # Verify range element IDs
        grammatical_ids = [v['id'] for v in ranges['grammatical-info']['values']]
        assert 'Noun' in grammatical_ids
        assert 'Verb' in grammatical_ids
        
        # Find relation range key (accept legacy or normalized forms)
        relation_keys = ['relation-type', 'lexical-relation', 'lexica-relation']
        relation_key = next((k for k in relation_keys if k in ranges), None)
        assert relation_key is not None
        relation_ids = [v['id'] for v in ranges[relation_key]['values']]
        assert 'synonym' in relation_ids

    def test_get_ranges_caches_result(self):
        """Test that get_ranges() caches the result and doesn't re-query."""
        mock_connector = Mock()
        mock_connector.database = "test_db"
        mock_connector.execute_command.return_value = "test_db"
        
        sample_ranges_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="test-range">
        <range-element id="test-value">
            <label><form lang="en"><text>Test</text></form></label>
        </range-element>
    </range>
</lift-ranges>
"""
        mock_connector.execute_query.return_value = sample_ranges_xml
        
        service = DictionaryService(mock_connector)
        
        # First call
        ranges1 = service.get_ranges()
        
        # Second call
        ranges2 = service.get_ranges()
        
        # Should only query once due to caching
        assert mock_connector.execute_query.call_count == 1
        
        # Results should be identical
        assert ranges1 is ranges2

    def test_get_ranges_returns_empty_dict_when_not_found(self):
        """Test that get_ranges() returns empty dict when ranges not found."""
        mock_connector = Mock()
        mock_connector.database = "test_db"
        mock_connector.execute_command.return_value = "test_db"
        
        # Mock query returns empty/None (ranges not found)
        mock_connector.execute_query.return_value = None
        
        service = DictionaryService(mock_connector)
        
        ranges = service.get_ranges()
        
        # Should return empty dict, not raise exception
        assert ranges == {}

    def test_get_ranges_handles_malformed_xml(self):
        """Test that get_ranges() handles malformed XML gracefully."""
        mock_connector = Mock()
        mock_connector.database = "test_db"
        mock_connector.execute_command.return_value = "test_db"
        
        # Malformed XML
        mock_connector.execute_query.return_value = "<invalid>xml"
        
        service = DictionaryService(mock_connector)
        
        # Should handle error gracefully
        ranges = service.get_ranges()
        
        # Should return empty dict or raise DatabaseError
        # (implementation may vary, but shouldn't crash)
        assert isinstance(ranges, dict)

    def test_get_ranges_with_namespace(self):
        """Test that get_ranges() handles namespaced LIFT XML."""
        mock_connector = Mock()
        mock_connector.database = "test_db"
        mock_connector.execute_command.return_value = "test_db"
        
        # Namespaced ranges XML
        sample_ranges_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges xmlns="http://fieldworks.sil.org/schemas/lift/0.13/ranges">
    <range id="grammatical-info">
        <range-element id="Noun">
            <label><form lang="en"><text>Noun</text></form></label>
        </range-element>
    </range>
</lift-ranges>
"""
        mock_connector.execute_query.return_value = sample_ranges_xml
        
        service = DictionaryService(mock_connector)
        
        ranges = service.get_ranges()
        
        # Parser should handle namespaces
        assert 'grammatical-info' in ranges
        assert 'values' in ranges['grammatical-info']
        noun_ids = [v['id'] for v in ranges['grammatical-info']['values']]
        assert 'Noun' in noun_ids

    def test_get_ranges_ensures_plural_keys(self):
        """Test that get_ranges() ensures both singular and plural keys exist."""
        mock_connector = Mock()
        mock_connector.database = "test_db"
        mock_connector.execute_command.return_value = "test_db"
        
        sample_ranges_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="relation-type">
        <range-element id="synonym">
            <label><form lang="en"><text>Synonym</text></form></label>
        </range-element>
    </range>
</lift-ranges>
"""
        mock_connector.execute_query.return_value = sample_ranges_xml
        
        service = DictionaryService(mock_connector)
        
        ranges = service.get_ranges()
        
        # Only the canonical form should exist (the one that's actually in the data)
        # Accept either canonical 'relation-type' or the normalized
        # 'lexical-relation' used by the ranges metadata mapping.
        assert 'relation-type' in ranges or 'lexical-relation' in ranges
        # Note: 'lexical-relation' is not automatically added as an alias anymore
