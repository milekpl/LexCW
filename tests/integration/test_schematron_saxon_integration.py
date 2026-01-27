"""Integration tests for Saxon-based Schematron validation.

These tests require a real Saxon-HE jar and are skipped if SAXON_JAR isn't set.
"""
from __future__ import annotations

import os
from pathlib import Path
import pytest

from app.services.validation_engine import SchematronValidator


@pytest.mark.integration
def test_schematron_xslt2_with_saxon(tmp_path: Path):
    saxon_jar = os.getenv('SAXON_JAR')
    if not saxon_jar or not Path(saxon_jar).exists():
        pytest.skip('Saxon JAR not configured (set SAXON_JAR env var to run)')

    schema_file = tmp_path / 'schema_xslt2.sch'
    schema_file.write_text('''<?xml version="1.0"?>
<schema xmlns="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt2">
  <pattern id="p"><rule context="/"><assert test="matches(., 'foo')">R1.1 Violation</assert></rule></pattern>
</schema>''')

    # Ensure the ISO SVRL XSLT2 stylesheet is available; skip if it's not downloadable or invalid
    validator = SchematronValidator()
    xsl_path = os.getenv('SCHEMATRON_XSL', 'tools/schematron/iso_svrl_for_xslt2.xsl')
    try:
        validator._ensure_iso_svrl_xslt2(xsl_path)
    except Exception as e:
        pytest.skip(f'iso_svrl_for_xslt2.xsl not available: {e}')

    # Quick sanity check: ensure XSL parses as XML
    from lxml import etree
    try:
        etree.parse(xsl_path)
    except Exception as e:
        pytest.skip(f'iso_svrl_for_xslt2.xsl is invalid: {e}')

    validator = SchematronValidator(schema_file=str(schema_file))

    # Validator should be configured as saxon-based
    assert isinstance(validator._validator, tuple) and validator._validator[0] == 'saxon'

    # Validate XML that does NOT match 'foo' -> should produce an error
    xml = '<?xml version="1.0"?><root>bar</root>'
    result = validator.validate_xml(xml)

    assert not result.is_valid
    assert len(result.errors) > 0
