"""
Integration tests for form field persistence - ensuring all form fields are saved and retrieved correctly.

This test suite systematically verifies that every field in the entry form (including ranges)
is properly saved to BaseX and can be retrieved correctly.
"""

from __future__ import annotations

import pytest
import uuid
from lxml import etree as ET


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
        response = client.get(f'/api/xml/entries/{entry_id}')
        print(f"GET response status: {response.status_code}")
        print(f"GET response data: {response.data}")
        assert response.status_code == 200
        data = response.get_json()
        print(f"GET response JSON: {data}")
        assert data is not None, "Response JSON is None"
        assert data['success'] is True
        
        # Check grammatical_info persisted
        entry_data = data['entry']
        assert 'senses' in entry_data
        assert len(entry_data['senses']) == 1
        sense = entry_data['senses'][0]
        assert 'grammatical_info' in sense
        assert sense['grammatical_info'] == 'Countable Noun'
        
    @pytest.mark.integration
    def test_entry_level_grammatical_info_persistence(self, client, basex_test_connector):
        """Test that entry-level grammatical_info persists correctly."""
        entry_xml = '''<entry id="test_entry_pos_456">
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
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        entry_data = response.get_json()['entry']
        
        # Check entry-level grammatical_info
        assert 'grammatical_info' in entry_data
        assert entry_data['grammatical_info'] == 'Verb'
        
    @pytest.mark.integration
    def test_usage_type_persistence(self, client, basex_test_connector):
        """Test that usage-type (trait) persists correctly."""
        entry_xml = '''<entry id="test_usage_789">
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
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        entry_data = response.get_json()['entry']
        
        # Check usage_type
        sense = entry_data['senses'][0]
        assert 'usage_type' in sense
        # usage_type is stored as a list
        assert isinstance(sense['usage_type'], list)
        assert 'potocznie' in sense['usage_type']
        
    @pytest.mark.integration
    def test_academic_domain_persistence(self, client, basex_test_connector):
        """Test that academic-domain (trait) persists correctly."""
        entry_xml = '''<entry id="test_domain_abc">
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
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        entry_data = response.get_json()['entry']
        
        # Check academic_domain
        sense = entry_data['senses'][0]
        assert 'academic_domain' in sense
        assert sense['academic_domain'] == 'mathematics'
        
    @pytest.mark.integration
    def test_semantic_domain_persistence(self, client, basex_test_connector):
        """Test that semantic-domain-ddp4 (trait) persists correctly."""
        entry_xml = '''<entry id="test_semantic_def">
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
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        entry_data = response.get_json()['entry']
        
        # Check domain_type (semantic domain)
        sense = entry_data['senses'][0]
        assert 'domain_type' in sense
        # domain_type is stored as a list
        assert isinstance(sense['domain_type'], list)
        assert '1.1 Sky' in sense['domain_type']
        
    @pytest.mark.integration
    def test_etymology_persistence(self, client, basex_test_connector):
        """Test that etymology data persists correctly."""
        entry_xml = '''<entry id="test_etym_ghi">
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
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        entry_data = response.get_json()['entry']
        
        # Check etymology
        assert 'etymology' in entry_data
        assert len(entry_data['etymology']) > 0
        etym = entry_data['etymology'][0]
        assert etym['type'] == 'borrowed'
        assert etym['source'] == 'English'
        
    @pytest.mark.integration
    def test_pronunciation_persistence(self, client, basex_test_connector):
        """Test that pronunciation data persists correctly."""
        entry_xml = '''<entry id="test_pron_jkl">
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
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        entry_data = response.get_json()['entry']
        
        # Check pronunciation
        assert 'pronunciations' in entry_data
        assert 'seh-fonipa' in entry_data['pronunciations']
        assert entry_data['pronunciations']['seh-fonipa'] == 'vɨmaˈvjanɛ ˈswɔvɔ'
        
    @pytest.mark.integration
    def test_variant_persistence(self, client, basex_test_connector):
        """Test that variant forms persist correctly."""
        entry_xml = '''<entry id="test_variant_mno">
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
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        entry_data = response.get_json()['entry']
        
        # Check variant
        assert 'variants' in entry_data
        assert len(entry_data['variants']) > 0
        variant = entry_data['variants'][0]
        assert variant['text']['pl'] == 'wariant'
        assert variant['type'] == 'dialectal'
        
    @pytest.mark.integration
    def test_relation_persistence(self, client, basex_test_connector):
        """Test that lexical relations persist correctly."""
        entry_xml = '''<entry id="test_relation_pqr">
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
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        entry_data = response.get_json()['entry']
        
        # Check relation
        sense = entry_data['senses'][0]
        assert 'relations' in sense
        assert len(sense['relations']) > 0
        relation = sense['relations'][0]
        assert relation['type'] == 'synonym'
        assert relation['ref'] == 'other_entry'
