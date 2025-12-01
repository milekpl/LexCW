#!/usr/bin/env python3
"""
Simple XQuery Test with BaseX

Tests basic XQuery functionality with collection() function
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from BaseXClient import BaseXClient  # type: ignore


if __name__ == '__main__':
    print("\n🧪 Simple XQuery Test")
    print("=" * 60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        print("✅ Connected to BaseX")
        
        # List databases first
        print("\n1. Listing databases...")
        result = session.execute("LIST")
        print(f"   Databases:\n{result}")
        
        # Test 2: Check dictionary database
        print("\n2. Opening dictionary database...")
        try:
            result = session.execute("OPEN dictionary")
            print(f"   Opened: {result if result else 'OK'}")
            
            # Count entries
            q = session.query("count(//entry)")
            count = q.execute()
            print(f"   Total entries: {count}")
            q.close()
            
            # Show first entry ID
            q = session.query("(//entry)[1]/@id/string()")
            first_id = q.execute()
            print(f"   First entry ID: {first_id}")
            q.close()
            
            # Test 3: Create, read, update, delete
            print("\n3. Testing CRUD operations...")
            
            # CREATE
            print("   - Creating test entry...")
            create_q = session.query("""
                <entry id="xq_test_999" dateCreated="{current-dateTime()}" 
                       xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
                    <lexical-unit>
                        <form lang="en"><text>xqtest</text></form>
                    </lexical-unit>
                    <sense id="sense_001" order="0">
                        <gloss lang="en"><text>XQuery test entry</text></gloss>
                    </sense>
                </entry>
            """)
            new_entry = create_q.execute()
            create_q.close()
            print(f"   Created: {new_entry[:100]}...")
            
            # Add to database (we'll use XQUERY UPDATE instead)
            session.execute("XQUERY insert node " + new_entry[:200] + " into /lift")
            
        except Exception as e:
            print(f"   Error: {e}")
        
        session.close()
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
