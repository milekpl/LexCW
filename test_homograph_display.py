#!/usr/bin/env python3
"""
Test script to verify homograph number display functionality.
"""

from __future__ import annotations

import sys
import os

# Add the app to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.entry import Entry
from app.parsers.lift_parser import LIFTParser


def test_homograph_model_and_api():
    """Test that homograph numbers work in model and API context."""
    app = create_app()
    with app.app_context():
        # Test Entry model with homograph number
        entry = Entry(
            id_="bank_1",
            lexical_unit={"en": "bank"},
            homograph_number=2
        )
        
        # Test that homograph_number is accessible
        assert entry.homograph_number == 2
        print(f"✅ Entry homograph_number: {entry.homograph_number}")
        
        # Test that to_dict() includes homograph_number
        entry_dict = entry.to_dict()
        assert 'homograph_number' in entry_dict
        assert entry_dict['homograph_number'] == 2
        print(f"✅ Entry to_dict() includes homograph_number: {entry_dict['homograph_number']}")
        
        return True


def test_homograph_lift_parsing():
    """Test that LIFT parser handles homograph numbers correctly."""
    # Test LIFT XML with homograph number
    lift_xml = '''
    <entry id="bank_1" homograph-number="2" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
        <lexical-unit>
            <form lang="en"><text>bank</text></form>
        </lexical-unit>
    </entry>
    '''
    
    parser = LIFTParser(validate=False)
    entry = parser.parse_entry(lift_xml.strip())
    
    assert entry.homograph_number == 2
    print(f"✅ LIFT parser correctly parsed homograph number: {entry.homograph_number}")
    
    # Test LIFT generation includes homograph number
    generated_xml = parser.generate_lift_string([entry])
    assert 'homograph-number="2"' in generated_xml
    print("✅ LIFT generation includes homograph number")
    
    return True


def test_homograph_ui_rendering():
    """Test template rendering with homograph numbers."""
    from jinja2 import Template
    
    # Test entry title with homograph number
    template_content = '''{% if entry.lexical_unit is mapping %}{{ entry.lexical_unit.values()|join(', ') }}{% else %}{{ entry.lexical_unit }}{% endif %}{% if entry.homograph_number %}<sub>{{ entry.homograph_number }}</sub>{% endif %}'''
    
    template = Template(template_content)
    
    # Test entry with homograph number
    entry = Entry(
        id_="bank_1",
        lexical_unit={"en": "bank"},
        homograph_number=2
    )
    
    rendered = template.render(entry=entry).strip()
    assert rendered == "bank<sub>2</sub>"
    print(f"✅ Template rendering with homograph number: {rendered}")
    
    # Test entry without homograph number
    entry_no_homograph = Entry(
        id_="river_1",
        lexical_unit={"en": "river"}
    )
    
    rendered_no_homograph = template.render(entry=entry_no_homograph).strip()
    assert rendered_no_homograph == "river"
    print(f"✅ Template rendering without homograph number: {rendered_no_homograph}")
    
    return True


if __name__ == '__main__':
    print("Testing homograph number display functionality...")
    
    try:
        test_homograph_model_and_api()
        test_homograph_lift_parsing()
        test_homograph_ui_rendering()
        print("\n✅ All homograph display tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
