"""
Unit tests for systematicity checker.

Tests checking dictionary coverage against predefined reference categories.
"""
import pytest
from app.services.coverage_check.models import (
    LexicalSenseFormat, Metadata, Entry, Sense,
)
from app.services.coverage_check.systematicity_checker import (
    SystematicityChecker, SystematicityCategory, SystematicityReport,
)


@pytest.fixture
def dict_with_elements():
    """Dictionary that has some chemical elements."""
    return LexicalSenseFormat(
        metadata=Metadata(name="test-dict", language="en"),
        entries=[
            Entry(headword="hydrogen", language="en",
                  senses=[Sense(id="s1", definition="element 1")]),
            Entry(headword="helium", language="en",
                  senses=[Sense(id="s2", definition="element 2")]),
            Entry(headword="oxygen", language="en",
                  senses=[Sense(id="s3", definition="element 8")]),
            Entry(headword="iron", language="en",
                  senses=[Sense(id="s4", definition="element 26")]),
            Entry(headword="gold", language="en",
                  senses=[Sense(id="s5", definition="element 79")]),
        ],
    )


class TestSystematicityChecker:
    def test_missing_elements(self, dict_with_elements):
        checker = SystematicityChecker(language="en")
        report = checker.check(dict_with_elements)
        assert isinstance(report, SystematicityReport)
        # Only 5 of 118 elements present
        elem_checks = [c for c in report.checks
                       if c.category == SystematicityCategory.CHEMICAL_ELEMENT]
        assert len(elem_checks) == 1
        assert elem_checks[0].found_count == 5
        assert elem_checks[0].missing_count == 113

    def test_coverage_percentage(self, dict_with_elements):
        checker = SystematicityChecker(language="en")
        report = checker.check(dict_with_elements)
        elem_checks = [c for c in report.checks
                       if c.category == SystematicityCategory.CHEMICAL_ELEMENT]
        assert elem_checks[0].coverage_percent < 10.0  # 5/118

    def test_found_items(self, dict_with_elements):
        checker = SystematicityChecker(language="en")
        report = checker.check(dict_with_elements)
        elem_checks = [c for c in report.checks
                       if c.category == SystematicityCategory.CHEMICAL_ELEMENT]
        found = set(elem_checks[0].found_items)
        assert "hydrogen" in found
        assert "helium" in found
        assert "iron" in found

    def test_missing_items(self, dict_with_elements):
        checker = SystematicityChecker(language="en")
        report = checker.check(dict_with_elements)
        elem_checks = [c for c in report.checks
                       if c.category == SystematicityCategory.CHEMICAL_ELEMENT]
        missing = set(elem_checks[0].missing_items)
        assert "carbon" in missing
        assert "nitrogen" in missing

    def test_calendar_months(self):
        dict_with_months = LexicalSenseFormat(
            metadata=Metadata(name="test", language="en"),
            entries=[
                Entry(headword=m, language="en", senses=[Sense()])
                for m in ["january", "february", "march", "april", "may", "june",
                          "july", "august", "september", "october", "november", "december"]
            ],
        )
        checker = SystematicityChecker(language="en")
        report = checker.check(dict_with_months)
        cal_checks = [c for c in report.checks
                      if c.category == SystematicityCategory.CALENDAR_MONTH]
        assert len(cal_checks) == 1
        assert cal_checks[0].coverage_percent == 100.0

    def test_country_coverage(self):
        # Just test that it runs without error on a small dict
        small_dict = LexicalSenseFormat(
            metadata=Metadata(name="test", language="en"),
            entries=[
                Entry(headword="poland", language="en", senses=[Sense()]),
                Entry(headword="germany", language="en", senses=[Sense()]),
                Entry(headword="france", language="en", senses=[Sense()]),
            ],
        )
        checker = SystematicityChecker(language="en")
        report = checker.check(small_dict)
        geo_checks = [c for c in report.checks
                      if c.category == SystematicityCategory.GEOGRAPHY_COUNTRY]
        assert len(geo_checks) == 1
        assert geo_checks[0].found_count >= 3

    def test_report_markdown(self, dict_with_elements):
        checker = SystematicityChecker(language="en")
        report = checker.check(dict_with_elements)
        md = report.generate_report(format="markdown")
        assert "Systematicity" in md or "chemical_element" in md.lower()

    def test_overall_coverage(self, dict_with_elements):
        checker = SystematicityChecker(language="en")
        report = checker.check(dict_with_elements)
        assert 0 <= report.overall_coverage <= 100.0
        assert report.total_checks > 0

    def test_custom_category(self):
        """Test that custom categories can be added."""
        checker = SystematicityChecker(language="en")
        checker.add_custom_category(
            "custom_fruits",
            ["apple", "banana", "cherry", "date", "elderberry"],
        )
        dict_with_fruits = LexicalSenseFormat(
            metadata=Metadata(name="test", language="en"),
            entries=[
                Entry(headword="apple", language="en", senses=[Sense()]),
                Entry(headword="cherry", language="en", senses=[Sense()]),
            ],
        )
        report = checker.check(dict_with_fruits)
        custom_checks = [c for c in report.checks
                         if getattr(c, 'category_name', None) == "custom_fruits"]
        assert len(custom_checks) == 1
        assert custom_checks[0].found_count == 2
        assert custom_checks[0].missing_count == 3
