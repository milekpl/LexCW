"""
PyTest fixtures for XML roundtrip testing.

This module provides fixtures for testing XML parsing, normalization,
and roundtrip functionality for LIFT format files.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Generator, Optional

import pytest
from typing import Generator

logger = logging.getLogger(__name__)


# ============================================================================
# Pytest Configuration Hook
# ============================================================================

def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for xml_roundtrip tests."""
    config.addinivalue_line(
        "markers", "xml_roundtrip: mark test as XML roundtrip test"
    )


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def lift_parser() -> Generator[Any, None, None]:
    """Return a LIFTParser instance from app.parsers.lift_parser."""
    from app.parsers.lift_parser import LIFTParser

    parser = LIFTParser(validate=True)
    yield parser


@pytest.fixture
def xml_normalizer() -> Generator[Any, None, None]:
    """Return the xml_normalizer module from this directory.

    This fixture attempts to import xml_normalizer from the test_xml_roundtrip
    package. If the module doesn't exist yet, it returns None with a skip.
    """
    try:
        from app.services.word_sketch import xml_normalizer as normalizer_module
        yield normalizer_module
    except ImportError:
        pytest.skip("xml_normalizer module not found in app.services.word_sketch")


@pytest.fixture
def patterns_json_path() -> Generator[str, None, None]:
    """Return the path to fixtures/patterns.json."""
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    patterns_path = os.path.join(fixtures_dir, 'patterns.json')
    yield patterns_path


@pytest.fixture
def extracted_patterns(patterns_json_path: str) -> Generator[dict, None, None]:
    """Load and return patterns from fixtures/patterns.json.

    Uses pytest.importorskip if the patterns.json file is missing.
    """
    if not os.path.exists(patterns_json_path):
        pytest.skip(
            f"patterns.json not found at {patterns_json_path}. "
            "This fixture is required for pattern-based tests."
        )

    try:
        with open(patterns_json_path, 'r', encoding='utf-8') as f:
            patterns = json.load(f)
        yield patterns
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in patterns.json: {e}")


@pytest.fixture
def basex_client() -> Generator[Optional[Any], None, None]:
    """Return a connection to BaseX using app.database.basex_connector.

    This fixture is optional - it skips if BaseX is unavailable.
    """
    try:
        from app.database.basex_connector import BaseXConnector
    except ImportError:
        pytest.skip("BaseXConnector not available")

    # Check if BaseXClient is available
    try:
        from BaseXClient.BaseXClient import Session as BaseXSession
    except ImportError:
        pytest.skip("BaseXClient Python package not installed")

    # Get connection parameters from environment or use defaults
    host = os.environ.get('BASEX_HOST', 'localhost')
    port = int(os.environ.get('BASEX_PORT', '1984'))
    username = os.environ.get('BASEX_USERNAME', 'admin')
    password = os.environ.get('BASEX_PASSWORD', 'admin')
    database = os.environ.get('BASEX_DATABASE', 'test_dictionary')

    connector = BaseXConnector(
        host=host,
        port=port,
        username=username,
        password=password,
        database=database
    )

    try:
        connector.connect()
        yield connector
    except Exception as e:
        pytest.skip(f"Could not connect to BaseX: {e}")
    finally:
        if connector.is_connected():
            connector.disconnect()


# ============================================================================
# Helper Fixtures
# ============================================================================

@pytest.fixture
def skip_if_no_patterns(patterns_json_path: str) -> Generator[None, None, None]:
    """Helper fixture to skip a test if patterns.json doesn't exist.

    Usage:
        def test_something(skip_if_no_patterns):
            # This test will be skipped if patterns.json is missing
            pass
    """
    if not os.path.exists(patterns_json_path):
        pytest.skip(
            f"patterns.json not found at {patterns_json_path}. "
            "Create this file to enable pattern-based tests."
        )
    yield


@pytest.fixture
def sample_xml_strings() -> dict[str, str]:
    """Provide sample XML strings for roundtrip testing."""
    return {
        "minimal": """<lift version="0.13">
            <entry id="test-1">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
        </lift>""",
        "with_sense": """<lift version="0.13">
            <entry id="test-2" dateCreated="2024-01-01T00:00:00Z">
                <lexical-unit>
                    <form lang="en"><text>example</text></form>
                </lexical-unit>
                <sense id="s1">
                    <definition>
                        <form lang="en"><text>A sample definition</text></form>
                    </definition>
                </sense>
            </entry>
        </lift>""",
        "with_namespace": """<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <entry id="test-3">
                <lexical-unit>
                    <form lang="en"><text>namespaced</text></form>
                </lexical-unit>
            </entry>
        </lift>""",
    }


@pytest.fixture
def xmldiff_options() -> dict[str, Any]:
    """Provide options for XML comparison/diffing."""
    return {
        "ignore_attribute_order": True,
        "ignore_whitespace": True,
        "ignore_comments": True,
        "normalization": "full"
    }
