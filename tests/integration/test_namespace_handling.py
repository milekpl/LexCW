"""
Test cases for XML namespace handling improvements.

This module contains tests to verify the new namespace handling utilities
work correctly with both namespaced and non-namespaced LIFT XML.
"""

import pytest
import xml.etree.ElementTree as ET
from app.utils.namespace_manager import LIFTNamespaceManager, XPathBuilder
from app.utils.xquery_builder import XQueryBuilder



@pytest.mark.integration
class TestLIFTNamespaceManager:
    """Test cases for LIFTNamespaceManager."""
    
    @pytest.mark.integration
    def test_detect_namespaces_with_lift_namespace(self):
        """Test namespace detection with LIFT namespace."""
        xml_with_ns = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13" version="0.13">
            <entry id="test">
                <lexical-unit>
                    <form lang="en">
                        <text>test</text>
                    </form>
                </lexical-unit>
            </entry>
        </lift>'''
        
        namespaces = LIFTNamespaceManager.detect_namespaces(xml_with_ns)
        assert '' in namespaces
        assert namespaces[''] == LIFTNamespaceManager.LIFT_NAMESPACE
        assert LIFTNamespaceManager.has_lift_namespace(xml_with_ns) is True
    
    @pytest.mark.integration
    def test_detect_namespaces_without_namespace(self):
        """Test namespace detection without namespace."""
        xml_without_ns = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test">
                <lexical-unit>
                    <form lang="en">
                        <text>test</text>
                    </form>
                </lexical-unit>
            </entry>
        </lift>'''
        
        assert LIFTNamespaceManager.has_lift_namespace(xml_without_ns) is False
    
    @pytest.mark.integration
    def test_normalize_add_namespace(self):
        """Test adding namespace to non-namespaced XML."""
        xml_without_ns = '''<lift version="0.13">
            <entry id="test">
                <lexical-unit>
                    <form lang="en">
                        <text>test</text>
                    </form>
                </lexical-unit>
            </entry>
        </lift>'''

        normalized = LIFTNamespaceManager.normalize_lift_xml(
            xml_without_ns, LIFTNamespaceManager.LIFT_NAMESPACE
        )

        # Check that namespace is properly added (either default or prefixed)
        has_default_ns = 'xmlns="http://fieldworks.sil.org/schemas/lift/0.13"' in normalized
        has_prefixed_ns = 'xmlns:lift="http://fieldworks.sil.org/schemas/lift/0.13"' in normalized
        assert has_default_ns or has_prefixed_ns, f"Expected namespace declaration in: {normalized[:200]}"
        assert LIFTNamespaceManager.has_lift_namespace(normalized) is True
    
    @pytest.mark.integration
    def test_normalize_remove_namespace(self):
        """Test removing namespace from namespaced XML."""
        xml_with_ns = '''<lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13" version="0.13">
            <entry id="test">
                <lexical-unit>
                    <form lang="en">
                        <text>test</text>
                    </form>
                </lexical-unit>
            </entry>
        </lift>'''
        
        normalized = LIFTNamespaceManager.normalize_lift_xml(xml_with_ns, None)
        
        assert 'xmlns=' not in normalized
        assert LIFTNamespaceManager.has_lift_namespace(normalized) is False
    
    @pytest.mark.integration
    def test_xpath_with_namespace(self):
        """Test XPath generation with namespace."""
        xpath_with_ns = LIFTNamespaceManager.get_xpath_with_namespace(
            "//entry[@id='test']", has_namespace=True
        )
        assert xpath_with_ns == "//lift:entry[@id='test']"
    
    @pytest.mark.integration
    def test_xpath_without_namespace(self):
        """Test XPath generation without namespace."""
        xpath_without_ns = LIFTNamespaceManager.get_xpath_with_namespace(
            "//lift:entry[@id='test']", has_namespace=False
        )
        assert xpath_without_ns == "//entry[@id='test']"



@pytest.mark.integration
class TestXPathBuilder:
    """Test cases for XPathBuilder."""
    
    @pytest.mark.integration
    def test_entry_xpath_with_namespace(self):
        """Test entry XPath with namespace."""
        xpath = XPathBuilder.entry("test_id", has_namespace=True)
        assert xpath == "//lift:entry[@id='test_id']"
    
    @pytest.mark.integration
    def test_entry_xpath_without_namespace(self):
        """Test entry XPath without namespace."""
        xpath = XPathBuilder.entry("test_id", has_namespace=False)
        assert xpath == "//entry[@id='test_id']"
    
    @pytest.mark.integration
    def test_sense_xpath(self):
        """Test sense XPath generation."""
        xpath_with_ns = XPathBuilder.sense("sense1", has_namespace=True)
        xpath_without_ns = XPathBuilder.sense("sense1", has_namespace=False)
        
        assert xpath_with_ns == "//lift:sense[@id='sense1']"
        assert xpath_without_ns == "//sense[@id='sense1']"
    
    @pytest.mark.integration
    def test_lexical_unit_xpath(self):
        """Test lexical-unit XPath generation."""
        xpath_with_ns = XPathBuilder.lexical_unit("en", has_namespace=True)
        xpath_without_ns = XPathBuilder.lexical_unit("en", has_namespace=False)
        
        assert xpath_with_ns == "//lift:lexical-unit/lift:form[@lang='en']"
        assert xpath_without_ns == "//lexical-unit/form[@lang='en']"



@pytest.mark.integration
class TestXQueryBuilder:
    """Test cases for XQueryBuilder."""
    
    @pytest.mark.integration
    def test_namespace_prologue(self):
        """Test XQuery namespace prologue generation."""
        prologue_with_ns = XQueryBuilder.get_namespace_prologue(has_lift_namespace=True)
        prologue_without_ns = XQueryBuilder.get_namespace_prologue(has_lift_namespace=False)
        
        assert 'declare namespace lift' in prologue_with_ns
        assert 'declare namespace flex' in prologue_with_ns
        assert prologue_without_ns == ""
    
    @pytest.mark.integration
    def test_entry_by_id_query_with_namespace(self):
        """Test entry by ID query with namespace."""
        query = XQueryBuilder.build_entry_by_id_query(
            "test_entry", "test_db", has_namespace=True
        )
        
        assert "declare namespace lift" in query
        assert "lift:entry[@id=\"test_entry\"]" in query
        assert "collection('test_db')" in query
    
    @pytest.mark.integration
    def test_entry_by_id_query_without_namespace(self):
        """Test entry by ID query without namespace."""
        query = XQueryBuilder.build_entry_by_id_query(
            "test_entry", "test_db", has_namespace=False
        )
        
        assert "declare namespace" not in query
        assert "entry[@id=\"test_entry\"]" in query
        assert "lift:" not in query
    
    @pytest.mark.integration
    def test_search_query_with_pagination(self):
        """Test search query with pagination."""
        query = XQueryBuilder.build_search_query(
            "test_term", "test_db", has_namespace=True, limit=10, offset=5
        )
        
        assert "contains(string($entry), \"test_term\")" in query
        assert "position() > 5" in query
        assert "[position() <= 10]" in query
    
    @pytest.mark.integration
    def test_count_entries_query(self):
        """Test count entries query."""
        count_query_all = XQueryBuilder.build_count_entries_query("test_db", has_namespace=True)
        count_query_search = XQueryBuilder.build_count_entries_query(
            "test_db", has_namespace=True, search_term="test"
        )
        
        assert "count(" in count_query_all
        assert "lift:entry" in count_query_all
        assert "contains(string($entry), \"test\")" in count_query_search
    
    @pytest.mark.integration
    def test_insert_entry_query(self):
        """Test insert entry query."""
        entry_xml = "<entry id='test'><lexical-unit><form lang='en'><text>test</text></form></lexical-unit></entry>"
        query = XQueryBuilder.build_insert_entry_query(entry_xml, "test_db", has_namespace=True)
        
        assert "insert node" in query
        assert "lift:lift" in query
        assert entry_xml in query
    
    @pytest.mark.integration
    def test_update_entry_query(self):
        """Test update entry query."""
        entry_xml = "<entry id='test'><lexical-unit><form lang='en'><text>updated</text></form></lexical-unit></entry>"
        query = XQueryBuilder.build_update_entry_query("test", entry_xml, "test_db", has_namespace=True)
        
        assert "replace node" in query
        assert "lift:entry[@id=\"test\"]" in query
        assert entry_xml in query
    
    @pytest.mark.integration
    def test_delete_entry_query(self):
        """Test delete entry query."""
        query = XQueryBuilder.build_delete_entry_query("test", "test_db", has_namespace=True)
        
        assert "delete node" in query
        assert "lift:entry[@id=\"test\"]" in query
    
    @pytest.mark.integration
    def test_statistics_query(self):
        """Test statistics query."""
        query = XQueryBuilder.build_statistics_query("test_db", has_namespace=True)
        
        assert "lift:entry" in query
        assert "lift:sense" in query
        assert "lift:example" in query
        assert "<statistics>" in query
    
    @pytest.mark.integration
    def test_advanced_search_query(self):
        """Test advanced search query."""
        criteria = {
            'lexical_unit': {'en': 'test'},
            'sense_gloss': 'meaning',
            'grammatical_info': 'noun'
        }
        
        query = XQueryBuilder.build_advanced_search_query(
            criteria, "test_db", has_namespace=True, limit=20
        )
        
        assert "lift:lexical-unit" in query
        assert "lift:gloss" in query
        assert "lift:grammatical-info" in query
        assert "contains($entry//lift:lexical-unit, \"test\")" in query
        assert "[position() <= 20]" in query
    
    @pytest.mark.integration
    def test_escape_xquery_string(self):
        """Test XQuery string escaping."""
        test_string = 'Test "quotes" & <tags>'
        escaped = XQueryBuilder.escape_xquery_string(test_string)
        
        assert '&quot;' in escaped
        assert '&amp;' in escaped
        assert '&lt;' in escaped
        assert '&gt;' in escaped



@pytest.mark.integration
class TestNamespaceIntegration:
    """Integration tests for namespace handling."""
    
    @pytest.mark.integration
    def test_round_trip_namespace_handling(self):
        """Test round-trip namespace handling."""
        # Start with non-namespaced XML
        original_xml = '''<lift version="0.13">
            <entry id="test">
                <lexical-unit>
                    <form lang="en">
                        <text>test</text>
                    </form>
                </lexical-unit>
            </entry>
        </lift>'''
        
        # Add namespace
        with_ns = LIFTNamespaceManager.normalize_lift_xml(
            original_xml, LIFTNamespaceManager.LIFT_NAMESPACE
        )
        assert LIFTNamespaceManager.has_lift_namespace(with_ns)
        
        # Remove namespace
        without_ns = LIFTNamespaceManager.normalize_lift_xml(with_ns, None)
        assert not LIFTNamespaceManager.has_lift_namespace(without_ns)
        
        # Parse both versions to ensure they're valid
        root_original = ET.fromstring(original_xml)
        root_with_ns = ET.fromstring(with_ns)
        root_without_ns = ET.fromstring(without_ns)
        
        assert root_original.find('.//entry') is not None
        assert root_with_ns.find('.//{http://fieldworks.sil.org/schemas/lift/0.13}entry') is not None
        assert root_without_ns.find('.//entry') is not None
    
    @pytest.mark.integration
    def test_xpath_and_xquery_consistency(self):
        """Test that XPath and XQuery builders produce consistent results."""
        # Test with namespace
        xpath_entry = XPathBuilder.entry("test", has_namespace=True)
        xquery_entry = XQueryBuilder.build_entry_by_id_query("test", "db", has_namespace=True)
        
        assert "lift:entry[@id=" in xpath_entry
        assert "lift:entry[@id=" in xquery_entry
        
        # Test without namespace
        xpath_entry_no_ns = XPathBuilder.entry("test", has_namespace=False)
        xquery_entry_no_ns = XQueryBuilder.build_entry_by_id_query("test", "db", has_namespace=False)
        
        assert "lift:" not in xpath_entry_no_ns
        assert "lift:" not in xquery_entry_no_ns
