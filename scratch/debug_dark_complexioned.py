import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app
from app.services.dictionary_service import DictionaryService

app = create_app()

with app.app_context():
    dict_service = app.injector.get(DictionaryService)
    db = dict_service.db_connector
    
    target_ref = "dark-complexioned_d52acad7-e5be-4222-b8bf-abb4dfa9ab33"
    target_guid = "d52acad7-e5be-4222-b8bf-abb4dfa9ab33"
    
    # 1. Query by full target_ref
    q1 = f'collection("dictionary")//entry[@id="{target_ref}" or @guid="{target_ref}"]'
    r1 = db.execute_query(q1)
    print("Direct query full ID r1:", bool(r1))
    
    # 2. Query by GUID
    q2 = f'collection("dictionary")//entry[@id="{target_guid}" or @guid="{target_guid}" or ends-with(@id, "_{target_guid}")]'
    r2 = db.execute_query(q2)
    print("Direct query GUID r2:", bool(r2))
    
    # 3. Search text matching d52acad7
    q3 = 'collection("dictionary")//entry[contains(@id, "d52acad7") or contains(@guid, "d52acad7") or .//sense[contains(@id, "d52acad7") or contains(@guid, "d52acad7")]]'
    r3 = db.execute_query(q3)
    print("Contains d52acad7 r3:", bool(r3))
    if r3:
        print("XML snippet:", r3[:500])
