"""
Unit tests for the IPA service (compression, validation, dedup, CER).
"""

import pytest
from app.services.ipa_service import (
    process_parentheses,
    process_and_split,
    is_valid_ipa,
    normalize_ipa,
    strip_stress_marks,
    stress_variant,
    ipa_equality,
    find_duplicates,
    levenshtein_distance,
    compute_cer,
)


class TestProcessParentheses:
    """Tests for parentheses expansion logic."""

    def test_no_parentheses(self):
        assert process_parentheses("triː") == ["triː"]

    def test_empty_string(self):
        assert process_parentheses("") == [""]

    def test_single_optional_sound(self):
        result = process_parentheses("ˈskɒtɪˌsɪz(ə)m")
        assert set(result) == {"ˈskɒtɪˌsɪzm", "ˈskɒtɪˌsɪzəm"}

    def test_two_optional_groups(self):
        result = process_parentheses("(ˌ)lækˈteɪʃ(ə)n")
        assert set(result) == {
            "lækˈteɪʃn",
            "lækˈteɪʃən",
            "ˌlækˈteɪʃn",
            "ˌlækˈteɪʃən",
        }

    def test_multiple_disjoint_groups(self):
        """Multiple non-nested parentheses groups."""
        result = process_parentheses("a(b)c(d)e")
        assert len(result) == 4  # 2^2 combinations
        # Possible if both kept, both removed, first kept, second kept
        assert "acde" in result or "abce" in result or "abcde" in result
        assert "ace" in result  # both removed

    def test_only_optional_part(self):
        result = process_parentheses("(ə)")
        assert set(result) == {"", "ə"}

    def test_leading_optional(self):
        result = process_parentheses("(ˌ)rekɔːd")
        assert set(result) == {"rekɔːd", "ˌrekɔːd"}

    def test_comma_separated(self):
        result = process_and_split("ab(c), de(f)")
        assert set(result) == {"ab", "abc", "de", "def"}

    def test_comma_separated_with_spaces(self):
        result = process_and_split("triː, ˈtriːɪŋ")
        assert set(result) == {"triː", "ˈtriːɪŋ"}


class TestIpaValidation:
    """Tests for IPA character validation."""

    def test_valid_simple_ipa(self):
        assert is_valid_ipa("triː") is True
        assert is_valid_ipa("ˈrekɔːd") is True
        assert is_valid_ipa("θɔːt") is True
        assert is_valid_ipa("ˈskɒtɪˌsɪzəm") is True

    def test_invalid_characters(self):
        assert is_valid_ipa("triː!!!") is False
        assert is_valid_ipa("hello world") is False
        assert is_valid_ipa("abc123") is False

    def test_empty_string(self):
        assert is_valid_ipa("") is True  # empty matches the pattern trivially

    def test_with_stress_marks(self):
        assert is_valid_ipa("ˌlækˈteɪʃən") is True


class TestIpaComparison:
    """Tests for IPA comparison utilities."""

    def test_strip_stress_marks(self):
        assert strip_stress_marks("ˈrekɔːd") == "rekɔːd"
        assert strip_stress_marks("ˌlækˈteɪʃən") == "lækteɪʃən"
        assert strip_stress_marks("triː") == "triː"

    def test_normalize_ipa(self):
        assert normalize_ipa("ˈrekɔːd") == normalize_ipa("rekɔːd")
        assert normalize_ipa("ˈTRIː") == normalize_ipa("triː")

    def test_ipa_equality_true(self):
        assert ipa_equality("ˈrekɔːd", "rekɔːd") is True

    def test_ipa_equality_false(self):
        assert ipa_equality("ˈrekɔːd", "rɪˈkɔːd") is False

    def test_stress_variant_detection(self):
        assert stress_variant("ˈrekɔːd", "ˌrekɔːd") is True
        assert stress_variant("ˈrekɔːd", "rɪˈkɔːd") is False  # different vowel
        assert stress_variant("ˈrekɔːd", "ˈrekɔːd") is False  # identical


class TestLevenshteinAndCer:
    """Tests for Levenshtein distance and CER computation."""

    def test_levenshtein_identical(self):
        assert levenshtein_distance("triː", "triː") == 0

    def test_levenshtein_substitution(self):
        assert levenshtein_distance("kæt", "kʌt") == 1  # æ → ʌ

    def test_levenshtein_insertion(self):
        assert levenshtein_distance("triː", "triːn") == 1  # extra n

    def test_levenshtein_deletion(self):
        assert levenshtein_distance("triːn", "triː") == 1  # missing n

    def test_cer_exact_match(self):
        assert compute_cer("triː", "triː") == 0.0

    def test_cer_partial(self):
        # "triː" vs "tri" — 1 deletion out of 4 chars
        assert compute_cer("triː", "tri") == 0.25

    def test_cer_completely_different(self):
        cer = compute_cer("kæt", "dɒɡ")
        assert cer > 0.0

    def test_cer_empty_reference(self):
        assert compute_cer("", "") == 0.0
        assert compute_cer("", "triː") == 1.0


class TestDeduplication:
    """Tests for pronunciation deduplication."""

    def test_no_duplicates(self):
        entries = [
            {"lexeme": "cat", "ipa": "kæt"},
            {"lexeme": "dog", "ipa": "dɒɡ"},
            {"lexeme": "tree", "ipa": "triː"},
        ]
        result = find_duplicates(entries)
        assert len(result) == 0

    def test_exact_duplicate(self):
        entries = [
            {"lexeme": "record", "ipa": "ˈrekɔːd"},
            {"lexeme": "record", "ipa": "ˈrekɔːd"},
        ]
        result = find_duplicates(entries)
        # Should find at least one duplicate group
        assert len(result) >= 1
        assert result[0]["type"] == "exact"

    def test_stress_variant_duplicate(self):
        entries = [
            {"lexeme": "record", "ipa": "ˈrekɔːd"},
            {"lexeme": "record", "ipa": "ˌrekɔːd"},
        ]
        result = find_duplicates(entries)
        types = {d["type"] for d in result}
        assert "stress_variant" in types

    def test_optional_sound_equivalent(self):
        entries = [
            {"lexeme": "lactation", "ipa": "(ˌ)lækˈteɪʃ(ə)n"},
            {"lexeme": "lactation", "ipa": "lækˈteɪʃən"},
        ]
        result = find_duplicates(entries)
        types = {d["type"] for d in result}
        assert "optional_sound_equivalent" in types or "exact" in types

    def test_different_words_not_flagged(self):
        entries = [
            {"lexeme": "cat", "ipa": "kæt"},
            {"lexeme": "dog", "ipa": "dɒɡ"},
        ]
        result = find_duplicates(entries)
        assert len(result) == 0

    def test_empty_ipa_handling(self):
        entries = [
            {"lexeme": "test", "ipa": ""},
            {"lexeme": "test", "ipa": ""},
        ]
        result = find_duplicates(entries)
        # Empty IPA shouldn't cause errors
        assert isinstance(result, list)


class TestProcessAndSplit:
    """Additional tests for process_and_split."""

    def test_multiple_variants(self):
        result = process_and_split("rɪˈkɔːd, ˈrekɔːd")
        assert "rɪˈkɔːd" in result
        assert "ˈrekɔːd" in result

    def test_variants_with_optional(self):
        result = process_and_split("(ˌ)lækˈteɪʃ(ə)n")
        assert "lækˈteɪʃn" in result
        assert "ˌlækˈteɪʃən" in result
