import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app
from app.services.dictionary_service import DictionaryService

app = create_app()

with app.app_context():
    svc = app.injector.get(DictionaryService)
    
    # Create an incomplete entry in database
    incomplete_id = "test_incomplete_entry_12345"
    incomplete_xml = f'<entry id="{incomplete_id}"><lexical-unit></lexical-unit></entry>'
    
    try:
        svc.db_connector.execute_update(f'insert node {incomplete_xml} as last into collection()')
        print(f"Inserted incomplete entry: {incomplete_id}")
    except Exception as e:
        print(f"Failed to insert incomplete entry: {e}")
        
    # Verify existence
    exists = svc.entry_exists(incomplete_id)
    print(f"Entry exists check: {exists}")
    
    # Delete entry
    try:
        deleted = svc.delete_entry(incomplete_id)
        print(f"Delete entry success: {deleted}")
    except Exception as e:
        print(f"Delete entry failed: {e}")
        
    # Verify deletion
    exists_after = svc.entry_exists(incomplete_id)
    print(f"Entry exists after deletion: {exists_after}")
