"""
Unit tests for CoverageService.

Tests the orchestration service that coordinates providers, analyzers,
and report generation.
"""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from app.services.coverage_check.coverage_service import CoverageService
from app.services.coverage_check.models import (
    LexicalSenseFormat, Metadata, Entry, Sense,
)


@pytest.fixture
def service():
    return CoverageService()


class TestCoverageService:
    def test_check_resource_coverage_text(self, service, tmp_path):
        words = "cat\ndog\nbird\nrun\n"
        f = tmp_path / "words.txt"
        f.write_text(words, encoding="utf-8")

        result = service.check_resource_coverage(
            source_path=str(f),
            resource_type="text",
            language="en",
        )
        assert result is not None
        assert "entries" in result
        assert len(result["entries"]) >= 3

    def test_check_resource_coverage_subtlex(self, service, tmp_path):
        content = "word\tLgCount\tCd\nbank\t2000\t1.5\ncat\t5000\t0.8\n"
        f = tmp_path / "subtlex.txt"
        f.write_text(content, encoding="utf-8")

        result = service.check_resource_coverage(
            source_path=str(f),
            resource_type="subtlex",
            language="en",
        )
        assert result is not None
        assert len(result["entries"]) == 2

    def test_check_text_coverage(self, service):
        text = "The cats are running in the garden."
        result = service.check_text_coverage(text, language="en")
        assert result is not None
        assert "entries" in result
        assert len(result["entries"]) > 0

    def test_check_systematicity(self, service):
        result = service.check_systematicity(language="en")
        assert result is not None
        assert "total_checks" in result
        assert result["total_checks"] > 0
        assert "checks" in result

    def test_check_sense_alignment(self, service):
        result = service.check_sense_alignment(language="en")
        assert result is not None
        assert "total_checked" in result
        assert "words" in result

    def test_get_wordnet_entry(self, service):
        entry = service.get_wordnet_entry("bank")
        assert entry is not None
        assert entry.headword == "bank"
        assert len(entry.senses) > 0

    def test_get_wordnet_synset_count(self, service):
        count = service.get_wordnet_synset_count("bank")
        assert count >= 5

    def test_gap_analysis(self, service):
        """Test gap analysis between two CLSF datasets."""
        baseline = LexicalSenseFormat(
            metadata=Metadata(name="wn", language="en"),
            entries=[
                Entry(headword="cat", language="en",
                      senses=[Sense(id="s1", definition="feline")]),
                Entry(headword="car", language="en",
                      senses=[Sense(id="s2", definition="automobile")]),
            ],
        )
        dictionary = LexicalSenseFormat(
            metadata=Metadata(name="dict", language="en"),
            entries=[
                Entry(headword="cat", language="en",
                      senses=[Sense(id="s3", definition="feline")]),
            ],
        )
        result = service.run_gap_analysis(baseline, dictionary)
        assert result is not None
        assert "summary" in result
        assert result["summary"]["headword_coverage"] == 50.0
