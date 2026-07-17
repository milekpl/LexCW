"""
Unit tests for WordNet sense alignment analyzer.

Tests comparing dictionary sense counts against WordNet synset counts
to detect suspicious divergence.
"""
import pytest
from app.services.coverage_check.models import (
    LexicalSenseFormat, Metadata, Entry, Sense,
)
from app.services.coverage_check.sense_alignment import (
    SenseAlignmentAnalyzer, AlignmentStatus, WordAlignment, AlignmentReport,
)


@pytest.fixture
def dict_with_bank():
    """Dictionary with 2 senses for 'bank'."""
    return LexicalSenseFormat(
        metadata=Metadata(name="dict", language="en"),
        entries=[
            Entry(headword="bank", part_of_speech="noun", language="en",
                  senses=[
                      Sense(id="s1", definition="financial institution"),
                      Sense(id="s2", definition="river bank"),
                  ]),
            Entry(headword="cat", part_of_speech="noun", language="en",
                  senses=[
                      Sense(id="s3", definition="feline"),
                  ]),
        ],
    )


@pytest.fixture
def wn_with_bank():
    """WordNet with many senses for 'bank'."""
    return LexicalSenseFormat(
        metadata=Metadata(name="wordnet", language="en"),
        entries=[
            Entry(headword="bank", part_of_speech="noun", language="en",
                  senses=[
                      Sense(id="wn:1", definition="financial institution"),
                      Sense(id="wn:2", definition="river bank"),
                      Sense(id="wn:3", definition="bank shot"),
                      Sense(id="wn:4", definition="blood bank"),
                      Sense(id="wn:5", definition="data bank"),
                      Sense(id="wn:6", definition="bank of switches"),
                  ]),
            Entry(headword="cat", part_of_speech="noun", language="en",
                  senses=[
                      Sense(id="wn:7", definition="feline"),
                      Sense(id="wn:8", definition="guy"),
                      Sense(id="wn:9", definition="game equipment"),
                  ]),
        ],
    )


class TestSenseAlignmentAnalyzer:
    def test_matching_senses(self):
        """Equal sense counts should be OK."""
        dict_clsf = LexicalSenseFormat(
            metadata=Metadata(name="dict", language="en"),
            entries=[
                Entry(headword="run", part_of_speech="verb", language="en",
                      senses=[Sense(id="s1"), Sense(id="s2"), Sense(id="s3")]),
            ],
        )
        wn_clsf = LexicalSenseFormat(
            metadata=Metadata(name="wn", language="en"),
            entries=[
                Entry(headword="run", part_of_speech="verb", language="en",
                      senses=[Sense(id="w1"), Sense(id="w2"), Sense(id="w3")]),
            ],
        )
        analyzer = SenseAlignmentAnalyzer()
        report = analyzer.analyze(dict_clsf, wn_clsf)
        run_align = [w for w in report.words if w.headword == "run"][0]
        assert run_align.status == AlignmentStatus.OK

    def test_dictionary_fewer_senses(self, dict_with_bank, wn_with_bank):
        """Dict has fewer senses → split candidate."""
        analyzer = SenseAlignmentAnalyzer()
        report = analyzer.analyze(dict_with_bank, wn_with_bank)
        bank_align = [w for w in report.words if w.headword == "bank"][0]
        assert bank_align.status == AlignmentStatus.SPLIT_CANDIDATE
        assert bank_align.dict_count < bank_align.wn_count

    def test_dictionary_more_senses(self):
        """Dict has more senses → merge candidate."""
        dict_clsf = LexicalSenseFormat(
            metadata=Metadata(name="dict", language="en"),
            entries=[
                Entry(headword="set", part_of_speech="noun", language="en",
                      senses=[Sense(id=f"s{i}") for i in range(10)]),
            ],
        )
        wn_clsf = LexicalSenseFormat(
            metadata=Metadata(name="wn", language="en"),
            entries=[
                Entry(headword="set", part_of_speech="noun", language="en",
                      senses=[Sense(id=f"w{i}") for i in range(4)]),
            ],
        )
        analyzer = SenseAlignmentAnalyzer()
        report = analyzer.analyze(dict_clsf, wn_clsf)
        set_align = [w for w in report.words if w.headword == "set"][0]
        assert set_align.status == AlignmentStatus.MERGE_CANDIDATE

    def test_missing_in_wn(self):
        """Word not in WN → not checked."""
        dict_clsf = LexicalSenseFormat(
            metadata=Metadata(name="dict", language="en"),
            entries=[
                Entry(headword="slangword", part_of_speech="noun", language="en",
                      senses=[Sense(id="s1")]),
            ],
        )
        wn_clsf = LexicalSenseFormat(
            metadata=Metadata(name="wn", language="en"),
            entries=[],
        )
        analyzer = SenseAlignmentAnalyzer()
        report = analyzer.analyze(dict_clsf, wn_clsf)
        assert len(report.words) == 0

    def test_ratio_calculation(self, dict_with_bank, wn_with_bank):
        analyzer = SenseAlignmentAnalyzer()
        report = analyzer.analyze(dict_with_bank, wn_with_bank)
        bank_align = [w for w in report.words if w.headword == "bank"][0]
        assert bank_align.dict_count == 2
        assert bank_align.wn_count == 6
        assert abs(bank_align.ratio - 2 / 6) < 0.01

    def test_summary_stats(self, dict_with_bank, wn_with_bank):
        analyzer = SenseAlignmentAnalyzer()
        report = analyzer.analyze(dict_with_bank, wn_with_bank)
        assert report.total_checked == 2
        assert report.flagged_count >= 1  # bank should be flagged

    def test_custom_threshold(self):
        """Stricter threshold should flag more words."""
        dict_clsf = LexicalSenseFormat(
            metadata=Metadata(name="dict", language="en"),
            entries=[
                Entry(headword="run", part_of_speech="verb", language="en",
                      senses=[Sense(id="s1"), Sense(id="s2"), Sense(id="s3")]),
            ],
        )
        wn_clsf = LexicalSenseFormat(
            metadata=Metadata(name="wn", language="en"),
            entries=[
                Entry(headword="run", part_of_speech="verb", language="en",
                      senses=[Sense(id=f"w{i}") for i in range(4)]),
            ],
        )
        # Default threshold: 0.5-2.0 range, ratio 3/4=0.75 → OK
        analyzer_default = SenseAlignmentAnalyzer(threshold_low=0.5, threshold_high=2.0)
        report_default = analyzer_default.analyze(dict_clsf, wn_clsf)
        run_default = [w for w in report_default.words if w.headword == "run"][0]
        assert run_default.status == AlignmentStatus.OK

        # Stricter: 0.8-1.2, ratio 0.75 → below 0.8 → split candidate
        analyzer_strict = SenseAlignmentAnalyzer(threshold_low=0.8, threshold_high=1.2)
        report_strict = analyzer_strict.analyze(dict_clsf, wn_clsf)
        run_strict = [w for w in report_strict.words if w.headword == "run"][0]
        assert run_strict.status == AlignmentStatus.SPLIT_CANDIDATE

    def test_per_sense_matching(self, dict_with_bank, wn_with_bank):
        """Per-sense details include matched/missed status."""
        # Add translations to dictionary senses for per-sense matching
        dict_with_bank.entries[0].senses[0].translations = ["bank"]
        dict_with_bank.entries[0].senses[1].translations = ["brzeg"]

        analyzer = SenseAlignmentAnalyzer()
        report = analyzer.analyze(dict_with_bank, wn_with_bank)

        bank_alignment = next(
            (w for w in report.words if w.headword == "bank"), None
        )
        assert bank_alignment is not None
        assert bank_alignment.per_sense is not None
        assert len(bank_alignment.per_sense) == 2

        # Check that each sense has matching details
        for sense_match in bank_alignment.per_sense:
            assert "matched" in sense_match
            assert "dict_sense_id" in sense_match

    def test_per_sense_with_matching_translations(self, dict_with_bank, wn_with_bank):
        """Per-sense matching with translation overlap shows matched_translation."""
        # Update dictionary sense with a Polish translation
        dict_with_bank.entries[0].senses[0].translations = ["bank"]

        analyzer = SenseAlignmentAnalyzer()
        report = analyzer.analyze(dict_with_bank, wn_with_bank)

        bank_alignment = next(
            (w for w in report.words if w.headword == "bank"), None
        )
        assert bank_alignment is not None
        if bank_alignment.per_sense:
            for sense_match in bank_alignment.per_sense:
                if sense_match["matched"]:
                    assert "matched_translation" in sense_match
        analyzer = SenseAlignmentAnalyzer()
        report = analyzer.analyze(dict_with_bank, wn_with_bank)
        md = report.generate_report(format="markdown")
        assert "bank" in md
        assert "6" in md  # wn_count
