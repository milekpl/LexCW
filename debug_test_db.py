#!/usr/bin/env python3
"""
Script to debug and fix test database contents for the sorting test.
"""

from app.database.basex_connector import BaseXConnector

def check_and_fix_test_database():
    try:
        # Connect to the most recent test database
        connector = BaseXConnector('localhost', 1984, 'admin', 'admin', 'test_c19c4eda')
        connector.connect()
        
        print("=== CHECKING TEST DATABASE ===")
        
        # Check all entries
        all_entries_query = 'for $entry in //entry return $entry/@id/string()'
        all_entries = connector.execute_query(all_entries_query)
        entry_ids = all_entries.split('\n') if all_entries.strip() else []
        print(f'Total entries: {len(entry_ids)}')
        
        # Check entries without dateModified
        no_date_query = 'for $entry in //entry[not(@dateModified)] return $entry/@id/string()'
        no_date = connector.execute_query(no_date_query)
        no_date_ids = no_date.split('\n') if no_date.strip() else []
        print(f'Entries without dateModified: {len(no_date_ids)}')
        
        # Check for our specific test entries
        test_entry_query = 'for $entry in //entry[starts-with(@id, "no_date_entry")] return $entry/@id/string()'
        test_entries = connector.execute_query(test_entry_query)
        test_entry_ids = test_entries.split('\n') if test_entries.strip() else []
        print(f'Test entries (no_date_entry*): {len(test_entry_ids)}')
        
        # If test entries are missing, add them properly
        if len(test_entry_ids) == 0:
            print("\n=== ADDING MISSING TEST ENTRIES ===")
            
            # Add test entries directly into the main collection
            test_entries_xml = '''
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
            '''
            
            # Insert directly into the database
            connector.execute_update(f"insert node {test_entries_xml} into collection('test_c19c4eda')")
            print("Added no_date_entry_1")
            
            # Add second test entry
            test_entry_2_xml = '''
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
            '''
            
            connector.execute_update(f"insert node {test_entry_2_xml} into collection('test_c19c4eda')")
            print("Added no_date_entry_2")
            
            # Add third test entry
            test_entry_3_xml = '''
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
            '''
            
            connector.execute_update(f"insert node {test_entry_3_xml} into collection('test_c19c4eda')")
            print("Added no_date_entry_3")
            
            # Verify the entries were added
            test_entries_check = connector.execute_query(test_entry_query)
            test_entry_ids_after = test_entries_check.split('\n') if test_entries_check.strip() else []
            print(f'Test entries after addition: {len(test_entry_ids_after)}')
            print(f'Test entry IDs: {test_entry_ids_after}')
        
        # Final verification
        no_date_final = connector.execute_query(no_date_query)
        no_date_ids_final = no_date_final.split('\n') if no_date_final.strip() else []
        print(f'\nFinal count - Entries without dateModified: {len(no_date_ids_final)}')
        
        connector.disconnect()
        print("\n=== DATABASE CHECK COMPLETE ===")
        
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    check_and_fix_test_database()
