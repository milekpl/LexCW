"""Tests for pattern extraction from XML roundtrip validation."""
import json
import os

import pytest

# Path to patterns.json - adjust base path as needed
PATTERNS_JSON_PATH = os.environ.get(
    "PATTERNS_JSON_PATH",
    os.path.join(os.path.dirname(__file__), "fixtures", "patterns.json")
)


def _load_patterns_json():
    """Helper to skip tests if patterns.json is not available."""
    if not os.path.isfile(PATTERNS_JSON_PATH):
        pytest.skip(f"patterns.json not found at {PATTERNS_JSON_PATH}")
    with open(PATTERNS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.xml_roundtrip
def test_patterns_json_exists():
    """Verify patterns.json exists."""
    assert os.path.isfile(PATTERNS_JSON_PATH), f"patterns.json must exist at {PATTERNS_JSON_PATH}"


@pytest.mark.xml_roundtrip
def test_patterns_json_valid():
    """Verify patterns.json is valid JSON."""
    patterns = _load_patterns_json()
    assert isinstance(patterns, dict), "patterns.json must be a JSON object (dict)"


@pytest.mark.xml_roundtrip
def test_patterns_has_required_metadata():
    """Check metadata has extracted_at, total_entries, unique_patterns."""
    patterns = _load_patterns_json()
    metadata = patterns.get("metadata", {})

    assert "extracted_at" in metadata, "metadata must contain 'extracted_at'"
    assert "total_entries" in metadata, "metadata must contain 'total_entries'"
    assert "unique_patterns" in metadata, "metadata must contain 'unique_patterns'"


@pytest.mark.xml_roundtrip
def test_patterns_is_list():
    """Verify patterns is a list."""
    patterns = _load_patterns_json()
    assert "patterns" in patterns, "patterns.json must contain 'patterns' key"
    assert isinstance(patterns["patterns"], list), "'patterns' must be a list"


@pytest.mark.xml_roundtrip
def test_each_pattern_has_required_fields():
    """Each pattern must have: id, element_path, structure, sample_xml, occurrences."""
    patterns = _load_patterns_json()
    pattern_list = patterns.get("patterns", [])

    required_fields = ["id", "element_path", "structure", "sample_xml", "occurrences"]

    for idx, pattern in enumerate(pattern_list):
        missing = [field for field in required_fields if field not in pattern]
        assert not missing, f"Pattern at index {idx} is missing fields: {missing}"
