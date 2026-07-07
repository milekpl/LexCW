import sys
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
    entries = ds.get_all_entries(limit=1000)
    print(f"Loaded {len(entries)} entries sample.")
    
    engine = ValidationEngine(project_id=1)
    
    invalid_count = 0
    issue_counts = {}
    
    for e in entries:
        e_dict = e.to_dict() if hasattr(e, 'to_dict') else (e if isinstance(e, dict) else {})
        res = engine.validate_json(e_dict)
        if not res.is_valid or res.error_count > 0:
            invalid_count += 1
            for err in res.errors + res.warnings + res.info:
                issue_counts[err.rule_id] = issue_counts.get(err.rule_id, 0) + 1
                
    print(f"Sample of {len(entries)} entries tested with ValidationEngine:")
    print(f" - Valid entries: {len(entries) - invalid_count}")
    print(f" - Invalid/Flagged entries: {invalid_count}")
    print(" - Issues found by rule:")
    for rule_id, count in issue_counts.items():
        print(f"    * Rule {rule_id}: {count} occurrences")
