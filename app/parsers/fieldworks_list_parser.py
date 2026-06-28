"""
Parser for FieldWorks list.xml files.

list.xml is the standard FieldWorks export format for possibility lists
(CmPossibilityList objects). It contains all the real abbreviations and
labels for Variant Types, Complex Form Types, Parts of Speech, and other
controlled vocabularies used throughout the lexicon.

This parser reads list.xml and produces a dict compatible with the
existing LIFT ranges format, so imported values can be stored in BaseX
and used by the Range Editor and CSS preview.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Set

LIST_TO_RANGE_MAP: Dict[str, Optional[str]] = {
    "Complex Form Types": "complex-form-type",
    "Variant Types": "variant-type",
    "Parts Of Speech": "grammatical-info",
    "Lexical Relations": "lexical-relation",
    "Semantic Domains": "semantic-domain-ddp4",
    "Morpheme Types": "morph-type",
    "Locations": "location",
    "Anthropology Categories": "anthro-code",
    "Publications": "Publications",
    "Status": "status",
    "People": "users",
    "Usages": "usage-type",
    "Academic Domains": "domain-type",
    "Sense Types": "sense-type",
    "Dialect Labels": "dialect",
    "Restrictions": "restrictions",
    "Translation Types": "translation-type",
    "Education Levels": None,
    "Languages": None,
    "Genres": None,
    "Roles": None,
    "Confidence Levels": None,
    "Time Of Day": None,
    "Note Types": "note-type",
    "Extended Note Types": None,
    "Annotation Definitions": None,
    "Phonological Rule Features": None,
    "Productivity Restrictions": None,
    "Text Markup Tags": None,
    "Text Chart Markers": None,
    "Text Constituent Chart Templates": None,
    "Parts of Speech for Polish Reversal Index": None,
    "Parts of Speech for English Reversal Index": None,
    "Affix Categories": "affix-categories",
    "Notebook Record Types": None,
    "Positions": None,
}

ITEM_TAGS = {
    "letitem", "positem", "item", "lrtitem", "mtitem",
    "sditem", "locitem", "peritem", "aitem",
}


class FieldWorksListParser:
    """Parse FieldWorks list.xml files into the app's range format."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_file(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        ranges: Dict[str, Dict[str, Any]] = {}
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            if root.tag != "lists":
                self.logger.warning("Expected <lists> root, got <%s>", root.tag)
            ranges = self._parse_lists(root)
        except ET.ParseError as e:
            self.logger.error("Failed to parse list.xml: %s", e)
        return ranges

    def parse_string(self, xml_string: str) -> Dict[str, Dict[str, Any]]:
        root = ET.fromstring(xml_string)
        return self._parse_lists(root)

    def _parse_lists(self, root: ET.Element) -> Dict[str, Dict[str, Any]]:
        ranges: Dict[str, Dict[str, Any]] = {}
        for list_elem in root.findall("list"):
            range_data = self._parse_list(list_elem)
            if range_data is not None:
                range_id, data = range_data
                ranges[range_id] = data
        return ranges

    def _parse_list(self, list_elem: ET.Element) -> Optional[tuple]:
        name = self._get_multitext(list_elem.find("name"))
        eng_name = name.get("en", "")
        if not eng_name:
            return None

        range_id = LIST_TO_RANGE_MAP.get(eng_name)
        if range_id is None:
            self.logger.debug("Skipping unmapped list: %s", eng_name)
            return None

        items_elem = list_elem.find("items")
        values = self._parse_items(items_elem) if items_elem is not None else []

        return range_id, {
            "id": range_id,
            "label": eng_name,
            "labels": name,
            "abbrev": self._get_multitext(list_elem.find("abbr")).get("en", ""),
            "description": self._get_multitext(list_elem.find("descr")).get("en", ""),
            "values": values,
        }

    def _parse_items(self, items_elem: ET.Element) -> List[Dict[str, Any]]:
        values: List[Dict[str, Any]] = []
        for child in items_elem:
            if child.tag in ITEM_TAGS:
                value = self._parse_item(child)
                if value is not None:
                    values.append(value)
        return values

    def _parse_item(self, item_elem: ET.Element) -> Optional[Dict[str, Any]]:
        guidi = item_elem.findtext("guidi", "").strip()
        labels = self._get_multitext(item_elem.find("name"))
        eng_name = labels.get("en", "")
        # Fall back to first available language, then guidi
        display_name = eng_name or next(iter(labels.values()), guidi)
        if not display_name:
            return None

        abbrevs = self._get_multitext(item_elem.find("abbr"))
        description = self._get_multitext(item_elem.find("descr"))

        item_id = display_name.lower().replace(" ", "-")

        children: List[Dict[str, Any]] = []
        subitems = item_elem.find("subitems")
        if subitems is not None:
            children = self._parse_items(subitems)

        result: Dict[str, Any] = {
            "id": item_id,
            "guid": guidi,
            "label": eng_name,
            "labels": labels,
            "abbrevs": abbrevs,
            "description": description,
        }

        # Prefer the English abbreviation as a simple string for backward compat
        eng_abbr = abbrevs.get("en", "")
        if eng_abbr:
            result["abbrev"] = eng_abbr

        if children:
            result["children"] = children

        return result

    FW_LANG_MAP = {
        "eng": "en", "enm": "en", "fro": "fr", "fra": "fr", "fre": "fr",
        "deu": "de", "ger": "de", "spa": "es", "rus": "ru",
        "pol": "pl", "por": "pt", "ita": "it", "nld": "nl", "dut": "nl",
        "jpn": "ja", "zho": "zh", "chi": "zh", "ara": "ar",
        "hin": "hi", "ben": "bn", "tur": "tr", "vie": "vi",
        "tha": "th", "kor": "ko", "swe": "sv", "nor": "nb",
        "dan": "da", "fin": "fi", "ces": "cs", "cze": "cs",
        "hun": "hu", "ron": "ro", "rum": "ro", "ukr": "uk",
        "ell": "el", "gre": "el", "heb": "he", "ind": "id",
        "msa": "ms", "may": "ms",
    }

    @staticmethod
    def _normalize_lang(code: str) -> str:
        """Normalize FieldWorks 3-letter language codes to 2-letter ISO 639-1 codes."""
        lower = code.strip().lower()
        return FieldWorksListParser.FW_LANG_MAP.get(lower, lower)

    def to_lift_ranges_xml(self, ranges: Dict[str, Dict[str, Any]]) -> str:
        """Convert parsed list.xml data into LIFT ranges XML format.

        The output can be stored in BaseX and parsed by LIFTRangesParser.
        """
        lines: list[str] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<lift-ranges>',
        ]
        for rid in sorted(ranges.keys()):
            rdata = ranges[rid]
            lines.append(f'  <range id="{rid}">')
            for val in rdata.get("values", []):
                lines += self._value_to_lift_xml(val, indent=4)
            lines.append("  </range>")
        lines.append("</lift-ranges>")
        return "\n".join(lines)

    def _value_to_lift_xml(self, val: Dict[str, Any], indent: int = 4) -> list[str]:
        """Convert a parsed value dict to LIFT range-element XML lines."""
        indent_s = " " * indent
        guid = val.get("guid", "")
        vid = val.get("id", "")
        attrs = f'id="{vid}"'
        if guid:
            attrs += f' guid="{guid}"'
        lines = [f'{indent_s}<range-element {attrs}>']

        labels = val.get("labels", {})
        if labels:
            lines.append(f'{indent_s}  <label>')
            for lang, text in sorted(labels.items()):
                lines.append(f'{indent_s}    <form lang="{lang}"><text>{self._xml_escape(text)}</text></form>')
            lines.append(f'{indent_s}  </label>')

        abbrevs = val.get("abbrevs", {})
        if abbrevs:
            lines.append(f'{indent_s}  <abbrev>')
            for lang, text in sorted(abbrevs.items()):
                lines.append(f'{indent_s}    <form lang="{lang}"><text>{self._xml_escape(text)}</text></form>')
            lines.append(f'{indent_s}  </abbrev>')

        description = val.get("description", {})
        if description:
            lines.append(f'{indent_s}  <description>')
            for lang, text in sorted(description.items()):
                lines.append(f'{indent_s}    <form lang="{lang}"><text>{self._xml_escape(text)}</text></form>')
            lines.append(f'{indent_s}  </description>')

        for child in val.get("children", []):
            lines += self._value_to_lift_xml(child, indent + 2)

        lines.append(f"{indent_s}</range-element>")
        return lines

    @staticmethod
    def _xml_escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _get_multitext(self, parent: Optional[ET.Element]) -> Dict[str, str]:
        """Extract multilingual text from <name>, <abbr>, <descr> etc.

        These elements contain <str ws="Eng">text</str> children.
        Normalizes FieldWorks 3-letter codes to 2-letter ISO 639-1.
        """
        result: Dict[str, str] = {}
        if parent is None:
            return result
        for str_elem in parent.findall("str"):
            ws = self._normalize_lang(str_elem.get("ws", ""))
            text = str_elem.text or ""
            if ws and text.strip():
                result[ws] = text.strip()
        return result
