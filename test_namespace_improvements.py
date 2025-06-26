"""
Test script to verify namespace handling improvements.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.utils.namespace_manager import LIFTNamespaceManager
from app.utils.xquery_builder import XQueryBuilder

def test_namespace_detection():
    """Test namespace detection functionality."""
    print("Testing namespace detection...")
    
    nm = LIFTNamespaceManager()
    
    # Test non-namespaced LIFT
    xml_no_ns = '''<?xml version="1.0"?>
<lift version="0.13">
    <entry id="test1">
        <lexical-unit>
            <form lang="en"><text>hello</text></form>
        </lexical-unit>
    </entry>
</lift>'''
    
    ns_map = nm.detect_namespaces(xml_no_ns)
    print(f"Non-namespaced XML detected namespaces: {ns_map}")
    
    # Test namespaced LIFT
    xml_with_ns = '''<?xml version="1.0"?>
<lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13" version="0.13">
    <entry id="test1">
        <lexical-unit>
            <form lang="en"><text>hello</text></form>
        </lexical-unit>
    </entry>
</lift>'''
    
    ns_map_with = nm.detect_namespaces(xml_with_ns)
    print(f"Namespaced XML detected namespaces: {ns_map_with}")

def test_xpath_generation():
    """Test XPath generation functionality."""
    print("\nTesting XPath generation...")
    
    from app.utils.namespace_manager import XPathBuilder
    
    # Test XPath for namespaced content
    xpath_ns = XPathBuilder.entry("test1", True)
    print(f"Namespaced XPath: {xpath_ns}")
    
    # Test XPath for non-namespaced content
    xpath_no_ns = XPathBuilder.entry("test1", False)
    print(f"Non-namespaced XPath: {xpath_no_ns}")
    
    # Test lexical unit XPath
    lu_xpath_ns = XPathBuilder.lexical_unit("en", True)
    print(f"Lexical unit XPath (namespaced): {lu_xpath_ns}")
    
    lu_xpath_no_ns = XPathBuilder.lexical_unit("en", False)
    print(f"Lexical unit XPath (non-namespaced): {lu_xpath_no_ns}")

def test_xquery_generation():
    """Test XQuery generation functionality."""
    print("\nTesting XQuery generation...")
    
    qb = XQueryBuilder()
    
    # Test namespace prologue
    prologue_ns = qb.get_namespace_prologue(True)
    print(f"Namespace prologue: {prologue_ns}")
    
    prologue_no_ns = qb.get_namespace_prologue(False)
    print(f"No namespace prologue: {prologue_no_ns}")
    
    # Test element path generation
    entry_path_ns = qb.get_element_path("entry", True)
    print(f"Entry path (namespaced): {entry_path_ns}")
    
    entry_path_no_ns = qb.get_element_path("entry", False)
    print(f"Entry path (non-namespaced): {entry_path_no_ns}")

def test_full_query_building():
    """Test complete query building."""
    print("\nTesting complete query building...")
    
    qb = XQueryBuilder()
    
    # Example query for namespaced content
    query_ns = qb.build_entry_by_id_query(
        entry_id="test1",
        db_name="test_db",
        has_namespace=True
    )
    print(f"Namespaced ID query:\n{query_ns}")
    
    # Example query for non-namespaced content
    query_no_ns = qb.build_entry_by_id_query(
        entry_id="test1",
        db_name="test_db", 
        has_namespace=False
    )
    print(f"Non-namespaced ID query:\n{query_no_ns}")
    
    # Test all entries query
    all_query = qb.build_all_entries_query(
        db_name="test_db",
        has_namespace=True,
        limit=10,
        offset=0
    )
    print(f"All entries query (paginated):\n{all_query}")

if __name__ == "__main__":
    print("Testing namespace handling improvements...")
    print("=" * 50)
    
    test_namespace_detection()
    test_xpath_generation()
    test_xquery_generation()
    test_full_query_building()
    
    print("\n" + "=" * 50)
    print("Namespace handling test completed!")
