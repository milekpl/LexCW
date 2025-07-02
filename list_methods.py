from app import create_app, injector
from app.services.dictionary_service import DictionaryService

app = create_app()
with app.app_context():
    dict_service = injector.get(DictionaryService)
    print("Available methods in DictionaryService:")
    methods = [method for method in dir(dict_service) if not method.startswith('_')]
    for method in methods:
        print(f"- {method}")
