#!/usr/bin/env python3
"""
Test basic XQuery to see what works
"""

import logging
from app.database.basex_connector import BaseXConnector
from config import Config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_basic_queries():
    """Test basic XQuery patterns"""
    config = Config()
    connector = BaseXConnector(config.BASEX_HOST, config.BASEX_PORT, config.BASEX_USERNAME, config.BASEX_PASSWORD)
    connector.database = config.BASEX_DATABASE
    
    # Connect to database
    connector.connect()
    
    print("Testing basic XQuery patterns...")
    
    # Test 1: Simple count (should work - like count_entries)
    try:
        query1 = f"xquery count(collection('{config.BASEX_DATABASE}')//*:entry)"
        result1 = connector.execute_query(query1)
        print(f"✓ Basic count query works: {result1}")
    except Exception as e:
        print(f"✗ Basic count query failed: {e}")
    
    # Test 2: Simple search without conditions
    try:
        query2 = f"xquery (for $entry in collection('{config.BASEX_DATABASE}')//*:entry return $entry)[position() = 1 to 3]"
        result2 = connector.execute_query(query2)
        print(f"✓ Basic list query works: {len(result2)} chars")
    except Exception as e:
        print(f"✗ Basic list query failed: {e}")
    
    # Test 3: Simple search with one condition
    try:
        query3 = f"xquery count(for $entry in collection('{config.BASEX_DATABASE}')//*:entry where contains(lower-case($entry/lexical-unit/form/text), 'a') return $entry)"
        result3 = connector.execute_query(query3)
        print(f"✓ Single condition search works: {result3}")
    except Exception as e:
        print(f"✗ Single condition search failed: {e}")
    
    # Test 4: Multiple conditions (this might be where it breaks)
    try:
        # Fix the "some" clause structure
        query4 = f"xquery count(for $entry in collection('{config.BASEX_DATABASE}')//*:entry where contains(lower-case($entry/lexical-unit/form/text), 'a') or (some $gloss in $entry/sense/gloss/text satisfies contains(lower-case($gloss), 'a')) return $entry)"
        result4 = connector.execute_query(query4)
        print(f"✓ Multi condition search works: {result4}")
    except Exception as e:
        print(f"✗ Multi condition search failed: {e}")
    
    # Test 5: Three conditions
    try:
        query5 = f"xquery count(for $entry in collection('{config.BASEX_DATABASE}')//*:entry where contains(lower-case($entry/lexical-unit/form/text), 'a') or (some $gloss in $entry/sense/gloss/text satisfies contains(lower-case($gloss), 'a')) or (some $def in $entry/sense/definition/form/text satisfies contains(lower-case($def), 'a')) return $entry)"
        result5 = connector.execute_query(query5)
        print(f"✓ Three condition search works: {result5}")
    except Exception as e:
        print(f"✗ Three condition search failed: {e}")
    
    connector.close()

if __name__ == "__main__":
    test_basic_queries()
