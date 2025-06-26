#!/usr/bin/env python3
"""
Debug script to examine grammatical info parsing in LIFT XML.
"""

import sys
sys.path.append('.')

from app import create_app
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry

def debug_grammatical_info_parsing():
    """Debug the grammatical info parsing issue."""
    
    app = create_app()
    with app.app_context():
        # Get the dictionary service via dependency injection
        from app import injector
        dict_service = injector.get(DictionaryService)
        
        # Create a test entry
        entry = Entry(
            id_="debug_entry",
            lexical_unit={"en": "debug"}
        )
        
        dict_service.create_entry(entry)
        
        # Add sense with grammatical info via direct BaseX update
        db_name = dict_service.db_connector.database
        
        update_query = f"""
        xquery 
        let $entry := collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry'][@id="debug_entry"]
        return (
            insert node 
            <sense id="debug_sense">
                <grammatical-info value="noun"/>
                <gloss lang="en">
                    <text>debug gloss</text>
                </gloss>
                <definition>
                    <form lang="en">
                        <text>A debug definition</text>
                    </form>
                </definition>
            </sense>
            into $entry
        )
        """
        
        dict_service.db_connector.execute_update(update_query)
        
        # Now get the raw XML to see what's actually stored
        raw_xml_query = f"""
        xquery 
        collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry'][@id="debug_entry"]
        """
        
        raw_xml = dict_service.db_connector.execute_query(raw_xml_query)
        print("Raw XML from database:")
        print(raw_xml)
        print("\n" + "="*50 + "\n")
        
        # Now try to retrieve the entry through our normal process
        retrieved_entry = dict_service.get_entry("debug_entry")
        print(f"Retrieved entry: {retrieved_entry}")
        print(f"Number of senses: {len(retrieved_entry.senses)}")
        
        if retrieved_entry.senses:
            sense = retrieved_entry.senses[0]
            print(f"First sense: {sense}")
            print(f"Sense ID: {sense.id}")
            print(f"Sense grammatical_info: {sense.grammatical_info}")
            print(f"Sense glosses: {sense.glosses}")
            print(f"Sense definitions: {sense.definitions}")
        
        # Clean up
        dict_service.delete_entry("debug_entry")

if __name__ == "__main__":
    debug_grammatical_info_parsing()
