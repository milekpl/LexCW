"""
Unit tests for LIFT 0.13 annotation elements (Day 26-27).

Annotations support editorial workflow with who/when/name/value attributes
and multitext content.

LIFT 0.13 Spec from docs/lift-0.13.rng:
  <define name="annotation-content">
    <ref name="multitext-content"/>
    <attribute name="name"/>
    <optional>
      <attribute name="value"/>
    </optional>
    <optional>
      <attribute name="who"/>
    </optional>
    <optional>
      <attribute name="when">
        <ref name="date.or.dateTime"/>
      </attribute>
    </optional>
  </define>
"""

import pytest
from lxml import etree as ET
from typing import Dict, Any


def test_annotation_basic_structure() -> None:
    """Test basic annotation with name and value."""
    xml_string = """
    <annotation name="review-status" value="approved">
    </annotation>
    """
    root = ET.fromstring(xml_string.strip())
    
    assert root.tag == 'annotation'
    assert root.get('name') == 'review-status'
    assert root.get('value') == 'approved'


def test_annotation_with_who_when() -> None:
    """Test annotation with who and when attributes."""
    xml_string = """
    <annotation name="review-status" value="pending" 
                who="editor@example.com" when="2024-12-01T10:00:00">
    </annotation>
    """
    root = ET.fromstring(xml_string.strip())
    
    assert root.get('who') == 'editor@example.com'
    assert root.get('when') == '2024-12-01T10:00:00'


def test_annotation_with_multitext_content() -> None:
    """Test annotation with multitext content."""
    xml_string = """
    <annotation name="comment" value="needs-revision">
        <form lang="en"><text>Please check the definition.</text></form>
        <form lang="pl"><text>Proszę sprawdzić definicję.</text></form>
    </annotation>
    """
    root = ET.fromstring(xml_string.strip())
    
    forms = root.findall('form')
    assert len(forms) == 2
    
    en_form = forms[0]
    assert en_form.get('lang') == 'en'
    assert en_form.find('text').text == 'Please check the definition.'
    
    pl_form = forms[1]
    assert pl_form.get('lang') == 'pl'
    assert pl_form.find('text').text == 'Proszę sprawdzić definicję.'


def test_annotation_without_value() -> None:
    """Test annotation without value attribute (optional)."""
    xml_string = """
    <annotation name="reviewer-comment" who="reviewer@example.com">
        <form lang="en"><text>Good entry</text></form>
    </annotation>
    """
    root = ET.fromstring(xml_string.strip())
    
    assert root.get('name') == 'reviewer-comment'
    assert root.get('value') is None
    assert root.get('who') == 'reviewer@example.com'


def test_annotation_minimal() -> None:
    """Test minimal annotation (only name attribute)."""
    xml_string = """
    <annotation name="flagged">
    </annotation>
    """
    root = ET.fromstring(xml_string.strip())
    
    assert root.get('name') == 'flagged'
    assert root.get('value') is None
    assert root.get('who') is None
    assert root.get('when') is None


def test_multiple_annotations() -> None:
    """Test multiple annotations in a parent element."""
    xml_string = """
    <sense>
        <annotation name="status" value="approved" who="editor1@example.com" when="2024-12-01">
            <form lang="en"><text>Approved for publication</text></form>
        </annotation>
        <annotation name="comment" who="editor2@example.com" when="2024-12-02">
            <form lang="en"><text>Add more examples</text></form>
        </annotation>
        <annotation name="flagged" value="priority">
        </annotation>
    </sense>
    """
    root = ET.fromstring(xml_string.strip())
    annotations = root.findall('annotation')
    
    assert len(annotations) == 3
    assert annotations[0].get('name') == 'status'
    assert annotations[1].get('name') == 'comment'
    assert annotations[2].get('name') == 'flagged'


def test_annotation_when_datetime_format() -> None:
    """Test various date/datetime formats for when attribute."""
    formats = [
        '2024-12-01',
        '2024-12-01T10:00:00',
        '2024-12-01T10:00:00Z',
        '2024-12-01T10:00:00+01:00'
    ]
    
    for date_str in formats:
        xml_string = f'<annotation name="test" when="{date_str}"></annotation>'
        root = ET.fromstring(xml_string)
        assert root.get('when') == date_str


def test_annotation_common_names() -> None:
    """Test common annotation names used in editorial workflows."""
    common_names = [
        'review-status',
        'comment',
        'reviewer-comment',
        'approval-status',
        'flagged',
        'priority',
        'needs-revision',
        'checked-by',
        'verification-status'
    ]
    
    for name in common_names:
        xml_string = f'<annotation name="{name}"></annotation>'
        root = ET.fromstring(xml_string)
        assert root.get('name') == name


def test_annotation_serialization_basic() -> None:
    """Test annotation can be serialized to dict."""
    annotation = {
        'name': 'review-status',
        'value': 'approved',
        'who': 'editor@example.com',
        'when': '2024-12-01T10:00:00'
    }
    
    # Should be JSON-serializable
    import json
    serialized = json.dumps(annotation)
    deserialized = json.loads(serialized)
    
    assert deserialized['name'] == 'review-status'
    assert deserialized['value'] == 'approved'
    assert deserialized['who'] == 'editor@example.com'
    assert deserialized['when'] == '2024-12-01T10:00:00'


def test_annotation_serialization_with_content() -> None:
    """Test annotation with multitext content can be serialized."""
    annotation = {
        'name': 'comment',
        'value': 'needs-review',
        'who': 'reviewer@example.com',
        'when': '2024-12-01',
        'content': {
            'en': 'Please add more context',
            'pl': 'Proszę dodać więcej kontekstu'
        }
    }
    
    # Should be JSON-serializable
    import json
    serialized = json.dumps(annotation)
    deserialized = json.loads(serialized)
    
    assert deserialized['content']['en'] == 'Please add more context'
    assert deserialized['content']['pl'] == 'Proszę dodać więcej kontekstu'


def test_annotation_empty_multitext() -> None:
    """Test annotation with empty multitext content."""
    xml_string = """
    <annotation name="placeholder" value="empty">
    </annotation>
    """
    root = ET.fromstring(xml_string.strip())
    
    forms = root.findall('form')
    assert len(forms) == 0


def test_annotation_full_structure() -> None:
    """Test annotation with all possible elements and attributes."""
    xml_string = """
    <annotation name="review-status" 
                value="approved" 
                who="editor@example.com" 
                when="2024-12-01T10:00:00Z">
        <form lang="en"><text>Reviewed and approved for publication</text></form>
        <form lang="pl"><text>Sprawdzone i zatwierdzone do publikacji</text></form>
        <form lang="fr"><text>Révisé et approuvé pour publication</text></form>
    </annotation>
    """
    root = ET.fromstring(xml_string.strip())
    
    # Verify all attributes
    assert root.get('name') == 'review-status'
    assert root.get('value') == 'approved'
    assert root.get('who') == 'editor@example.com'
    assert root.get('when') == '2024-12-01T10:00:00Z'
    
    # Verify multitext content
    forms = root.findall('form')
    assert len(forms) == 3
    
    languages = [form.get('lang') for form in forms]
    assert 'en' in languages
    assert 'pl' in languages
    assert 'fr' in languages
