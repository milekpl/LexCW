import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app
from app.services.dictionary_service import DictionaryService
from app.services.pos_tagger_service import get_pos_tagger_service
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
    res = ds.list_entries(limit=1000)
    
    # Properly unpack the tuple (entries_list, total_count)
    if isinstance(res, tuple):
        entries_list = res[0]
    else:
        entries_list = res
        
    tagger = get_pos_tagger_service()
    
    checked = 0
    contradictions_found = 0
    
    for e in entries_list:
        e_dict = e.to_dict() if hasattr(e, 'to_dict') else (e if isinstance(e, dict) else {})
        entry_pos = e_dict.get("grammatical_info") or e_dict.get("pos")
        
        for i, sense in enumerate(e_dict.get("senses", [])):
            sense_pos = sense.get("grammatical_info") or entry_pos
            definitions = sense.get("definition") or sense.get("gloss") or {}
            
            def_texts = []
            if isinstance(definitions, dict):
                def_texts = [str(v) for v in definitions.values() if v]
            elif isinstance(definitions, str):
                def_texts = [definitions]
                
            for def_str in def_texts:
                checked += 1
                analysis = tagger.analyze_definition_phrases(
                    def_str,
                    expected_pos=sense_pos,
                    delimiter=","
                )
                if not analysis["is_consistent"]:
                    contradictions_found += 1
                    if contradictions_found <= 10:
                        print(f"Match found in '{e_dict.get('id')}':")
                        print(f"  - Definition: '{def_str}'")
                        print(f"  - Expected POS: {sense_pos}")
                        print(f"  - Contradictions: {analysis['contradictions']}")
                        
    print(f"Total definition segments checked: {checked}")
    print(f"Total POS coherence contradictions found: {contradictions_found}")
