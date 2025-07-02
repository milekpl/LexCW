from app import create_app
from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector
from flask import current_app

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
    
    # Get entry
    try:
        entry = ds.get_entry('1')
        print(f"Entry type: {type(entry)}")
        print(f"Entry: {entry}")
        if entry:
            print(f"Entry to_dict: {entry.to_dict()}")
    except Exception as e:
        print(f"Error: {e}")
