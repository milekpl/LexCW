"""
Integration tests for form field persistence - ensuring all form fields are saved and retrieved correctly.

This test suite systematically verifies that every field in the entry form (including ranges)
is properly saved to BaseX and can be retrieved correctly.
"""

from __future__ import annotations

import pytest
import uuid
from lxml import etree as ET

# LIFT namespace for XPath queries
LIFT_NS = "{http://fieldworks.sil.org/schemas/lift/0.13}"


def generate_test_id(prefix: str) -> str:
    """Generate a unique test ID."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.mark.integration
class TestFormFieldPersistence:
    """Test that all form fields persist correctly through save/load cycles."""

    @pytest.mark.integration
    def test_sense_grammatical_info_persistence(self, client, basex_test_connector):
        """Test that sense-level grammatical_info (Part of Speech) persists correctly."""
        entry_id = generate_test_id("test_pos")
        # Create entry with sense-level grammatical info
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>testowe słowo</text></form>
            </lexical-unit>
            <sense id="sense1">
                <grammatical-info value="Countable Noun"/>
                <definition>
                    <form lang="pl"><text>Testowa definicja</text></form>
                </definition>
            </sense>
        </entry>'''
        
        # Save the entry
        response = client.post(
            '/api/xml/entries',
            data=entry_xml,
            headers={'Content-Type': 'application/xml'}
        )
        print(f"POST response status: {response.status_code}")
        print(f"POST response data: {response.data}")
        assert response.status_code == 201
        data = response.get_json()
        print(f"POST response JSON: {data}")
        assert data is not None, "POST response JSON is None"
        assert data['success'] is True
        entry_id = data['entry_id']
        
        # Retrieve the entry
        response = client.get(f'/api/xml/entries/{entry_id}?format=json')
        print(f"GET response status: {response.status_code}")
        print(f"GET response data: {response.data}")
        assert response.status_code == 200
        entry_data = response.get_json()
        print(f"GET response JSON: {entry_data}")
        assert entry_data is not None, "Response JSON is None"
        assert 'xml' in entry_data
        
        # Parse the XML to check grammatical_info persisted
        xml_root = ET.fromstring(entry_data['xml'])
        sense = xml_root.find(f'.//{LIFT_NS}sense[@id="sense1"]')
        assert sense is not None, "Sense not found in XML"
        gram_info = sense.find(f'{LIFT_NS}grammatical-info')
        assert gram_info is not None, "grammatical-info element not found"
        assert gram_info.get('value') == 'Countable Noun'
        
    @pytest.mark.integration
    def test_entry_level_grammatical_info_persistence(self, client, basex_test_connector):
        """Test that entry-level grammatical_info persists correctly."""
        entry_id = generate_test_id("test_entry_pos")
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>inne słowo</text></form>
            </lexical-unit>
            <grammatical-info value="Verb"/>
            <sense id="sense1">
                <definition>
                    <form lang="pl"><text>Definicja czasownika</text></form>
                </definition>
            </sense>
        </entry>'''
        
        # Save
        response = client.post(
            '/api/xml/entries',
            data=entry_xml,
            headers={'Content-Type': 'application/xml'}
        )
        assert response.status_code == 201
        entry_id = response.get_json()['entry_id']
        
        # Retrieve
        response = client.get(f'/api/xml/entries/{entry_id}?format=json')
        assert response.status_code == 200
        entry_data = response.get_json()
        
        # Check entry-level grammatical_info
        xml_root = ET.fromstring(entry_data['xml'])
        gram_info = xml_root.find(f'{LIFT_NS}grammatical-info')
        assert gram_info is not None, "entry-level grammatical-info not found"
        assert gram_info.get('value') == 'Verb'
        
    @pytest.mark.integration
    def test_usage_type_persistence(self, client, basex_test_connector):
        """Test that usage-type (trait) persists correctly."""
        entry_id = generate_test_id("test_usage")
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>potoczne słowo</text></form>
            </lexical-unit>
            <sense id="sense1">
                <definition>
                    <form lang="pl"><text>Potoczna definicja</text></form>
                </definition>
                <trait name="usage-type" value="potocznie"/>
            </sense>
        </entry>'''
        
        # Save
        response = client.post(
            '/api/xml/entries',
            data=entry_xml,
            headers={'Content-Type': 'application/xml'}
        )
        assert response.status_code == 201
        entry_id = response.get_json()['entry_id']
        
        # Retrieve
        response = client.get(f'/api/xml/entries/{entry_id}?format=json')
        assert response.status_code == 200
        entry_data = response.get_json()
        
        # Check usage_type trait
        xml_root = ET.fromstring(entry_data['xml'])
        sense = xml_root.find(f'.//{LIFT_NS}sense[@id="sense1"]')
        assert sense is not None
        trait = sense.find(f'{LIFT_NS}trait[@name="usage-type"]')
        assert trait is not None, "usage-type trait not found"
        assert trait.get('value') == 'potocznie'
        
    @pytest.mark.integration
    def test_academic_domain_persistence(self, client, basex_test_connector):
        """Test that academic-domain (trait) persists correctly."""
        entry_id = generate_test_id("test_domain")
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>termin naukowy</text></form>
            </lexical-unit>
            <sense id="sense1">
                <definition>
                    <form lang="pl"><text>Naukowa definicja</text></form>
                </definition>
                <trait name="academic-domain" value="mathematics"/>
            </sense>
        </entry>'''
        
        # Save
        response = client.post(
            '/api/xml/entries',
            data=entry_xml,
            headers={'Content-Type': 'application/xml'}
        )
        assert response.status_code == 201
        entry_id = response.get_json()['entry_id']
        
        # Retrieve
        response = client.get(f'/api/xml/entries/{entry_id}?format=json')
        assert response.status_code == 200
        entry_data = response.get_json()
        
        # Check academic_domain trait
        xml_root = ET.fromstring(entry_data['xml'])
        sense = xml_root.find(f'.//{LIFT_NS}sense[@id="sense1"]')
        assert sense is not None
        trait = sense.find(f'{LIFT_NS}trait[@name="academic-domain"]')
        assert trait is not None, "academic-domain trait not found"
        assert trait.get('value') == 'mathematics'
        
    @pytest.mark.integration
    def test_semantic_domain_persistence(self, client, basex_test_connector):
        """Test that semantic-domain-ddp4 (trait) persists correctly."""
        entry_id = generate_test_id("test_semantic")
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>słowo semantyczne</text></form>
            </lexical-unit>
            <sense id="sense1">
                <definition>
                    <form lang="pl"><text>Definicja semantyczna</text></form>
                </definition>
                <trait name="semantic-domain-ddp4" value="1.1 Sky"/>
            </sense>
        </entry>'''
        
        # Save
        response = client.post(
            '/api/xml/entries',
            data=entry_xml,
            headers={'Content-Type': 'application/xml'}
        )
        assert response.status_code == 201
        entry_id = response.get_json()['entry_id']
        
        # Retrieve
        response = client.get(f'/api/xml/entries/{entry_id}?format=json')
        assert response.status_code == 200
        entry_data = response.get_json()
        
        # Check semantic_domain trait
        xml_root = ET.fromstring(entry_data['xml'])
        sense = xml_root.find(f'.//{LIFT_NS}sense[@id="sense1"]')
        assert sense is not None
        trait = sense.find(f'{LIFT_NS}trait[@name="semantic-domain-ddp4"]')
        assert trait is not None, "semantic-domain-ddp4 trait not found"
        assert trait.get('value') == '1.1 Sky'
        
    @pytest.mark.integration
    def test_etymology_persistence(self, client, basex_test_connector):
        """Test that etymology data persists correctly."""
        entry_id = generate_test_id("test_etym")
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>zapożyczone słowo</text></form>
            </lexical-unit>
            <etymology type="borrowed" source="English">
                <form lang="en"><text>borrowed word</text></form>
                <gloss lang="pl"><text>pożyczone</text></gloss>
            </etymology>
            <sense id="sense1">
                <definition>
                    <form lang="pl"><text>Definicja zapożyczenia</text></form>
                </definition>
            </sense>
        </entry>'''
        
        # Save
        response = client.post(
            '/api/xml/entries',
            data=entry_xml,
            headers={'Content-Type': 'application/xml'}
        )
        assert response.status_code == 201
        entry_id = response.get_json()['entry_id']
        
        # Retrieve
        response = client.get(f'/api/xml/entries/{entry_id}?format=json')
        assert response.status_code == 200
        entry_data = response.get_json()
        
        # Check etymology
        xml_root = ET.fromstring(entry_data['xml'])
        etym = xml_root.find(f'{LIFT_NS}etymology')
        assert etym is not None, "etymology element not found"
        assert etym.get('type') == 'borrowed'
        assert etym.get('source') == 'English'
        
    @pytest.mark.integration
    def test_pronunciation_persistence(self, client, basex_test_connector):
        """Test that pronunciation data persists correctly."""
        entry_id = generate_test_id("test_pron")
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>wymawiane słowo</text></form>
            </lexical-unit>
            <pronunciation>
                <form lang="seh-fonipa"><text>vɨmaˈvjanɛ ˈswɔvɔ</text></form>
            </pronunciation>
            <sense id="sense1">
                <definition>
                    <form lang="pl"><text>Definicja z wymową</text></form>
                </definition>
            </sense>
        </entry>'''
        
        # Save
        response = client.post(
            '/api/xml/entries',
            data=entry_xml,
            headers={'Content-Type': 'application/xml'}
        )
        assert response.status_code == 201
        entry_id = response.get_json()['entry_id']
        
        # Retrieve
        response = client.get(f'/api/xml/entries/{entry_id}?format=json')
        assert response.status_code == 200
        entry_data = response.get_json()
        
        # Check pronunciation
        xml_root = ET.fromstring(entry_data['xml'])
        pron = xml_root.find(f'{LIFT_NS}pronunciation')
        assert pron is not None, "pronunciation element not found"
        form = pron.find(f'{LIFT_NS}form[@lang="seh-fonipa"]')
        assert form is not None, "pronunciation form not found"
        text = form.find(f'{LIFT_NS}text')
        assert text is not None and text.text == 'vɨmaˈvjanɛ ˈswɔvɔ'
        
    @pytest.mark.integration
    def test_variant_persistence(self, client, basex_test_connector):
        """Test that variant forms persist correctly."""
        entry_id = generate_test_id("test_variant")
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>podstawowa forma</text></form>
            </lexical-unit>
            <variant>
                <form lang="pl"><text>wariant</text></form>
                <trait name="variant-type" value="dialectal"/>
            </variant>
            <sense id="sense1">
                <definition>
                    <form lang="pl"><text>Definicja z wariantem</text></form>
                </definition>
            </sense>
        </entry>'''
        
        # Save
        response = client.post(
            '/api/xml/entries',
            data=entry_xml,
            headers={'Content-Type': 'application/xml'}
        )
        assert response.status_code == 201
        entry_id = response.get_json()['entry_id']
        
        # Retrieve
        response = client.get(f'/api/xml/entries/{entry_id}?format=json')
        assert response.status_code == 200
        entry_data = response.get_json()
        
        # Check variant
        xml_root = ET.fromstring(entry_data['xml'])
        variant = xml_root.find(f'{LIFT_NS}variant')
        assert variant is not None, "variant element not found"
        form = variant.find(f'{LIFT_NS}form[@lang="pl"]')
        assert form is not None, "variant form not found"
        text = form.find(f'{LIFT_NS}text')
        assert text is not None and text.text == 'wariant'
        trait = variant.find(f'{LIFT_NS}trait[@name="variant-type"]')
        assert trait is not None and trait.get('value') == 'dialectal'
        
    @pytest.mark.integration
    def test_relation_persistence(self, client, basex_test_connector):
        """Test that lexical relations persist correctly."""
        entry_id = generate_test_id("test_relation")
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="pl"><text>słowo z relacją</text></form>
            </lexical-unit>
            <sense id="sense1">
                <definition>
                    <form lang="pl"><text>Definicja z relacją</text></form>
                </definition>
                <relation type="synonym" ref="other_entry">
                    <form lang="pl"><text>synonim</text></form>
                </relation>
            </sense>
        </entry>'''
        
        # Save
        response = client.post(
            '/api/xml/entries',
            data=entry_xml,
            headers={'Content-Type': 'application/xml'}
        )
        assert response.status_code == 201
        entry_id = response.get_json()['entry_id']
        
        # Retrieve
        response = client.get(f'/api/xml/entries/{entry_id}?format=json')
        assert response.status_code == 200
        entry_data = response.get_json()
        
        # Check relation
        xml_root = ET.fromstring(entry_data['xml'])
        sense = xml_root.find(f'.//{LIFT_NS}sense[@id="sense1"]')
        assert sense is not None
        relation = sense.find(f'{LIFT_NS}relation')
        assert relation is not None, "relation element not found"
        assert relation.get('type') == 'synonym'
        assert relation.get('ref') == 'other_entry'
