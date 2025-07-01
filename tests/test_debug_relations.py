"""Test the actual test case with debug output"""

import pytest
from app.models.entry import Entry, Relation

def test_debug_relations(dict_service_with_db):
    """Debug the related entries functionality."""
    # Create entries with relationships
    entry1 = Entry(id_="word1", lexical_unit={"en": "word1"})
    entry2 = Entry(id_="word2", lexical_unit={"en": "word2"})
    
    # Add relationship from entry1 to entry2
    entry1.relations = [Relation(type="synonym", ref="word2")]
    
    print(f"Entry1 before creation: {entry1}")
    print(f"Entry1 relations: {entry1.relations}")
    if entry1.relations:
        print(f"First relation: type={entry1.relations[0].type}, ref={entry1.relations[0].ref}")
    
    # Create the entries
    dict_service_with_db.create_entry(entry1)
    dict_service_with_db.create_entry(entry2)
    
    # Now retrieve entry1 to check if relations were saved
    retrieved_entry1 = dict_service_with_db.get_entry("word1")
    print(f"Retrieved entry1: {retrieved_entry1}")
    print(f"Retrieved entry1 relations: {retrieved_entry1.relations}")
    if retrieved_entry1.relations:
        rel = retrieved_entry1.relations[0]
        print(f"Retrieved relation: type={rel.type}, ref={rel.ref}")
    else:
        print("No relations found in retrieved entry!")
    
    # Get related entries for entry1 with debug output
    print("\\n=== Checking Database Content ===")
    db_name = dict_service_with_db.db_connector.database
    
    # Check what's actually in the database
    try:
        all_entries_ns = dict_service_with_db.db_connector.execute_query(f"collection('{db_name}')//lift:entry")
        print(f"All entries with namespace: '{all_entries_ns}'")
    except Exception as e:
        print(f"Namespace query failed: {e}")
        
    try:
        all_entries_no_ns = dict_service_with_db.db_connector.execute_query(f"collection('{db_name}')//*[local-name()='entry']")
        print(f"All entries without namespace: '{all_entries_no_ns}'")
    except Exception as e:
        print(f"Non-namespace query failed: {e}")
    
    print("\\n=== Checking XQuery ===")
    from app.utils.xquery_builder import XQueryBuilder
    
    # Let's test the XQuery generation
    has_ns = dict_service_with_db._detect_namespace_usage()
    print(f"Database uses namespaces: {has_ns}")
    query = dict_service_with_db._query_builder.build_related_entries_query(
        "word1", db_name, has_ns, None
    )
    print(f"Generated query: {query}")
    
    # Execute the query directly
    raw_result = dict_service_with_db.db_connector.execute_query(query)
    print(f"Raw query result: '{raw_result}'")
    
    # Try a simpler query without namespace prefixes
    print("\\n=== Testing alternative queries ===")
    try:
        # Test 1: Use local-name() approach  
        test_query1 = f"""
        let $entry_relations := collection('{db_name}')//*[local-name()='entry'][@id='word1']/*[local-name()='relation']/@ref
        for $related in collection('{db_name}')//*[local-name()='entry'][@id = $entry_relations]
        return $related
        """
        result1 = dict_service_with_db.db_connector.execute_query(test_query1)
        print(f"Local-name query result: '{result1}'")
    except Exception as e:
        print(f"Local-name query failed: {e}")
        
    try:
        # Test 2: Just get the relation refs first
        test_query2 = f"""
        collection('{db_name}')//*[local-name()='entry'][@id='word1']/*[local-name()='relation']/@ref
        """
        result2 = dict_service_with_db.db_connector.execute_query(test_query2)
        print(f"Relation refs query result: '{result2}'")
    except Exception as e:
        print(f"Relation refs query failed: {e}")
    
    # Get related entries for entry1
    related_entries = dict_service_with_db.get_related_entries("word1")
    print(f"Found {len(related_entries)} related entries")
    for i, rel_entry in enumerate(related_entries):
        print(f"Related entry {i}: {rel_entry}")

if __name__ == "__main__":
    pytest.main([__file__ + "::test_debug_relations", "-v", "-s"])
