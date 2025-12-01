#!/usr/bin/env python3
"""
Test XQuery Functions with BaseX (Direct Method)

This script tests the XQuery functions by executing them directly
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from BaseXClient import BaseXClient  # type: ignore


def test_basic_operations():
    """Test basic entry operations"""
    print("\n" + "="*60)
    print("Testing Basic Entry Operations")
    print("="*60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        
        # Test 1: Count entries
        print("\n1. Counting entries in dictionary-test...")
        query = """
        count(collection('dictionary-test')//entry[@xmlns='http://fieldworks.sil.org/schemas/lift/0.13'])
        """
        result = session.query(query).execute()
        print(f"   Found {result} entries")
        
        # Test 2: Create entry
        print("\n2. Creating test entry...")
        query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := <entry id="xq_test_001" dateCreated="{current-dateTime()}" 
                             xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>xqtest</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>XQuery test entry</text></gloss>
            </sense>
        </entry>
        
        let $insert := db:add('dictionary-test', $entry, 'xq_test_001.xml')
        return <result status="success"><message>Created entry xq_test_001</message></result>
        """
        result = session.query(query).execute()
        print(f"   Result: {result}")
        
        # Test 3: Read entry
        print("\n3. Reading test entry...")
        query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        db:open('dictionary-test')//lift:entry[@id='xq_test_001']
        """
        result = session.query(query).execute()
        print(f"   Result: {result[:200]}...")
        
        # Test 4: Search entries
        print("\n4. Searching for 'xqtest'...")
        query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        for $entry in db:open('dictionary-test')//lift:entry[
            .//lift:text[contains(lower-case(.), 'xqtest')]
        ]
        return <entry id="{$entry/@id/string()}">
            {$entry/lift:lexical-unit}
        </entry>
        """
        result = session.query(query).execute()
        print(f"   Result: {result}")
        
        # Test 5: Delete entry
        print("\n5. Deleting test entry...")
        query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := db:open('dictionary-test')//lift:entry[@id='xq_test_001']
        let $delete := db:delete('dictionary-test', db:path($entry))
        return <result status="success"><message>Deleted entry xq_test_001</message></result>
        """
        result = session.query(query).execute()
        print(f"   Result: {result}")
        
        session.close()
        print("\n✅ Basic entry operations tests completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_sense_operations():
    """Test sense operations"""
    print("\n" + "="*60)
    print("Testing Sense Operations")
    print("="*60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        
        # Test 1: Create entry with multiple senses
        print("\n1. Creating entry with multiple senses...")
        query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := <entry id="xq_test_002" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>multisense</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>first meaning</text></gloss>
            </sense>
            <sense id="sense_002" order="1">
                <gloss lang="en"><text>second meaning</text></gloss>
            </sense>
        </entry>
        
        let $insert := db:add('dictionary-test', $entry, 'xq_test_002.xml')
        return <result status="success"><message>Created entry with 2 senses</message></result>
        """
        result = session.query(query).execute()
        print(f"   Result: {result}")
        
        # Test 2: List senses
        print("\n2. Listing senses...")
        query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        for $sense in db:open('dictionary-test')//lift:entry[@id='xq_test_002']/lift:sense
        order by xs:integer($sense/@order)
        return <sense id="{$sense/@id/string()}" order="{$sense/@order/string()}">
            {$sense/lift:gloss}
        </sense>
        """
        result = session.query(query).execute()
        print(f"   Result: {result}")
        
        # Test 3: Add new sense
        print("\n3. Adding new sense...")
        query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := db:open('dictionary-test')//lift:entry[@id='xq_test_002']
        let $max-order := max($entry/lift:sense/@order)
        let $new-order := if ($max-order) then xs:integer($max-order) + 1 else 0
        let $new-sense := <sense id="sense_003" order="{$new-order}" 
                                xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <gloss lang="en"><text>third meaning</text></gloss>
        </sense>
        
        let $updated-entry := element {node-name($entry)} {
            $entry/@*,
            $entry/lift:lexical-unit,
            $entry/lift:sense,
            $new-sense
        }
        
        let $path := db:path($entry)
        let $delete := db:delete('dictionary-test', $path)
        let $insert := db:add('dictionary-test', $updated-entry, $path)
        
        return <result status="success"><message>Added sense_003 with order {$new-order}</message></result>
        """
        result = session.query(query).execute()
        print(f"   Result: {result}")
        
        # Cleanup
        print("\n4. Cleaning up...")
        query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        let $entry := db:open('dictionary-test')//lift:entry[@id='xq_test_002']
        let $delete := db:delete('dictionary-test', db:path($entry))
        return <result status="success"/>
        """
        session.query(query).execute()
        
        session.close()
        print("\n✅ Sense operations tests completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_validation():
    """Test validation queries"""
    print("\n" + "="*60)
    print("Testing Validation Queries")
    print("="*60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        
        # Test 1: Database statistics
        print("\n1. Getting database statistics...")
        query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $db := db:open('dictionary-test')
        let $entries := $db//lift:entry
        let $total-entries := count($entries)
        let $total-senses := count($db//lift:sense)
        let $avg-senses := if ($total-entries > 0) 
                          then $total-senses div $total-entries 
                          else 0
        
        return <stats>
            <entries>{$total-entries}</entries>
            <senses>{$total-senses}</senses>
            <avgSenses>{$avg-senses}</avgSenses>
        </stats>
        """
        result = session.query(query).execute()
        print(f"   Result: {result}")
        
        # Test 2: Check for duplicate IDs
        print("\n2. Checking for duplicate IDs...")
        query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $all-ids := db:open('dictionary-test')//lift:entry/@id/string()
        let $duplicates := for $id in distinct-values($all-ids)
                          where count($all-ids[. = $id]) > 1
                          return $id
        
        return <duplicates count="{count($duplicates)}">
        {
            for $id in $duplicates
            return <duplicate>{$id}</duplicate>
        }
        </duplicates>
        """
        result = session.query(query).execute()
        print(f"   Result: {result}")
        
        # Test 3: Check for missing lexical units
        print("\n3. Checking for missing lexical units...")
        query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $missing := db:open('dictionary-test')//lift:entry[
            not(lift:lexical-unit/lift:form/lift:text)
        ]
        
        return <missing-lexical-units count="{count($missing)}">
        {
            for $entry in $missing
            return <entry id="{$entry/@id/string()}"/>
        }
        </missing-lexical-units>
        """
        result = session.query(query).execute()
        print(f"   Result: {result}")
        
        session.close()
        print("\n✅ Validation queries tests completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == '__main__':
    print("\n🔬 XQuery Direct Operations Test Suite")
    print("=" * 60)
    
    # Check if BaseX is running
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        session.close()
        print("✅ BaseX connection successful")
    except Exception as e:
        print(f"❌ Cannot connect to BaseX: {e}")
        print("\nPlease ensure BaseX is running:")
        print("  ./start-services.sh")
        sys.exit(1)
    
    # Run tests
    results = []
    results.append(("Basic Entry Operations", test_basic_operations()))
    results.append(("Sense Operations", test_sense_operations()))
    results.append(("Validation Queries", test_validation()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:.<40} {status}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + "="*60)
    if all_passed:
        print("🎉 All tests PASSED!")
        sys.exit(0)
    else:
        print("⚠️  Some tests FAILED")
        sys.exit(1)
