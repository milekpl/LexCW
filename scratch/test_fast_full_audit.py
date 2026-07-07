import time
import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app
from app.services.dictionary_service import DictionaryService

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

    t1 = time.time()
    res_refs = db.execute_query('XQUERY distinct-values(collection("dictionary")//relation/@ref/string())') or ""
    all_refs = [line.strip() for line in res_refs.splitlines() if line.strip()]
    
    dead_refs = []
    for ref in all_refs:
        if ref not in all_targets:
            # Check if suffix or guid matches
            if "_" in ref and ref.rsplit("_", 1)[-1] in all_targets:
                continue
            dead_refs.append(ref)
            
    print(f"Full dictionary audit of {len(all_refs)} relation references finished in {time.time() - t0:.2f}s!")
    print(f"Total dead references in entire dictionary: {len(dead_refs)}")
    for dr in dead_refs:
        print(" - Dead ref:", dr)
