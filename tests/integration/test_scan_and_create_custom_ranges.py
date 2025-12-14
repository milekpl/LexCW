"""Integration test for automatic scanning and creation of custom ranges."""

from app.models.custom_ranges import CustomRange, CustomRangeValue


def test_scan_and_create_custom_ranges_creates_trait_values(dict_service_with_db, basex_test_connector):
    # Add a LIFT entry that contains an undefined trait value
    connector = basex_test_connector

    entry_xml = '''<?xml version="1.0" encoding="utf-8"?>
<lift>
  <entry id="scan_test">
    <lexical-unit>
      <form lang="en"><text>scan</text></form>
    </lexical-unit>
    <relation type="_component-lexeme" ref="other" />
    <trait name="custom-trait" value="custom-value" />
  </entry>
</lift>'''

    # Add to DB
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(entry_xml)
        tmp_path = f.name

    try:
        connector.execute_command(f'ADD {tmp_path}')

        # Ensure no custom range exists initially
        pre = CustomRange.query.filter_by(project_id=1, element_id='custom-trait').first()
        if pre:
            # cleanup if existing (shouldn't normally be present)
            from app.models.custom_ranges import db
            db.session.delete(pre)
            db.session.commit()

        # Run the scan
        dict_service_with_db.scan_and_create_custom_ranges(project_id=1)

        cr = CustomRange.query.filter_by(project_id=1, element_id='custom-trait').first()
        assert cr is not None

        # Check values include 'custom-value'
        val = CustomRangeValue.query.filter_by(custom_range_id=cr.id, value='custom-value').first()
        assert val is not None

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def test_ranges_editor_returns_custom_range(client, dict_service_with_db, basex_test_connector):
    # Ensure a scan runs and then call the ranges-editor API
    dict_service_with_db.scan_and_create_custom_ranges(project_id=1)

    rv = client.get('/api/ranges-editor/custom')
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'data' in data
    # Should return a list (may be empty, but after scan should include at least our custom-trait if present)
    assert isinstance(data['data'], list)
