"""Simple test to check if grammatical_info persists."""

import pytest
import uuid


def gen_id():
    return f"pos_test_{uuid.uuid4().hex[:8]}"


@pytest.mark.integration
def test_grammatical_info_persists(client, basex_test_connector):
    """Test that grammatical_info field persists through save/load cycle."""
    entry_id = gen_id()
    
    # Create XML with grammatical-info
    xml = f'''<entry id="{entry_id}">
        <lexical-unit>
            <form lang="pl"><text>test</text></form>
        </lexical-unit>
        <sense id="s1">
            <grammatical-info value="Countable Noun"/>
            <definition>
                <form lang="pl"><text>definicja</text></form>
            </definition>
        </sense>
    </entry>'''
    
    # POST the entry
    resp = client.post('/api/xml/entries', data=xml, headers={'Content-Type': 'application/xml'})
    print(f"\\nPOST status: {resp.status_code}")
    print(f"POST data: {resp.data}")
    
    if resp.status_code != 201:
        pytest.fail(f"Failed to create entry. Status: {resp.status_code}, Data: {resp.data}")
    
    # GET the entry back
    resp = client.get(f'/api/xml/entries/{entry_id}')
    print(f"GET status: {resp.status_code}")
    print(f"GET data: {resp.data}")
    
    assert resp.status_code == 200, f"Failed to retrieve entry: {resp.data}"
    
    # Parse XML response
    from lxml import etree as ET
    xml_data = resp.data.decode('utf-8')
    root = ET.fromstring(xml_data)
    
    # Check if grammatical_info element exists
    grammatical_info_elem = root.find('.//sense[@id="s1"]/grammatical-info')
    print(f"grammatical-info element: {grammatical_info_elem}")
    
    # THE ACTUAL TEST - does grammatical_info persist?
    assert grammatical_info_elem is not None, "No <grammatical-info> element found in XML"
    
    value = grammatical_info_elem.get('value')
    print(f"grammatical-info value: {value}")
    assert value == 'Countable Noun', f"Wrong value: {value}"
    
    print("✓ Test passed - grammatical_info persisted correctly")
