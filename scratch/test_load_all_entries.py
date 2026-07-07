import time
import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app
from app.services.dictionary_service import DictionaryService

app = create_app()

with app.app_context():
    dict_service = app.injector.get(DictionaryService)
    t0 = time.time()
    entries, total = dict_service.list_entries(limit=0)
    print(f"Loaded {len(entries)} entries out of total {total} in {time.time() - t0:.2f}s")
