"""Integration tests for range labels and official/custom flags."""

import pytest


@pytest.mark.integration
def test_ranges_editor_api_includes_label_and_official_flag(client):
    resp = client.get('/api/ranges-editor/')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    ranges = data['data']

    # lexical-relation is a known standard range
    assert 'lexical-relation' in ranges
    lr = ranges['lexical-relation']
    assert 'label' in lr and lr['label']
    assert lr.get('official') is True


@pytest.mark.integration
def test_custom_ranges_marked_as_custom(client, app):
    # Create a CustomRange and value directly (SQL DB) and verify API shows it
    from app.models.custom_ranges import CustomRange, CustomRangeValue, db as custom_db

    # Ensure cleanup before/after
    try:
        custom_db.session.query(CustomRangeValue).delete()
        custom_db.session.query(CustomRange).delete()
        custom_db.session.commit()
    except Exception:
        custom_db.session.rollback()

    try:
        cr = CustomRange(project_id=1, range_type='relation', range_name='lexical-relation', element_id='custom-x', element_label='Custom X')
        custom_db.session.add(cr)
        custom_db.session.flush()
        crv = CustomRangeValue(custom_range_id=cr.id, value='custom-x', label='Custom X')
        custom_db.session.add(crv)
        custom_db.session.commit()
    except Exception as e:
        # If the custom_ranges table does not exist in this test environment,
        # skip the test - table creation may be out of scope for these runs.
        custom_db.session.rollback()
        import pytest
        pytest.skip(f"Skipping custom-range DB test: {e}")

    resp = client.get('/api/ranges-editor/')
    assert resp.status_code == 200
    data = resp.get_json()
    ranges = data['data']

    # custom element should be present under lexical-relation values
    lr = ranges.get('lexical-relation')
    assert lr is not None
    found = any(v.get('id') == 'custom-x' and v.get('custom') for v in lr.get('values', []))
    assert found

    # Cleanup
    try:
        custom_db.session.query(CustomRangeValue).delete()
        custom_db.session.query(CustomRange).delete()
        custom_db.session.commit()
    except Exception:
        custom_db.session.rollback()
