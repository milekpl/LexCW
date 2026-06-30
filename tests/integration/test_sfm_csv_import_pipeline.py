"""
Integration tests for SFM and CSV import pipeline (parse -> convert -> store).

Verifies:
1. Generated LIFT XML has bare `lang` (not `xml:lang`) — matches parser expectations
2. Every `<entry>` and `<sense>` has UUID `id`/`guid`
3. Pronunciation language codes (`seh-fonipa`) are correctly preserved
4. Full round-trip: import from SFM/CSV → verify in BaseX
"""

from __future__ import annotations

import io
import re
import uuid as uuid_mod
import xml.etree.ElementTree as ET
from typing import Any

import pytest

from app.services.sfm_parser import SFMParser, ParsedDocument, ParsedField
from app.services.csv_parser import CSVParser
from app.services.import_converter import build_lift_tree, import_parsed_document
from app.services.dictionary_service import DictionaryService


# ── SFM test data ──────────────────────────────────────────────────────────

SFM_DATA = """\\lx dog-whistle
\\ph ˈdɒɡ wɪsəl
\\ps noun
\\d sygnał dla wybranych
\\xv Eng: His speech contained a dog-whistle that resonated with his base.

\\lx yarnbomb
\\ph ˈjɑːnbɒm
\\ps verb
\\d bombardować włóczką
\\xv Eng: The local park was yarnbombed with colorful knitwear."""

SFM_FIELD_MAP: dict[str, dict] = {
    "lx": {"lift_element": "lexeme", "level": "entry", "is_key": True, "field_type": "normal"},
    "ph": {"lift_element": "pronunciation_form", "level": "pronunciation", "is_key": False, "field_type": "normal", "lang": "seh-fonipa"},
    "ps": {"lift_element": "grammatical_info", "level": "sense", "is_key": False, "field_type": "normal"},
    "d":  {"lift_element": "definition", "level": "sense", "is_key": False, "field_type": "normal", "lang": "pl"},
    "xv": {"lift_element": "example_form", "level": "example", "is_key": False, "field_type": "normal", "lang": "en"},
}

# ── CSV test data ──────────────────────────────────────────────────────────

CSV_DATA = """headword,pos,definition
cat,noun,a small domesticated carnivore
dog,noun,a domesticated canine"""

CSV_FIELD_MAP: dict[str, dict] = {
    "headword":   {"lift_element": "lexeme", "level": "entry", "is_key": True, "field_type": "normal"},
    "pos":        {"lift_element": "grammatical_info", "level": "sense", "is_key": False, "field_type": "normal"},
    "definition": {"lift_element": "definition", "level": "sense", "is_key": False, "field_type": "normal", "lang": "en"},
}


# ── Helpers ────────────────────────────────────────────────────────────────

def _iter_entries(root: ET.Element) -> list[ET.Element]:
    return [e for e in root if e.tag == "entry"]


def _find_tag(parent: ET.Element, tag: str) -> ET.Element | None:
    return parent.find(tag)


def _parse_xml(xml_str: str) -> ET.Element:
    return ET.fromstring(xml_str)


def _assert_lang_not_xml_lang(el: ET.Element, path: str):
    """Assert element at *path* from *el* has bare `lang`, not `xml:lang`."""
    parts = path.strip("/").split("/")
    current = el
    for p in parts:
        found = None
        for child in current:
            if child.tag == p or child.tag.endswith("}" + p):
                found = child
                break
        assert found is not None, f"Element <{p}> not found in path {path}"
        current = found
    # Check for xml:lang (XML namespace qualified)
    xml_ns_lang = current.get("{http://www.w3.org/XML/1998/namespace}lang")
    bare_lang = current.get("lang")
    assert xml_ns_lang is None, (
        f"Element <{current.tag}> has xml:lang='{xml_ns_lang}' "
        f"instead of lang='{bare_lang}' at path {path}"
    )
    return current


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def sfm_doc() -> ParsedDocument:
    parser = SFMParser(
        entry_keys={"lx"},
        sense_keys={"ps"},
        example_keys={"xv"},
        pronun_keys={"ph"},
    )
    return parser.parse(SFM_DATA)


@pytest.fixture
def csv_doc():
    parser = CSVParser()
    return parser.parse(CSV_DATA)


# ══════════════════════════════════════════════════════════════════════════
# SFM tests
# ══════════════════════════════════════════════════════════════════════════

class TestSFMImportPipeline:

    def test_sfm_parses_correctly(self, sfm_doc: ParsedDocument):
        assert len(sfm_doc.entries) == 2
        e1 = sfm_doc.entries[0]
        assert [f.value for f in e1.fields if f.marker == "lx"] == ["dog-whistle"]

    def test_sfm_lift_tree_uses_bare_lang(self, sfm_doc: ParsedDocument):
        """The generated XML uses bare `lang`, not `xml:lang`."""
        root, _ = build_lift_tree(sfm_doc, SFM_FIELD_MAP, {}, "sfm")
        entries = _iter_entries(root)
        assert len(entries) == 2

        for entry_el in entries:
            # Every <form> anywhere in the tree should have bare lang (never xml:lang)
            for form in entry_el.iter("form"):
                xml_lang = form.get("{http://www.w3.org/XML/1998/namespace}lang")
                assert xml_lang is None, (
                    f"Found xml:lang={xml_lang} on <form>: "
                    f"{ET.tostring(form, encoding='unicode')[:200]}"
                )
                # If a <form> has no lang attribute, that's OK — some elements
                # (e.g. lexeme) don't configure a language;
                # but when present it must be bare `lang`
                bare = form.get("lang")
                if bare:
                    assert bare in ("en", "pl", "seh-fonipa"), f"Unexpected lang={bare!r}"

    def test_sfm_entries_have_uuid_id_and_guid(self, sfm_doc: ParsedDocument):
        root, _ = build_lift_tree(sfm_doc, SFM_FIELD_MAP, {}, "sfm")
        for entry_el in _iter_entries(root):
            eid = entry_el.get("id")
            guid = entry_el.get("guid")
            assert eid, f"Entry missing @id"
            assert guid, f"Entry missing @guid"
            assert uuid_mod.UUID(eid), f"Entry @id={eid} is not a valid UUID"
            assert uuid_mod.UUID(guid), f"Entry @guid={guid} is not a valid UUID"
            # Senses should also have id
            for sense in entry_el.iter("sense"):
                sid = sense.get("id")
                assert sid, f"Sense missing @id"
                assert uuid_mod.UUID(sid), f"Sense @id={sid} is not a valid UUID"

    def test_sfm_pronunciation_preserves_seh_fonipa(self, sfm_doc: ParsedDocument):
        root, _ = build_lift_tree(sfm_doc, SFM_FIELD_MAP, {}, "sfm")
        for entry_el in _iter_entries(root):
            pron = _find_tag(entry_el, "pronunciation")
            if pron is not None:
                pform = _find_tag(pron, "form")
                assert pform is not None
                lang = pform.get("lang")
                assert lang == "seh-fonipa", (
                    f"Expected lang='seh-fonipa', got lang={lang!r}: "
                    f"{ET.tostring(pron, encoding='unicode')}"
                )

    def test_sfm_roundtrip_import(self, sfm_doc: ParsedDocument, dict_service_with_db):
        """Full pipeline: parse → convert → import to BaseX → verify retrieval."""
        svc = dict_service_with_db
        initial_count = int(svc.db_connector.execute_query("count(//entry)") or 0)

        result = import_parsed_document(sfm_doc, SFM_FIELD_MAP, {}, svc, mode="merge")
        assert result["imported"] == 2

        # Verify entries landed in BaseX
        after_count = int(svc.db_connector.execute_query("count(//entry)") or 0)
        assert after_count == initial_count + 2

        # Verify they have UUID ids
        no_id = int(svc.db_connector.execute_query("count(//entry[not(@id)])") or 0)
        assert no_id == 0

        # Verify all form elements use bare lang (not xml:lang)
        xml_lang_count = int(
            svc.db_connector.execute_query("count(//form[@xml:lang])") or 0
        )
        assert xml_lang_count == 0, f"Found {xml_lang_count} <form> elements with xml:lang"

        # Verify pronunciations have seh-fonipa
        bad_pron = svc.db_connector.execute_query("count(//pronunciation/form[@lang='und'])")
        assert int(bad_pron or 0) == 0, "Found pronunciations with lang='und'"

        # Fetch one entry by id and verify pronunciation
        entry_xml = svc.db_connector.execute_query(
            "serialize((//entry[lexical-unit/form/text='dog-whistle'])[1])"
        )
        assert "lang=\"seh-fonipa\"" in entry_xml, (
            f"Missing lang='seh-fonipa' in stored entry:\n{entry_xml[:300]}"
        )
        assert "xml:lang" not in entry_xml, (
            f"Stored entry still has xml:lang:\n{entry_xml[:300]}"
        )


# ══════════════════════════════════════════════════════════════════════════
# CSV tests
# ══════════════════════════════════════════════════════════════════════════

class TestCSVImportPipeline:

    def test_csv_parses_correctly(self, csv_doc):
        assert len(csv_doc.rows) == 2
        assert csv_doc.rows[0].columns["headword"] == "cat"

    def test_csv_lift_tree_uses_bare_lang(self, csv_doc):
        root, _ = build_lift_tree(csv_doc, CSV_FIELD_MAP, {}, "csv")
        entries = _iter_entries(root)
        assert len(entries) == 2

        for entry_el in entries:
            for form in entry_el.iter("form"):
                xml_lang = form.get("{http://www.w3.org/XML/1998/namespace}lang")
                assert xml_lang is None, (
                    f"Found xml:lang={xml_lang} on <form> in CSV output"
                )

    def test_csv_entries_have_uuid_id_and_guid(self, csv_doc):
        root, _ = build_lift_tree(csv_doc, CSV_FIELD_MAP, {}, "csv")
        for entry_el in _iter_entries(root):
            eid = entry_el.get("id")
            guid = entry_el.get("guid")
            assert eid, "CSV entry missing @id"
            assert guid, "CSV entry missing @guid"
            assert uuid_mod.UUID(eid)
            assert uuid_mod.UUID(guid)

    def test_csv_roundtrip_import(self, csv_doc, dict_service_with_db):
        svc = dict_service_with_db
        initial_count = int(svc.db_connector.execute_query("count(//entry)") or 0)

        result = import_parsed_document(csv_doc, CSV_FIELD_MAP, {}, svc, mode="merge", file_type="csv")
        assert result["imported"] == 2

        after_count = int(svc.db_connector.execute_query("count(//entry)") or 0)
        assert after_count == initial_count + 2

        # Verify zero forms with xml:lang
        xml_lang_count = int(
            svc.db_connector.execute_query("count(//form[@xml:lang])") or 0
        )
        assert xml_lang_count == 0

        # Verify entries have UUID ids
        no_id = int(svc.db_connector.execute_query("count(//entry[not(@id)])") or 0)
        assert no_id == 0

        # Verify entries retrievable by @id
        entry_xml = svc.db_connector.execute_query(
            "serialize((//entry[lexical-unit/form/text='cat'])[1])"
        )
        assert '<entry' in entry_xml
        assert 'xml:lang' not in entry_xml


# ══════════════════════════════════════════════════════════════════════════
# Edge cases
# ══════════════════════════════════════════════════════════════════════════

class TestImportEdgeCases:

    def test_empty_sfm_produces_no_entries(self):
        parser = SFMParser(entry_keys={"lx"}, sense_keys={"ps"})
        doc = parser.parse("")
        assert len(doc.entries) == 0

    def test_sfm_with_only_key_produces_entry_without_sense(self):
        parser = SFMParser(entry_keys={"lx"}, sense_keys={"ps"})
        doc = parser.parse("\\lx lonely")
        assert len(doc.entries) == 1

    def test_xml_lang_is_never_generated(self, sfm_doc: ParsedDocument):
        """Definitive check: scan raw XML output for xml:lang anywhere."""
        root, _ = build_lift_tree(sfm_doc, SFM_FIELD_MAP, {}, "sfm")
        raw = ET.tostring(root, encoding="unicode")
        assert 'xml:lang' not in raw, (
            f"Found xml:lang in output:\n{raw[:500]}"
        )

    def test_csv_xml_lang_is_never_generated(self, csv_doc):
        root, _ = build_lift_tree(csv_doc, CSV_FIELD_MAP, {}, "csv")
        raw = ET.tostring(root, encoding="unicode")
        assert 'xml:lang' not in raw, (
            f"Found xml:lang in CSV output:\n{raw[:500]}"
        )
