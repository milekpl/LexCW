"""
WordNet sense alignment analyzer.

Compares dictionary sense counts against WordNet synset counts per headword
to detect suspicious divergence. This is a diagnostic, not prescriptive —
it surfaces data for lexicographers to make informed decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from app.services.coverage_check.models import LexicalSenseFormat
from app.services.coverage_check.normalizer import normalize


class AlignmentStatus(Enum):
    OK = "ok"                # ratio within thresholds
    SPLIT_CANDIDATE = "split_candidate"  # dict has fewer senses than WN
    MERGE_CANDIDATE = "merge_candidate"  # dict has more senses than WN
    MISSING = "missing"      # word not in one of the resources


@dataclass
class WordAlignment:
    """Alignment result for a single headword."""
    headword: str
    dict_count: int
    wn_count: int
    ratio: float
    status: AlignmentStatus
    dict_definition_sample: str = ""
    wn_definition_sample: str = ""
    per_sense: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SenseAlignment:
    """Per-sense alignment between dictionary and WordNet."""
    dict_sense_id: str
    dict_definition: str
    wn_synset_id: str
    wn_definition: str
    matched: bool
    matched_translation: str = ""


@dataclass
class AlignmentReport:
    """Complete alignment analysis report."""
    words: List[WordAlignment] = field(default_factory=list)
    total_checked: int = 0
    flagged_count: int = 0

    def generate_report(self, format: str = "markdown") -> str:
        if format == "json":
            import json
            return json.dumps({
                "total_checked": self.total_checked,
                "flagged_count": self.flagged_count,
                "words": [
                    {
                        "headword": w.headword,
                        "dict_count": w.dict_count,
                        "wn_count": w.wn_count,
                        "ratio": round(w.ratio, 2),
                        "status": w.status.value,
                    }
                    for w in self.words
                ],
            }, indent=2, ensure_ascii=False)

        lines = [
            "# Sense Alignment Report",
            "",
            f"**Total checked:** {self.total_checked}",
            f"**Flagged:** {self.flagged_count}",
            "",
            "| Headword | Dict Senses | WN Senses | Ratio | Status |",
            "|----------|-------------|-----------|-------|--------|",
        ]
        for w in self.words:
            status_emoji = {
                AlignmentStatus.OK: "✅",
                AlignmentStatus.SPLIT_CANDIDATE: "🔀",
                AlignmentStatus.MERGE_CANDIDATE: "📎",
                AlignmentStatus.MISSING: "❓",
            }.get(w.status, "")
            lines.append(
                f"| {w.headword} | {w.dict_count} | {w.wn_count} | "
                f"{w.ratio:.2f} | {status_emoji} {w.status.value} |"
            )
        lines.append("")
        return "\n".join(lines)


class SenseAlignmentAnalyzer:
    """Compare dictionary sense counts against WordNet synset counts."""

    def __init__(
        self,
        threshold_low: float = 0.5,
        threshold_high: float = 2.0,
    ):
        """
        Args:
            threshold_low: Below this ratio → split candidate (dict has fewer senses)
            threshold_high: Above this ratio → merge candidate (dict has more senses)
        """
        self.threshold_low = threshold_low
        self.threshold_high = threshold_high

    def analyze(
        self,
        dictionary: LexicalSenseFormat,
        wordnet: LexicalSenseFormat,
    ) -> AlignmentReport:
        """Compare sense counts between dictionary and WordNet."""
        # Build WN index: headword -> entry
        wn_by_headword: Dict[str, List] = {}
        for entry in wordnet.entries:
            hw = normalize(entry.headword)
            if hw:
                if hw not in wn_by_headword:
                    wn_by_headword[hw] = []
                wn_by_headword[hw].append(entry)

        words = []
        for entry in dictionary.entries:
            hw = normalize(entry.headword)
            if not hw:
                continue

            # Look up in WordNet (try all POS variants)
            wn_entries = wn_by_headword.get(hw, [])
            if not wn_entries:
                continue  # Word not in WN, skip

            # Sum senses across all POS variants
            wn_senses = sum(len(e.senses) for e in wn_entries)
            dict_senses = len(entry.senses)

            if wn_senses == 0:
                continue

            ratio = dict_senses / wn_senses

            # Determine status
            if ratio < self.threshold_low:
                status = AlignmentStatus.SPLIT_CANDIDATE
            elif ratio > self.threshold_high:
                status = AlignmentStatus.MERGE_CANDIDATE
            else:
                status = AlignmentStatus.OK

            # Sample definitions
            dict_def = ""
            if entry.senses and entry.senses[0].definition:
                dict_def = entry.senses[0].definition[:60]

            wn_def = ""
            if wn_entries and wn_entries[0].senses and wn_entries[0].senses[0].definition:
                wn_def = wn_entries[0].senses[0].definition[:60]

            # Compute per-sense matching
            per_sense = []
            all_wn_senses = []
            for wn_entry in wn_entries:
                all_wn_senses.extend(wn_entry.senses)

            for dict_sense in entry.senses:
                if not dict_sense.translations:
                    continue

                # Try to match this dictionary sense to a WordNet synset
                best_match = None
                best_match_score = 0

                for wn_sense in all_wn_senses:
                    if not wn_sense.translations:
                        continue

                    # Check for translation overlap
                    for dict_trans in dict_sense.translations:
                        dict_trans_lower = dict_trans.lower()
                        for wn_trans in wn_sense.translations:
                            wn_trans_lower = wn_trans.lower()
                            if dict_trans_lower == wn_trans_lower:
                                score = 1.0
                            elif dict_trans_lower in wn_trans_lower or wn_trans_lower in dict_trans_lower:
                                score = 0.7
                            else:
                                continue

                            if score > best_match_score:
                                best_match_score = score
                                best_match = wn_sense

                if best_match:
                    per_sense.append({
                        "dict_sense_id": dict_sense.id,
                        "dict_definition": dict_sense.definition[:100],
                        "wn_synset_id": best_match.synset_id or "",
                        "wn_definition": best_match.definition[:100],
                        "matched": True,
                        "matched_translation": best_match.translations[0] if best_match.translations else "",
                    })
                else:
                    per_sense.append({
                        "dict_sense_id": dict_sense.id,
                        "dict_definition": dict_sense.definition[:100],
                        "wn_synset_id": "",
                        "wn_definition": "",
                        "matched": False,
                    })

            words.append(WordAlignment(
                headword=hw,
                dict_count=dict_senses,
                wn_count=wn_senses,
                ratio=ratio,
                status=status,
                dict_definition_sample=dict_def,
                wn_definition_sample=wn_def,
                per_sense=per_sense,
            ))

        # Sort: flagged words first
        words.sort(key=lambda w: (0 if w.status != AlignmentStatus.OK else 1, w.headword))

        flagged = sum(1 for w in words if w.status != AlignmentStatus.OK)

        return AlignmentReport(
            words=words,
            total_checked=len(words),
            flagged_count=flagged,
        )
