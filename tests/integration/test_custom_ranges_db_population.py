"""Integration test: automatic population of custom ranges from LIFT data in DB."""
import tempfile
import os

from app.models.custom_ranges import CustomRange


def test_db_scan_creates_custom_ranges(dict_service_with_db, basex_test_connector):
    """When custom ranges are missing, scanning the LIFT data should create them."""
    connector = basex_test_connector

    # Ensure starting state: no custom ranges for project 1
    existing = CustomRange.query.filter_by(project_id=1).all()
    assert len(existing) == 0

    # Add a LIFT document that contains an undefined relation type
    entry_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift>
  <entry id="custom_rel_entry">
    <relation type="custom-relation" ref="other"/>
  </entry>
</lift>'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(entry_xml)
        tmp_path = f.name

    try:
        connector.execute_command(f'ADD {tmp_path}')

        # Call get_ranges which should trigger the automatic scan and create custom ranges
        ranges = dict_service_with_db.get_ranges(project_id=1)

        # Now there should be at least one CustomRange for the undefined relation
        cr = CustomRange.query.filter_by(project_id=1, element_id='custom-relation').first()
        assert cr is not None
        assert cr.range_type == 'relation'
        assert cr.element_label == 'custom-relation'

        # Also ensure ranges returned include the custom element under its parent range
        assert 'lexical-relation' in ranges
        found = any(v.get('id') == 'custom-relation' for v in ranges['lexical-relation']['values'])
        assert found

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
