import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app
from app.services.dictionary_service import DictionaryService

app = create_app()

with app.app_context():
    ds = app.injector.get(DictionaryService)
    db = ds.db_connector
    
    db_name = db.database or 'dictionary'
    
    print("db.database:", db.database)
    
    c1 = db.execute_query('XQUERY count(collection()//entry)')
    print("c1 count(collection()//entry):", c1)
    
    c2 = db.execute_query(f'XQUERY count(collection("{db_name}")//entry)')
    print(f'c2 count(collection("{db_name}")//entry):', c2)
