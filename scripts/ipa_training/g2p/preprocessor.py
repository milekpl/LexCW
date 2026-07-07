# encoding: UTF-8
"""
G2P Preprocessor - IPA cleaning, normalization, and flattening for G2P training.

This module provides utilities to:
- Clean and normalize IPA transcriptions
- Flatten optional variants (parentheses)
- Validate IPA strings
- Extract phoneme sequences for training
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class PreprocessedPair:
    """A single grapheme-phoneme pair for training."""
    grapheme: str
    phoneme: str
    pos: Optional[str] = None
    location: Optional[str] = None
    is_filled: bool = False  # Whether optional variant was filled


class G2PPreprocessor:
    """
    Preprocessor for G2P training data.

    Handles IPA cleaning, optional variant flattening, and normalization
    to prepare data for the G2P transformer model.
    """

    # IPA vowel nuclei (for validation)
    NUCLEI = 'aeiouəæɛɪʊɔʌɜɐɑːɪ̈ʉɯɤoøɵœɤɜɐ'

    # IPA consonants
    CONSONANTS = ('bcdfɡɟɥɬɮɲɳɲɳɲʃʒʂʐʔʘʎʏʑǃǂɕʑɣɦʁʀwʍhjklmnprstfxzʦʧðθvɸβɱŋɳɲɲŋɴ')

    # Stress markers
    PRIMARY_STRESS = 'ˈ'  # U+02C8 MODIFIER LETTER VERTICAL LINE
    SECONDARY_STRESS = 'ˌ'  # U+02CC MODIFIER LETTER LOW VERTICAL LINE

    # Syllable delimiter
    SYLLABLE_DELIMITER = '.'

    def __init__(self,
                 flatten_variants: bool = True,
                 normalize_stress: bool = True,
                 remove_spaces: bool = True,
                 min_phoneme_length: int = 1,
                 max_phoneme_length: int = 50):
        """
        Initialize the preprocessor.

        Args:
            flatten_variants: Whether to expand optional variants in parentheses
            normalize_stress: Whether to standardize stress markers
            remove_spaces: Whether to remove spaces from IPA
            min_phoneme_length: Minimum phoneme sequence length
            max_phoneme_length: Maximum phoneme sequence length
        """
        self.flatten_variants = flatten_variants
        self.normalize_stress = normalize_stress
        self.remove_spaces = remove_spaces
        self.min_phoneme_length = min_phoneme_length
        self.max_phoneme_length = max_phoneme_length

        # Regex patterns
        self._stress_pattern = re.compile(r'[' + self.PRIMARY_STRESS + self.SECONDARY_STRESS + ']')
        self._space_pattern = re.compile(r'\s+')
        self._optional_pattern = re.compile(r'\(([^)]+)\)')
        self._ipa_pattern = self._build_ipa_pattern()

    def _build_ipa_pattern(self) -> re.Pattern:
        """Build regex pattern for valid IPA characters."""
        # All valid IPA characters plus stress markers and common punctuation
        ipa_chars = (
            self.NUCLEI +
            self.CONSONANTS +
            self.PRIMARY_STRESS +
            self.SECONDARY_STRESS +
            self.SYLLABLE_DELIMITER
        )
        return re.compile(r'^[' + re.escape(ipa_chars) + r'\s]*$')

    def clean_ipa(self, ipa: str) -> str:
        """
        Clean and normalize an IPA transcription.

        Args:
            ipa: Raw IPA string from FLEx

        Returns:
            Cleaned IPA string
        """
        if not ipa:
            return ""

        # Remove leading/trailing whitespace
        cleaned = ipa.strip()

        # Remove spaces if configured
        if self.remove_spaces:
            cleaned = self._space_pattern.sub('', cleaned)

        # Normalize stress markers if configured
        if self.normalize_stress:
            # Ensure consistent stress marker representation
            cleaned = cleaned.replace('ˈ', self.PRIMARY_STRESS)
            cleaned = cleaned.replace('ˌ', self.SECONDARY_STRESS)

        return cleaned

    def flatten_variants_aggressive(self, ipa: str) -> List[str]:
        """
        Flatten optional variants in IPA (aggressive mode).

        Expands patterns like "lækˈteɪʃ(ə)n" to both forms:
        - "lækˈteɪʃn"
        - "lækˈteɪʃən"

        Uses recursive expansion for multiple optional variants.

        Args:
            ipa: IPA string with optional variants

        Returns:
            List of expanded IPA strings
        """
        # First clean the IPA
        cleaned = self.clean_ipa(ipa)
        if not cleaned:
            return []

        # Find all optional variants
        matches = self._optional_pattern.findall(cleaned)

        if not matches:
            return [cleaned]

        # Generate all combinations
        results = {cleaned}

        for match in matches:
            new_results = set()
            for base in results:
                # Option 1: Remove the variant entirely
                without_var = base.replace(f'({match})', '')
                new_results.add(without_var)

                # Option 2: Keep the variant without parentheses
                with_var = base.replace(f'({match})', match)
                new_results.add(with_var)

            results = new_results

        # Filter and sort results
        final_results = [r for r in results if r]
        return sorted(final_results, key=len)

    def flatten_variants_minimal(self, ipa: str) -> str:
        """
        Flatten optional variants to minimal form (remove optional parts).

        Converts "lækˈteɪʃ(ə)n" to "lækˈteɪʃn" (removes optional).

        Args:
            ipa: IPA string with optional variants

        Returns:
            Minimal form with optional parts removed
        """
        cleaned = self.clean_ipa(ipa)
        if not cleaned:
            return ""

        # Remove all optional variants (keep only required parts)
        result = self._optional_pattern.sub('', cleaned)
        return result

    def flatten_variants_expanded(self, ipa: str) -> List[PreprocessedPair]:
        """
        Flatten variants and return PreprocessedPair objects.

        Creates pairs for each variant, marking whether it was filled.

        Args:
            ipa: IPA string with optional variants

        Returns:
            List of PreprocessedPair objects
        """
        variants = self.flatten_variants_aggressive(ipa)

        pairs = []
        for variant in variants:
            # Check if this has the optional part filled
            has_optional = bool(self._optional_pattern.search(ipa))
            is_filled = '(' in variant and ')' in variant

            pair = PreprocessedPair(
                grapheme='',  # To be filled by data extractor
                phoneme=variant,
                is_filled=is_filled
            )
            pairs.append(pair)

        return pairs

    def validate_ipa(self, ipa: str) -> Tuple[bool, str]:
        """
        Validate an IPA transcription.

        Args:
            ipa: IPA string to validate

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        if not ipa:
            return False, "Empty IPA string"

        cleaned = self.clean_ipa(ipa)

        if not cleaned:
            return False, "IPA string became empty after cleaning"

        if len(cleaned) < self.min_phoneme_length:
            return False, f"IPA too short ({len(cleaned)} < {self.min_phoneme_length})"

        if len(cleaned) > self.max_phoneme_length:
            return False, f"IPA too long ({len(cleaned)} > {self.max_phoneme_length})"

        # Check for at least one vowel or stress marker
        has_vowel = any(c in self.NUCLEI for c in cleaned)
        has_stress = self._stress_pattern.search(cleaned)
        has_consonant = any(c in self.CONSONANTS for c in cleaned)

        if not has_vowel and not has_stress:
            return False, "No vowels or stress markers found"

        # Check for unsupported characters
        valid_chars = set(self.NUCLEI + self.CONSONANTS +
                         self.PRIMARY_STRESS + self.SECONDARY_STRESS +
                         self.SYLLABLE_DELIMITER)
        invalid_chars = set(cleaned) - valid_chars
        if invalid_chars:
            return False, f"Invalid IPA characters: {invalid_chars}"

        return True, ""

    def extract_phonemes(self, ipa: str) -> List[str]:
        """
        Extract individual phonemes from IPA string.

        Args:
            ipa: IPA string

        Returns:
            List of individual phoneme characters
        """
        cleaned = self.clean_ipa(ipa)
        if not cleaned:
            return []

        # Split into characters, keeping stress markers attached to following char
        phonemes = []
        i = 0
        while i < len(cleaned):
            char = cleaned[i]
            if char in (self.PRIMARY_STRESS, self.SECONDARY_STRESS):
                # Attach stress to next character
                if i + 1 < len(cleaned):
                    phonemes.append(char + cleaned[i + 1])
                    i += 2
                    continue
            phonemes.append(char)
            i += 1

        return phonemes

    def normalize_for_training(self, grapheme: str, ipa: str) -> Optional[Tuple[str, str]]:
        """
        Normalize a grapheme-IPA pair for training.

        Args:
            grapheme: The headword/lexeme form
            ipa: The IPA transcription

        Returns:
            Tuple of (normalized_grapheme, normalized_ipa) or None if invalid
        """
        # Clean IPA
        cleaned_ipa = self.clean_ipa(ipa)
        if not cleaned_ipa:
            return None

        # Validate IPA
        is_valid, reason = self.validate_ipa(cleaned_ipa)
        if not is_valid:
            return None

        # Normalize grapheme (lowercase, remove diacritics for matching)
        normalized_grapheme = grapheme.lower().strip()

        return (normalized_grapheme, cleaned_ipa)

    def split_into_syllables(self, ipa: str) -> List[str]:
        """
        Split IPA into syllables (if syllable markers present).

        Args:
            ipa: IPA string

        Returns:
            List of syllable strings
        """
        cleaned = self.clean_ipa(ipa)
        if not cleaned:
            return []

        # Split by syllable delimiter
        syllables = cleaned.split(self.SYLLABLE_DELIMITER)
        return [s.strip() for s in syllables if s.strip()]

    def get_stress_pattern(self, ipa: str) -> List[int]:
        """
        Get the positions of stressed syllables in IPA.

        Args:
            ipa: IPA string

        Returns:
            List of syllable indices that have stress markers
        """
        cleaned = self.clean_ipa(ipa)
        if not cleaned:
            return []

        syllables = self.split_into_syllables(cleaned)
        stressed = []

        for idx, syl in enumerate(syllables):
            if self.PRIMARY_STRESS in syl or self.SECONDARY_STRESS in syl:
                stressed.append(idx)

        return stressed

    def remove_stress_markers(self, ipa: str) -> str:
        """
        Remove all stress markers from IPA.

        Args:
            ipa: IPA string

        Returns:
            IPA string without stress markers
        """
        cleaned = self.clean_ipa(ipa)
        return self._stress_pattern.sub('', cleaned)

    def compute_phoneme_error_rate(self, reference: str, hypothesis: str) -> float:
        """
        Compute Phoneme Error Rate between reference and hypothesis.

        Uses edit distance (Levenshtein) at phoneme level.

        Args:
            reference: Reference IPA string
            hypothesis: Hypothesis IPA string

        Returns:
            PER as a float (0.0 to 1.0)
        """
        ref_phonemes = self.extract_phonemes(reference)
        hyp_phonemes = self.extract_phonemes(hypothesis)

        if not ref_phonemes:
            return 0.0 if not hyp_phonemes else 1.0

        # Compute edit distance
        edit_dist = self._levenshtein_distance(ref_phonemes, hyp_phonemes)
        per = edit_dist / len(ref_phonemes)

        return min(per, 1.0)  # Cap at 1.0

    def _levenshtein_distance(self, s1: List[str], s2: List[str]) -> int:
        """
        Compute Levenshtein distance between two lists.

        Args:
            s1: First list
            s2: Second list

        Returns:
            Edit distance
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


# Convenience function for quick preprocessing
def preprocess_pair(grapheme: str, ipa: str,
                    flatten: bool = True) -> Optional[Tuple[str, str]]:
    """
    Quick preprocessing of a grapheme-IPA pair.

    Args:
        grapheme: Headword
        ipa: IPA transcription
        flatten: Whether to flatten variants

    Returns:
        Tuple of (grapheme, cleaned_ipa) or None if invalid
    """
    preprocessor = G2PPreprocessor(flatten_variants=flatten)
    return preprocessor.normalize_for_training(grapheme, ipa)


if __name__ == '__main__':
    # Basic testing
    prep = G2PPreprocessor()

    test_cases = [
        "lækˈteɪʃ(ə)n",
        "ˈæpəl",
        "ˌfəʊtəˈɡræfɪ",
    ]

    for tc in test_cases:
        print(f"Original: {tc}")
        print(f"  Cleaned: {prep.clean_ipa(tc)}")
        print(f"  Flattened: {prep.flatten_variants_aggressive(tc)}")
        print(f"  Minimal: {prep.flatten_variants_minimal(tc)}")
        print(f"  Valid: {prep.validate_ipa(prep.clean_ipa(tc))}")
        print()
