#!/usr/bin/env python3
"""
Debug script to test variant data in the browser
"""

from app import create_app
import webbrowser
import time

app = create_app()

with app.app_context():
    # Test entry with variants
    from app.models.entry import Entry
    from app.services.dictionary_service import DictionaryService
    from app.database.basex_connector import BaseXConnector
    from config import Config
    
    # Initialize connector and service
    connector = BaseXConnector(Config.BASEX_HOST, Config.BASEX_PORT, Config.BASEX_USERNAME, Config.BASEX_PASSWORD)
    service = DictionaryService(connector)
    
    entry = service.get_entry('Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf')
    
    if entry:
        print(f'✅ Entry found: {entry.id}')
        print(f'✅ Variant relations: {len(entry.variant_relations)}')
        for variant in entry.variant_relations:
            print(f'   - {variant}')
        
        # Test template serialization
        import json
        serialized = json.dumps(entry.variant_relations)
        print(f'✅ JSON serialization: {serialized}')
        
        # Check if the object has the right structure
        if hasattr(entry, 'variant_relations') and entry.variant_relations:
            print('✅ entry.variant_relations attribute exists and has data')
        else:
            print('❌ entry.variant_relations is missing or empty')
            
    else:
        print('❌ Entry not found')
    
    connector.close()
