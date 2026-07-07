import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app
from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector

app = create_app()

with app.app_context():
    db = BaseXConnector(
        host=app.config.get('BASEX_HOST', 'localhost'),
        port=app.config.get('BASEX_PORT', 1984),
        username=app.config.get('BASEX_USER', 'admin'),
        password=app.config.get('BASEX_PASSWORD', 'admin'),
        database=app.config.get('BASEX_DB', 'dictionary')
    )
    ds = DictionaryService(db_connector=db)
    res = ds.list_entries(limit=5)
    entries = res.get('entries', []) if isinstance(res, dict) else res
    
    print("Entries type:", type(entries))
    if len(entries) > 0:
        first = entries[0]
        print("First entry type:", type(first))
        print("First entry dir:", dir(first))
        if hasattr(first, 'to_dict'):
            print("first.to_dict():", first.to_dict())
        else:
            print("dict(first) or similar:", str(first))
