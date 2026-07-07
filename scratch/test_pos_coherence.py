import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app

app = create_app()

with app.app_context():
    from app.services.pos_tagger_service import get_pos_tagger_service
    tagger = get_pos_tagger_service()
    
    print("NLP Parser:", tagger.nlp_parser)
    if tagger.nlp_parser:
        print("Pipe names:", tagger.nlp_parser.pipe_names)
        
    # Test definition phrase coherence check
    res1 = tagger.analyze_definition_phrases("to walk slowly, to wander", expected_pos="Verb", delimiter=",")
    print("res1 (expected Verb):", res1)
    
    res2 = tagger.analyze_definition_phrases("quick, fast, to run", expected_pos="Adjective", delimiter=",")
    print("res2 (expected Adjective):", res2)
