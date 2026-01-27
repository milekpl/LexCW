"""Unit test: ensure cached ranges are merged with DB custom ranges."""
from __future__ import annotations

import pytest


@pytest.mark.unit
def test_cached_ranges_merge_with_db_custom(client, app):
    """If a cached ranges dict exists, get_all_ranges should merge in
    any custom ranges present in the SQL DB so direct inserts are visible.
    """
    from app.services.ranges_service import RangesService
    from app.models.custom_ranges import CustomRange, CustomRangeValue, db as custom_db

    service: RangesService = app.injector.get(RangesService)

    # Ensure clean state
    try:
        custom_db.session.query(CustomRangeValue).delete()
        custom_db.session.query(CustomRange).delete()
        custom_db.session.commit()
    except Exception:
        custom_db.session.rollback()

    # Put a cached ranges state that lacks custom values
    cached = {
        'lexical-relation': {
            'id': 'lexical-relation',
            'values': [],
            'official': True,
            'label': 'Lexical Relations'
        }
    }
    service._set_cached_ranges(cached, project_id=1)

    # Insert a CustomRange and value directly into the DB
    try:
        cr = CustomRange(project_id=1, range_type='relation', range_name='lexical-relation', element_id='custom-y', element_label='Custom Y')
        custom_db.session.add(cr)
        custom_db.session.flush()
        crv = CustomRangeValue(custom_range_id=cr.id, value='custom-y', label='Custom Y')
        custom_db.session.add(crv)
        custom_db.session.commit()
    except Exception:
        custom_db.session.rollback()
        pytest.skip("CustomRanges table not available in this environment")

    # Now retrieve ranges - the cached result should be merged with the DB custom
    ranges = service.get_all_ranges(project_id=1)
    lr = ranges.get('lexical-relation')
    assert lr is not None
    found = any(v.get('id') == 'custom-y' and v.get('custom') for v in lr.get('values', []))
    assert found

    # Cleanup
    try:
        custom_db.session.query(CustomRangeValue).delete()
        custom_db.session.query(CustomRange).delete()
        custom_db.session.commit()
    except Exception:
        custom_db.session.rollback()
