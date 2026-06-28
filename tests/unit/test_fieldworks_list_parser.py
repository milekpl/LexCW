"""Tests for FieldWorks list.xml parser."""

import pytest
from app.parsers.fieldworks_list_parser import FieldWorksListParser


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<lists>
  <list>
    <guidl>aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa</guidl>
    <name><str ws="Eng">Variant Types</str></name>
    <abbr><str ws="Eng">EntTyp</str></abbr>
    <cid>5118</cid>
    <items>
      <letitem>
        <guidi>bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb</guidi>
        <name>
          <str ws="Eng">Dialectal Variant</str>
          <str ws="Pol">Wariant</str>
        </name>
        <abbr>
          <str ws="Eng">dial.</str>
          <str ws="Pol">war.</str>
        </abbr>
        <descr>
          <str ws="Eng">A variant used by a specific demographic subset.</str>
        </descr>
        <subitems>
          <letitem>
            <guidi>cccccccc-cccc-cccc-cccc-cccccccccccc</guidi>
            <name><str ws="Eng">British</str></name>
            <abbr><str ws="Eng">UK</str></abbr>
          </letitem>
          <letitem>
            <guidi>dddddddd-dddd-dddd-dddd-dddddddddddd</guidi>
            <name><str ws="Eng">American</str></name>
            <abbr><str ws="Eng">US</str></abbr>
          </letitem>
        </subitems>
      </letitem>
      <letitem>
        <guidi>eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee</guidi>
        <name><str ws="Eng">Free Variant</str></name>
        <abbr/>
      </letitem>
      <letitem>
        <guidi>ffffffff-ffff-ffff-ffff-ffffffffffff</guidi>
        <name><str ws="Eng">Irregularly Inflected Form</str></name>
        <abbr><str ws="Eng">irreg. infl.</str></abbr>
      </letitem>
    </items>
  </list>
  <list>
    <guidl>11111111-1111-1111-1111-111111111111</guidl>
    <name><str ws="Eng">Parts Of Speech</str></name>
    <abbr><str ws="Eng">POS</str></abbr>
    <cid>5124</cid>
    <items>
      <positem>
        <guidi>22222222-2222-2222-2222-222222222222</guidi>
        <name><str ws="Eng">Noun</str></name>
        <abbr><str ws="Eng">n</str></abbr>
      </positem>
      <positem>
        <guidi>33333333-3333-3333-3333-333333333333</guidi>
        <name><str ws="Eng">Verb</str></name>
        <abbr><str ws="Eng">v</str></abbr>
      </positem>
    </items>
  </list>
</lists>"""


@pytest.fixture
def parser():
    return FieldWorksListParser()


class TestFieldWorksListParser:
    def test_parse_variant_types(self, parser):
        ranges = parser.parse_string(SAMPLE_XML)
        assert "variant-type" in ranges
        vt = ranges["variant-type"]
        assert vt["id"] == "variant-type"
        assert vt["label"] == "Variant Types"

    def test_variant_type_abbreviations(self, parser):
        ranges = parser.parse_string(SAMPLE_XML)
        values = ranges["variant-type"]["values"]
        assert len(values) == 3

        # Dialectal Variant
        dial = next(v for v in values if v["id"] == "dialectal-variant")
        assert dial["abbrev"] == "dial."
        assert dial["abbrevs"]["en"] == "dial."
        assert dial["abbrevs"]["pl"] == "war."  # pol -> pl (ISO 639-1)
        assert len(dial["children"]) == 2
        assert dial["children"][0]["abbrev"] == "UK"
        assert dial["children"][1]["abbrev"] == "US"

        # Free Variant (no abbreviation)
        free = next(v for v in values if v["id"] == "free-variant")
        assert "abbrev" not in free or free["abbrev"] == ""
        assert free["abbrevs"] == {}

        # Irregularly Inflected Form
        irreg = next(v for v in values if v["id"] == "irregularly-inflected-form")
        assert irreg["abbrev"] == "irreg. infl."

    def test_parse_parts_of_speech(self, parser):
        ranges = parser.parse_string(SAMPLE_XML)
        assert "grammatical-info" in ranges
        values = ranges["grammatical-info"]["values"]
        assert len(values) == 2
        noun = next(v for v in values if v["id"] == "noun")
        assert noun["abbrev"] == "n"

    def test_parse_unmapped_list_skipped(self, parser):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<lists>
  <list>
    <name><str ws="Eng">Unknown Custom List</str></name>
    <items/>
  </list>
</lists>"""
        ranges = parser.parse_string(xml)
        assert len(ranges) == 0

    def test_language_normalization_eng_to_en(self, parser):
        ranges = parser.parse_string(SAMPLE_XML)
        dial = ranges["variant-type"]["values"][0]
        assert dial["labels"]["en"] == "Dialectal Variant"
        assert dial["labels"]["pl"] == "Wariant"  # "Pol" normalized to "pl"  # pol -> pl

    def test_empty_abbreviation_not_included(self, parser):
        ranges = parser.parse_string(SAMPLE_XML)
        free = ranges["variant-type"]["values"][1]
        # Free Variant has <abbr/> (empty) — should have no abbrevs
        assert "abbrev" not in free or free.get("abbrev") == ""
        assert free["abbrevs"] == {}

    def test_output_format_matches_lift_ranges(self, parser):
        ranges = parser.parse_string(SAMPLE_XML)

        # Check that the output format is compatible with the existing
        # LIFTRangesParser format: each range has id, label, values
        vt = ranges["variant-type"]
        assert isinstance(vt, dict)
        assert "id" in vt
        assert "label" in vt
        assert "values" in vt
        assert isinstance(vt["values"], list)
