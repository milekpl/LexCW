#!/usr/bin/env python3
"""
Test etymology types in ranges.
"""

from app import create_app, injector
from app.services.dictionary_service import DictionaryService

app = create_app('testing')
with app.app_context():
    dict_service = injector.get(DictionaryService)
    ranges = dict_service.get_ranges()
    if 'etymology-types' in ranges:
        print('Etymology types found in ranges:')
        for ety_type in ranges['etymology-types']['values']:
            print(f'  - {ety_type["value"]}: {ety_type["description"]["en"]}')
    else:
        print('Etymology types not found in ranges')
        print('Available range keys:', list(ranges.keys()))
