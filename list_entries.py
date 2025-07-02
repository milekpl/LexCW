from app import create_app, injector
from app.services.dictionary_service import DictionaryService

app = create_app()
with app.app_context():
    print('Existing entries:')
    dict_service = injector.get(DictionaryService)
    try:
        entries = dict_service.list_entries(limit=5)
        if entries:
            for i, entry in enumerate(entries):
                print(f"{i+1}. Entry: {entry}")
        else:
            print("No entries found")
    except Exception as e:
        print(f"Error: {e}")
