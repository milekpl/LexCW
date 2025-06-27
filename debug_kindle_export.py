#!/usr/bin/env python3

from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.exporters.kindle_exporter import KindleExporter
import tempfile
import os
import uuid

# Create test database connection
db_name = f'test_debug_{uuid.uuid4().hex[:8]}'
connector = BaseXConnector(
    host='localhost',
    port=1984,
    username='admin',
    password='admin',
    database=db_name
)

try:
    # Simple database creation
    connector.connect()
    connector.create_database(db_name)

    # Add minimal test data
    minimal_lift = '''<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
        <entry id="test_entry_1">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
            <sense id="test_sense_1">
                <definition>
                    <form lang="en"><text>A test entry</text></form>
                </definition>
            </sense>
        </entry>
    </lift>'''
    connector.execute_update(f'db:add("{db_name}", "{minimal_lift}", "lift.xml")')

    service = DictionaryService(db_connector=connector)
    entries, count = service.list_entries()
    print(f'Found {count} entries:', [e.id for e in entries])

    # Test export
    exporter = KindleExporter(service)
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
        temp_filename = temp_file.name

    try:
        result = exporter.export(temp_filename, title='Test Dictionary')
        print(f'Export result: {result}')
        
        # Check if file exists
        if os.path.exists(temp_filename):
            with open(temp_filename, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f'File content length: {len(content)}')
                print(f'Content preview: {content[:200] if content else "Empty file"}')
        else:
            print('Export file does not exist')
            
        # Check result directory  
        if os.path.exists(result):
            files = os.listdir(result)
            print(f'Result directory files: {files}')
            
            for file in files:
                file_path = os.path.join(result, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f'{file} content length: {len(content)}')
                    print(f'{file} preview: {content[:200] if content else "Empty"}')
                    
    finally:
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)
            
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
