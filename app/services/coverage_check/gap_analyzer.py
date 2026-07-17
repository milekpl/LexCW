"""
Gap analyzer for comparing lexical resources.

Compares a dictionary CLSF against a baseline CLSF (e.g., WordNet)
to identify missing headwords, senses, and translations.

Architecture: All data is extracted first, then analysis runs purely
in-memory with no database calls.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
import logging
from datetime import datetime

from app.services.coverage_check.models import (
    LexicalSenseFormat, Entry, Sense, Metadata,
    GapAnalysis, GapSummary, MissingHeadword, MissingSense
)

logger = logging.getLogger(__name__)


class GapAnalyzer:
    """
    Analyzer for finding gaps between dictionary (CLSF) and baseline CLSF.

    Identifies:
    - Missing headwords (in baseline but not in dictionary)
    - Missing senses (for headwords that exist)
    - Translation gaps

    Architecture: Works purely on CLSF data structures, no DB calls.
    """

    def __init__(self, baseline: LexicalSenseFormat,
                 dictionary: LexicalSenseFormat = None,
                 threshold: float = 0.7):
        """
        Initialize the gap analyzer.

        Args:
            baseline: CLSF baseline (e.g., WordNet converted to CLSF)
            dictionary: Dictionary data in CLSF format
            threshold: Similarity threshold for translation matching
        """
        self.baseline = baseline
        self.dictionary = dictionary
        self.threshold = threshold

        # Build baseline indices
        self._baseline_headwords: Set[str] = set()
        self._baseline_translations: Set[str] = set()
        self._baseline_entries_by_headword: Dict[str, Entry] = {}
        self._build_baseline_indices()

        # Build dictionary indices (from CLSF data)
        self._dict_headwords: Set[str] = set()
        self._dict_translations_by_headword: Dict[str, Set[str]] = {}
        self._dict_senses_count: Dict[str, int] = {}
        self._dict_variants_to_headword: Dict[str, str] = {}  # variant -> parent headword
        self._build_dict_indices()

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison.

        Handles:
        - Case normalization (lowercase)
        - Whitespace normalization (strip, collapse multiple spaces)
        - Apostrophe normalization (typographical → ASCII)
        """
        if not text:
            return ""

        # Normalize typographical apostrophes to ASCII apostrophe
        normalized = text.replace('\u2019', "'").replace('\u2018', "'").replace('\uff07', "'")

        # Normalize whitespace
        normalized = ' '.join(normalized.split())

        return normalized.lower().strip()

    def _build_baseline_indices(self) -> None:
        """Build search indices from baseline CLSF."""
        self._baseline_headwords = set()
        self._baseline_translations = set()
        self._baseline_entries_by_headword = {}

        for entry in self.baseline.entries:
            # Add normalized headword
            norm_headword = self._normalize(entry.headword)
            self._baseline_headwords.add(norm_headword)
            self._baseline_entries_by_headword[norm_headword] = entry

            # Add all translations
            for sense in entry.senses:
                if sense.translations:
                    for trans in sense.translations:
                        self._baseline_translations.add(self._normalize(trans))

    def _build_dict_indices(self) -> None:
        """Build search indices from dictionary CLSF data."""
        self._dict_headwords = set()
        self._dict_translations_by_headword = {}
        self._dict_senses_count = {}
        self._dict_variants_to_headword = {}

        if not self.dictionary:
            return

        for entry in self.dictionary.entries:
            norm_headword = self._normalize(entry.headword)
            self._dict_headwords.add(norm_headword)

            # Map variants to their parent headword
            for variant in entry.variants:
                norm_variant = self._normalize(variant)
                self._dict_variants_to_headword[norm_variant] = norm_headword
                # Also add variant to headwords set for coverage calculation
                self._dict_headwords.add(norm_variant)

            # Collect translations for this headword
            translations = set()
            senses_count = 0
            for sense in entry.senses:
                senses_count += 1
                if sense.translations:
                    for trans in sense.translations:
                        if trans:
                            translations.add(self._normalize(trans))

            self._dict_translations_by_headword[norm_headword] = translations
            self._dict_senses_count[norm_headword] = senses_count

    def _get_dict_translations(self, headword: str) -> Set[str]:
        """Get translations for a headword from dictionary CLSF data."""
        norm = self._normalize(headword)
        return self._dict_translations_by_headword.get(norm, set())

    def _get_dict_senses_count(self, headword: str) -> int:
        """Get sense count for a headword from dictionary CLSF data."""
        norm = self._normalize(headword)
        return self._dict_senses_count.get(norm, 0)

    def _get_baseline_translations(self, headword: str) -> Set[str]:
        """Get all translations for a headword from baseline."""
        norm = self._normalize(headword)
        entry = self._baseline_entries_by_headword.get(norm)
        if not entry:
            return set()

        translations = set()
        for sense in entry.senses:
            if sense.translations:
                for trans in sense.translations:
                    if trans:
                        translations.add(self._normalize(trans))
        return translations

    def _translations_match(self, baseline_trans: str,
                             dict_trans: str) -> bool:
        """
        Check if two translations match (case-insensitive).

        Uses:
        - Exact match (case-insensitive)
        - Substring containment
        """
        if not baseline_trans or not dict_trans:
            return False

        norm_baseline = baseline_trans.lower().strip()
        norm_dict = dict_trans.lower().strip()

        # Exact match (case-insensitive)
        if norm_baseline == norm_dict:
            return True

        # Check if one is contained in the other
        if norm_baseline in norm_dict or norm_dict in norm_baseline:
            return True

        return False

    def _determine_priority(self, headword: str,
                            translations: Set[str]) -> str:
        """Determine priority for a missing headword."""
        # High priority: common words with multiple translations
        common_words = {"the", "be", "have", "do", "say", "get", "make", "go", "see", "know"}

        if headword.lower() in common_words:
            return "high"

        # High priority: if there are multiple translations
        if len(translations) >= 3:
            return "high"

        # Medium priority: if there are translations
        if len(translations) >= 1:
            return "medium"

        return "low"

    def _is_headword_covered(self, headword: str) -> bool:
        """
        Check if a headword is covered in dictionary.

        A headword is covered if:
        1. It exists directly in dictionary, OR
        2. It is a variant form of an entry that exists
        """
        norm_hw = self._normalize(headword)

        # Direct match
        if norm_hw in self._dict_headwords:
            return True

        # Check if it's a variant of a covered headword
        if norm_hw in self._dict_variants_to_headword:
            parent_headword = self._dict_variants_to_headword[norm_hw]
            return parent_headword in self._dict_headwords

        return False

    def find_missing_headwords(self) -> List[MissingHeadword]:
        """
        Find headwords in baseline that are missing from dictionary.

        Returns:
            List of MissingHeadword objects sorted by priority
        """
        missing = []

        for entry in self.baseline.entries:
            if not self._is_headword_covered(entry.headword):
                translations = self._get_baseline_translations(entry.headword)
                priority = self._determine_priority(entry.headword, translations)

                missing_headword = MissingHeadword(
                    headword=entry.headword,
                    pos=entry.part_of_speech,
                    priority=priority,
                    translations=list(translations)[:5]  # Top 5 translations
                )
                missing.append(missing_headword)

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        missing.sort(key=lambda x: (priority_order.get(x.priority, 3), x.headword))

        return missing

    def find_sense_gaps(self) -> List[MissingSense]:
        """
        Find senses that exist in baseline but not in dictionary.

        Only checks headwords that exist in dictionary.

        Returns:
            List of MissingSense objects
        """
        sense_gaps = []

        for entry in self.baseline.entries:
            if not self._is_headword_covered(entry.headword):
                continue

            # Get dictionary translations for this headword
            dict_translations = self._get_dict_translations(entry.headword)

            # Check each sense
            missing_senses = []
            baseline_senses = entry.senses
            dict_senses_count = self._get_dict_senses_count(entry.headword)

            for sense in baseline_senses:
                # Check if this sense's translations exist in dictionary
                sense_found = False
                if sense.translations:
                    for trans in sense.translations:
                        if not trans:
                            continue
                        for dtrans in dict_translations:
                            if self._translations_match(trans, dtrans):
                                sense_found = True
                                break
                        if sense_found:
                            break

                if not sense_found:
                    missing_senses.append({
                        "definition": sense.definition,
                        "translations": (sense.translations[:3] if sense.translations else []),
                        "synset_id": sense.synset_id,
                    })

            if missing_senses:
                gap = MissingSense(
                    headword=entry.headword,
                    flex_senses=dict_senses_count,
                    baseline_senses=len(baseline_senses),
                    missing_senses=missing_senses
                )
                sense_gaps.append(gap)

        return sense_gaps

    def find_translation_gaps(self) -> List[Dict[str, Any]]:
        """Find specific translations that are missing."""
        translation_gaps = []

        for entry in self.baseline.entries:
            if not self._is_headword_covered(entry.headword):
                continue

            dict_translations = self._get_dict_translations(entry.headword)

            baseline_translations = set()
            for sense in entry.senses:
                if sense.translations:
                    for trans in sense.translations:
                        if trans:
                            baseline_translations.add(self._normalize(trans))

            # Find missing translations
            missing = baseline_translations - dict_translations

            if missing:
                translation_gaps.append({
                    "headword": entry.headword,
                    "existing_translations": list(dict_translations),
                    "missing_translations": list(missing)
                })

        return translation_gaps

    def analyze(self) -> GapAnalysis:
        """
        Run complete gap analysis.

        Returns:
            Complete GapAnalysis object
        """
        logger.info("Running gap analysis (pure in-memory)...")

        # Find missing headwords
        missing_headwords = self.find_missing_headwords()

        # Find sense gaps
        sense_gaps = self.find_sense_gaps()

        # Find translation gaps
        translation_gaps = self.find_translation_gaps()

        # Calculate summary statistics
        total_baseline_headwords = len(self.baseline.entries)
        total_dict_headwords = len(self._dict_headwords)
        total_baseline_senses = sum(len(e.senses) for e in self.baseline.entries)
        total_dict_senses = sum(self._dict_senses_count.values())

        summary = GapSummary(
            date=datetime.now().strftime("%Y-%m-%d"),
            baseline=self.baseline.metadata.name,
            baseline_version=self.baseline.metadata.version,
            flex_project=self.dictionary.metadata.name if self.dictionary else "",
            total_headwords_baseline=total_baseline_headwords,
            total_headwords_flex=total_dict_headwords,
            # Coverage: min(dict, baseline) / baseline (capped at 100%)
            headword_coverage=(
                min(total_dict_headwords, total_baseline_headwords) / total_baseline_headwords * 100
                if total_baseline_headwords > 0 else 100.0
            ),
            total_senses_baseline=total_baseline_senses,
            total_senses_flex=total_dict_senses,
            sense_coverage=100.0 if total_baseline_senses == 0 else 0.0
        )

        # Calculate sense coverage
        if total_baseline_senses > 0:
            found_senses = total_baseline_senses - sum(
                len(g.missing_senses) for g in sense_gaps
            )
            summary.sense_coverage = (
                found_senses / total_baseline_senses * 100
            )

        analysis = GapAnalysis(
            summary=summary,
            missing_headwords=missing_headwords,
            missing_senses=sense_gaps,
            translation_gaps=translation_gaps
        )

        logger.info(
            f"Gap analysis: {len(missing_headwords)} missing headwords, "
            f"{len(sense_gaps)} sense gaps, {len(translation_gaps)} translation gaps"
        )

        return analysis
