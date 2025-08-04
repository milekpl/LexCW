#!/usr/bin/env python3
"""Check dateModified values in database entries."""

import sys
sys.path.append('.')

from app.database.basex_connector import BaseXConnector

def main():
    # Connect to database
    connector = BaseXConnector('localhost', 1984, 'admin', 'admin')
    try:
        connector.connect()
        connector.set_database('dictionary')
        
        # Check for entries without dateModified attribute
        query1 = 'for $entry in collection("dictionary")//entry where not($entry/@dateModified) return $entry/@id'
        result1 = connector.execute_query(query1)
        count1 = len([x for x in result1.split('\n') if x.strip()]) if result1.strip() else 0
        print(f'Entries without dateModified: {count1}')
        
        # Check entries with empty dateModified
        query2 = 'for $entry in collection("dictionary")//entry where $entry/@dateModified = "" return $entry/@id'
        result2 = connector.execute_query(query2)
        count2 = len([x for x in result2.split('\n') if x.strip()]) if result2.strip() else 0
        print(f'Entries with empty dateModified: {count2}')
        
        # Get all entries count for comparison
        query3 = 'count(collection("dictionary")//entry)'
        total = connector.execute_query(query3)
        print(f'Total entries: {total}')
        
        # Sample a few entries with null dates to see how they sort
        if count1 > 0 or count2 > 0:
            print("\nSample entries with null/empty dates:")
            sample_query = 'for $entry in collection("dictionary")//entry where not($entry/@dateModified) or $entry/@dateModified = "" return concat($entry/@id, " | ", string($entry/@dateModified))'
            sample_result = connector.execute_query(sample_query)
            lines = sample_result.split('\n')[:5]  # First 5
            for line in lines:
                if line.strip():
                    print(f"  {line.strip()}")
                    
    finally:
        connector.disconnect()

if __name__ == "__main__":
    main()
