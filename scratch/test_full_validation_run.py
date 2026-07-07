import time
import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app
from app.services.dictionary_service import DictionaryService
from app.services.validation_engine import ValidationEngine

app = create_app()

with app.app_context():
    dict_service = app.injector.get(DictionaryService)
    db = dict_service.db_connector
    
    t0 = time.time()
    res_entry_ids = db.execute_query('XQUERY collection("dictionary")//entry/@id/string()') or ""
    res_entry_guids = db.execute_query('XQUERY collection("dictionary")//entry/@guid/string()') or ""
    res_sense_ids = db.execute_query('XQUERY collection("dictionary")//sense/@id/string()') or ""
    res_sense_guids = db.execute_query('XQUERY collection("dictionary")//sense/@guid/string()') or ""

    all_targets = set(
        [line.strip() for line in res_entry_ids.splitlines() if line.strip()]
        + [line.strip() for line in res_entry_guids.splitlines() if line.strip()]
        + [line.strip() for line in res_sense_ids.splitlines() if line.strip()]
        + [line.strip() for line in res_sense_guids.splitlines() if line.strip()]
    )
    for eid in list(all_targets):
        if "_" in eid:
            all_targets.add(eid.rsplit("_", 1)[-1])
            
    print(f"Loaded {len(all_targets)} target IDs in {time.time() - t0:.2f}s")
