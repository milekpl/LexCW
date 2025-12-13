"""
Integration tests for multiple trait value serialization.

Verifies that usage_type and domain_type fields with multiple values
are correctly serialized as separate <trait> elements in LIFT XML,
preventing data loss when editing entries.
"""
from __future__ import annotations

import pytest
import xml.etree.ElementTree as ET


LIFT_NS = '{http://fieldworks.sil.org/schemas/lift/0.13}'


@pytest.mark.integration
class TestMultipleTraitSerialization:
    """Test that multiple usage_type and domain_type values are serialized correctly."""

    def test_multiple_usage_types_create_separate_traits(self, client, app):
        """Test that multiple usage_type values create separate trait elements."""
        # Create entry with multiple usage types
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="multi_usage_test" dateCreated="2025-01-01T00:00:00Z" dateModified="2025-01-01T00:00:00Z">
            <lexical-unit>
                <form lang="en"><text>formal word</text></form>
            </lexical-unit>
            <sense id="sense1" order="0">
                <gloss lang="pl"><text>formalne słowo</text></gloss>
                <trait name="usage-type" value="formal"/>
                <trait name="usage-type" value="written"/>
                <trait name="usage-type" value="academic"/>
            </sense>
        </entry>'''

        # Create the entry
        response = client.post(
            '/api/entries',
            data=xml_content,
            content_type='application/xml'
        )
        assert response.status_code in [200, 201], f"Failed to create entry: {response.data}"

        # Retrieve the entry
        response = client.get('/api/entries/multi_usage_test')
        assert response.status_code == 200

        # Parse the response XML
        root = ET.fromstring(response.data)
        
        # Find all usage-type traits in the sense
        sense = root.find(f'.//{LIFT_NS}sense[@id="sense1"]')
        assert sense is not None, "Sense not found"
        
        usage_traits = sense.findall(f'{LIFT_NS}trait[@name="usage-type"]')
        assert len(usage_traits) == 3, f"Expected 3 usage-type traits, got {len(usage_traits)}"
        
        usage_values = [trait.get('value') for trait in usage_traits]
        assert 'formal' in usage_values, "'formal' not found in usage types"
        assert 'written' in usage_values, "'written' not found in usage types"
        assert 'academic' in usage_values, "'academic' not found in usage types"

    def test_multiple_domain_types_create_separate_traits(self, client, app):
        """Test that multiple domain_type values create separate trait elements."""
        # Create entry with multiple domain types
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="multi_domain_test" dateCreated="2025-01-01T00:00:00Z" dateModified="2025-01-01T00:00:00Z">
            <lexical-unit>
                <form lang="en"><text>universe</text></form>
            </lexical-unit>
            <sense id="sense1" order="0">
                <gloss lang="pl"><text>wszechświat</text></gloss>
                <trait name="domain-type" value="astronomy"/>
                <trait name="domain-type" value="physics"/>
            </sense>
        </entry>'''

        # Create the entry
        response = client.post(
            '/api/entries',
            data=xml_content,
            content_type='application/xml'
        )
        assert response.status_code in [200, 201], f"Failed to create entry: {response.data}"

        # Retrieve the entry
        response = client.get('/api/entries/multi_domain_test')
        assert response.status_code == 200

        # Parse the response XML
        root = ET.fromstring(response.data)
        
        # Find all domain-type traits in the sense
        sense = root.find(f'.//{LIFT_NS}sense[@id="sense1"]')
        assert sense is not None, "Sense not found"
        
        domain_traits = sense.findall(f'{LIFT_NS}trait[@name="domain-type"]')
        assert len(domain_traits) == 2, f"Expected 2 domain-type traits, got {len(domain_traits)}"
        
        domain_values = [trait.get('value') for trait in domain_traits]
        assert 'astronomy' in domain_values, "'astronomy' not found in domain types"
        assert 'physics' in domain_values, "'physics' not found in domain types"

    def test_combined_multiple_usage_and_domain_types(self, client, app):
        """Test entry with both multiple usage types and domain types."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="combined_traits_test" dateCreated="2025-01-01T00:00:00Z" dateModified="2025-01-01T00:00:00Z">
            <lexical-unit>
                <form lang="en"><text>technical term</text></form>
            </lexical-unit>
            <sense id="sense1" order="0">
                <definition>
                    <form lang="en"><text>A specialized word</text></form>
                </definition>
                <trait name="usage-type" value="technical"/>
                <trait name="usage-type" value="formal"/>
                <trait name="domain-type" value="computing"/>
                <trait name="domain-type" value="engineering"/>
                <trait name="domain-type" value="science"/>
            </sense>
        </entry>'''

        # Create the entry
        response = client.post(
            '/api/entries',
            data=xml_content,
            content_type='application/xml'
        )
        assert response.status_code in [200, 201], f"Failed to create entry: {response.data}"

        # Retrieve the entry
        response = client.get('/api/entries/combined_traits_test')
        assert response.status_code == 200

        # Parse the response XML
        root = ET.fromstring(response.data)
        sense = root.find(f'.//{LIFT_NS}sense[@id="sense1"]')
        assert sense is not None, "Sense not found"
        
        # Verify usage types
        usage_traits = sense.findall(f'{LIFT_NS}trait[@name="usage-type"]')
        assert len(usage_traits) == 2, f"Expected 2 usage-type traits, got {len(usage_traits)}"
        
        # Verify domain types
        domain_traits = sense.findall(f'{LIFT_NS}trait[@name="domain-type"]')
        assert len(domain_traits) == 3, f"Expected 3 domain-type traits, got {len(domain_traits)}"

    def test_single_usage_type_still_works(self, client, app):
        """Test that single usage_type value still works correctly."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="single_usage_test" dateCreated="2025-01-01T00:00:00Z" dateModified="2025-01-01T00:00:00Z">
            <lexical-unit>
                <form lang="en"><text>slang word</text></form>
            </lexical-unit>
            <sense id="sense1" order="0">
                <gloss lang="pl"><text>slangowe słowo</text></gloss>
                <trait name="usage-type" value="informal"/>
            </sense>
        </entry>'''

        # Create the entry
        response = client.post(
            '/api/entries',
            data=xml_content,
            content_type='application/xml'
        )
        assert response.status_code in [200, 201], f"Failed to create entry: {response.data}"

        # Retrieve the entry
        response = client.get('/api/entries/single_usage_test')
        assert response.status_code == 200

        # Parse the response XML
        root = ET.fromstring(response.data)
        sense = root.find(f'.//{LIFT_NS}sense[@id="sense1"]')
        assert sense is not None, "Sense not found"
        
        usage_traits = sense.findall(f'{LIFT_NS}trait[@name="usage-type"]')
        assert len(usage_traits) == 1, f"Expected 1 usage-type trait, got {len(usage_traits)}"
        assert usage_traits[0].get('value') == 'informal'
