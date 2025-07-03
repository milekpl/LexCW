#!/usr/bin/env python3
"""
Test script to verify that variant data is correctly passed to templates
"""

from flask import Flask
from app import create_app

app = create_app()

# Test if variant data is passed to template correctly
print('Testing if variant data is passed to template...')

with app.app_context():
    from app.models.entry import Entry
    from app.services.dictionary_service import DictionaryService
    from config import Config
    
    # Initialize service
    service = DictionaryService(Config.BASEX_HOST, Config.BASEX_PORT, Config.BASEX_USERNAME, Config.BASEX_PASSWORD)
    
    # Test entry with variants
    entry = service.get_entry('Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf')
    if entry:
        print(f'Entry ID: {entry.id}')
        print(f'Variant relations found: {len(entry.variant_relations)}')
        for i, variant in enumerate(entry.variant_relations):
            ref = variant.get('ref')
            variant_type = variant.get('variant_type')
            print(f'  Variant {i+1}: ref={ref}, type={variant_type}')
        
        # Check if template would receive this data
        from jinja2 import Template
        test_template = Template('{{ (entry.variant_relations or []) | tojson | safe }}')
        rendered = test_template.render(entry=entry)
        print(f'Template would render: {rendered}')
    else:
        print('Entry not found')
    
    service.close()
