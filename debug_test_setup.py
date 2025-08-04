#!/usr/bin/env python3

"""Debug script to check test data setup for integration tests."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.basex_connector import BaseXConnector
import secrets

def debug_test_setup():
    """Debug the test data setup process."""
    
    # Create test database name
    test_db_name = f"test_{secrets.token_hex(4)}"
    print(f"Creating test database: {test_db_name}")
    
    # Initialize connector without a database
    connector = BaseXConnector(
        host='localhost',
        port=1984,
        username='admin',
        password='admin',
        database=None  # No database initially
    )
    
    try:
        # Connect without opening a database
        connector.connect()
        print("✓ Connected to BaseX without database")
        
        # Create database
        connector.create_database(test_db_name)
        print("✓ Database created")
        
        # Set database and reconnect
        connector.database = test_db_name
        connector.disconnect()
        connector.connect()
        print("✓ Reconnected to test database")
        
        # Skip adding sample LIFT file for now - focus on test entries
        print("Skipping sample LIFT file - focusing on test entries")
        
        # Count initial entries  
        initial_count = connector.execute_query("count(//entry)")
        print(f"Initial entry count: {initial_count}")
        
        # Add test entries using the same method as conftest
        test_entry_1_content = '''<entry id="no_date_entry_1">
            <lexical-unit>
                <form lang="en">
                    <text>no date entry one</text>
                </form>
            </lexical-unit>
            <sense>
                <definition>
                    <form lang="en">
                        <text>Entry without date modification for testing sorting</text>
                    </form>
                </definition>
            </sense>
        </entry>'''
        
        test_entry_2_content = '''<entry id="no_date_entry_2" dateCreated="2023-01-01T10:00:00Z">
            <lexical-unit>
                <form lang="en">
                    <text>no date entry two</text>
                </form>
            </lexical-unit>
            <sense>
                <definition>
                    <form lang="en">
                        <text>Another entry without dateModified for testing</text>
                    </form>
                </definition>
            </sense>
        </entry>'''
        
        test_entry_3_content = '''<entry id="no_date_entry_3">
            <lexical-unit>
                <form lang="en">
                    <text>zzz last alphabetically</text>
                </form>
            </lexical-unit>
            <sense>
                <definition>
                    <form lang="en">
                        <text>Entry that should be last alphabetically but has no date</text>
                    </form>
                </definition>
            </sense>
        </entry>'''
        
        print("\nAdding test entries...")
        
        # Use simple BaseX insert syntax - we're already connected to the database
        try:
            # First create a root element if the database is empty
            root_check = connector.execute_query("exists(/)")
            if root_check == "false":
                connector.execute_update("insert node <root/> into /")
                print("✓ Created root element")
            
            # First entry - no dateModified
            insert_query1 = """
            insert node 
            <entry id="no_date_entry_1">
                <lexical-unit>
                    <form lang="en">
                        <text>no date entry one</text>
                    </form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en">
                            <text>Entry without date modification for testing sorting</text>
                        </form>
                    </definition>
                </sense>
            </entry>
            into /
            """
            connector.execute_update(insert_query1)
            print("✓ Test entry 1 added")
            
            # Second entry - dateCreated but no dateModified
            insert_query2 = """
            insert node 
            <entry id="no_date_entry_2" dateCreated="2023-01-01T10:00:00Z">
                <lexical-unit>
                    <form lang="en">
                        <text>no date entry two</text>
                    </form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en">
                            <text>Another entry without dateModified for testing</text>
                        </form>
                    </definition>
                </sense>
            </entry>
            into /
            """
            connector.execute_update(insert_query2)
            print("✓ Test entry 2 added")
            
            # Third entry - no dateModified
            insert_query3 = """
            insert node 
            <entry id="no_date_entry_3">
                <lexical-unit>
                    <form lang="en">
                        <text>zzz last alphabetically</text>
                    </form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en">
                            <text>Entry that should be last alphabetically but has no date</text>
                        </form>
                    </definition>
                </sense>
            </entry>
            into /
            """
            connector.execute_update(insert_query3)
            print("✓ Test entry 3 added")
            
        except Exception as e:
            print(f"✗ Failed to add test entries: {e}")
            import traceback
            traceback.print_exc()
        
        # Check what was actually added
        print("\nChecking database contents...")
        
        # Check the root structure more thoroughly
        try:
            root_structure = connector.execute_query("serialize(/)")
            print(f"Root structure: {root_structure[:500]}...")  # First 500 chars
        except Exception as e:
            print(f"Could not serialize root: {e}")
        
        # Check if entries are children of root
        root_children = connector.execute_query("for $child in /* return name($child)")
        print(f"Root children names: {root_children}")
        
        # Count all elements in database
        all_elements = connector.execute_query("count(//*)")
        print(f"Total elements in database: {all_elements}")
        
        # Check simple path queries
        simple_entry_count = connector.execute_query("count(//entry)")
        print(f"Simple path entry count: {simple_entry_count}")
        
        # Check root structure
        root_elements = connector.execute_query("for $elem in /* return name($elem)")
        print(f"Root elements: {root_elements}")
        
        # Check all entries using simple path
        all_simple_entries = connector.execute_query("for $entry in //entry return $entry/@id/string()")
        print(f"All entries (simple path): {all_simple_entries}")
        
        # Check if collection function works at all
        try:
            collection_exists = connector.execute_query(f"db:exists('{test_db_name}')")
            print(f"Database exists: {collection_exists}")
        except Exception as e:
            print(f"Error checking db existence: {e}")
        
        final_count = connector.execute_query("count(//entry)")
        print(f"Final entry count: {final_count}")
        
        test_entry_count = connector.execute_query(f"count(collection('{test_db_name}')//entry[starts-with(@id, 'no_date_entry')])")
        print(f"Test entries found: {test_entry_count}")
        
        # List all document names in the collection
        doc_names = connector.execute_query(f"for $doc in collection('{test_db_name}') return base-uri($doc)")
        print(f"Documents in collection: {doc_names}")
        
        # Check all entry IDs
        all_entry_ids = connector.execute_query(f"for $entry in collection('{test_db_name}')//entry return $entry/@id/string()")
        print(f"All entry IDs: {all_entry_ids}")
        
        # Check entries without dateModified using simple path
        entries_no_date_simple = connector.execute_query("count(//entry[not(@dateModified)])")
        print(f"Entries without dateModified (simple path): {entries_no_date_simple}")
        
        # Check entries without dateModified using collection
        entries_no_date = connector.execute_query(f"count(collection('{test_db_name}')//entry[not(@dateModified)])")
        print(f"Entries without dateModified (collection): {entries_no_date}")
        
        # List some entries without dateModified
        some_no_date_entries = connector.execute_query(f"for $entry in collection('{test_db_name}')//entry[not(@dateModified)][position() <= 5] return $entry/@id/string()")
        print(f"Sample entries without dates: {some_no_date_entries}")
        
    except Exception as e:
        print(f"Error during debug: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            # Clean up - drop the test database
            connector.execute_update(f"db:drop('{test_db_name}')")
            print(f"\n✓ Test database {test_db_name} dropped")
        except Exception as e:
            print(f"✗ Failed to drop test database: {e}")

if __name__ == "__main__":
    debug_test_setup()
