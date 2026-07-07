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
            
    engine = ValidationEngine(existing_entry_ids=all_targets)
    
    print(f"Loaded targets in {time.time() - t0:.2f}s")
    
    # Query BaseX for entries that might violate rules directly, or iterate
    # E.g. Check relation target validity via XQuery:
    t1 = time.time()
    # Find invalid relation targets directly in BaseX
    xquery_invalid_refs = '''
    declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
    for $e in collection("dictionary")//entry
    for $r in $e//relation
    let $ref := $r/@ref/string()
    where not(collection("dictionary")//entry[@id=$ref or @guid=$ref or ends-with(@id, concat('_', $ref))] or collection("dictionary")//sense[@id=$ref or @guid=$ref])
    return concat($e/@id/string(), " -> ", $ref)
    '''
    invalid_refs = db.execute_query(xquery_invalid_refs) or ""
    print(f"BaseX direct dead ref audit finished in {time.time() - t1:.2f}s:")
    print("Invalid refs found:", invalid_refs.splitlines())
