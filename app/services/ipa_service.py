"""
IPA (International Phonetic Alphabet) processing service.

Provides compression (parentheses expansion), validation, deduplication,
and comparison utilities for IPA pronunciation strings.

Ported from the FlexTools Wielki pronunciation_tools.py module.
"""

from __future__ import annotations

import re
from typing import List, Set, Tuple, Optional
from itertools import combinations


# ---------------------------------------------------------------------------
# IPA character classification (English-centric, extensible)
# ---------------------------------------------------------------------------

DIPHTHONGS = r"[eaɔ]ɪ|[ɪeʊ]ə|[aəo]ʊ"
NON_CONSONANTS = r"[ʌɪᵻæʊəeɒ]|([iɑɔuɜ]ː)"
CONSONANTS = r"(tʃ|dʒ)|[pbtdkɡfvθðszʃʒhmnŋlrjwx]"
PUNCTUATION = r"[ ˌˈ]"

VALID_IPA_REGEX = re.compile(
    r"^("
    + PUNCTUATION
    + "|"
    + NON_CONSONANTS
    + "|"
    + CONSONANTS
    + "|"
    + DIPHTHONGS
    + r")*$"
)

STRESS_MARKS = {"ˈ", "ˌ"}


# ---------------------------------------------------------------------------
# Parentheses compression — the core IPA expansion logic
# ---------------------------------------------------------------------------


def process_parentheses(input_string: str) -> List[str]:
    """Expand parenthesised optional sounds in an IPA string.

    Each parenthesised group produces two variants: one with the group
    included and one without. Nested parentheses are handled recursively.

    Examples::

        >>> process_parentheses("a(b)c")
        ["abc", "ac"]

        >>> process_parentheses("(ˌ)lækˈteɪʃ(ə)n")
        ["lækˈteɪʃn", "lækˈteɪʃən", "ˌlækˈteɪʃn", "ˌlækˈteɪʃən"]

        >>> process_parentheses("ˈskɒtɪˌsɪz(ə)m")
        ["ˈskɒtɪˌsɪzm", "ˈskɒtɪˌsɪzəm"]

    Args:
        input_string: IPA string with optional (parenthesised) segments.

    Returns:
        List of all expanded variants.
    """
    optional_re = re.compile(r"\((.*?)\)")
    matches = optional_re.findall(input_string)

    if not matches:
        return [input_string]

    modified: Set[str] = set()
    for match in matches:
        without = input_string.replace(f"({match})", "")
        with_ = input_string.replace(f"({match})", match)
        modified.add(without)
        modified.add(with_)

    # Handle nested parentheses iteratively
    while optional_re.search(" ".join(modified)):
        new_set: Set[str] = set()
        for expansion in modified:
            new_set.update(process_parentheses(expansion))
        modified = new_set

    return sorted(modified)


def process_and_split(input_string: str, split_string: str = ",") -> List[str]:
    """Split a comma-separated IPA string and expand each part.

    Examples::

        >>> process_and_split("ab(c), de(f)")
        ["ab", "abc", "de", "def"]

    Args:
        input_string: Comma-separated IPA string with optional parentheses.
        split_string: Delimiter (default comma).

    Returns:
        Sorted list of all expanded variants across all parts.
    """
    variants: Set[str] = set()
    for part in input_string.split(split_string):
        stripped = part.strip()
        if stripped:
            variants.update(process_parentheses(stripped))
    return sorted(variants)


# ---------------------------------------------------------------------------
# IPA validation
# ---------------------------------------------------------------------------


def is_valid_ipa(text: str) -> bool:
    """Check if a string contains only valid IPA characters."""
    return bool(VALID_IPA_REGEX.match(text.strip()))


def strip_stress_marks(ipa: str) -> str:
    """Remove primary (ˈ) and secondary (ˌ) stress marks from IPA."""
    return "".join(c for c in ipa if c not in STRESS_MARKS)


def normalize_ipa(ipa: str) -> str:
    """Normalize an IPA string for comparison: strip stress, lowercase."""
    return strip_stress_marks(ipa).strip().lower()


# ---------------------------------------------------------------------------
# Comparison & similarity
# ---------------------------------------------------------------------------


def ipa_equality(ipa_a: str, ipa_b: str) -> bool:
    """Check if two IPA strings are equivalent (ignoring stress marks)."""
    return normalize_ipa(ipa_a) == normalize_ipa(ipa_b)


def stress_variant(ipa_a: str, ipa_b: str) -> bool:
    """Check if two IPAs differ only by stress marks on the same syllable
    (same phoneme sequence, same stress position but different marker type)."""
    a_no_stress = strip_stress_marks(ipa_a)
    b_no_stress = strip_stress_marks(ipa_b)
    if a_no_stress != b_no_stress:
        return False
    # Both have stress marks in the same positions
    a_stress_pos = [i for i, c in enumerate(ipa_a) if c in STRESS_MARKS]
    b_stress_pos = [i for i, c in enumerate(ipa_b) if c in STRESS_MARKS]
    return a_stress_pos == b_stress_pos and ipa_a != ipa_b


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _expand_entry_ipa(ipa: str) -> Set[str]:
    """Expand an IPA string into all normalised variants (split + compress)."""
    return {normalize_ipa(v) for v in process_and_split(ipa)}


DuplicateGroup = dict
"""
A dict describing a group of duplicate entries:

    {
        "type": "exact" | "stress_variant" | "optional_sound_equivalent",
        "lexeme": str,
        "ipa_values": [str, ...],
        "variants_normalized": [str, ...],
        "recommendation": str,
    }
"""


def find_duplicates(entries: List[dict]) -> List[DuplicateGroup]:
    """Find duplicate or near-duplicate pronunciations within a list of entries.

    Each entry dict must have at least ``"lexeme"`` and ``"ipa"`` keys.

    Detects three types:
    1. **exact** — identical IPA strings
    2. **stress_variant** — same phonemes, stress on same syllable, different marker
    3. **optional_sound_equivalent** — same after parentheses expansion

    Args:
        entries: List of dicts with ``lexeme`` and ``ipa`` keys.

    Returns:
        List of duplicate groups with type, recommendation, and involved values.
    """
    duplicates: List[DuplicateGroup] = []

    # Index by normalized form for O(n) exact dedup
    seen: dict = {}  # normalized_ipa -> [(index, entry)]
    for i, entry in enumerate(entries):
        expanded = _expand_entry_ipa(entry.get("ipa", ""))
        for norm in expanded:
            if norm in seen:
                for j, other in seen[norm]:
                    if other["lexeme"] == entry["lexeme"]:
                        duplicates.append(
                            {
                                "type": "exact",
                                "lexeme": entry["lexeme"],
                                "ipa_values": [other["ipa"], entry["ipa"]],
                                "variants_normalized": [norm],
                                "recommendation": "Remove duplicate IPA variant",
                            }
                        )
            seen.setdefault(norm, []).append((i, entry))

    # Stress variant detection: compare within same lexeme
    by_lexeme: dict = {}
    for entry in entries:
        by_lexeme.setdefault(entry.get("lexeme", ""), []).append(entry)

    for lexeme, lex_entries in by_lexeme.items():
        for a, b in combinations(lex_entries, 2):
            ipa_a = a.get("ipa", "")
            ipa_b = b.get("ipa", "")
            if ipa_a == ipa_b:
                continue  # already caught as exact
            if stress_variant(ipa_a, ipa_b):
                duplicates.append(
                    {
                        "type": "stress_variant",
                        "lexeme": lexeme,
                        "ipa_values": [ipa_a, ipa_b],
                        "variants_normalized": [
                            normalize_ipa(ipa_a),
                            normalize_ipa(ipa_b),
                        ],
                        "recommendation": (
                            "Merge stress variants — choose one marker style"
                        ),
                    }
                )

    # Optional-sound equivalents: compare expanded sets
    for lexeme, lex_entries in by_lexeme.items():
        for a, b in combinations(lex_entries, 2):
            ipa_a = a.get("ipa", "")
            ipa_b = b.get("ipa", "")
            if ipa_a == ipa_b:
                continue
            expanded_a = _expand_entry_ipa(ipa_a)
            expanded_b = _expand_entry_ipa(ipa_b)
            if expanded_a & expanded_b:
                # They share at least one normalised variant
                common = expanded_a & expanded_b
                duplicates.append(
                    {
                        "type": "optional_sound_equivalent",
                        "lexeme": lexeme,
                        "ipa_values": [ipa_a, ipa_b],
                        "variants_normalized": sorted(common),
                        "recommendation": (
                            f"Merge into compressed form "
                            f"(variants overlap: {', '.join(sorted(common))})"
                        ),
                    }
                )

    return duplicates


# ---------------------------------------------------------------------------
# IPA-level Levenshtein distance (character-based)
# ---------------------------------------------------------------------------


def levenshtein_distance(ref: str, hyp: str) -> int:
    """Compute Levenshtein edit distance between two IPA strings."""
    m, n = len(ref), len(hyp)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[m][n]


def compute_cer(stored_ipa: str, predicted_ipa: str) -> float:
    """Compute Character Error Rate between two IPA strings.

    CER = edit_distance / len(stored_ipa). Returns 1.0 for empty references.
    """
    if not stored_ipa:
        return 1.0 if predicted_ipa else 0.0
    return levenshtein_distance(stored_ipa, predicted_ipa) / len(stored_ipa)
