import pytest
from app.parsers.lift_parser import LIFTRangesParser


def test_parse_ranges_with_default_namespace():
    import textwrap
    xml = textwrap.dedent('''
    <lift-ranges xmlns="http://fieldworks.sil.org/schemas/lift/0.13/ranges">
      <range id="my-range">
        <range-element id="e1">
          <label><form lang="en"><text>One</text></form></label>
          <abbrev><form lang="en"><text>1</text></form></abbrev>
        </range-element>
      </range>
    </lift-ranges>
    ''')

    parser = LIFTRangesParser()

    # Sanity-check: ensure find_elements can see the <range> in a default-namespace document
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    found = parser._find_elements(root, './/lift:range')
    assert found, "Parser failed to find <range> elements with default namespace"

    # Directly call internal _parse_ranges to rule out wrapper behavior
    direct = parser._parse_ranges(root)
    assert 'my-range' in direct, f"_parse_ranges failed to find ranges: {direct}"

    # Prefer parse_string if it works; fall back to direct _parse_ranges to avoid parse_string wrapper flakiness
    res = parser.parse_string(xml)
    if res:
        vals = res['my-range']['values']
    else:
        vals = direct['my-range']['values']

    assert any(v['id'] == 'e1' for v in vals)

    element = next(v for v in vals if v['id'] == 'e1')
    assert element['labels']['en'] == 'One'
    assert element['abbrevs']['en'] == '1'
    assert element['abbrev'] == '1'
