import time
import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app

from app.services.dictionary_service import DictionaryService

app = create_app()

with app.app_context():
    dict_service = app.injector.get(DictionaryService)

    
    t0 = time.time()
    # Query database for total entry count
    connector = dict_service.db_connector
    count_res = connector.execute_query('XQUERY count(collection("dictionary")//entry)')
    print(f"Total entries in database: {count_res} (query took {time.time() - t0:.2f}s)")
