"""Unit tests for Saxon-based Schematron support.

These tests are fast and do not require a real Saxon JAR; they verify
fallback behavior and download helper logic.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from app.services.validation_engine import SchematronValidator


def _write_minimal_xslt2_schema(path: Path) -> None:
    path.write_text(
        '''<?xml version="1.0"?>
<schema xmlns="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt2">
  <pattern id="p">
    <rule context="/">
      <assert test="matches('abc','a')">R1.1.1 Violation</assert>
    </rule>
  </pattern>
</schema>'''
    )


def test_xslt2_schema_without_saxon_sets_reason(tmp_path: Path, monkeypatch: Any) -> None:
    # Ensure environment has no SAXON_JAR
    monkeypatch.delenv('SAXON_JAR', raising=False)

    schema_file = tmp_path / 'schema_xslt2.sch'
    schema_file.write_text('''<?xml version="1.0"?>
<schema xmlns="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt2">
  <pattern id="p"><rule context="/"><assert test="matches('x','x')">R1.1 Violation</assert></rule></pattern>
</schema>''')

    validator = SchematronValidator(schema_file=str(schema_file))

    assert validator._validator is None
    assert getattr(validator, '_xslt2_reason', '') == 'xslt2_required_no_saxon'


def test_ensure_iso_xslt2_download(monkeypatch: Any, tmp_path: Path) -> None:
    # Simulate urlretrieve by creating the target file
    target = tmp_path / 'iso_svrl_for_xslt2.xsl'

    def fake_urlretrieve(url, filename):
        Path(filename).write_text('<!-- fake iso svrl xsl -->')
        return (filename, None)

    monkeypatch.setattr('urllib.request.urlretrieve', fake_urlretrieve)

    # Call the helper via SchematronValidator instance
    validator = SchematronValidator()
    validator._ensure_iso_svrl_xslt2(str(target))

    assert target.exists()
    assert '<!-- fake iso svrl xsl -->' in target.read_text()


def test_xslt2_schema_with_saxon_and_xmlresolver(monkeypatch: Any, tmp_path: Path) -> None:
    # Create fake Saxon and xmlresolver JAR files
    tools_dir = tmp_path / 'tools' / 'saxon'
    tools_dir.mkdir(parents=True)
    saxon_jar = tools_dir / 'saxon-he.jar'
    xmlresolver_jar = tools_dir / 'xmlresolver.jar'
    saxon_jar.write_text('fake')
    xmlresolver_jar.write_text('fake')

    monkeypatch.setenv('SAXON_JAR', str(saxon_jar))
    monkeypatch.setenv('XMLRESOLVER_JAR', str(xmlresolver_jar))

    # Write a minimal xslt2 schema
    schema_file = tmp_path / 'schema_xslt2.sch'
    _write_minimal_xslt2_schema(schema_file)

    # Ensure iso_svrl xslt2 XSL is available by faking urlretrieve
    def fake_urlretrieve(url, filename):
        Path(filename).write_text('<!-- fake iso svrl xsl -->')
        return (filename, None)

    monkeypatch.setattr('urllib.request.urlretrieve', fake_urlretrieve)

    # Fake subprocess.run to simulate successful compilation
    def fake_run(cmd, check=True, timeout=None):
        # Find -o:output entry and create the compiled xsl
        for part in cmd:
            if isinstance(part, str) and part.startswith('-o:'):
                out = part.split(':', 1)[1]
                Path(out).parent.mkdir(parents=True, exist_ok=True)
                Path(out).write_text('<!-- compiled xsl -->')
                break
        return None

    # Patch subprocess.run globally since validation_engine imports it dynamically
    monkeypatch.setattr('subprocess.run', fake_run)

    validator = SchematronValidator(schema_file=str(schema_file))

    assert isinstance(validator._validator, tuple)
    assert validator._validator[0] == 'saxon'
    # Ensure compiled xsl was created
    compiled_xsl_path = validator._validator[1]
    assert Path(compiled_xsl_path).exists()
    assert getattr(validator, '_saxon_jar') == str(saxon_jar)
    assert getattr(validator, '_xmlresolver_jar') == str(xmlresolver_jar)
