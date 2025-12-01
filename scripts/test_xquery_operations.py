#!/usr/bin/env python3
"""
Test XQuery Operations with BaseX

This script tests the XQuery modules for LIFT entry operations
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from BaseXClient import BaseXClient  # type: ignore


def test_entry_operations():
    """Test entry CRUD operations"""
    print("\n" + "="*60)
    print("Testing Entry Operations")
    print("="*60)
    
    # Sample LIFT entry XML
    test_entry = '''
    <entry id="test_entry_001" dateCreated="2024-11-30T12:00:00Z" 
           xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="sense_001" order="0">
            <grammatical-info value="Noun"/>
            <gloss lang="en"><text>examination</text></gloss>
            <definition>
                <form lang="en"><text>A procedure to assess knowledge.</text></form>
            </definition>
        </sense>
    </entry>
    '''
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        
        # Import entry operations module
        session.execute("import module namespace entry = 'http://dictionaryapp.local/xquery/entry' at 'app/xquery/entry_operations.xq'")
        
        # Test COUNT
        print("\n1. Testing entry:count()...")
        result = session.execute("entry:count('dictionary-test')")
        print(f"   Result: {result}")
        
        # Test CREATE
        print("\n2. Testing entry:create()...")
        escaped_entry = test_entry.replace("'", "&apos;").replace("\n", " ")
        query = f"import module namespace entry = 'http://dictionaryapp.local/xquery/entry' at 'app/xquery/entry_operations.xq'; entry:create('dictionary-test', '{escaped_entry}')"
        result = session.execute(query)
        print(f"   Result: {result}")
        
        # Test READ
        print("\n3. Testing entry:read()...")
        query = "import module namespace entry = 'http://dictionaryapp.local/xquery/entry' at 'app/xquery/entry_operations.xq'; entry:read('dictionary-test', 'test_entry_001')"
        result = session.execute(query)
        print(f"   Result: {result[:200]}...")  # Truncate for readability
        
        # Test SEARCH
        print("\n4. Testing entry:search()...")
        query = "import module namespace entry = 'http://dictionaryapp.local/xquery/entry' at 'app/xquery/entry_operations.xq'; entry:search('dictionary-test', 'test', '', 10)"
        result = session.execute(query)
        print(f"   Result: {result[:200]}...")
        
        # Test DELETE
        print("\n5. Testing entry:delete()...")
        query = "import module namespace entry = 'http://dictionaryapp.local/xquery/entry' at 'app/xquery/entry_operations.xq'; entry:delete('dictionary-test', 'test_entry_001')"
        result = session.execute(query)
        print(f"   Result: {result}")
        
        session.close()
        print("\n✅ Entry operations tests completed successfully")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    return True


def test_sense_operations():
    """Test sense CRUD operations"""
    print("\n" + "="*60)
    print("Testing Sense Operations")
    print("="*60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        
        # First create a test entry
        test_entry = '''
        <entry id="test_entry_002" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>sample</text></form>
            </lexical-unit>
        </entry>
        '''
        
        print("\n1. Creating test entry...")
        escaped_entry = test_entry.replace("'", "&apos;").replace("\n", " ")
        query = f"import module namespace entry = 'http://dictionaryapp.local/xquery/entry' at 'app/xquery/entry_operations.xq'; entry:create('dictionary-test', '{escaped_entry}')"
        result = session.execute(query)
        print(f"   Result: {result[:100]}...")
        
        # Test ADD SENSE
        print("\n2. Testing sense:add()...")
        test_sense = '''
        <sense id="sense_new_001" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <gloss lang="en"><text>new sense</text></gloss>
        </sense>
        '''
        
        escaped_sense = test_sense.replace("'", "&apos;").replace("\n", " ")
        query = f"import module namespace sense = 'http://dictionaryapp.local/xquery/sense' at 'app/xquery/sense_operations.xq'; sense:add('dictionary-test', 'test_entry_002', '{escaped_sense}')"
        result = session.execute(query)
        print(f"   Result: {result}")
        
        # Test LIST SENSES
        print("\n3. Testing sense:list()...")
        query = "import module namespace sense = 'http://dictionaryapp.local/xquery/sense' at 'app/xquery/sense_operations.xq'; sense:list('dictionary-test', 'test_entry_002')"
        result = session.execute(query)
        print(f"   Result: {result[:200]}...")
        
        # Cleanup
        print("\n4. Cleaning up...")
        query = "import module namespace entry = 'http://dictionaryapp.local/xquery/entry' at 'app/xquery/entry_operations.xq'; entry:delete('dictionary-test', 'test_entry_002')"
        session.execute(query)
        
        session.close()
        print("\n✅ Sense operations tests completed successfully")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    return True


def test_validation_queries():
    """Test validation queries"""
    print("\n" + "="*60)
    print("Testing Validation Queries")
    print("="*60)
    
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        
        # Test DATABASE STATS
        print("\n1. Testing validate:database-stats()...")
        query = "import module namespace validate = 'http://dictionaryapp.local/xquery/validate' at 'app/xquery/validation_queries.xq'; validate:database-stats('dictionary-test')"
        result = session.execute(query)
        print(f"   Result: {result}")
        
        # Test CHECK DATABASE
        print("\n2. Testing validate:check-database()...")
        query = "import module namespace validate = 'http://dictionaryapp.local/xquery/validate' at 'app/xquery/validation_queries.xq'; validate:check-database('dictionary-test')"
        result = session.execute(query)
        print(f"   Result: {result[:300]}...")
        
        session.close()
        print("\n✅ Validation queries tests completed successfully")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    return True


if __name__ == '__main__':
    print("\n🔬 XQuery Operations Test Suite")
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
    results.append(("Entry Operations", test_entry_operations()))
    results.append(("Sense Operations", test_sense_operations()))
    results.append(("Validation Queries", test_validation_queries()))
    
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
