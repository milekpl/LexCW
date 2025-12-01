#!/usr/bin/env python
"""
Basic XQuery Operations Test
Tests fundamental XQuery operations that work with BaseX database.
"""

import sys
from pathlib import Path

# Add parent directory to path to find BaseXClient
sys.path.insert(0, str(Path(__file__).parent.parent))

from BaseXClient import BaseXClient


def test_basic_queries():
    """Test basic query operations."""
    print("\n" + "="*60)
    print("Testing Basic XQuery Queries")
    print("="*60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        session.execute("OPEN dictionary")
        
        # 1. COUNT ALL ENTRIES
        print("\n1. COUNT all entries...")
        count_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        count(//lift:entry)
        """
        q = session.query(count_query)
        count = q.execute()
        q.close()
        print(f"   ✅ Total entries: {count}")
        
        # 2. COUNT ALL SENSES
        print("\n2. COUNT all senses...")
        sense_count_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        count(//lift:sense)
        """
        q = session.query(sense_count_query)
        count = q.execute()
        q.close()
        print(f"   ✅ Total senses: {count}")
        
        # 3. CHECK FOR DUPLICATES
        print("\n3. CHECK for duplicate entry IDs...")
        dup_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $duplicates :=
            for $id in distinct-values(//lift:entry/@id)
            let $count := count(//lift:entry[@id = $id])
            where $count > 1
            return $id
            
        return <duplicates count="{count($duplicates)}">
        {
            for $dup in $duplicates
            return <duplicate>{$dup}</duplicate>
        }
        </duplicates>
        """
        q = session.query(dup_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Duplicates: {result}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            session.close()
        except:
            pass
        return False


def test_add_operation():
    """Test adding a new entry using db:add."""
    print("\n" + "="*60)
    print("Testing ADD Operation")
    print("="*60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        session.execute("OPEN dictionary")
        
        # ADD A NEW ENTRY
        print("\n1. ADD new entry to database...")
        add_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := 
        <entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" 
               id="test_basic_001" 
               guid="test_basic_001"
               dateCreated="{current-dateTime()}">
            <lexical-unit>
                <form lang="en"><text>testword</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>a test word</text></gloss>
            </sense>
        </entry>
        
        return db:add('dictionary', $entry, concat('test_basic_001', '.xml'))
        """
        q = session.query(add_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Added entry")
        
        # VERIFY IT EXISTS
        print("\n2. VERIFY entry was added...")
        verify_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := //lift:entry[@id='test_basic_001']
        return if ($entry) then
            <result status="success">
                <id>{$entry/@id/string()}</id>
                <lexical-unit>{$entry/lift:lexical-unit/lift:form/lift:text/string()}</lexical-unit>
                <gloss>{$entry/lift:sense/lift:gloss/lift:text/string()}</gloss>
            </result>
        else
            <result status="error"><message>Not found</message></result>
        """
        q = session.query(verify_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Verified: {result}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            session.close()
        except:
            pass
        return False


def test_delete_operation():
    """Test deleting an entry using db:delete."""
    print("\n" + "="*60)
    print("Testing DELETE Operation")
    print("="*60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        session.execute("OPEN dictionary")
        
        # DELETE THE ENTRY
        print("\n1. DELETE test entry...")
        delete_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        for $entry in //lift:entry[@id='test_basic_001']
        return db:delete('dictionary', db:path($entry))
        """
        q = session.query(delete_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Deleted entry")
        
        # VERIFY IT'S GONE
        print("\n2. VERIFY entry was deleted...")
        verify_query = """
        declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
        
        let $entry := //lift:entry[@id='test_basic_001']
        return if ($entry) then
            <result status="error"><message>Entry still exists!</message></result>
        else
            <result status="success"><message>Entry successfully deleted</message></result>
        """
        q = session.query(verify_query)
        result = q.execute()
        q.close()
        print(f"   ✅ Verified: {result}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            session.close()
        except:
            pass
        return False


def main():
    """Run all tests."""
    print("🧪 Basic XQuery Operations Test Suite")
    print("="*60)
    
    # Test BaseX connection
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        print("✅ BaseX connection successful")
        session.close()
    except Exception as e:
        print(f"❌ BaseX connection failed: {e}")
        return
    
    # Run tests
    results = []
    results.append(("Basic Queries", test_basic_queries()))
    results.append(("Add Operation", test_add_operation()))
    results.append(("Delete Operation", test_delete_operation()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:.<40} {status}")
    
    # Final result
    all_passed = all(passed for _, passed in results)
    print("\n" + "="*60)
    if all_passed:
        print("✅ All tests PASSED")
    else:
        print("⚠️  Some tests FAILED")
    print("="*60)


if __name__ == "__main__":
    main()
