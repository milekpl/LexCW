from __future__ import annotations

import copy
import pytest

from app.services.dictionary_service import DictionaryService


def make_node(id_, label=None, abbrev=None, children=None):
    return {
        'id': id_,
        'value': id_,
        'labels': ({'en': label} if label else {}),
        'abbrev': abbrev or '',
        'abbrevs': ({'en': abbrev} if abbrev else {}),
        'children': children or [],
    }


@pytest.fixture
def dict_service():
    # Create a DictionaryService without touching BaseX by passing a mock connector
    return DictionaryService(db_connector=None)


def test_get_ranges_resolved_inherits_values(dict_service):
    # Build a fake parsed ranges structure and set it on the service
    parent = make_node('parent', label='Parent Label', abbrev='PL')
    child = make_node('child', label=None, abbrev=None)
    parent['children'] = [child]

    fake_ranges = {
        'test-range': {
            'id': 'test-range',
            'guid': 'test-range-guid',
            'values': [parent],
            'labels': {},
            'description': {}
        }
    }

    # Inject into the service cache
    dict_service.ranges = copy.deepcopy(fake_ranges)

    # Request resolved view
    resolved = dict_service.get_ranges(resolved=True)

    assert 'test-range' in resolved
    vals = resolved['test-range']['values']
    assert vals[0]['effective_label'] == 'Parent Label'
    assert vals[0]['effective_abbrev'] == 'PL'

    c = vals[0]['children'][0]
    assert c['effective_label'] == 'Parent Label'
    assert c['effective_abbrev'] == 'PL'

    # Ensure original cached ranges are not mutated
    assert 'effective_label' not in dict_service.ranges['test-range']['values'][0]
