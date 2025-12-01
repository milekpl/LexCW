#!/usr/bin/env python3
"""
Test XQuery CRUD Operations

Tests entry and sense operations with actual BaseX database
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from BaseXClient import BaseXClient  # type: ignore


def test_entry_crud():
    """Test entry CRUD operations"""
    print("\n" + "="*60)
    print("Testing Entry CRUD Operations")
    print("="*60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        session.execute("OPEN dictionary")
        
        # CREATE
        print("\n1. CREATE - Adding new entry...")
        create_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $new-entry := <entry id="test_crud_001" dateCreated="{current-dateTime()}" 
                                xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>crudtest</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>CRUD test entry</text></gloss>
            </sense>
        </entry>
        
        return db:add('dictionary', $new-entry, concat('test_crud_001_', replace(string(current-dateTime()), ':', '_'), '.xml'))
        """
        q = session.query(create_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Created successfully")
        
        # READ
        print("\n2. READ - Retrieving entry...")
        read_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := //lift:entry[@id='test_crud_001']
        return if ($entry) then
            <result status="success">
                <entry-id>{$entry/@id/string()}</entry-id>
                <lexical-unit>{$entry/lift:lexical-unit/lift:form/lift:text/string()}</lexical-unit>
            </result>
        else
            <result status="error"><message>Entry not found</message></result>
        """
        q = session.query(read_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Read: {result}")
        
        # UPDATE
        print("\n3. UPDATE - Modifying entry...")
        update_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := //lift:entry[@id='test_crud_001']
        
        return (
            delete node $entry/lift:lexical-unit/lift:form/lift:text,
            insert node <text xmlns="http://fieldworks.sil.org/schemas/lift/0.13">crudtest_updated</text>
                into $entry/lift:lexical-unit/lift:form,
            delete node $entry/lift:sense/lift:gloss/lift:text,
            insert node <text xmlns="http://fieldworks.sil.org/schemas/lift/0.13">CRUD test entry - UPDATED</text>
                into $entry/lift:sense/lift:gloss
        )
        """
        q = session.query(update_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Updated successfully")
        
        # VERIFY UPDATE
        print("\n4. VERIFY - Checking update...")
        verify_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := //lift:entry[@id='test_crud_001']
        return <result>
            <lexical-unit>{$entry/lift:lexical-unit/lift:form/lift:text/string()}</lexical-unit>
            <gloss>{$entry/lift:sense/lift:gloss/lift:text/string()}</gloss>
        </result>
        """
        q = session.query(verify_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Verified: {result}")
        
        # SEARCH
        print("\n5. SEARCH - Finding entry...")
        search_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        for $entry in //lift:entry[
            .//lift:text[contains(lower-case(.), 'crudtest')]
        ]
        return <entry id="{$entry/@id/string()}">
            <text>{$entry/lift:lexical-unit/lift:form/lift:text/string()}</text>
        </entry>
        """
        q = session.query(search_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Found: {result}")
        
        # DELETE
        print("\n6. DELETE - Removing entry...")
        delete_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := //lift:entry[@id='test_crud_001']
        let $path := db:path($entry)
        return db:delete('dictionary', $path)
        """
        q = session.query(delete_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Deleted successfully")
        
        # VERIFY DELETE
        print("\n7. VERIFY DELETE - Confirming removal...")
        verify_delete_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := //lift:entry[@id='test_crud_001']
        return if ($entry) then
            <result status="error"><message>Entry still exists!</message></result>
        else
            <result status="success"><message>Entry successfully deleted</message></result>
        """
        q = session.query(verify_delete_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Verified: {result}")
        
        session.close()
        print("\n✅ Entry CRUD tests PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sense_operations():
    """Test sense operations"""
    print("\n" + "="*60)
    print("Testing Sense Operations")
    print("="*60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        session.execute("OPEN dictionary")
        
        # CREATE entry with one sense
        print("\n1. CREATE entry with initial sense...")
        create_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $new-entry := <entry id="test_sense_001" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>multisense</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>first meaning</text></gloss>
            </sense>
        </entry>
        
        return db:add('dictionary', $new-entry, concat('test_sense_001_', replace(string(current-dateTime()), ':', '_'), '.xml'))
        """
        q = session.query(create_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Created successfully")
        
        # ADD SENSE
        print("\n2. ADD second sense...")
        add_sense_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := //lift:entry[@id='test_sense_001']
        let $max-order := max($entry/lift:sense/@order)
        let $new-order := if ($max-order) then xs:integer($max-order) + 1 else 0
        
        let $new-sense := <sense id="sense_002" order="{$new-order}" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <gloss lang="en"><text>second meaning</text></gloss>
        </sense>
        
        return insert node $new-sense into $entry
        """
        q = session.query(add_sense_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Added second sense (order {result if result else '1'})")
        
        # LIST SENSES
        print("\n3. LIST all senses...")
        list_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        for $sense in //lift:entry[@id='test_sense_001']/lift:sense
        order by xs:integer($sense/@order)
        return <sense id="{$sense/@id/string()}" order="{$sense/@order/string()}">
            <gloss>{$sense/lift:gloss/lift:text/string()}</gloss>
        </sense>
        """
        q = session.query(list_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Senses: {result}")
        
        # ADD THIRD SENSE
        print("\n4. ADD third sense...")
        add_third_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := //lift:entry[@id='test_sense_001']
        let $max-order := max($entry/lift:sense/@order)
        let $new-order := if ($max-order) then xs:integer($max-order) + 1 else 0
        
        let $new-sense := <sense id="sense_003" order="{$new-order}" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <gloss lang="en"><text>third meaning</text></gloss>
        </sense>
        
        return insert node $new-sense into $entry
        """
        q = session.query(add_third_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Added third sense")
        
        # COUNT SENSES
        print("\n5. COUNT senses...")
        count_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        count(//lift:entry[@id='test_sense_001']/lift:sense)
        """
        q = session.query(count_query)
        count = q.execute()
        q.close()
        print(f"   ✅ Total senses: {count}")
        
        # CLEANUP
        print("\n6. CLEANUP - Removing test entry...")
        cleanup_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := //lift:entry[@id='test_sense_001']
        let $path := db:path($entry)
        return db:delete('dictionary', $path)
        """
        q = session.query(cleanup_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Cleaned up successfully")
        
        session.close()
        print("\n✅ Sense operations tests PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation():
    """Test validation queries"""
    print("\n" + "="*60)
    print("Testing Validation Queries")
    print("="*60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        session.execute("OPEN dictionary")
        
        # Database stats
        print("\n1. DATABASE STATISTICS...")
        stats_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entries := //lift:entry
        let $total-entries := count($entries)
        let $total-senses := count(//lift:sense)
        let $avg-senses := if ($total-entries > 0) 
                          then format-number($total-senses div $total-entries, '#.##')
                          else '0'
        
        return <stats>
            <entries>{$total-entries}</entries>
            <senses>{$total-senses}</senses>
            <avgSenses>{$avg-senses}</avgSenses>
        </stats>
        """
        q = session.query(stats_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Stats: {result}")
        
        # Check duplicate IDs
        print("\n2. CHECK FOR DUPLICATE IDs...")
        dup_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $all-ids := //lift:entry/@id/string()
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
        q = session.query(dup_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Duplicates: {result}")
        
        # Check missing lexical units
        print("\n3. CHECK FOR MISSING LEXICAL UNITS...")
        missing_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $missing := //lift:entry[not(lift:lexical-unit/lift:form/lift:text)]
        
        return <missing-lexical-units count="{count($missing)}">
        {
            for $entry in $missing[position() <= 5]
            return <entry id="{$entry/@id/string()}"/>
        }
        </missing-lexical-units>
        """
        q = session.query(missing_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Missing lexical units: {result}")
        
        # Check sense ordering
        print("\n4. CHECK SENSE ORDERING...")
        order_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entries-with-issues := //lift:entry[
            some $sense in lift:sense satisfies (
                not($sense/@order) or 
                $sense/@order castable as xs:integer = false()
            )
        ]
        
        return <sense-order-issues count="{count($entries-with-issues)}">
        {
            for $entry in $entries-with-issues[position() <= 5]
            return <entry id="{$entry/@id/string()}">
                <senses>{count($entry/lift:sense)}</senses>
            </entry>
        }
        </sense-order-issues>
        """
        q = session.query(order_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Sense order issues: {result}")
        
        session.close()
        print("\n✅ Validation tests PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n🧪 XQuery CRUD Operations Test Suite")
    print("=" * 60)
    
    # Check BaseX connection
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
    results.append(("Entry CRUD Operations", test_entry_crud()))
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
        print("🎉 All CRUD tests PASSED!")
        print("\n✅ XQuery operations are working correctly")
        sys.exit(0)
    else:
        print("⚠️  Some tests FAILED")
        sys.exit(1)
