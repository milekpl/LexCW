"""
Check the test pronunciation entry.
"""
from app import create_app
from app.services.dictionary_service import DictionaryService

def check_pronunciation_entry():
    """Check the test pronunciation entry in the database."""
    app = create_app()
    with app.app_context():
        dict_service = app.injector.get(DictionaryService)
        try:
            entry = dict_service.get_entry('test_pronunciation_entry')
            print(f'Entry ID: {entry.id}')
            print(f'Lexical Unit: {entry.lexical_unit}')
            print(f'Pronunciations: {entry.pronunciations}')
            
            # Convert to the format expected by JavaScript
            pronunciations_array = []
            for writing_system, value in entry.pronunciations.items():
                pronunciations_array.append({
                    "type": writing_system,
                    "value": value,
                    "audio_file": "",
                    "is_default": True
                })
            
            print(f'Pronunciations array: {pronunciations_array}')
        except Exception as e:
            print(f'Error: {e}')

if __name__ == '__main__':
    check_pronunciation_entry()
