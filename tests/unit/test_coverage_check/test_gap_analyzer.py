"""
Unit tests for gap analyzer.

Tests comparing a dictionary CLSF against a baseline CLSF
to find missing headwords, senses, and translations.
"""
import pytest
from app.services.coverage_check.models import (
    LexicalSenseFormat, Metadata, Entry, Sense,
    GapAnalysis, GapSummary, MissingHeadword, MissingSense,
)
from app.services.coverage_check.gap_analyzer import GapAnalyzer


class TestGapAnalyzer:
    def test_missing_headwords(self, bilingual_clsf, wn_baseline_clsf):
        """Car is in WN but not in dictionary."""
        analyzer = GapAnalyzer(baseline=wn_baseline_clsf, dictionary=bilingual_clsf)
        result = analyzer.analyze()
        missing = {mh.headword for mh in result.missing_headwords}
        assert "car" in missing

    def test_no_missing_for_present_words(self, bilingual_clsf, wn_baseline_clsf):
        """Cat and dog are in both."""
        analyzer = GapAnalyzer(baseline=wn_baseline_clsf, dictionary=bilingual_clsf)
        result = analyzer.analyze()
        missing = {mh.headword for mh in result.missing_headwords}
        assert "cat" not in missing
        assert "dog" not in missing

    def test_sense_gaps(self, bilingual_clsf, wn_baseline_clsf):
        """Cat has 3 WN senses but only 2 in dictionary."""
        analyzer = GapAnalyzer(baseline=wn_baseline_clsf, dictionary=bilingual_clsf)
        result = analyzer.analyze()
        cat_gaps = [ms for ms in result.missing_senses if ms.headword == "cat"]
        assert len(cat_gaps) >= 1

    def test_headword_coverage_percentage(self, bilingual_clsf, wn_baseline_clsf):
        """2 out of 3 baseline headwords present = 66.7%."""
        analyzer = GapAnalyzer(baseline=wn_baseline_clsf, dictionary=bilingual_clsf)
        result = analyzer.analyze()
        assert 60.0 <= result.summary.headword_coverage <= 70.0

    def test_normalization(self):
        """Apostrophes and case should not prevent matching."""
        baseline = LexicalSenseFormat(
            metadata=Metadata(name="wn", language="en"),
            entries=[
                Entry(headword="don't", language="en",
                      senses=[Sense(id="s1", definition="contraction")]),
            ],
        )
        dictionary = LexicalSenseFormat(
            metadata=Metadata(name="dict", language="en"),
            entries=[
                Entry(headword="don\u2019t", language="en",
                      senses=[Sense(id="s2", definition="contraction")]),
            ],
        )
        analyzer = GapAnalyzer(baseline=baseline, dictionary=dictionary)
        result = analyzer.analyze()
        missing = {mh.headword for mh in result.missing_headwords}
        assert "don't" not in missing

    def test_variant_matching(self):
        """Dictionary variants should count as coverage."""
        baseline = LexicalSenseFormat(
            metadata=Metadata(name="wn", language="en"),
            entries=[
                Entry(headword="life span", language="en",
                      senses=[Sense(id="s1")]),
            ],
        )
        dictionary = LexicalSenseFormat(
            metadata=Metadata(name="dict", language="en"),
            entries=[
                Entry(headword="lifespan", language="en", variants=["life span"],
                      senses=[Sense(id="s2")]),
            ],
        )
        analyzer = GapAnalyzer(baseline=baseline, dictionary=dictionary)
        result = analyzer.analyze()
        missing = {mh.headword for mh in result.missing_headwords}
        assert "life span" not in missing

    def test_empty_baseline(self, bilingual_clsf):
        empty_baseline = LexicalSenseFormat(
            metadata=Metadata(name="empty", language="en"), entries=[]
        )
        analyzer = GapAnalyzer(baseline=empty_baseline, dictionary=bilingual_clsf)
        result = analyzer.analyze()
        assert result.summary.headword_coverage == 100.0
        assert len(result.missing_headwords) == 0

    def test_report_generation(self, bilingual_clsf, wn_baseline_clsf):
        analyzer = GapAnalyzer(baseline=wn_baseline_clsf, dictionary=bilingual_clsf)
        result = analyzer.analyze()
        md = result.generate_report(format="markdown")
        assert "Gap Analysis" in md
        assert "66" in md or "67" in md  # coverage %

    def test_translation_gaps(self):
        """Sense with missing translations produces a gap entry."""
        baseline = LexicalSenseFormat(
            metadata=Metadata(name="wn", language="en"),
            entries=[
                Entry(headword="cat", language="en",
                      senses=[
                          Sense(id="s1", translations=["кот", "кіт"]),
                          Sense(id="s2", translations=["кішка"]),
                      ]),
            ],
        )
        dictionary = LexicalSenseFormat(
            metadata=Metadata(name="dict", language="en"),
            entries=[
                Entry(headword="cat", language="en",
                      senses=[Sense(id="s3", translations=["кот"])]),
            ],
        )
        analyzer = GapAnalyzer(baseline=baseline, dictionary=dictionary)
        result = analyzer.analyze()
        assert len(result.missing_senses) > 0
        cat_gap = [ms for ms in result.missing_senses if ms.headword == "cat"][0]
        assert cat_gap.baseline_senses == 2
        assert cat_gap.flex_senses == 1


class TestGapAnalyzerPriority:
    def test_high_priority_for_common_words(self, bilingual_clsf, wn_baseline_clsf):
        analyzer = GapAnalyzer(baseline=wn_baseline_clsf, dictionary=bilingual_clsf)
        result = analyzer.analyze()
        priorities = {mh.headword: mh.priority for mh in result.missing_headwords}
        # "car" has translations, so should be medium or high
        assert priorities.get("car") in ("high", "medium")
