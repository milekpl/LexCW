"""Script to check available LIFT ranges."""
from __future__ import annotations

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.dictionary_service import DictionaryService

app = create_app()
with app.app_context():
    dict_service = app.injector.get(DictionaryService)
    ranges = dict_service.get_lift_ranges()
    
    print("Available LIFT ranges:")
    print("=" * 50)
    for range_name, range_data in ranges.items():
        print(f"Range: {range_name}")
        if isinstance(range_data, dict) and 'values' in range_data:
            values_count = len(range_data['values']) if range_data['values'] else 0
            print(f"  Values count: {values_count}")
            if values_count > 0 and values_count <= 5:
                print(f"  Sample values: {[v.get('value', v) for v in range_data['values'][:3]]}")
        print()
