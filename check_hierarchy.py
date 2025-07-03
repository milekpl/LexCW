#!/usr/bin/env python3
"""
Check hierarchical structure of LIFT ranges
"""

import os
os.environ['FLASK_ENV'] = 'development'

from app import create_app
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService

app = create_app()
with app.app_context():
    # Get connector from app context
    connector = app.injector.get(BaseXConnector)
    service = DictionaryService(connector)
    
    # Check raw XML structure
    print("Checking raw LIFT ranges XML structure:")
    raw_query = "collection('dictionary')//lift-ranges//range[@id='semantic-domain-ddp4']//range-element[position() <= 5]"
    connector = app.injector.get(BaseXConnector)
    result = connector.execute_query(raw_query)
    print("Raw semantic domain elements (first 5):")
    print(result)
    
    print("\nChecking grammatical-info raw XML:")
    raw_query2 = "collection('dictionary')//lift-ranges//range[@id='grammatical-info']//range-element[position() <= 5]"
    result2 = connector.execute_query(raw_query2)
    print("Raw grammatical info elements (first 5):")
    print(result2)
