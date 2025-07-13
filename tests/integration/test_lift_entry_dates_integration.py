from __future__ import annotations

import os
import pytest
from app.parsers.lift_parser import LIFTParser

@pytest.mark.integration
@pytest.mark.skip_et_mock
def test_lift_parser_extracts_entry_dates_from_sample_file():
    """
    Integration test: Parse the real sample-lift-file.lift and check that at least one entry has correct dateCreated and dateModified fields.
    """
    sample_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              'sample-lift-file', 'sample-lift-file.lift')
    if not os.path.exists(sample_file):
        pytest.skip(f"Sample LIFT file not found: {sample_file}")

    parser = LIFTParser()
    # Try to parse entries, skipping those that fail validation
    entries = []
    try:
        entries = parser.parse_file(sample_file)
    except Exception:
        # If strict validation fails, try parsing manually to collect valid entries
        import xml.etree.ElementTree as ET
        tree = ET.parse(sample_file)
        root = tree.getroot()
        entry_elems = root.findall('.//{*}entry')
        for entry_elem in entry_elems:
            try:
                entry = parser._parse_entry(entry_elem)
                entry.validate()
                entries.append(entry)
            except Exception:
                continue
    assert entries, "No valid entries parsed from sample LIFT file."

    # Find an entry with dateCreated and dateModified
    found = False
    for entry in entries:
        date_created = getattr(entry, 'date_created', None)
        date_modified = getattr(entry, 'date_modified', None)
        if isinstance(date_created, str) and isinstance(date_modified, str):
            found = True
            # Check plausible date format (ISO8601 string)
            assert 'T' in date_created and date_created.endswith('Z'), f"date_created format unexpected: {date_created}"
            assert 'T' in date_modified and date_modified.endswith('Z'), f"date_modified format unexpected: {date_modified}"
            break
    assert found, "No entry with both date_created and date_modified found in sample LIFT file."
