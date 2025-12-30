from __future__ import annotations

import os
import pytest
from app.parsers.lift_parser import LIFTRangesParser

# Use the skip_et_mock marker to avoid the unit test conftest auto-mocking ET
pytestmark = pytest.mark.skip_et_mock


def test_parent_based_hierarchy_parsed_correctly():
    xml = '''
    <lift-ranges>
      <range id="test-range">
        <range-element id="parent1">
          <label>
            <form lang="en"><text>Parent 1</text></form>
          </label>
        </range-element>
        <range-element id="child1" parent="parent1"/>
      </range>
    </lift-ranges>
    '''

    parser = LIFTRangesParser()
    r = parser.parse_string(xml)

    assert 'test-range' in r
    vals = r['test-range']['values']
    # Parent should be present and have child embedded in children
    parent = next((v for v in vals if v['id'] == 'parent1'), None)
    assert parent is not None
    assert 'children' in parent
    child_ids = [c['id'] for c in parent['children']]
    assert 'child1' in child_ids


def test_nested_hierarchy_parsed_correctly():
    xml = '''
    <lift-ranges>
      <range id="nested-range">
        <range-element id="p2">
          <range-element id="c2">
            <label><form lang="en"><text>Child 2</text></form></label>
          </range-element>
        </range-element>
      </range>
    </lift-ranges>
    '''

    parser = LIFTRangesParser()
    r = parser.parse_string(xml)
    vals = r['nested-range']['values']
    p = next((v for v in vals if v['id'] == 'p2'), None)
    assert p is not None
    assert 'children' in p
    assert p['children'][0]['id'] == 'c2'
    assert p['children'][0]['labels'].get('en') == 'Child 2'


def test_labels_and_abbrev_collection():
    xml = '''
    <lift-ranges>
      <range id="label-range">
        <range-element id="parentA">
          <abbrev>PA</abbrev>
          <label><form lang="en"><text>Parent A</text></form></label>
        </range-element>
        <range-element id="childA" parent="parentA"/>
      </range>
    </lift-ranges>
    '''
    parser = LIFTRangesParser()
    r = parser.parse_string(xml)
    parent = r['label-range']['values'][0]
    assert parent['abbrev'] == 'PA'
    # child has empty abbrev/labels raw (no mutation) but is present
    child = None
    for p in r['label-range']['values']:
        if p['id'] == 'parentA':
            for c in p.get('children', []):
                if c['id'] == 'childA':
                    child = c
    assert child is not None
    assert child['labels'] == {}
    assert child['abbrev'] == ''


def test_large_sample_file_has_semantic_domain():
    parser = LIFTRangesParser()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_path = os.path.join(project_root, '..', 'sample-lift-file', 'sample-lift-file.lift-ranges')
    sample_path = os.path.abspath(sample_path)
    assert os.path.exists(sample_path)

    ranges = parser.parse_file(sample_path)
    assert 'semantic-domain-ddp4' in ranges
    # Expect many values (count recursively since parent-based representation uses top-level roots)
    def count_nodes(xs):
        total = 0
        for x in xs:
            total += 1
            if x.get('children'):
                total += count_nodes(x['children'])
        return total

    total = count_nodes(ranges['semantic-domain-ddp4']['values'])
    assert total > 1000
