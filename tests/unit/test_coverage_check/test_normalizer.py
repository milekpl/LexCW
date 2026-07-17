"""
Unit tests for text normalization.

Tests apostrophe normalization, whitespace handling, and case folding.
"""
import pytest
from app.services.coverage_check.normalizer import normalize, normalize_strict


class TestNormalize:
    def test_lowercase(self):
        assert normalize("Hello") == "hello"

    def test_strip_whitespace(self):
        assert normalize("  hello  ") == "hello"

    def test_collapse_internal_whitespace(self):
        assert normalize("hello   world") == "hello world"

    def test_typographic_apostrophe_right(self):
        # U+2019 RIGHT SINGLE QUOTATION MARK
        assert normalize("don\u2019t") == "don't"

    def test_typographic_apostrophe_left(self):
        # U+2018 LEFT SINGLE QUOTATION MARK
        assert normalize("\u2018til") == "'til"

    def test_fullwidth_apostrophe(self):
        # U+FF07 FULLWIDTH APOSTROPHE
        assert normalize("don\uff07t") == "don't"

    def test_ascii_apostrophe_unchanged(self):
        assert normalize("don't") == "don't"

    def test_empty_string(self):
        assert normalize("") == ""

    def test_none_returns_empty(self):
        assert normalize(None) == ""

    def test_tab_and_newline_collapsed(self):
        assert normalize("hello\t\nworld") == "hello world"

    def test_mixed_normalization(self):
        assert normalize("  Don\u2019T   Stop  ") == "don't stop"


class TestNormalizeStrict:
    """Strict mode preserves case for proper noun matching."""

    def test_preserves_case(self):
        assert normalize_strict("Berlin") == "Berlin"

    def test_strips_whitespace(self):
        assert normalize_strict("  Berlin  ") == "Berlin"

    def test_collapse_whitespace(self):
        assert normalize_strict("New  York") == "New York"

    def test_apostrophe_normalized(self):
        assert normalize_strict("don\u2019t") == "don't"
