"""
Generic Shoebox / Standard Format Marker (SFM) parser.

Fully marker-agnostic — no hardcoded markers. Uses an ImportMapping to
interpret marker semantics. Can auto-detect key markers from the data
when no mapping is provided.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from collections import Counter

logger = logging.getLogger(__name__)


# -- Intermediate data model -----------------------------------------------


@dataclass
class ParsedField:
    marker: str
    value: str
    lang: Optional[str] = None


@dataclass
class ParsedCrossRef:
    source_marker: str
    source_value: str
    target_marker: str
    target_value: str
    target_sense: Optional[int] = None


@dataclass
class ParsedVariantRef:
    target_marker: str
    target_value: str
    type_marker: str
    type_value: Optional[str] = None


@dataclass
class ParsedExample:
    fields: list[ParsedField] = field(default_factory=list)


@dataclass
class ParsedSense:
    fields: list[ParsedField] = field(default_factory=list)
    examples: list[ParsedExample] = field(default_factory=list)


@dataclass
class ParsedPronunciation:
    fields: list[ParsedField] = field(default_factory=list)


@dataclass
class ParsedVariant:
    fields: list[ParsedField] = field(default_factory=list)


@dataclass
class ParsedEntry:
    fields: list[ParsedField] = field(default_factory=list)
    senses: list[ParsedSense] = field(default_factory=list)
    pronunciations: list[ParsedPronunciation] = field(default_factory=list)
    variants: list[ParsedVariant] = field(default_factory=list)
    cross_refs: list[ParsedCrossRef] = field(default_factory=list)
    variant_refs: list[ParsedVariantRef] = field(default_factory=list)


@dataclass
class ParsedDocument:
    entries: list[ParsedEntry] = field(default_factory=list)


# -- Marker pattern --------------------------------------------------------

MARKER_RE = re.compile(r"\\([a-zA-Z][a-zA-Z0-9_-]*)(?:_([a-zA-Z]+))?")


def _parse_marker_line(line: str) -> tuple[Optional[str], Optional[str], str]:
    """Parse a single SFM line into (marker, lang, value).

    Returns (None, None, line) if line has no marker.
    """
    stripped = line.strip()
    if not stripped.startswith("\\"):
        return None, None, stripped
    m = MARKER_RE.match(stripped)
    if not m:
        return None, None, stripped
    marker = m.group(1)
    lang = m.group(2)
    value = stripped[m.end() :].strip()
    return marker, lang, value


# -- Level hierarchy constants (sensible defaults for auto-detect) ---------

# Default key markers per level — only used when no mapping is provided.
# These match the MDF (Multi-Dictionary Formatter) convention.
DEFAULT_ENTRY_KEYS = {"lx"}
DEFAULT_SENSE_KEYS = {"sn", "ps"}
DEFAULT_EXAMPLE_KEYS = {"xv"}
DEFAULT_PRONUN_KEYS = {"ph"}
DEFAULT_VARIANT_KEYS = {"am"}

# Markers that begin a cross-reference pair
CROSS_REF_SOURCE_KEYS = {"lf"}
CROSS_REF_TARGET_KEYS = {"lv"}
CROSS_REF_END_KEYS = {"le"}
VARIANT_TARGET_KEYS = {"mn"}
VARIANT_TYPE_KEYS = {"vt"}


# -- Parser ----------------------------------------------------------------


class SFMParser:
    """Parse SFM (Standard Format Marker) text into a ParsedDocument.

    Args:
        entry_keys: Marker names that start a new entry (e.g. {"lx"}).
        sense_keys: Marker names that start a new sense (e.g. {"sn", "ps"}).
        example_keys: Marker names that start a new example (e.g. {"xv"}).
        pronun_keys: Marker names that start a new pronunciation (e.g. {"ph"}).
        cross_ref_source: Marker name for cross-ref source (e.g. {"lf"}).
        cross_ref_target: Marker name for cross-ref target (e.g. {"lv"}).
        cross_ref_end: Marker name that ends a cross-ref block (e.g. {"le"}).
        variant_target: Marker for main-entry variant target (e.g. {"mn"}).
        variant_type: Marker for variant type (e.g. {"vt"}).
        language_map: Optional dict mapping source language codes to target
                      (e.g. {"Vernacular": "en", "National": "pl"}).
    """

    def __init__(
        self,
        entry_keys: Optional[set[str]] = None,
        sense_keys: Optional[set[str]] = None,
        example_keys: Optional[set[str]] = None,
        pronun_keys: Optional[set[str]] = None,
        variant_keys: Optional[set[str]] = None,
        cross_ref_source: Optional[set[str]] = None,
        cross_ref_target: Optional[set[str]] = None,
        cross_ref_end: Optional[set[str]] = None,
        variant_target: Optional[set[str]] = None,
        variant_type: Optional[set[str]] = None,
        language_map: Optional[dict[str, str]] = None,
        **kwargs,
    ):
        self.entry_keys = entry_keys or DEFAULT_ENTRY_KEYS
        self.sense_keys = sense_keys or DEFAULT_SENSE_KEYS
        self.example_keys = example_keys or DEFAULT_EXAMPLE_KEYS
        self.pronun_keys = pronun_keys or DEFAULT_PRONUN_KEYS
        self.variant_keys = variant_keys or DEFAULT_VARIANT_KEYS
        self.cross_ref_source = cross_ref_source or CROSS_REF_SOURCE_KEYS
        self.cross_ref_target = cross_ref_target or CROSS_REF_TARGET_KEYS
        self.cross_ref_end = cross_ref_end or CROSS_REF_END_KEYS
        self.variant_target = variant_target or VARIANT_TARGET_KEYS
        self.variant_type = variant_type or VARIANT_TYPE_KEYS
        self.language_map = language_map or {}

        # Markers that are valid within a pronunciation section.
        self.pronun_field_keys: set[str] = (
            kwargs.get("pronun_field_keys")
            or self.pronun_keys
            or DEFAULT_PRONUN_KEYS
        )

        # Markers that are valid within an example section.
        self.example_field_keys: set[str] = (
            kwargs.get("example_field_keys")
            or self.example_keys
            or DEFAULT_EXAMPLE_KEYS
        )

        # Markers that are valid within a variant section.
        self.variant_field_keys: set[str] = (
            kwargs.get("variant_field_keys")
            or self.variant_keys
            or DEFAULT_VARIANT_KEYS
        )

    @classmethod
    def auto_detect(
        cls,
        text: str,
        language_map: Optional[dict[str, str]] = None,
    ) -> "SFMParser":
        """Auto-detect key markers from the file content.

        Heuristic: split on blank lines; the marker that most consistently
        appears at the start of records is the entry key. Sense/example
        keys are detected by frequency within records.
        """
        records = re.split(r"\n\s*\n", text.strip())
        first_markers: Counter = Counter()
        all_markers: Counter = Counter()

        for rec in records:
            lines = [l.strip() for l in rec.split("\n") if l.strip()]
            if not lines:
                continue
            marker, _, _ = _parse_marker_line(lines[0])
            if marker:
                first_markers[marker] += 1
            for line in lines:
                m, _, _ = _parse_marker_line(line)
                if m:
                    all_markers[m] += 1

        entry_keys: set[str] = set()
        if first_markers:
            max_first = first_markers.most_common(1)[0][1]
            entry_keys = {
                m for m, c in first_markers.items()
                if c >= max_first * 0.5 and c >= 2
            }

        if not entry_keys and all_markers:
            entry_keys = {all_markers.most_common(1)[0][0]}

        # Sense keys: markers that appear frequently but are NOT entry keys
        sense_keys: set[str] = set()
        example_keys: set[str] = set()
        pronun_keys: set[str] = set()
        variant_keys: set[str] = set()
        for marker, count in all_markers.most_common():
            if marker in entry_keys:
                continue
            if count >= 2:
                if marker.startswith("xv") or marker.startswith("ex"):
                    example_keys.add(marker)
                elif marker.startswith("ph") or marker.startswith("pr"):
                    pronun_keys.add(marker)
                elif marker.startswith("am") or marker.startswith("al"):
                    variant_keys.add(marker)
                else:
                    sense_keys.add(marker)

        return cls(
            entry_keys=entry_keys or DEFAULT_ENTRY_KEYS,
            sense_keys=sense_keys or DEFAULT_SENSE_KEYS,
            example_keys=example_keys or DEFAULT_EXAMPLE_KEYS,
            pronun_keys=pronun_keys or DEFAULT_PRONUN_KEYS,
            variant_keys=variant_keys or DEFAULT_VARIANT_KEYS,
            pronun_field_keys=pronun_keys or DEFAULT_PRONUN_KEYS,
            example_field_keys=example_keys or DEFAULT_EXAMPLE_KEYS,
            variant_field_keys=variant_keys or DEFAULT_VARIANT_KEYS,
            language_map=language_map or {},
        )

    def parse(self, text: str) -> ParsedDocument:
        """Parse SFM text into a structured document."""
        doc = ParsedDocument()
        lines = text.split("\n")
        entries: list[ParsedEntry] = []
        current_entry: Optional[ParsedEntry] = None
        current_sense: Optional[ParsedSense] = None
        current_example: Optional[ParsedExample] = None
        current_pronun: Optional[ParsedPronunciation] = None
        current_variant: Optional[ParsedVariant] = None

        in_cross_ref = False
        cross_ref_source: Optional[ParsedField] = None

        for line in lines:
            marker, lang, value = _parse_marker_line(line)

            # Non-marker line — append to previous field value if applicable
            if marker is None:
                if (
                    current_entry
                    and current_entry.fields
                    and value
                ):
                    current_entry.fields[-1].value += " " + value
                continue

            # -- Check for cross-ref start ---------------------------------
            if marker in self.cross_ref_source:
                in_cross_ref = True
                cross_ref_source = ParsedField(marker=marker, value=value, lang=lang)
                continue

            if marker in self.cross_ref_target and in_cross_ref and cross_ref_source:
                # Parse target for possible sense number suffix
                target_value = value
                target_sense: Optional[int] = None
                sense_match = re.search(r"\s+(\d+)$", value)
                if sense_match:
                    target_value = value[: sense_match.start()].strip()
                    target_sense = int(sense_match.group(1))
                ref = ParsedCrossRef(
                    source_marker=cross_ref_source.marker,
                    source_value=cross_ref_source.value,
                    target_marker=marker,
                    target_value=target_value,
                    target_sense=target_sense,
                )
                if current_entry:
                    current_entry.cross_refs.append(ref)
                cross_ref_source = None
                in_cross_ref = False
                continue

            if marker in self.cross_ref_end:
                in_cross_ref = False
                cross_ref_source = None
                continue

            # -- Check for variant ref --------------------------------------
            if marker in self.variant_target:
                # \mn value — the headword this entry is a variant of
                # Collect it and wait for variant_type on next marker
                if current_entry:
                    current_entry.variant_refs.append(ParsedVariantRef(
                        target_marker=marker,
                        target_value=value,
                        type_marker="",
                        type_value=None,
                    ))
                continue

            if marker in self.variant_type and current_entry and current_entry.variant_refs:
                current_entry.variant_refs[-1].type_marker = marker
                current_entry.variant_refs[-1].type_value = value
                continue

            # -- Check for level-start markers -----------------------------
            if marker in self.entry_keys:
                current_entry = ParsedEntry()
                entries.append(current_entry)
                current_sense = None
                current_example = None
                current_pronun = None
                in_cross_ref = False
                cross_ref_source = None

            elif marker in self.sense_keys:
                new_sense = ParsedSense()
                if current_entry is None:
                    current_entry = ParsedEntry()
                    entries.append(current_entry)
                current_entry.senses.append(new_sense)
                current_sense = new_sense
                current_example = None

            elif marker in self.example_keys:
                new_example = ParsedExample()
                target = current_sense if current_sense else current_entry
                if target is not None:
                    if current_sense is None and current_entry is None:
                        current_entry = ParsedEntry()
                        entries.append(current_entry)
                    if current_sense is None:
                        current_entry.senses.append(ParsedSense())
                        current_sense = current_entry.senses[-1]
                    current_sense.examples.append(new_example)
                    current_example = new_example

            elif marker in self.pronun_keys:
                if current_entry is None:
                    current_entry = ParsedEntry()
                    entries.append(current_entry)
                current_pronun = ParsedPronunciation()
                current_entry.pronunciations.append(current_pronun)

            elif marker in self.variant_keys:
                if current_entry is None:
                    current_entry = ParsedEntry()
                    entries.append(current_entry)
                current_variant = ParsedVariant()
                current_entry.variants.append(current_variant)

            # -- Auto-close pronunciation/example/variant if marker doesn't belong --
            if current_pronun is not None and marker not in self.pronun_field_keys:
                current_pronun = None
            if current_example is not None and marker not in self.example_field_keys:
                current_example = None
            if current_variant is not None and marker not in self.variant_field_keys:
                current_variant = None

            # -- Add field to current container ----------------------------
            pf = ParsedField(marker=marker, value=value, lang=lang)

            if current_example is not None:
                current_example.fields.append(pf)
            elif current_pronun is not None:
                current_pronun.fields.append(pf)
            elif current_variant is not None:
                current_variant.fields.append(pf)
            elif current_sense is not None:
                current_sense.fields.append(pf)
            elif current_entry is not None:
                current_entry.fields.append(pf)
            else:
                # Orphaned field before any entry — start one
                current_entry = ParsedEntry()
                entries.append(current_entry)
                current_entry.fields.append(pf)

        doc.entries = entries
        return doc
