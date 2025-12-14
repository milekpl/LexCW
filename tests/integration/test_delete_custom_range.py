"""Integration test for deleting a custom range that exists only in SQL."""
from __future__ import annotations

import pytest
from app.models.custom_ranges import CustomRange
from app.services.ranges_service import RangesService


@pytest.mark.integration
def test_delete_custom_range_removes_db_rows(client, app):
    service: RangesService = client.application.injector.get(RangesService)

    # Create a DB-only custom range
    cr = CustomRange(
        project_id=1,
        range_type='trait',
        range_name='weird_range',
        element_id='dt-1',
        element_label='Weird range'
    )
    from app.models.custom_ranges import db as custom_db
    custom_db.session.add(cr)
    custom_db.session.commit()

    # Ensure it shows up in ranges
    ranges = service.get_all_ranges()
    assert 'weird_range' in ranges

    # Delete via API
    resp = client.delete('/api/ranges-editor/weird_range')
    assert resp.status_code == 200

    # Ensure DB rows removed
    remaining = CustomRange.query.filter_by(range_name='weird_range').all()
    assert len(remaining) == 0

    # And range no longer present in get_all_ranges
    ranges2 = service.get_all_ranges()
    assert 'weird_range' not in ranges2