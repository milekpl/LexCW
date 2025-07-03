#!/usr/bin/env python3
"""Check available LIFT range IDs from the service."""

import os
os.environ['FLASK_ENV'] = 'development'

from app import create_app
from app.services.dictionary_service import DictionaryService

def main():
    app = create_app()
    with app.app_context():
        service = app.injector.get(DictionaryService)
        ranges = service.get_lift_ranges()
        
        print(f"Total ranges available: {len(ranges)}")
        print("\nAvailable range IDs:")
        for range_id in sorted(ranges.keys()):
            range_data = ranges[range_id]
            value_count = len(range_data.get('values', []))
            print(f"  {range_id:<25} ({value_count} values)")

if __name__ == "__main__":
    main()
