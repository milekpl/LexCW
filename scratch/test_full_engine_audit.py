import sys
import time
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app

app = create_app()

with app.app_context():
    from app.services.dictionary_service import DictionaryService
    from app.services.validation_engine import ValidationEngine
    from app.database.basex_connector import BaseXConnector

    db = BaseXConnector(
        host=app.config.get('BASEX_HOST', 'localhost'),
        port=app.config.get('BASEX_PORT', 1984),
        username=app.config.get('BASEX_USER', 'admin'),
        password=app.config.get('BASEX_PASSWORD', 'admin'),
        database=app.config.get('BASEX_DB', 'dictionary')
    )

    ds = DictionaryService(db_connector=db)
    
    # Pre-fetch all valid targets for relation validation (R5.3.1)
    t0 = time.time()
    res_entry_ids = db.execute_query('XQUERY collection("dictionary")//entry/@id/string()') or ""
    res_entry_guids = db.execute_query('XQUERY collection("dictionary")//entry/@guid/string()') or ""
    res_sense_ids = db.execute_query('XQUERY collection("dictionary")//sense/@id/string()') or ""
    res_sense_guids = db.execute_query('XQUERY collection("dictionary")//sense/@guid/string()') or ""

    existing_entry_ids = set(
        [line.strip() for line in res_entry_ids.splitlines() if line.strip()]
        + [line.strip() for line in res_entry_guids.splitlines() if line.strip()]
        + [line.strip() for line in res_sense_ids.splitlines() if line.strip()]
        + [line.strip() for line in res_sense_guids.splitlines() if line.strip()]
    )
    for eid in list(existing_entry_ids):
        if "_" in eid:
            existing_entry_ids.add(eid.rsplit("_", 1)[-1])

    engine = ValidationEngine(existing_entry_ids=existing_entry_ids, project_id=1)
    print(f"Target IDs loaded in {time.time() - t0:.2f}s ({len(existing_entry_ids)} targets)")

    # Fetch total count
    count_str = db.execute_query('XQUERY count(collection("dictionary")//entry)') or "0"
    total_count = int(count_str.strip()) if count_str.strip().isdigit() else 0
    print(f"Total entries to validate: {total_count}")

    chunk_size = 5000
    invalid_results = []
    valid_count = 0
    invalid_count = 0
    total_issues = 0

    t1 = time.time()
    for offset in range(0, total_count, chunk_size):
        chunk_res = ds.list_entries(limit=chunk_size, offset=offset)
        entries = chunk_res.get('entries', []) if isinstance(chunk_res, dict) else chunk_res
        
        for e in entries:
            e_dict = e.to_dict() if hasattr(e, 'to_dict') else (e if isinstance(e, dict) else {})
            res = engine.validate_json(e_dict)
            if not res.is_valid or res.error_count > 0:
                invalid_count += 1
                total_issues += res.error_count
                invalid_results.append({
                    'entry_id': e_dict.get('id'),
                    'valid': res.is_valid,
                    'error_count': len(res.errors),
                    'has_critical_errors': res.has_critical_errors,
                    'errors': [{'rule_id': err.rule_id, 'message': err.message, 'path': err.path, 'priority': err.priority.value if hasattr(err.priority, 'value') else str(err.priority)} for err in res.errors],
                    'warnings': [{'rule_id': w.rule_id, 'message': w.message, 'path': w.path, 'priority': w.priority.value if hasattr(w.priority, 'value') else str(w.priority)} for w in res.warnings],
                    'info': [{'rule_id': i.rule_id, 'message': i.message, 'path': i.path, 'priority': i.priority.value if hasattr(i.priority, 'value') else str(i.priority)} for i in res.info]
                })
            else:
                valid_count += 1
        print(f"Validated chunk offset {offset}-{offset+len(entries)} (Progress: {offset+len(entries)}/{total_count}, Invalid so far: {invalid_count})")

    t_end = time.time()
    print(f"FULL DICTIONARY AUDIT COMPLETE in {t_end - t1:.2f}s!")
    print(f"Total: {total_count}, Valid: {valid_count}, Invalid: {invalid_count}, Issues: {total_issues}")
