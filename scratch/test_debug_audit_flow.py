import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app

app = create_app()

with app.app_context():
    from app.services.dictionary_service import get_dictionary_service
    dict_service = get_dictionary_service()
    db = dict_service.db_connector
    
    print("1. db.database:", db.database)
    
    db_name = db.database or 'dictionary'
    
    q_count = f'XQUERY count(collection("{db_name}")//entry)'
    print("2. Query count:", q_count)
    res_count = db.execute_query(q_count)
    print("3. Res count:", repr(res_count))
    
    q_count_no_db = 'XQUERY count(collection()//entry)'
    print("4. Query count no db:", q_count_no_db)
    res_count_no_db = db.execute_query(q_count_no_db)
    print("5. Res count no db:", repr(res_count_no_db))
    
    q_ids = f'XQUERY collection("{db_name}")//entry/@id/string()'
    res_ids = db.execute_query(q_ids) or ""
    print("6. Res IDs lines count:", len(res_ids.splitlines()))
