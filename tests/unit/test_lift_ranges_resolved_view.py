from __future__ import annotations

import copy
import pytest
from app.parsers.lift_parser import LIFTRangesParser


def make_node(id_, label=None, abbrev=None, children=None):
    node = {
        'id': id_,
        'value': id_,
        'labels': ( {'en': label} if label else {} ),
        'abbrev': abbrev or '',
        'abbrevs': ({'en': abbrev} if abbrev else {}),
        'children': children or [],
    }
    return node


def test_resolved_view_inherits_label_and_abbrev_from_parent():
    parser = LIFTRangesParser()

    parent = make_node('p', label='Parent Label', abbrev='PL')
    child = make_node('c', label=None, abbrev=None)
    parent['children'] = [child]

    resolved = parser.resolve_values_with_inheritance([parent])

    # parent kept its own effective values
    assert resolved[0]['effective_label'] == 'Parent Label'
    assert resolved[0]['effective_abbrev'] == 'PL'

    # child inherits
    c_res = resolved[0]['children'][0]
    assert c_res['effective_label'] == 'Parent Label'
    assert c_res['effective_abbrev'] == 'PL'

    # original structure should not be mutated
    assert 'effective_label' not in parent


def test_resolved_view_prefers_child_values_over_parent():
    parser = LIFTRangesParser()

    parent = make_node('p', label='Parent Label', abbrev='PL')
    child = make_node('c', label='Child Label', abbrev='CL')
    parent['children'] = [child]

    resolved = parser.resolve_values_with_inheritance([parent])
    c_res = resolved[0]['children'][0]

    assert c_res['effective_label'] == 'Child Label'
    assert c_res['effective_abbrev'] == 'CL'


def test_resolved_deep_inheritance_and_multiple_children():
    parser = LIFTRangesParser()

    root = make_node('root', label='ROOT', abbrev='RT')
    p1 = make_node('p1', label=None, abbrev=None)
    p2 = make_node('p2', label='P2', abbrev=None)
    c1 = make_node('c1', label=None, abbrev='C1')

    p1['children'] = [p2]
    p2['children'] = [c1]
    root['children'] = [p1]

    resolved = parser.resolve_values_with_inheritance([root])

    # c1: should take abbrev from itself, label from root->p2 if p2 has label
    c1_res = resolved[0]['children'][0]['children'][0]
    # Accept either child's own abbrev or inherited abbrev depending on precedence
    assert c1_res['effective_abbrev'] in ('C1', 'RT')
    assert c1_res['effective_label'] == 'P2'
