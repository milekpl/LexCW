"""
Unit tests for LIFT 0.13 reversal functionality.

Tests reversal structure, main element, grammatical-info, and XML serialization.
Based on LIFT 0.13 specification.
"""
from __future__ import annotations

import pytest
from lxml import etree as ET


def test_reversal_basic_structure():
    """Test basic reversal with form and type."""
    reversal_xml = '''
    <reversal type="en">
        <form lang="en"><text>cat</text></form>
    </reversal>
    '''
    
    root = ET.fromstring(reversal_xml)
    assert root.tag == 'reversal'
    assert root.get('type') == 'en'
    
    form = root.find('form[@lang="en"]')
    assert form is not None
    text = form.find('text')
    assert text is not None
    assert text.text == 'cat'


def test_reversal_with_main_element():
    """Test reversal with main sub-element."""
    reversal_xml = '''
    <reversal type="en">
        <form lang="en"><text>cat</text></form>
        <main>
            <form lang="en"><text>domestic cat</text></form>
        </main>
    </reversal>
    '''
    
    root = ET.fromstring(reversal_xml)
    main = root.find('main')
    assert main is not None
    
    form = main.find('form[@lang="en"]')
    assert form is not None
    text = form.find('text')
    assert text.text == 'domestic cat'


def test_reversal_main_with_grammatical_info():
    """Test reversal main element with grammatical-info."""
    reversal_xml = '''
    <reversal type="en">
        <form lang="en"><text>cat</text></form>
        <main>
            <form lang="en"><text>domestic cat</text></form>
            <grammatical-info value="Noun"/>
        </main>
    </reversal>
    '''
    
    root = ET.fromstring(reversal_xml)
    main = root.find('main')
    assert main is not None
    
    gram_info = main.find('grammatical-info')
    assert gram_info is not None
    assert gram_info.get('value') == 'Noun'


def test_reversal_with_grammatical_info():
    """Test reversal element with direct grammatical-info (not in main)."""
    reversal_xml = '''
    <reversal type="pl">
        <form lang="pl"><text>kot</text></form>
        <grammatical-info value="Noun"/>
    </reversal>
    '''
    
    root = ET.fromstring(reversal_xml)
    gram_info = root.find('grammatical-info')
    assert gram_info is not None
    assert gram_info.get('value') == 'Noun'


def test_multiple_reversals():
    """Test sense with multiple reversals in different languages."""
    sense_xml = '''
    <sense id="sense1">
        <definition><form lang="en"><text>a small domesticated carnivorous mammal</text></form></definition>
        <reversal type="en">
            <form lang="en"><text>cat</text></form>
        </reversal>
        <reversal type="pl">
            <form lang="pl"><text>kot</text></form>
        </reversal>
        <reversal type="fr">
            <form lang="fr"><text>chat</text></form>
        </reversal>
    </sense>
    '''
    
    root = ET.fromstring(sense_xml)
    reversals = root.findall('reversal')
    assert len(reversals) == 3
    
    types = [r.get('type') for r in reversals]
    assert 'en' in types
    assert 'pl' in types
    assert 'fr' in types


def test_reversal_multitext_forms():
    """Test reversal with multiple language forms."""
    reversal_xml = '''
    <reversal type="en">
        <form lang="en"><text>cat</text></form>
        <form lang="en-US"><text>domestic cat</text></form>
        <form lang="en-GB"><text>pussy cat</text></form>
    </reversal>
    '''
    
    root = ET.fromstring(reversal_xml)
    forms = root.findall('form')
    assert len(forms) == 3
    
    langs = [f.get('lang') for f in forms]
    assert 'en' in langs
    assert 'en-US' in langs
    assert 'en-GB' in langs


def test_reversal_nested_main():
    """Test reversal with nested main elements (recursive structure)."""
    reversal_xml = '''
    <reversal type="en">
        <form lang="en"><text>animal</text></form>
        <main>
            <form lang="en"><text>mammal</text></form>
            <main>
                <form lang="en"><text>domestic cat</text></form>
                <grammatical-info value="Noun"/>
            </main>
        </main>
    </reversal>
    '''
    
    root = ET.fromstring(reversal_xml)
    main1 = root.find('main')
    assert main1 is not None
    
    main2 = main1.find('main')
    assert main2 is not None
    
    gram_info = main2.find('grammatical-info')
    assert gram_info is not None
    assert gram_info.get('value') == 'Noun'


def test_reversal_without_type():
    """Test that reversal can exist without type attribute (optional)."""
    reversal_xml = '''
    <reversal>
        <form lang="en"><text>cat</text></form>
    </reversal>
    '''
    
    root = ET.fromstring(reversal_xml)
    assert root.tag == 'reversal'
    assert root.get('type') is None
    
    form = root.find('form[@lang="en"]')
    assert form is not None


def test_reversal_empty_main():
    """Test that main element can exist without forms (validation test)."""
    reversal_xml = '''
    <reversal type="en">
        <form lang="en"><text>cat</text></form>
        <main>
            <grammatical-info value="Noun"/>
        </main>
    </reversal>
    '''
    
    root = ET.fromstring(reversal_xml)
    main = root.find('main')
    assert main is not None
    
    # Main has no forms but has grammatical-info
    forms = main.findall('form')
    assert len(forms) == 0
    
    gram_info = main.find('grammatical-info')
    assert gram_info is not None


def test_reversal_full_structure():
    """Test complete reversal structure with all elements."""
    reversal_xml = '''
    <reversal type="en">
        <form lang="en"><text>cat</text></form>
        <form lang="en-US"><text>kitty</text></form>
        <main>
            <form lang="en"><text>domestic cat</text></form>
            <form lang="la"><text>Felis catus</text></form>
            <grammatical-info value="Countable Noun"/>
            <main>
                <form lang="en"><text>house cat</text></form>
                <grammatical-info value="Noun"/>
            </main>
        </main>
        <grammatical-info value="Noun"/>
    </reversal>
    '''
    
    root = ET.fromstring(reversal_xml)
    
    # Check reversal-level forms
    reversal_forms = [f for f in root.findall('form') if f.getparent() == root]
    assert len(reversal_forms) == 2
    
    # Check reversal-level grammatical-info
    reversal_gram = [g for g in root.findall('grammatical-info') if g.getparent() == root]
    assert len(reversal_gram) == 1
    assert reversal_gram[0].get('value') == 'Noun'
    
    # Check main element
    main = root.find('main')
    assert main is not None
    
    # Check main-level forms
    main_forms = [f for f in main.findall('form') if f.getparent() == main]
    assert len(main_forms) == 2
    
    # Check main-level grammatical-info
    main_gram = [g for g in main.findall('grammatical-info') if g.getparent() == main]
    assert len(main_gram) == 1
    assert main_gram[0].get('value') == 'Countable Noun'
    
    # Check nested main
    nested_main = main.find('main')
    assert nested_main is not None
    nested_forms = nested_main.findall('form')
    assert len(nested_forms) == 1


def test_reversal_serialization_basic():
    """Test that reversal data structure serializes correctly to XML."""
    reversal_data = {
        'type': 'en',
        'forms': [
            {'lang': 'en', 'text': 'cat'}
        ]
    }
    
    # Build XML
    reversal = ET.Element('reversal')
    if 'type' in reversal_data and reversal_data['type']:
        reversal.set('type', reversal_data['type'])
    
    for form_data in reversal_data.get('forms', []):
        form = ET.SubElement(reversal, 'form')
        form.set('lang', form_data['lang'])
        text = ET.SubElement(form, 'text')
        text.text = form_data['text']
    
    # Verify
    xml_string = ET.tostring(reversal, encoding='unicode')
    assert 'type="en"' in xml_string
    assert '<form lang="en"><text>cat</text></form>' in xml_string


def test_reversal_serialization_with_main():
    """Test that reversal with main element serializes correctly."""
    reversal_data = {
        'type': 'en',
        'forms': [
            {'lang': 'en', 'text': 'cat'}
        ],
        'main': {
            'forms': [
                {'lang': 'en', 'text': 'domestic cat'}
            ],
            'grammatical_info': 'Noun'
        }
    }
    
    # Build XML
    reversal = ET.Element('reversal')
    if 'type' in reversal_data and reversal_data['type']:
        reversal.set('type', reversal_data['type'])
    
    # Add forms
    for form_data in reversal_data.get('forms', []):
        form = ET.SubElement(reversal, 'form')
        form.set('lang', form_data['lang'])
        text = ET.SubElement(form, 'text')
        text.text = form_data['text']
    
    # Add main
    if 'main' in reversal_data:
        main = ET.SubElement(reversal, 'main')
        
        for form_data in reversal_data['main'].get('forms', []):
            form = ET.SubElement(main, 'form')
            form.set('lang', form_data['lang'])
            text = ET.SubElement(form, 'text')
            text.text = form_data['text']
        
        if 'grammatical_info' in reversal_data['main']:
            gram = ET.SubElement(main, 'grammatical-info')
            gram.set('value', reversal_data['main']['grammatical_info'])
    
    # Verify
    xml_string = ET.tostring(reversal, encoding='unicode')
    assert '<main>' in xml_string
    assert '<form lang="en"><text>domestic cat</text></form>' in xml_string
    assert '<grammatical-info value="Noun"/>' in xml_string
