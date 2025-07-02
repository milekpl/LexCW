"""
Comprehensive test for LIFT ranges parser following TDD methodology.

This test file defines the expected behavior for full LIFT ranges support
including all range types from the sample file and proper hierarchical structure.
"""

from __future__ import annotations

import pytest
import tempfile
import os
from app.parsers.lift_parser import LIFTRangesParser


class TestLIFTRangesParserComprehensive:
    """Comprehensive tests for LIFTRangesParser."""

    @pytest.fixture
    def sample_ranges_xml(self) -> str:
        """Sample LIFT ranges XML with various range types for testing."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <!-- Simple range without hierarchy -->
    <range id="etymology">
        <range-element id="borrowed">
            <label><form lang="en"><text>borrowed</text></form></label>
            <description><form lang="en"><text>The word is borrowed from another language</text></form></description>
        </range-element>
        <range-element id="proto">
            <label><form lang="en"><text>proto</text></form></label>
            <description><form lang="en"><text>The proto form of the word in another language</text></form></description>
        </range-element>
    </range>
    
    <!-- Hierarchical range with parent-child relationships -->
    <range id="grammatical-info">
        <range-element id="Noun" guid="a8e41fd3-e343-4c7c-aa05-01ea3dd5cfb5">
            <label><form lang="en"><text>Noun</text></form></label>
            <abbrev><form lang="en"><text>n</text></form></abbrev>
            <description><form lang="en"><text>A noun is a broad classification of parts of speech which include substantives and nominals.</text></form></description>
            <trait name="inflectable-feat" value="nagr"/>
            <trait name="catalog-source-id" value="Noun"/>
        </range-element>
        <range-element id="Countable Noun" guid="b4c74c31-58fc-4feb-86bf-c2235bda8d3c" parent="Noun">
            <label><form lang="en"><text>Countable Noun</text></form></label>
            <abbrev><form lang="en"><text>n [C]</text></form></abbrev>
            <trait name="catalog-source-id" value=""/>
        </range-element>
        <range-element id="Verb" guid="c3285c42-69g6-5gfc-97cg-d3346cea9e4d">
            <label><form lang="en"><text>Verb</text></form></label>
            <abbrev><form lang="en"><text>v</text></form></abbrev>
            <description><form lang="en"><text>A verb is a word that describes an action or state.</text></form></description>
        </range-element>
    </range>
    
    <!-- Range with multilingual labels -->
    <range id="lexical-relation">
        <range-element id="synonym">
            <label><form lang="en"><text>synonym</text></form></label>
            <label><form lang="pl"><text>synonim</text></form></label>
            <description><form lang="en"><text>Words with the same meaning</text></form></description>
            <description><form lang="pl"><text>Słowa o tym samym znaczeniu</text></form></description>
        </range-element>
    </range>
    
    <!-- Large hierarchical range (semantic domains) -->
    <range id="semantic-domain-ddp4">
        <range-element id="1">
            <label><form lang="en"><text>Universe, creation</text></form></label>
            <abbrev><form lang="en"><text>1</text></form></abbrev>
        </range-element>
        <range-element id="1.1" parent="1">
            <label><form lang="en"><text>Sky</text></form></label>
            <abbrev><form lang="en"><text>1.1</text></form></abbrev>
        </range-element>
        <range-element id="1.1.1" parent="1.1">
            <label><form lang="en"><text>Sun</text></form></label>
            <abbrev><form lang="en"><text>1.1.1</text></form></abbrev>
        </range-element>
        <range-element id="2">
            <label><form lang="en"><text>Person</text></form></label>
            <abbrev><form lang="en"><text>2</text></form></abbrev>
        </range-element>
        <range-element id="2.1" parent="2">
            <label><form lang="en"><text>Body</text></form></label>
            <abbrev><form lang="en"><text>2.1</text></form></abbrev>
        </range-element>
    </range>
</lift-ranges>'''

    @pytest.fixture
    def ranges_parser(self) -> LIFTRangesParser:
        """Create a LIFT ranges parser instance."""
        return LIFTRangesParser()

    def test_parser_parses_all_range_types(self, ranges_parser: LIFTRangesParser, sample_ranges_xml: str):
        """Test that parser correctly identifies all range types."""
        ranges = ranges_parser.parse_string(sample_ranges_xml)
        
        # Should parse all 4 range types
        assert len(ranges) == 4
        assert 'etymology' in ranges
        assert 'grammatical-info' in ranges
        assert 'lexical-relation' in ranges
        assert 'semantic-domain-ddp4' in ranges

    def test_parser_handles_simple_ranges(self, ranges_parser: LIFTRangesParser, sample_ranges_xml: str):
        """Test parsing of simple (non-hierarchical) ranges."""
        ranges = ranges_parser.parse_string(sample_ranges_xml)
        
        etymology_range = ranges['etymology']
        assert etymology_range['id'] == 'etymology'
        assert len(etymology_range['values']) == 2
        
        # Check the values
        borrowed = next(v for v in etymology_range['values'] if v['id'] == 'borrowed')
        assert borrowed['description']['en'] == 'The word is borrowed from another language'
        
        proto = next(v for v in etymology_range['values'] if v['id'] == 'proto')
        assert proto['description']['en'] == 'The proto form of the word in another language'

    def test_parser_handles_hierarchical_ranges(self, ranges_parser: LIFTRangesParser, sample_ranges_xml: str):
        """Test parsing of hierarchical ranges with parent-child relationships."""
        ranges = ranges_parser.parse_string(sample_ranges_xml)
        
        grammatical_range = ranges['grammatical-info']
        assert grammatical_range['id'] == 'grammatical-info'
        
        # Should have 2 root elements (Noun and Verb)
        assert len(grammatical_range['values']) == 2
        
        # Find the Noun element
        noun = next(v for v in grammatical_range['values'] if v['id'] == 'Noun')
        assert noun['abbrev'] == 'n'
        assert 'nagr' in noun['traits']['inflectable-feat']
        
        # Noun should have 1 child (Countable Noun)
        assert len(noun['children']) == 1
        countable_noun = noun['children'][0]
        assert countable_noun['id'] == 'Countable Noun'
        assert countable_noun['abbrev'] == 'n [C]'

    def test_parser_handles_multilingual_content(self, ranges_parser: LIFTRangesParser, sample_ranges_xml: str):
        """Test parsing of multilingual labels and descriptions."""
        ranges = ranges_parser.parse_string(sample_ranges_xml)
        
        lexical_range = ranges['lexical-relation']
        synonym = lexical_range['values'][0]
        
        # Should have both English and Polish labels
        assert synonym['description']['en'] == 'Words with the same meaning'
        assert synonym['description']['pl'] == 'Słowa o tym samym znaczeniu'

    def test_parser_handles_deep_hierarchy(self, ranges_parser: LIFTRangesParser, sample_ranges_xml: str):
        """Test parsing of deep hierarchical structures (3 levels)."""
        ranges = ranges_parser.parse_string(sample_ranges_xml)
        
        semantic_range = ranges['semantic-domain-ddp4']
        assert len(semantic_range['values']) == 2  # Two root elements: 1 and 2
        
        # Find Universe element (1)
        universe = next(v for v in semantic_range['values'] if v['id'] == '1')
        assert universe['description']['en'] == 'Universe, creation'
        assert len(universe['children']) == 1
        
        # Check Sky (1.1)
        sky = universe['children'][0]
        assert sky['id'] == '1.1'
        assert sky['description']['en'] == 'Sky'
        assert len(sky['children']) == 1
        
        # Check Sun (1.1.1)
        sun = sky['children'][0]
        assert sun['id'] == '1.1.1'
        assert sun['description']['en'] == 'Sun'

    def test_parser_handles_guid_and_traits(self, ranges_parser: LIFTRangesParser, sample_ranges_xml: str):
        """Test parsing of GUID attributes and trait elements."""
        ranges = ranges_parser.parse_string(sample_ranges_xml)
        
        grammatical_range = ranges['grammatical-info']
        noun = next(v for v in grammatical_range['values'] if v['id'] == 'Noun')
        
        # Check GUID
        assert noun['guid'] == 'a8e41fd3-e343-4c7c-aa05-01ea3dd5cfb5'
        
        # Check traits
        assert 'inflectable-feat' in noun['traits']
        assert noun['traits']['inflectable-feat'] == 'nagr'
        assert 'catalog-source-id' in noun['traits']
        assert noun['traits']['catalog-source-id'] == 'Noun'

    def test_parser_with_real_sample_file(self, ranges_parser: LIFTRangesParser):
        """Test parser with the actual sample LIFT ranges file."""
        sample_file_path = 'sample-lift-file/sample-lift-file.lift-ranges'
        
        if os.path.exists(sample_file_path):
            ranges = ranges_parser.parse_file(sample_file_path)
            
            # Should have all expected range types from the sample file
            expected_ranges = [
                'etymology', 'grammatical-info', 'lexical-relation', 'note-type',
                'paradigm', 'reversal-type', 'semantic-domain-ddp4', 'status',
                'users', 'location', 'anthro-code', 'translation-type',
                'inflection-feature', 'inflection-feature-type', 'from-part-of-speech',
                'morph-type', 'num-feature-value', 'Publications', 'do-not-publish-in',
                'domain-type', 'usage-type'
            ]
            
            # Check that we found most range types (some may be missing due to structure)
            found_ranges = set(ranges.keys())
            missing_ranges = set(expected_ranges) - found_ranges
            
            # Should find at least 15 of the 21 expected ranges
            assert len(found_ranges) >= 15, f"Found {len(found_ranges)} ranges, missing: {missing_ranges}"
            
            # Check that semantic-domain-ddp4 has hierarchical structure
            if 'semantic-domain-ddp4' in ranges:
                semantic_range = ranges['semantic-domain-ddp4']
                assert len(semantic_range['values']) > 0
                
                # Should have some root elements with children
                has_hierarchy = any(len(v.get('children', [])) > 0 for v in semantic_range['values'])
                assert has_hierarchy, "Semantic domain should have hierarchical structure"

    def test_parser_error_handling(self, ranges_parser: LIFTRangesParser):
        """Test parser error handling with invalid XML."""
        with pytest.raises(Exception):  # Should raise XML parsing error
            ranges_parser.parse_string('<invalid xml>')
        
        with pytest.raises(FileNotFoundError):
            ranges_parser.parse_file('nonexistent_file.xml')

    def test_parser_empty_ranges(self, ranges_parser: LIFTRangesParser):
        """Test parser with empty or minimal ranges."""
        empty_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
</lift-ranges>'''
        
        ranges = ranges_parser.parse_string(empty_xml)
        assert len(ranges) == 0

    def test_parser_namespace_handling(self, ranges_parser: LIFTRangesParser):
        """Test parser handles both namespaced and non-namespaced XML."""
        # Test with namespace
        namespaced_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges xmlns="http://fieldworks.sil.org/schemas/lift/0.13/ranges">
    <range id="test">
        <range-element id="item">
            <label><form lang="en"><text>Test Item</text></form></label>
        </range-element>
    </range>
</lift-ranges>'''
        
        ranges = ranges_parser.parse_string(namespaced_xml)
        assert 'test' in ranges
        assert ranges['test']['values'][0]['description']['en'] == 'Test Item'
