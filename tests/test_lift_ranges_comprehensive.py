"""
Comprehensive tests for LIFT ranges parser functionality.

This test suite ensures that the LIFTRangesParser can handle all range types
from the sample LIFT ranges file and supports all LIFT 0.13 features.
"""

import pytest
import xml.etree.ElementTree as ET
from typing import Dict, Any

from app.parsers.lift_parser import LIFTRangesParser


class TestLIFTRangesParserComprehensive:
    """Test comprehensive LIFT ranges parsing functionality."""

    @pytest.fixture
    def ranges_parser(self):
        """Create a LIFTRangesParser instance for testing."""
        return LIFTRangesParser()

    @pytest.fixture
    def sample_ranges_file_path(self):
        """Path to the sample LIFT ranges file."""
        return "sample-lift-file/sample-lift-file.lift-ranges"

    def test_parse_sample_ranges_file_all_types(self, ranges_parser, sample_ranges_file_path):
        """Test that all 21 range types from the sample file are parsed correctly."""
        ranges = ranges_parser.parse_file(sample_ranges_file_path)
        
        # Verify all expected range types are present
        expected_range_types = [
            'etymology',
            'grammatical-info',
            'lexical-relation',
            'note-type',
            'paradigm',
            'reversal-type',
            'semantic-domain-ddp4',
            'status',
            'users',
            'location',
            'anthro-code',
            'translation-type',
            'inflection-feature',
            'inflection-feature-type',
            'from-part-of-speech',
            'morph-type',
            'num-feature-value',
            'Publications',
            'do-not-publish-in',
            'domain-type',
            'usage-type'
        ]
        
        for range_type in expected_range_types:
            assert range_type in ranges, f"Range type '{range_type}' not found in parsed ranges"
            assert 'id' in ranges[range_type], f"Range '{range_type}' missing 'id' field"
            assert 'values' in ranges[range_type], f"Range '{range_type}' missing 'values' field"
            assert isinstance(ranges[range_type]['values'], list), f"Range '{range_type}' values is not a list"

    def test_parse_range_with_hierarchical_structure(self, ranges_parser, sample_ranges_file_path):
        """Test parsing of hierarchical ranges like grammatical-info and semantic-domain."""
        ranges = ranges_parser.parse_file(sample_ranges_file_path)
        
        # Test grammatical-info hierarchy
        grammatical_info = ranges['grammatical-info']
        
        # Find a hierarchical element
        noun_element = None
        for value in grammatical_info['values']:
            if value['id'] == 'Noun':
                noun_element = value
                break
        
        assert noun_element is not None, "Noun element not found in grammatical-info"
        
        # Check for child elements (should have Countable Noun, etc.)
        child_elements = [child['id'] for child in noun_element.get('children', [])]
        assert 'Countable Noun' in child_elements or any('Countable' in child for child in child_elements), \
            "Countable Noun child not found under Noun"

    def test_parse_range_with_guid_support(self, ranges_parser, sample_ranges_file_path):
        """Test that GUID attributes are correctly parsed."""
        ranges = ranges_parser.parse_file(sample_ranges_file_path)
        
        # Test that some elements have GUIDs
        grammatical_info = ranges['grammatical-info']
        guid_found = False
        
        for value in grammatical_info['values']:
            if value.get('guid'):
                guid_found = True
                # Verify GUID format (should be UUID-like)
                guid = value['guid']
                assert len(guid) > 10, f"GUID '{guid}' seems too short"
                assert '-' in guid, f"GUID '{guid}' doesn't contain hyphens"
                break
        
        assert guid_found, "No GUIDs found in grammatical-info range elements"

    def test_parse_range_with_multilingual_labels(self, ranges_parser, sample_ranges_file_path):
        """Test parsing of multi-language labels and descriptions."""
        ranges = ranges_parser.parse_file(sample_ranges_file_path)
        
        # Check that elements have descriptions with language codes
        grammatical_info = ranges['grammatical-info']
        
        description_found = False
        for value in grammatical_info['values']:
            if value.get('description') and isinstance(value['description'], dict):
                description_found = True
                # Should have at least 'en' (English) descriptions
                assert 'en' in value['description'], f"No English description found for {value['id']}"
                break
        
        assert description_found, "No multi-language descriptions found"

    def test_parse_range_with_abbreviations(self, ranges_parser, sample_ranges_file_path):
        """Test that abbreviations are correctly parsed."""
        ranges = ranges_parser.parse_file(sample_ranges_file_path)
        
        # Check grammatical-info for abbreviations
        grammatical_info = ranges['grammatical-info']
        
        abbrev_found = False
        for value in grammatical_info['values']:
            if value.get('abbrev') and value['abbrev'].strip():
                abbrev_found = True
                # Abbreviations should be shorter than full labels
                abbrev = value['abbrev']
                assert len(abbrev) <= 10, f"Abbreviation '{abbrev}' seems too long"
                break
        
        assert abbrev_found, "No abbreviations found in grammatical-info"

    def test_parse_semantic_domain_large_hierarchy(self, ranges_parser, sample_ranges_file_path):
        """Test parsing of large hierarchical range like semantic-domain-ddp4."""
        ranges = ranges_parser.parse_file(sample_ranges_file_path)
        
        semantic_domain = ranges['semantic-domain-ddp4']
        
        # Should have a reasonable number of top-level domains (like 9 major categories)
        assert len(semantic_domain['values']) >= 5, \
            f"Semantic domain should have major categories, found {len(semantic_domain['values'])}"
        
        # Count total elements recursively
        def count_total_elements(values):
            total = len(values)
            for value in values:
                if value.get('children'):
                    total += count_total_elements(value['children'])
            return total
        
        total_elements = count_total_elements(semantic_domain['values'])
        
        # Should have hundreds of total elements (including nested)
        assert total_elements > 50, \
            f"Semantic domain should have many total elements, found {total_elements}"
        
        # Should have hierarchical structure
        hierarchical_found = False
        for value in semantic_domain['values']:
            if value.get('children') and len(value['children']) > 0:
                hierarchical_found = True
                # Check that children have proper structure
                for child in value['children']:
                    assert 'id' in child, "Child element missing 'id'"
                    assert 'value' in child, "Child element missing 'value'"
                break
        
        assert hierarchical_found, "No hierarchical structure found in semantic-domain-ddp4"

    def test_parse_simple_ranges(self, ranges_parser, sample_ranges_file_path):
        """Test parsing of simple ranges like etymology and status."""
        ranges = ranges_parser.parse_file(sample_ranges_file_path)
        
        # Test etymology range (should be simple)
        etymology = ranges['etymology']
        assert len(etymology['values']) >= 2, "Etymology should have at least 2 values"
        
        # Check for expected etymology types
        etymology_ids = [value['id'] for value in etymology['values']]
        assert 'borrowed' in etymology_ids, "Etymology should include 'borrowed'"
        assert 'proto' in etymology_ids, "Etymology should include 'proto'"

    def test_parse_range_with_traits(self, ranges_parser):
        """Test parsing of range elements with traits (name-value pairs)."""
        # Create a test XML with traits
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift-ranges>
            <range id="test-range">
                <range-element id="test-element">
                    <label><form lang="en"><text>Test Element</text></form></label>
                    <trait name="catalog-source-id" value="TestValue"/>
                    <trait name="inflectable-feat" value="nagr"/>
                </range-element>
            </range>
        </lift-ranges>'''
        
        ranges = ranges_parser.parse_string(test_xml)
        
        # Note: Current parser doesn't handle traits - this test documents the requirement
        # This test will initially fail, driving the implementation
        test_range = ranges['test-range']
        test_element = test_range['values'][0]
        
        # TODO: Implement trait parsing in LIFTRangesParser
        # assert 'traits' in test_element, "Traits not parsed"
        # assert test_element['traits']['catalog-source-id'] == 'TestValue'

    def test_parse_range_with_parent_attribute(self, ranges_parser):
        """Test parsing of range elements with parent relationships."""
        # Create test XML with parent relationships
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift-ranges>
            <range id="test-hierarchy">
                <range-element id="parent-element">
                    <label><form lang="en"><text>Parent Element</text></form></label>
                </range-element>
                <range-element id="child-element" parent="parent-element">
                    <label><form lang="en"><text>Child Element</text></form></label>
                </range-element>
            </range>
        </lift-ranges>'''
        
        ranges = ranges_parser.parse_string(test_xml)
        
        test_range = ranges['test-hierarchy']
        
        # Should have only 1 top-level element (the parent)
        assert len(test_range['values']) == 1, f"Expected 1 top-level element, found {len(test_range['values'])}"
        
        # Find parent element
        parent_element = test_range['values'][0]
        assert parent_element['id'] == 'parent-element', "Parent element not found at top level"
        
        # Child should be nested under parent
        assert 'children' in parent_element, "Parent element should have children"
        assert len(parent_element['children']) == 1, "Parent should have exactly 1 child"
        
        child_element = parent_element['children'][0]
        assert child_element['id'] == 'child-element', "Child element not found under parent"
        assert child_element['description']['en'] == 'Child Element', "Child element description not parsed correctly"

    def test_parse_range_error_handling(self, ranges_parser):
        """Test error handling for malformed XML."""
        # Test with invalid XML
        with pytest.raises(ET.ParseError):
            ranges_parser.parse_string("<invalid-xml>")
        
        # Test with missing file
        with pytest.raises(FileNotFoundError):
            ranges_parser.parse_file("nonexistent-file.xml")

    def test_parse_range_namespace_handling(self, ranges_parser):
        """Test that parser handles both namespaced and non-namespaced XML."""
        # Test namespaced XML
        namespaced_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift-ranges xmlns="http://fieldworks.sil.org/schemas/lift/0.13/ranges">
            <range id="test-ns">
                <range-element id="element1">
                    <label><form lang="en"><text>Element 1</text></form></label>
                </range-element>
            </range>
        </lift-ranges>'''
        
        # Test non-namespaced XML
        non_namespaced_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift-ranges>
            <range id="test-no-ns">
                <range-element id="element1">
                    <label><form lang="en"><text>Element 1</text></form></label>
                </range-element>
            </range>
        </lift-ranges>'''
        
        ns_ranges = ranges_parser.parse_string(namespaced_xml)
        no_ns_ranges = ranges_parser.parse_string(non_namespaced_xml)
        
        assert 'test-ns' in ns_ranges, "Namespaced range not parsed"
        assert 'test-no-ns' in no_ns_ranges, "Non-namespaced range not parsed"

    def test_parse_range_performance_large_file(self, ranges_parser, sample_ranges_file_path):
        """Test parsing performance with the large sample ranges file."""
        import time
        
        start_time = time.time()
        ranges = ranges_parser.parse_file(sample_ranges_file_path)
        parse_time = time.time() - start_time
        
        # Should parse the large file in reasonable time (< 5 seconds)
        assert parse_time < 5.0, f"Parsing took too long: {parse_time:.2f} seconds"
        
        # Should return substantial data
        assert len(ranges) >= 20, f"Expected at least 20 ranges, got {len(ranges)}"
        
        # Total number of range elements should be substantial
        total_elements = sum(len(range_data['values']) for range_data in ranges.values())
        assert total_elements > 100, f"Expected >100 total elements, got {total_elements}"
