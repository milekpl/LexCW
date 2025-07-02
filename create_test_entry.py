from app import create_app
from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector
from app.models.entry import Entry, Relation
from flask import current_app
import json

app = create_app()
with app.app_context():
    # Get config values
    host = current_app.config.get('BASEX_HOST', 'localhost')
    port = current_app.config.get('BASEX_PORT', 1984)
    username = current_app.config.get('BASEX_USERNAME', 'admin')
    password = current_app.config.get('BASEX_PASSWORD', 'admin')
    database = current_app.config.get('BASEX_DATABASE', 'dictionary')
    
    # Create the BaseX connector
    db = BaseXConnector(host=host, port=port, username=username, password=password)
    db.database = database
    
    # Create dictionary service
    ds = DictionaryService(db)
    
    # Create a test entry
    entry = Entry(lexical_unit="test")
    entry.id = "test123"
    
    # Add a relation to cause the JSON serialization error
    relation = Relation(type="synonym", ref="another-entry")
    entry.relations = [relation]
    
    try:
        # Create a LIFT file with the entry
        lift_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test123">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <relation type="synonym" ref="another-entry" />
    </entry>
</lift>
"""
        
        # Create a temporary file for the LIFT data
        import os
        from tempfile import NamedTemporaryFile
        
        with NamedTemporaryFile(delete=False, suffix='.lift', mode='w', encoding='utf-8') as f:
            f.write(lift_xml)
            temp_path = f.name
        
        print(f"Created temporary LIFT file: {temp_path}")
        
        # Import the LIFT file
        print("Importing LIFT file...")
        entry_count = ds.import_lift(temp_path)
        print(f"Imported {entry_count} entries")
        
        # Clean up the temporary file
        os.unlink(temp_path)
        
        # Now try to retrieve the entry
        print("Retrieving entry...")
        retrieved_entry = ds.get_entry("test123")
        print(f"Retrieved entry: {retrieved_entry}")
        
        # Check for relations
        if hasattr(retrieved_entry, 'relations') and retrieved_entry.relations:
            print(f"Relations: {retrieved_entry.relations}")
            for rel in retrieved_entry.relations:
                print(f"Relation type: {rel.type}, ref: {rel.ref}")
        
        # Convert to dict
        entry_dict = retrieved_entry.to_dict()
        print(f"Entry as dict: {entry_dict}")
        
        # Verify we can serialize to JSON
        entry_json = json.dumps(entry_dict)
        print(f"Entry as JSON: {entry_json}")
    except Exception as e:
        print(f"Error: {e}")
