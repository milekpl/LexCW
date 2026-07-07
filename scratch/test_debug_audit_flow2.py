import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app
from app.services.dictionary_service import DictionaryService

app = create_app()

with app.app_context():
    dict_service = DictionaryService()
    db = dict_service.db_connector
    
    print("1. db.database:", db.database)
    db_name = db.database or 'dictionary'
    
    q_count = f'XQUERY count(collection("{db_name}")//entry)'
    res_count = db.execute_query(q_count)
    print("2. Res count:", repr(res_count))
