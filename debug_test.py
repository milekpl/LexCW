#!/usr/bin/env python3
"""
Debug script to mimic the exact failing test
"""
import sys
sys.path.append('/mnt/d/Dokumenty/slownik-wielki/flask-app')

from unittest.mock import Mock, MagicMock, patch
from app.services.xml_entry_service import (
    XMLEntryService,
    LIFT_NS
)

# Test XML with namespace prefixes
VALID_ENTRY_XML_WITH_PREFIXES = f'''
<lift:entry xmlns:lift="{LIFT_NS}" id="test_001" guid="test_guid_001" dateCreated="2024-01-01T12:00:00Z">
    <lift:lexical-unit>
        <lift:form lang="en"><lift:text>testword</lift:text></lift:form>
    </lift:lexical-unit>
    <lift:sense id="sense_001" order="0">
        <lift:gloss lang="en"><lift:text>a test word</lift:text></lift:gloss>
    </lift:sense>
</lift:entry>
'''.strip()

def debug_failing_test():
    print("=== Mimicking the failing test ===")
    
    # Create mock BaseX session exactly like the test
    mock_basex_session = MagicMock()
    mock_basex_session.execute = MagicMock(return_value="")
    mock_basex_session.close = MagicMock()
    
    # Mock query object
    query_mock = MagicMock()
    query_mock.execute = MagicMock(return_value=VALID_ENTRY_XML_WITH_PREFIXES)
    query_mock.close = MagicMock()
    
    mock_basex_session.query = MagicMock_mock)
    
   (return_value=query # Create service with mocked connection
    with patch('app.services.xml_entry_service.BaseXClient.Session') as mock_session_class:
        mock_session_class.return_value = mock_basex_session
        
        # Create service
        service = XMLEntryService()
        
        # Patch _get_session to always return our mock
        service._get_session = Mock(return_value=mock_basex_session)
        
        # Force namespace detection to work correctly in tests
        detection_query_mock = MagicMock()
        detection_query_mock.execute.return_value = 'true'
        detection_query_mock.close.return_value = None
        mock_basex_session.query.return_value = detection_query_mock
        
        print(f"Service _has_namespace: {service._has_namespace}")
        
        # Call get_entry exactly like the test
        result = service.get_entry('test_001')
        
        print(f"Result keys: {result.keys()}")
        print(f"ID: {result.get('id')}")
        print(f"GUID: {result.get('guid')}")
        print(f"Lexical units: {result.get('lexical_units')}")
        print(f"Length of lexical_units: {len(result.get('lexical_units', []))}")
        print(f"Senses: {result.get('senses')}")
        print(f"Length of senses: {len(result.get('senses', []))}")
        
        # Check the assertion that was failing
        lexical_units_length = len(result.get('lexical_units', []))
        senses_length = len(result.get('senses', []))
        
        print(f"\nAssertion checks:")
        print(f"len(result['lexical_units']) > 0: {lexical_units_length} > 0 = {lexical_units_length > 0}")
        print(f"len(result['senses']) > 0: {senses_length} > 0 = {senses_length > 0}")
        
        if lexical_units_length > 0 and senses_length > 0:
            print("✅ Test assertions would PASS")
        else:
            print("❌ Test assertions would FAIL")

if __name__ == "__main__":
    debug_failing_test()