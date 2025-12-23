"""
Integration tests for LIFT allomorph and header support implementation.
Tests the full flow: parsing LIFT with direct traits -> storing -> retrieving -> serializing.
"""
import pytest
import tempfile
import os
from xml.etree import ElementTree as ET

from app.models.entry import Entry, Variant
from app.parsers.lift_parser import LIFTParser
from app.utils.multilingual_form_processor import process_variant_forms_data, merge_form_data_with_entry_data


def test_parse_variant_with_direct_traits():
    """Test parsing LIFT variant elements with direct trait elements."""
    parser = LIFTParser(validate=False)  # Disable validation for testing

    lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" producer="slownik-wielki">
  <entry id="test-entry-1">
    <lexical-unit>
      <form lang="en">
        <text>grass</text>
      </form>
    </lexical-unit>
    <sense id="s1">
      <gloss lang="en"><text>grass sense</text></gloss>
    </sense>
    <variant>
      <form lang="en">
        <text>grass roots</text>
      </form>
      <trait name="morph-type" value="stem"/>
    </variant>
  </entry>
</lift>'''

    entries = parser.parse_string(lift_xml)
    assert len(entries) == 1
    entry = entries[0]

    assert len(entry.variants) == 1
    variant = entry.variants[0]

    # Check that the variant form was parsed
    assert 'en' in variant.form
    assert variant.form['en'] == 'grass roots'

    # Check that the direct trait was parsed
    assert hasattr(variant, 'traits')
    assert variant.traits is not None
    assert 'morph-type' in variant.traits
    assert variant.traits['morph-type'] == 'stem'


def test_parse_variant_with_both_direct_and_grammatical_traits():
    """Test parsing LIFT variant with both direct traits and grammatical traits."""
    parser = LIFTParser(validate=False)  # Disable validation for testing

    lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" producer="slownik-wielki">
  <entry id="test-entry-2">
    <lexical-unit>
      <form lang="en">
        <text>word</text>
      </form>
    </lexical-unit>
    <sense id="s1">
      <gloss lang="en"><text>word sense</text></gloss>
    </sense>
    <variant>
      <form lang="en">
        <text>variant form</text>
      </form>
      <trait name="morph-type" value="stem"/>
      <trait name="usage" value="informal"/>
      <grammatical-info value="noun">
        <trait name="number" value="plural"/>
        <trait name="case" value="accusative"/>
      </grammatical-info>
    </variant>
  </entry>
</lift>'''

    entries = parser.parse_string(lift_xml)
    assert len(entries) == 1
    entry = entries[0]

    assert len(entry.variants) == 1
    variant = entry.variants[0]

    # Check form
    assert variant.form['en'] == 'variant form'

    # Check direct traits
    assert variant.traits is not None
    assert 'morph-type' in variant.traits
    assert variant.traits['morph-type'] == 'stem'
    assert 'usage' in variant.traits
    assert variant.traits['usage'] == 'informal'

    # Check grammatical traits
    assert variant.grammatical_info == 'noun'
    assert variant.grammatical_traits is not None
    assert 'number' in variant.grammatical_traits
    assert variant.grammatical_traits['number'] == 'plural'
    assert 'case' in variant.grammatical_traits
    assert variant.grammatical_traits['case'] == 'accusative'


def test_serialize_variant_with_direct_traits():
    """Test serializing entries with variants that have direct traits."""
    parser = LIFTParser(validate=False)  # Disable validation for testing

    # Create an entry with a variant that has direct traits
    variant = Variant(form={'en': 'grass roots'})
    variant.traits = {'morph-type': 'stem', 'usage': 'figurative'}

    entry = Entry(
        id_='test-entry-3',
        lexical_unit={'en': 'grass'},
        variants=[variant]
    )
    # Add a sense to make the entry valid
    from app.models.sense import Sense
    entry.senses = [Sense(id_='s1', glosses={'en': 'test gloss'})]

    # Serialize the entry
    xml_string = parser.generate_lift_string([entry])

    # Parse it back to verify it can be round-tripped
    entries = parser.parse_string(xml_string)
    assert len(entries) == 1
    parsed_entry = entries[0]

    assert len(parsed_entry.variants) == 1
    parsed_variant = parsed_entry.variants[0]

    # Verify the form and traits are preserved
    assert parsed_variant.form['en'] == 'grass roots'
    assert parsed_variant.traits is not None
    assert parsed_variant.traits['morph-type'] == 'stem'
    assert parsed_variant.traits['usage'] == 'figurative'


def test_parse_lift_header_information():
    """Test parsing LIFT header information."""
    parser = LIFTParser(validate=False)  # Disable validation for testing

    lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" producer="slownik-wielki">
  <header>
    <description lang="en"><text>Test dictionary</text></description>
    <description lang="pl"><text>Słownik testowy</text></description>
    <ranges href="ranges.xml"/>
    <fields>
      <field type="literal-meaning"/>
      <field type="scientific-name"/>
    </fields>
  </header>
  <entry id="test-entry-4">
    <lexical-unit>
      <form lang="en">
        <text>test</text>
      </form>
    </lexical-unit>
    <sense id="s1">
      <gloss lang="en"><text>test gloss</text></gloss>
    </sense>
  </entry>
</lift>'''

    entries = parser.parse_string(lift_xml)
    assert len(entries) == 1
    entry = entries[0]

    # Check that header info was parsed and stored
    assert hasattr(entry, 'header_info')
    assert entry.header_info is not None

    header = entry.header_info
    assert 'description' in header
    assert header['description']['en'] == 'Test dictionary'
    assert header['description']['pl'] == 'Słownik testowy'

    assert 'ranges_href' in header
    assert header['ranges_href'] == 'ranges.xml'

    assert 'fields' in header
    assert len(header['fields']) == 2
    assert header['fields'][0]['type'] == 'literal-meaning'
    assert header['fields'][1]['type'] == 'scientific-name'


def test_serialize_lift_with_header():
    """Test serializing LIFT with header information."""
    parser = LIFTParser(validate=False)  # Disable validation for testing

    # Create an entry with header info
    entry = Entry(
        id_='test-entry-5',
        lexical_unit={'en': 'test'},
        header_info={
            'description': {'en': 'Test dictionary', 'pl': 'Słownik testowy'},
            'ranges_href': 'ranges.xml',
            'fields': [
                {'type': 'literal-meaning'},
                {'type': 'scientific-name'}
            ]
        }
    )
    # Add a sense to make the entry valid
    from app.models.sense import Sense
    entry.senses = [Sense(id_='s1', glosses={'en': 'test gloss'})]

    # Serialize the entry
    xml_string = parser.generate_lift_string([entry])

    # Parse it back to verify it can be round-tripped
    entries = parser.parse_string(xml_string)
    assert len(entries) == 1
    parsed_entry = entries[0]

    # Verify header info is preserved
    assert parsed_entry.header_info is not None
    header = parsed_entry.header_info

    assert header['description']['en'] == 'Test dictionary'
    assert header['description']['pl'] == 'Słownik testowy'
    assert header['ranges_href'] == 'ranges.xml'
    assert len(header['fields']) == 2


def test_form_processing_for_direct_variants():
    """Test form processing for direct variant forms with traits."""
    # Simulate form data for direct variants
    form_data = {
        'variants[0].form.en': 'grass roots',
        'variants[0].traits.morph-type': 'stem',
        'variants[0].traits.usage': 'figurative',
        'variants[0].grammatical_info': 'noun',
        'variants[0].grammatical_traits.number': 'plural',
        'variants[1].form.en': 'alternative form',
        'variants[1].traits.morph-type': 'variant'
    }
    
    variant_forms = process_variant_forms_data(form_data)
    
    assert len(variant_forms) == 2
    
    # First variant
    first_variant = variant_forms[0]
    assert first_variant['form']['en'] == 'grass roots'
    assert first_variant['traits']['morph-type'] == 'stem'
    assert first_variant['traits']['usage'] == 'figurative'
    assert first_variant['grammatical_info'] == 'noun'
    assert first_variant['grammatical_traits']['number'] == 'plural'
    
    # Second variant
    second_variant = variant_forms[1]
    assert second_variant['form']['en'] == 'alternative form'
    assert second_variant['traits']['morph-type'] == 'variant'


def test_merge_form_data_with_direct_variants():
    """Test merging form data that includes direct variant forms."""
    # Start with existing entry data that has variants
    existing_data = {
        'id': 'test-entry-6',
        'lexical_unit': {'en': 'existing'},
        'variants': [
            {
                'form': {'en': 'existing form'},
                'traits': {'morph-type': 'existing-type'}
            }
        ]
    }
    
    # Form data with additional direct variants
    form_data = {
        'lexical_unit[en]': 'updated',
        'variants[0].form.en': 'new form',
        'variants[0].traits.morph-type': 'stem',
        'variants[0].traits.usage': 'new'
    }
    
    merged_data = merge_form_data_with_entry_data(form_data, existing_data)
    
    # Should have both the existing and new variants
    assert merged_data['lexical_unit']['en'] == 'updated'
    assert len(merged_data['variants']) >= 1  # May have both existing and new
    
    # Check if the new variant from form data was added
    new_variant_found = False
    for variant in merged_data['variants']:
        if variant.get('form', {}).get('en') == 'new form':
            new_variant_found = True
            assert variant['traits']['morph-type'] == 'stem'
            assert variant['traits']['usage'] == 'new'
            break
    
    assert new_variant_found, "New variant from form data should be present"


def test_roundtrip_allomorph_parsing_and_serialization():
    """Test full round-trip: parse -> serialize -> parse again."""
    parser = LIFTParser(validate=False)  # Disable validation for testing

    original_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" producer="slownik-wielki">
  <header>
    <description lang="en"><text>Round-trip test</text></description>
  </header>
  <entry id="roundtrip-test">
    <lexical-unit>
      <form lang="en">
        <text>word</text>
      </form>
    </lexical-unit>
    <sense id="s1">
      <gloss lang="en"><text>word sense</text></gloss>
    </sense>
    <variant>
      <form lang="en">
        <text>allomorph form</text>
      </form>
      <trait name="morph-type" value="stem"/>
      <trait name="usage" value="formal"/>
    </variant>
  </entry>
</lift>'''

    # Parse the original XML
    entries = parser.parse_string(original_xml)
    assert len(entries) == 1

    # Serialize back to XML
    serialized_xml = parser.generate_lift_string(entries)

    # Parse the serialized XML again
    reparsed_entries = parser.parse_string(serialized_xml)
    assert len(reparsed_entries) == 1

    # Verify the data is preserved
    entry = reparsed_entries[0]
    assert entry.lexical_unit['en'] == 'word'
    assert len(entry.variants) == 1

    variant = entry.variants[0]
    assert variant.form['en'] == 'allomorph form'
    assert variant.traits is not None
    assert variant.traits['morph-type'] == 'stem'
    assert variant.traits['usage'] == 'formal'

    # Check header info is preserved
    assert entry.header_info is not None
    assert entry.header_info['description']['en'] == 'Round-trip test'


if __name__ == '__main__':
    # Run the tests
    test_parse_variant_with_direct_traits()
    print("✓ test_parse_variant_with_direct_traits passed")
    
    test_parse_variant_with_both_direct_and_grammatical_traits()
    print("✓ test_parse_variant_with_both_direct_and_grammatical_traits passed")
    
    test_serialize_variant_with_direct_traits()
    print("✓ test_serialize_variant_with_direct_traits passed")
    
    test_parse_lift_header_information()
    print("✓ test_parse_lift_header_information passed")
    
    test_serialize_lift_with_header()
    print("✓ test_serialize_lift_with_header passed")
    
    test_form_processing_for_direct_variants()
    print("✓ test_form_processing_for_direct_variants passed")
    
    test_merge_form_data_with_direct_variants()
    print("✓ test_merge_form_data_with_direct_variants passed")
    
    test_roundtrip_allomorph_parsing_and_serialization()
    print("✓ test_roundtrip_allomorph_parsing_and_serialization passed")
    
    print("\nAll tests passed! ✓")