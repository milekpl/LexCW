
import sys
import os
from flask import Flask

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.dictionary_service import DictionaryService

app = create_app()

with app.app_context():
    try:
        print("Attempting to get ranges...")
        dict_service = app.injector.get(DictionaryService)
        ranges = dict_service.get_ranges()
        print("Successfully retrieved ranges.")
        print(f"Ranges keys: {list(ranges.keys())}")
    except Exception as e:
        print(f"Error retrieving ranges: {e}")
        import traceback
        traceback.print_exc()
