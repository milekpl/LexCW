"""
End-to-end integration test for grammatical_info field persistence.

This test verifies that the Part of Speech (grammatical_info) field works correctly
from form serialization through XML generation, storage in BaseX, and retrieval.
"""

from __future__ import annotations

import pytest
import uuid
from lxml import etree as ET


def gen_id(prefix: str = "pos_e2e") -> str:
    """Generate unique test ID."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.mark.integration
class TestGrammaticalInfoEndToEnd:
    """Test grammatical_info field end-to-end."""

    def test_sense_level_grammatical_info_roundtrip(self, client, basex_test_connector):
        """Test that sense-level grammatical_info persists through save/load cycle."""
        entry_id = gen_id()
        
        # Create entry with sense-level grammatical-info
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>testowe słowo</text></form>
            </lexical-unit>
            <sense id="s1">
                <grammatical-info value="Countable Noun"/>
                <definition>
                    <form lang="pl"><text>Testowa definicja</text></form>
                </definition>
            </sense>
        </entry>'''
        
        # POST: Create the entry
        resp = client.post('/api/xml/entries', data=entry_xml, 
                          headers={'Content-Type': 'application/xml'})
        assert resp.status_code == 201, f"Failed to create entry: {resp.data}"
        
        # GET: Retrieve the entry (returns XML)
        resp = client.get(f'/api/xml/entries/{entry_id}')
        assert resp.status_code == 200, f"Failed to retrieve entry: {resp.data}"
        
        # Parse XML response
        xml_data = resp.data.decode('utf-8')
        root = ET.fromstring(xml_data)
        
        # Verify grammatical-info element exists and has correct value
        grammatical_info_elem = root.find('.//sense[@id="s1"]/grammatical-info')
        assert grammatical_info_elem is not None, "Missing <grammatical-info> element"
        assert grammatical_info_elem.get('value') == 'Countable Noun', \
            f"Wrong value: {grammatical_info_elem.get('value')}"

    def test_entry_level_grammatical_info_roundtrip(self, client, basex_test_connector):
        """Test that entry-level grammatical_info persists through save/load cycle."""
        entry_id = gen_id()
        
        # Create entry with entry-level grammatical-info
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>słowo</text></form>
            </lexical-unit>
            <grammatical-info value="Verb"/>
            <sense id="s1">
                <definition>
                    <form lang="pl"><text>definicja</text></form>
                </definition>
            </sense>
        </entry>'''
        
        # POST: Create the entry
        resp = client.post('/api/xml/entries', data=entry_xml,
                          headers={'Content-Type': 'application/xml'})
        assert resp.status_code == 201
        
        # GET: Retrieve the entry
        resp = client.get(f'/api/xml/entries/{entry_id}')
        assert resp.status_code == 200
        
        # Parse XML response
        xml_data = resp.data.decode('utf-8')
        root = ET.fromstring(xml_data)
        
        # Verify entry-level grammatical-info
        grammatical_info_elem = root.find('./grammatical-info')
        assert grammatical_info_elem is not None, "Missing entry-level <grammatical-info>"
        assert grammatical_info_elem.get('value') == 'Verb'

    def test_multiple_senses_with_different_pos(self, client, basex_test_connector):
        """Test multiple senses each with different Part of Speech."""
        entry_id = gen_id()
        
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>run</text></form>
            </lexical-unit>
            <sense id="s1" order="0">
                <grammatical-info value="Verb"/>
                <definition>
                    <form lang="en"><text>To move quickly on foot</text></form>
                </definition>
            </sense>
            <sense id="s2" order="1">
                <grammatical-info value="Countable Noun"/>
                <definition>
                    <form lang="en"><text>A race or jog</text></form>
                </definition>
            </sense>
        </entry>'''
        
        # Create
        resp = client.post('/api/xml/entries', data=entry_xml,
                          headers={'Content-Type': 'application/xml'})
        assert resp.status_code == 201
        
        # Retrieve
        resp = client.get(f'/api/xml/entries/{entry_id}')
        assert resp.status_code == 200
        
        # Parse and verify both senses retained their grammatical-info
        xml_data = resp.data.decode('utf-8')
        root = ET.fromstring(xml_data)
        
        sense1_pos = root.find('.//sense[@id="s1"]/grammatical-info')
        assert sense1_pos is not None
        assert sense1_pos.get('value') == 'Verb'
        
        sense2_pos = root.find('.//sense[@id="s2"]/grammatical-info')
        assert sense2_pos is not None
        assert sense2_pos.get('value') == 'Countable Noun'

    def test_update_grammatical_info(self, client, basex_test_connector):
        """Test updating grammatical_info value."""
        entry_id = gen_id()
        
        # Create with initial POS
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>test</text></form>
            </lexical-unit>
            <sense id="s1">
                <grammatical-info value="Noun"/>
                <definition>
                    <form lang="pl"><text>def</text></form>
                </definition>
            </sense>
        </entry>'''
        
        resp = client.post('/api/xml/entries', data=entry_xml,
                          headers={'Content-Type': 'application/xml'})
        assert resp.status_code == 201
        
        # Update to different POS
        updated_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>test</text></form>
            </lexical-unit>
            <sense id="s1">
                <grammatical-info value="Verb"/>
                <definition>
                    <form lang="pl"><text>def</text></form>
                </definition>
            </sense>
        </entry>'''
        
        resp = client.put(f'/api/xml/entries/{entry_id}', data=updated_xml,
                         headers={'Content-Type': 'application/xml'})
        assert resp.status_code == 200
        
        # Verify update persisted
        resp = client.get(f'/api/xml/entries/{entry_id}')
        assert resp.status_code == 200
        
        xml_data = resp.data.decode('utf-8')
        root = ET.fromstring(xml_data)
        
        pos_elem = root.find('.//sense[@id="s1"]/grammatical-info')
        assert pos_elem is not None
        assert pos_elem.get('value') == 'Verb', "Update did not persist"
