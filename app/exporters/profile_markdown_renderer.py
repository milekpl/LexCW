"""
Profile-driven Markdown renderer.

Reads a DisplayProfile to determine field selection, ordering,
visibility, and abbreviation rules, then emits Markdown.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict, Set
from collections import defaultdict

from app.models.display_profile import DisplayProfile, ProfileElement
from app.models.entry import Entry
from app.models.sense import Sense
from app.services.dictionary_service import DictionaryService
from app.services.css_mapping_service import CSSMappingService


logger = logging.getLogger(__name__)


# -- Constants -----------------------------------------------------------

ELEMENT_CATEGORY: dict[str, str] = {
    "lexical-unit": "entry",
    "citation": "entry",
    "pronunciation": "entry",
    "variant": "entry",
    "variant-relation": "entry",
    "relation": "entry",
    "etymology": "entry",
    "note": "entry|sense",
    "field": "entry",
    "trait": "entry",
    "sense": "sense",
    "subsense": "sense",
    "grammatical-info": "entry|sense",
    "gloss": "sense",
    "definition": "sense",
    "example": "sense",
    "reversal": "sense",
    "illustration": "sense",
}

# System/internal trait names to suppress from output
SYSTEM_TRAITS: set[str] = {
    "morph-type", "entry-type", "dateCreated", "dateModified",
    "doNotUseForParsing", "doNotUseForGeneration",
}

# Elements that belong to both entry and sense categories —
# suppress at entry level when the entry has senses to avoid duplication.
DUAL_ELEMENTS: set[str] = {
    elem for elem, cat in ELEMENT_CATEGORY.items()
    if "entry" in cat and "sense" in cat
}

RANGE_IDS: dict[str, str] = {
    "grammatical-info": "grammatical-info",
    "relation": "lexical-relation",
    "variant": "variant-type",
    "variant-relation": "variant-type",
    "etymology": "etymology",
    "note": "note-type",
}


@dataclass
class UnmappedWarning:
    entry_headword: str = ""
    entry_id: str = ""
    element_type: str = ""
    value: str = ""
    range_id: str = ""


# -- Text helpers --------------------------------------------------------

def _text(d: dict[str, str] | str | None, lang: str = "en") -> str:
    if not d:
        return ""
    if isinstance(d, str):
        return d
    return d.get(lang) or next(iter(d.values()), "")


def _has_content(entry: Entry, lift_element: str) -> bool:
    if lift_element == "sense":
        return bool(getattr(entry, "senses", None))
    if lift_element == "lexical-unit":
        return bool(getattr(entry, "lexical_unit", None))
    if lift_element == "pronunciation":
        return bool(getattr(entry, "pronunciations", None))
    if lift_element == "citation":
        return bool(getattr(entry, "citations", None))
    if lift_element == "variant":
        return bool(getattr(entry, "variants", None))
    if lift_element == "variant-relation":
        return bool(getattr(entry, "variant_relations", None))
    if lift_element == "relation":
        return bool(getattr(entry, "relations", None))
    if lift_element == "etymology":
        return bool(getattr(entry, "etymologies", None))
    if lift_element == "note":
        return bool(getattr(entry, "notes", None))
    if lift_element == "field":
        return bool(getattr(entry, "custom_fields", None))
    if lift_element == "trait":
        return bool(getattr(entry, "traits", None))
    if lift_element == "grammatical-info":
        return bool(getattr(entry, "grammatical_info", None))
    return False


def _sense_has_content(sense: Sense, lift_element: str) -> bool:
    if lift_element == "gloss":
        return bool(getattr(sense, "glosses", None))
    if lift_element == "definition":
        return bool(getattr(sense, "definitions", None))
    if lift_element == "example":
        return bool(getattr(sense, "examples", None))
    if lift_element == "grammatical-info":
        return bool(getattr(sense, "grammatical_info", None))
    if lift_element == "reversal":
        return bool(getattr(sense, "reversals", None))
    if lift_element == "note":
        return bool(getattr(sense, "notes", None))
    if lift_element == "illustration":
        return bool(getattr(sense, "illustrations", None))
    if lift_element == "subsense":
        return bool(getattr(sense, "subsenses", None))
    return False


# -- Main renderer -------------------------------------------------------

class ProfileDrivenMarkdownRenderer:

    def __init__(
        self,
        dictionary_service: DictionaryService,
        css_mapping_service: CSSMappingService,
    ):
        self.dict_service = dictionary_service
        self.css_service = css_mapping_service
        self.warnings: list[UnmappedWarning] = []
        self.abbr_maps: dict[str, dict[str, str]] = {}
        self._entry_cache: dict[str, Entry] = {}

    def _get_entry(self, entry_id: str) -> Entry | None:
        if entry_id in self._entry_cache:
            return self._entry_cache[entry_id]
        entry = self.dict_service.get_entry(entry_id)
        if entry is not None:
            self._entry_cache[entry_id] = entry
        return entry

    def _get_subentries_data(self, entry: Entry) -> list[dict]:
        eid = _get_entry_id(entry)
        return self._subentry_map.get(eid, [])

    def _build_subentry_map(self, entries: list[Entry]) -> dict[str, list[dict]]:
        """Build parent→[subentries] mapping from in-memory relations in one pass."""
        submap: dict[str, list[dict]] = {}
        for entry in entries:
            eid = _get_entry_id(entry)
            for rel in entry.relations or []:
                rtype = rel.type if hasattr(rel, 'type') else (rel.get('type') if isinstance(rel, dict) else None)
                if rtype != '_component-lexeme':
                    continue
                rref = rel.ref if hasattr(rel, 'ref') else (rel.get('ref') if isinstance(rel, dict) else None)
                if not rref:
                    continue
                traits = rel.traits if hasattr(rel, 'traits') else (rel.get('traits', {}) if isinstance(rel, dict) else {})
                info = {
                    'id': eid,
                    'lexical_unit': _text(entry.lexical_unit),
                    'complex_form_type': traits.get('complex-form-type', 'Unknown') if traits else 'Unknown',
                    'is_primary': traits.get('is-primary') == 'true' if traits else False,
                    'order': int(traits.get('order', 0)) if traits else 0,
                }
                submap.setdefault(rref, []).append(info)
        # Sort each parent's subentries by order
        for parent_id in submap:
            submap[parent_id].sort(key=lambda x: x.get('order', 0))
        return submap

    def render(
        self,
        entries: list[Entry],
        profile: DisplayProfile,
        lang: str = "en",
    ) -> tuple[str, list[UnmappedWarning]]:
        print(f"  [export] Starting profile-driven export ({len(entries)} entries)...", flush=True)
        self.warnings = []
        config = profile.get_export_config()
        lexicon_type = config.get("lexicon_type", "lexeme-based")
        self.subentry_style = config.get("subentry_style", "indented")

        # Pre-populate entry cache from the already-loaded entries
        for entry in entries:
            eid = _get_entry_id(entry)
            self._entry_cache[eid] = entry

        # Build subentry hierarchy from in-memory relations (zero BaseX queries)
        print(f"  [export] Building subentry hierarchy from {len(entries)} entries...", flush=True)
        self._subentry_map = self._build_subentry_map(entries)
        print(f"  [export] Found {len(self._subentry_map)} parent→subentry mappings", flush=True)

        # Build abbreviation maps
        for range_id in ("grammatical-info", "lexical-relation", "variant-type",
                         "etymology", "note-type"):
            self.abbr_maps[range_id] = self.css_service.get_abbreviation_map(range_id, lang)

        # Separate profile elements
        self.entry_elements: list[ProfileElement] = []
        self.sense_elements: list[ProfileElement] = []
        self._has_sense_element = False
        for pe in profile.elements:
            cat = ELEMENT_CATEGORY.get(pe.lift_element, "entry")
            if "sense" in cat:
                self.sense_elements.append(pe)
                if pe.lift_element == "sense":
                    self._has_sense_element = True
            if "entry" in cat:
                self.entry_elements.append(pe)

        self.entry_elements.sort(key=lambda e: e.display_order or 0)
        self.sense_elements.sort(key=lambda e: e.display_order or 0)

        # Sort entries alphabetically
        entries.sort(key=lambda e: _text(e.lexical_unit).lower())

        if lexicon_type == "root-based":
            md = self._render_root_based(entries, profile)
        else:
            md = self._render_lexeme_based(entries, profile)

        return md, self.warnings

    def _visible(self, pe: ProfileElement, has_data: bool) -> bool:
        if pe.visibility == "never":
            return False
        if pe.visibility == "always":
            return True
        return has_data  # if-content

    # -- Abbreviation helpers -------------------------------------------

    def _abbr(self, value: str, range_id: str, entry_hw: str, entry_id: str) -> str:
        """Return abbreviation if available, otherwise the raw value."""
        abbr_map = self.abbr_maps.get(range_id, {})
        return abbr_map.get(value, value)

    # -- Lexeme-based (flat alphabetical) --------------------------------

    def _render_lexeme_based(
        self, entries: list[Entry], profile: DisplayProfile
    ) -> str:
        lines: list[str] = []
        grouped: dict[str, list[Entry]] = defaultdict(list)
        for entry in entries:
            hw = _text(entry.lexical_unit).strip()
            letter = hw[0].upper() if hw else "#"
            grouped[letter].append(entry)

        total = len(entries)
        done = 0
        log_every = max(1, total // 20)
        for letter in sorted(grouped):
            lines.append(f"# {letter}")
            lines.append("")
            for entry in grouped[letter]:
                entry_md = self._render_entry(entry, profile, 2)
                if entry_md:
                    lines.append(entry_md)
                if profile.show_subentries:
                    lines.extend(self._render_subentries(entry, profile, 3))
                done += 1
                if done % log_every == 0:
                    pct = done * 100 // total
                    print(f"  [export] Progress: {done}/{total} entries ({pct}%)", flush=True)
        return "\n".join(lines)

    # -- Root-based (hierarchical) ---------------------------------------

    def _render_root_based(
        self, entries: list[Entry], profile: DisplayProfile
    ) -> str:
        # Find roots ahead of time
        root_ids: set[str] = set()
        sub_ids: set[str] = set()
        root_entry_map: dict[str, Entry] = {}
        remaining: list[Entry] = []

        for entry in entries:
            eid = _get_entry_id(entry)
            root_entry_map[eid] = entry
            if entry.morph_type == "root":
                root_ids.add(eid)
            # Check for incoming component relations (has subentries)
            subentries = self._get_subentries_data(entry)
            if subentries:
                root_ids.add(eid)
                for s in subentries:
                    sub_ids.add(s.get("id", ""))

        lines: list[str] = []
        grouped: dict[str, list[Entry]] = defaultdict(list)

        # Roots go into letter groups
        roots_in_letter: dict[str, list[Entry]] = defaultdict(list)
        standalone: list[Entry] = []
        for entry in entries:
            eid = _get_entry_id(entry)
            hw = _text(entry.lexical_unit).strip()
            letter = hw[0].upper() if hw else "#"
            if eid in root_ids:
                roots_in_letter[letter].append(entry)
            elif eid not in sub_ids:
                standalone.append(entry)

        # Sort standalone by letter too
        standalone_in_letter: dict[str, list[Entry]] = defaultdict(list)
        for entry in standalone:
            hw = _text(entry.lexical_unit).strip()
            letter = hw[0].upper() if hw else "#"
            standalone_in_letter[letter].append(entry)

        all_letters = sorted(set(list(roots_in_letter.keys()) + list(standalone_in_letter.keys())))
        total = len(entries)
        done = 0
        log_every = max(1, total // 20)

        for letter in all_letters:
            lines.append(f"# {letter}")
            lines.append("")
            for root in roots_in_letter.get(letter, []):
                entry_md = self._render_entry(root, profile, 2)
                if entry_md:
                    lines.append(entry_md)
                if profile.show_subentries:
                    lines.extend(self._render_subentries(root, profile, 3))
                done += 1
                if done % log_every == 0:
                    pct = done * 100 // total
                    print(f"  [export] Progress: {done}/{total} entries ({pct}%)", flush=True)
            for entry in standalone_in_letter.get(letter, []):
                entry_md = self._render_entry(entry, profile, 2)
                if entry_md:
                    lines.append(entry_md)
                done += 1
                if done % log_every == 0:
                    pct = done * 100 // total
                    print(f"  [export] Progress: {done}/{total} entries ({pct}%)", flush=True)

        return "\n".join(lines)

    # -- Subentries ------------------------------------------------------

    def _render_subentries(
        self, entry: Entry, profile: DisplayProfile, heading_level: int
    ) -> list[str]:
        lines: list[str] = []
        subentries_data = self._get_subentries_data(entry)
        if not subentries_data:
            return lines

        for sd in subentries_data:
            sub_id = sd.get("id", "")
            complex_type = sd.get("complex_form_type", "")
            try:
                sub_entry = self._get_entry(sub_id)
            except Exception:
                continue
            if not sub_entry:
                continue

            entry_md = self._render_entry(sub_entry, profile, heading_level)
            if entry_md:
                if complex_type:
                    type_label = complex_type.replace("-", " ").title()
                    lines.append(f"*{type_label}*")
                lines.append(entry_md)

            # Recurse for deeper subentry levels
            lines.extend(self._render_subentries(sub_entry, profile, heading_level + 1))

        return lines

    # -- Entry rendering -------------------------------------------------

    def _render_entry(
        self, entry: Entry, profile: DisplayProfile, heading_level: int = 2
    ) -> str:
        lines: list[str] = []
        hw = _text(entry.lexical_unit)
        eid = _get_entry_id(entry)

        heading_prefix = "#" * heading_level
        display_hw = hw
        if entry.homograph_number:
            display_hw += f"<sub>{entry.homograph_number}</sub>"
        lines.append(f"{heading_prefix} {display_hw}")
        lines.append("")

        # Entry-level elements
        senses = getattr(entry, "senses", []) or []
        for pe in self.entry_elements:
            # Skip elements that are also rendered at sense level when senses exist
            if senses and pe.lift_element in DUAL_ELEMENTS:
                continue
            has_data = _has_content(entry, pe.lift_element)
            if not self._visible(pe, has_data):
                continue
            md = self._render_entry_element(entry, pe, eid, hw)
            if md is not None:
                lines.append(md)

        # Sense-level elements
        if self._has_sense_element and senses:
            for idx, sense in enumerate(senses):
                if idx > 0:
                    lines.append("")
                sense_md = self._render_sense(sense, profile, idx, eid, hw)
                if sense_md:
                    lines.append(sense_md)
        elif senses and not self._has_sense_element:
            # No explicit sense wrapper — render sense elements directly
            for idx, sense in enumerate(senses):
                if idx > 0:
                    lines.append("")
                for pe in self.sense_elements:
                    has_data = _sense_has_content(sense, pe.lift_element)
                    if not self._visible(pe, has_data):
                        continue
                    md = self._render_sense_element(sense, pe, idx, eid, hw)
                    if md is not None:
                        lines.append(md)

        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def _render_entry_element(
        self, entry: Entry, pe: ProfileElement, eid: str, hw: str
    ) -> str | None:
        elem = pe.lift_element
        prefix = pe.prefix or ""
        suffix = pe.suffix or ""
        aspect = pe.get_display_aspect()

        if elem == "lexical-unit":
            val = _text(entry.lexical_unit)
            return f"{prefix}**{val}**{suffix}" if val else None

        if elem == "pronunciation":
            val = _text(entry.pronunciations)
            if not val:
                return None
            return f"{prefix}{val}{suffix}"

        if elem == "citation":
            vals = [_text(c) if isinstance(c, dict) else str(c) for c in (entry.citations or [])]
            vals = [v for v in vals if v]
            if not vals:
                return None
            return f"{prefix}{'; '.join(vals)}{suffix}"

        if elem == "variant":
            parts = []
            for v in (entry.variants or []):
                vform = _text(v.form if hasattr(v, "form") else {})
                if not vform:
                    continue
                vtype = ""
                if hasattr(v, "grammatical_info") and v.grammatical_info:
                    vtype = self._abbr(v.grammatical_info, "variant-type", hw, eid) if aspect == "abbr" else v.grammatical_info
                parts.append(f"{vform} ({vtype})" if vtype else vform)
            if not parts:
                return None
            return f"{prefix}*Variants:* {', '.join(parts)}{suffix}"

        if elem == "relation":
            parts = []
            for r in (entry.relations or []):
                rtype = getattr(r, "type", "") if not isinstance(r, dict) else r.get("type", "")
                rref = getattr(r, "ref", "") if not isinstance(r, dict) else r.get("ref", "")
                # Skip system/internal relations (LIFT convention: starts with _)
                if not rtype or rtype.startswith("_"):
                    continue
                if aspect == "abbr":
                    rtype = self._abbr(rtype, "lexical-relation", hw, eid)
                rlabel = rtype.replace("_", " ").replace("-", " ").strip().title()
                if rref:
                    # Resolve ref to headword from the pre-loaded entry cache
                    ref_entry = self._entry_cache.get(rref)
                    ref_text = _text(ref_entry.lexical_unit) if ref_entry else rref
                    parts.append(f"*{rlabel}:* {ref_text}")
            if not parts:
                return None
            return f"{prefix}{'; '.join(parts)}{suffix}"

        if elem == "etymology":
            parts = []
            for et in (entry.etymologies or []):
                et_type = getattr(et, "type", "") if not isinstance(et, dict) else et.get("type", "")
                et_source = getattr(et, "source", "") if not isinstance(et, dict) else et.get("source", "")
                if aspect == "abbr":
                    et_type = self._abbr(et_type, "etymology", hw, eid)
                if et_type or et_source:
                    parts.append(f"<{et_type}: {et_source}>" if et_type and et_source else et_type or et_source)
            if not parts:
                return None
            return f"{prefix}{'; '.join(parts)}{suffix}"

        if elem == "note":
            notes = entry.notes or {}
            if not notes:
                return None
            note_texts = []
            for ntype, nval in notes.items():
                nt = self._abbr(ntype, "note-type", hw, eid) if aspect == "abbr" else ntype
                note_texts.append(f"*Note ({nt}):* {_text(nval) if isinstance(nval, dict) else nval}")
            return f"{prefix}{'; '.join(note_texts)}{suffix}"

        if elem == "field":
            cfs = entry.custom_fields or {}
            if not cfs:
                return None
            parts = [f"{k}: {v}" for k, v in cfs.items() if v]
            if not parts:
                return None
            return f"{prefix}{'; '.join(parts)}{suffix}"

        if elem == "trait":
            raw = getattr(entry, "traits", None)
            if not raw:
                return None
            traits = raw if isinstance(raw, dict) else {}
            parts = [
                f"{k}: {v}" for k, v in traits.items()
                if v and k not in SYSTEM_TRAITS and not k.startswith("_")
            ]
            if not parts:
                return None
            return f"{prefix}{'; '.join(parts)}{suffix}"

        if elem == "grammatical-info":
            val = getattr(entry, "grammatical_info", None)
            if not val:
                return None
            if aspect == "abbr":
                val = self._abbr(val, "grammatical-info", hw, eid)
            return f"{prefix}*{val}*{suffix}"

        return None

    def _render_sense(
        self, sense: Sense, profile: DisplayProfile,
        idx: int, eid: str, hw: str
    ) -> str:
        lines: list[str] = []
        for pe in self.sense_elements:
            has_data = _sense_has_content(sense, pe.lift_element)
            if not self._visible(pe, has_data):
                continue
            md = self._render_sense_element(sense, pe, idx, eid, hw)
            if md is not None:
                lines.append(md)
        return "\n".join(lines)

    def _render_sense_element(
        self, sense: Sense, pe: ProfileElement,
        idx: int, eid: str, hw: str
    ) -> str | None:
        elem = pe.lift_element
        prefix = pe.prefix or ""
        suffix = pe.suffix or ""
        aspect = pe.get_display_aspect()

        if elem == "sense":
            return ""  # just a container marker

        if elem == "grammatical-info":
            val = getattr(sense, "grammatical_info", None)
            if not val:
                return None
            if aspect == "abbr":
                val = self._abbr(val, "grammatical-info", hw, eid)
            return f"{prefix}*{val}*{suffix}"

        if elem == "gloss":
            val = _text(sense.glosses)
            return f"{prefix}*{val}*{suffix}" if val else None

        if elem == "definition":
            val = _text(sense.definitions)
            return f"{prefix}{val}{suffix}" if val else None

        if elem == "example":
            exs = getattr(sense, "examples", []) or []
            ex_lines = []
            for ex in exs:
                ex_form = _text(
                    ex.get("form") if isinstance(ex, dict) else getattr(ex, "form", None)
                )
                if ex_form:
                    ex_lines.append(f"> \"{ex_form}\"")
                ex_tr = _text(
                    ex.get("translations") if isinstance(ex, dict)
                    else getattr(ex, "translations", None)
                )
                if ex_tr:
                    ex_lines.append(f"> *{ex_tr}*")
            if not ex_lines:
                return None
            return f"{prefix}{chr(10).join(ex_lines)}{suffix}"

        if elem == "note":
            notes = getattr(sense, "notes", {}) or {}
            if not notes:
                return None
            note_texts = []
            for ntype, nval in notes.items():
                nt = self._abbr(ntype, "note-type", hw, eid) if aspect == "abbr" else ntype
                note_texts.append(f"*Note ({nt}):* {_text(nval) if isinstance(nval, dict) else nval}")
            return f"{prefix}{'; '.join(note_texts)}{suffix}"

        if elem == "reversal":
            revs = getattr(sense, "reversals", None)
            if not revs:
                return None
            rev_text = "; ".join(str(r) for r in revs)
            return f"{prefix}*Reversal:* {rev_text}{suffix}" if rev_text else None

        if elem == "illustration":
            ills = getattr(sense, "illustrations", None) or []
            parts = []
            for il in ills:
                href = il.get("href", "") if isinstance(il, dict) else ""
                label = il.get("label", "") if isinstance(il, dict) else ""
                if href:
                    parts.append(f"![{label}]({href})" if label else f"![]({href})")
            if not parts:
                return None
            return f"{prefix}{chr(10).join(parts)}{suffix}"

        if elem == "subsense":
            # For now, handle as inline content
            subs = getattr(sense, "subsenses", None) or []
            if not subs:
                return None
            sub_lines = []
            for sub in subs:
                sub_md = self._render_sense(sub, DisplayProfile(
                    id=0, name="_sub",
                    elements=self.sense_elements
                ), 0, eid, hw)
                if sub_md:
                    sub_lines.append(sub_md)
            if not sub_lines:
                return None
            return f"{prefix}{chr(10).join(sub_lines)}{suffix}"

        return None


def _get_entry_id(entry: Entry) -> str:
    eid = getattr(entry, "id", None) or getattr(entry, "id_", None)
    if eid is None:
        eid = _text(entry.lexical_unit)
    return str(eid)
