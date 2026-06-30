"""
Import Converter: transforms parsed files (SFM / CSV) into LIFT XML
for import via DictionaryService.import_lift().

Two-phase approach:
  Phase 1 — convert everything to LIFT XML, import entries.
  Phase 2 — resolve cross-references (@ref) in the LIFT XML and
            update entries; unresolved refs → <annotation type="import-residue">.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import uuid
from typing import Optional

from lxml import etree as ET

from app.services.sfm_parser import (
    ParsedDocument,
    ParsedEntry,
    ParsedField,
    ParsedSense,
    ParsedExample,
    ParsedPronunciation,
)
from app.services.csv_parser import CSVData
from app.services.dictionary_service import DictionaryService

logger = logging.getLogger(__name__)

# LIFT namespace
LIFT_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
LIFT = "http://fieldworks.sil.org/schemas/lift/0.13"


def _lift_tag(tag: str) -> str:
    return tag


# -- Mapping from lift_element to <entry> child tag and attrib -------------

# Fields that become attributes of the <entry> element
ENTRY_ATTR_ELEMENTS = {"date_created", "date_modified", "guid"}

# Mapping: lift_element → (tag, attribute_on_parent, level)
# level: "entry", "sense", "example", "pronunciation", "note"
LIFT_ELEMENT_MAP: dict[str, tuple[str, str, str]] = {
    # Entry-level
    "lexeme":               ("lexical-unit", "form", "entry"),
    "citation":             ("citation", "form", "entry"),
    "entry_note":           ("note", "entry", "entry"),
    "entry_trait":          ("trait", "entry", "entry"),
    "entry_field":          ("field", "entry", "entry"),
    # Pronunciation
    "pronunciation_form":   ("form", "pronunciation", "pronunciation"),
    "pronunciation_media":  ("media", "pronunciation", "pronunciation"),
    # Sense-level
    "gloss":                ("gloss", "sense", "sense"),
    "definition":           ("definition", "sense", "sense"),
    "sense_trait":          ("trait", "sense", "sense"),
    "sense_note":           ("note", "sense", "sense"),
    "sense_field":          ("field", "sense", "sense"),
    "grammatical_info":     ("grammatical-info", "sense", "sense"),
    "sense_relation":       ("relation", "sense", "sense"),
    "reversal":             ("reversal", "sense", "sense"),
    "illustration":         ("illustration", "sense", "sense"),
    # Example-level
    "example_form":         ("form", "example", "example"),
    "example_translation":  ("translation", "example", "example"),
    "example_note":         ("note", "example", "example"),
    # Variant-level
    "variant_form":         ("form", "variant", "variant"),
    "variant_note":         ("note", "variant", "variant"),
    "variant_trait":        ("trait", "variant", "variant"),
    "variant_field":        ("field", "variant", "variant"),
    # Etymology
    "etymology_form":       ("form", "etymology", "etymology"),
    "etymology_gloss":      ("gloss", "etymology", "etymology"),
    # General
    "annotation":           ("annotation", "entry", "entry"),
}

# Fields that are language-form elements (<form lang="...">...</form>)
FORM_ELEMENTS = {
    "lexeme", "citation",
    "definition", "gloss",
    "example_translation",
}


def _make_form_element(
    parent: ET.Element,
    tag: str,
    value: str,
    lang: Optional[str] = None,
) -> ET.Element:
    """Create <tag><form><text>value</text></form></tag> structure."""
    outer = ET.SubElement(parent, tag)
    form = ET.SubElement(outer, _lift_tag("form"))
    if lang:
        form.set("lang", lang)
    text = ET.SubElement(form, _lift_tag("text"))
    text.text = value
    return outer


def _make_trait(parent: ET.Element, name: str, value: str) -> ET.Element:
    t = ET.SubElement(parent, _lift_tag("trait"))
    t.set("name", name)
    t.set("value", value)
    return t


def _resolve_lang(
    field: ParsedField,
    language_map: dict[str, str],
) -> Optional[str]:
    """Resolve a field's lang to an ISO code using the language map."""
    if field.lang:
        return language_map.get(field.lang, field.lang)
    return None


# ---------------------------------------------------------------------------
# Phase 1: Build LIFT XML tree from parsed data
# ---------------------------------------------------------------------------


def build_lift_tree(
    parsed: ParsedDocument | CSVData,
    field_map: dict[str, dict],
    language_map: dict[str, str],
    file_type: str = "sfm",
) -> tuple[ET.Element, list[str]]:
    """Build a LIFT XML tree from parsed SFM or CSV data.

    Args:
        parsed: ParsedDocument (SFM) or CSVData (CSV).
        field_map: Dict mapping field_marker → field_config dict with keys:
            lift_element, level, lang, is_key, field_type.
        language_map: Dict mapping source language → target ISO code.
        file_type: "sfm" or "csv".

    Returns:
        (lxml root Element, list of cross-ref dicts as repr strings).
    """
    root = ET.Element("lift")
    root.set("version", "0.13")
    root.set("producer", "opencode-sfm-import")

    cross_refs_raw: list[str] = []

    if file_type == "sfm":
        _build_from_sfm(root, parsed, field_map, language_map, cross_refs_raw)
    else:
        _build_from_csv(root, parsed, field_map, language_map, cross_refs_raw)

    return root, cross_refs_raw


def _build_from_sfm(
    root: ET.Element,
    doc: ParsedDocument,
    field_map: dict[str, dict],
    language_map: dict[str, str],
    cross_refs_raw: list[str],
) -> None:
    """Populate LIFT tree from ParsedDocument."""
    for entry in doc.entries:
        entry_el = _convert_sfm_entry(
            entry, field_map, language_map, cross_refs_raw
        )
        if entry_el is not None:
            root.append(entry_el)


def _convert_sfm_entry(
    entry: ParsedEntry,
    field_map: dict[str, dict],
    language_map: dict[str, str],
    cross_refs_raw: list[str],
) -> Optional[ET.Element]:
    """Convert one SFM entry to a LIFT <entry> element."""
    import uuid
    entry_guid = str(uuid.uuid4())
    entry_el = ET.Element(_lift_tag("entry"))
    entry_el.set("id", entry_guid)
    entry_el.set("guid", entry_guid)

    # Track whether we found any actual content
    has_content = False

    # Process top-level fields
    for f in entry.fields:
        cfg = field_map.get(f.marker)
        if cfg is None:
            continue
        has_content = True
        _apply_field(entry_el, f, cfg, language_map)

    # Process pronunciations
    for pron in entry.pronunciations:
        pron_el = _convert_pronunciation(pron, field_map, language_map)
        if pron_el is not None:
            entry_el.append(pron_el)

    # Process variants (inline allomorphs/variants)
    for var in entry.variants:
        var_el = _convert_sfm_variant(var, field_map, language_map)
        if var_el is not None:
            entry_el.append(var_el)

    # Process senses
    for sense in entry.senses:
        sense_el = _convert_sfm_sense(
            sense, entry, field_map, language_map, cross_refs_raw
        )
        if sense_el is not None:
            entry_el.append(sense_el)

    # Add variant references
    add_variant_refs(entry_el, entry)

    if not has_content and not entry.senses and not entry.pronunciations and not entry.variant_refs:
        return None

    # Add unmapped fields as <field> elements (after content check so empty
    # entries with only unmapped fields don't create spurious entries)
    add_entry_level_orphans(entry_el, entry, field_map, language_map)

    return entry_el


def _convert_pronunciation(
    pron: ParsedPronunciation,
    field_map: dict[str, dict],
    language_map: dict[str, str],
) -> Optional[ET.Element]:
    pron_el = ET.Element(_lift_tag("pronunciation"))
    has = False
    for f in pron.fields:
        cfg = field_map.get(f.marker)
        if cfg is None:
            continue
        has = True
        _apply_field(pron_el, f, cfg, language_map)
    return pron_el if has else None


def _convert_sfm_variant(
    var: ParsedVariant,
    field_map: dict[str, dict],
    language_map: dict[str, str],
) -> Optional[ET.Element]:
    var_el = ET.Element(_lift_tag("variant"))
    has = False
    for f in var.fields:
        cfg = field_map.get(f.marker)
        if cfg is None:
            continue
        has = True
        _apply_field(var_el, f, cfg, language_map)
    return var_el if has else None


def _convert_sfm_sense(
    sense: ParsedSense,
    entry: ParsedEntry,
    field_map: dict[str, dict],
    language_map: dict[str, str],
    cross_refs_raw: list[str],
) -> Optional[ET.Element]:
    import uuid
    sense_el = ET.Element(_lift_tag("sense"))
    sense_el.set("id", str(uuid.uuid4()))
    has = False

    for f in sense.fields:
        cfg = field_map.get(f.marker)
        if cfg is None:
            continue
        has = True
        _apply_field(sense_el, f, cfg, language_map)

    for ex in sense.examples:
        ex_el = _convert_example(ex, field_map, language_map)
        if ex_el is not None:
            sense_el.append(ex_el)
            has = True

    return sense_el if has else None


def _convert_example(
    example: ParsedExample,
    field_map: dict[str, dict],
    language_map: dict[str, str],
) -> Optional[ET.Element]:
    ex_el = ET.Element(_lift_tag("example"))
    has = False
    for f in example.fields:
        cfg = field_map.get(f.marker)
        if cfg is None:
            continue
        has = True
        _apply_field(ex_el, f, cfg, language_map)
    return ex_el if has else None


# ---------------------------------------------------------------------------
# Phase 2: Cross-reference resolution
# ---------------------------------------------------------------------------


def _build_guid_index(lift_path: str) -> dict[str, str]:
    """Build {headword_lower: guid} index from a LIFT XML file."""
    index: dict[str, str] = {}
    tree = ET.parse(lift_path)
    root = tree.getroot()
    for entry in root.findall(".//entry"):
        guid = entry.get("id")
        if not guid:
            guid = entry.get("guid")
        lf = entry.find(".//lexical-unit/form/text")
        if lf is None:
            lf = entry.find(".//lexeme-form/form/text")
        headword = lf.text.strip().lower() if lf is not None and lf.text else None
        if headword and guid:
            index[headword] = guid
    return index


def resolve_cross_refs(
    lift_path: str,
    cross_refs_raw: list[str],
) -> int:
    """Phase 2: Resolve cross-references in a LIFT XML file.

    Scans for <annotation type="x-cross-reference"> elements,
    resolves their text to target GUIDs, and replaces them with
    proper <relation> elements. Unresolved entries are annotated.

    Args:
        lift_path: Path to the LIFT file to modify in-place.
        cross_refs_raw: Serialized cross-ref info (for logging).

    Returns:
        Number of resolved cross-references.
    """
    # Build headword → guid index
    guid_index = _build_guid_index(lift_path)

    tree = ET.parse(lift_path)
    root = tree.getroot()
    ns = {"lift": LIFT}

    annotations = root.findall(
        ".//lift:annotation[@type='x-cross-reference']", ns
    )
    resolved = 0

    for ann in annotations:
        ref_type = ann.get("ref_type", "x-reference")
        target_headword = ann.text.strip() if ann.text else ""

        if not target_headword:
            continue

        target_guid = guid_index.get(target_headword.lower())
        if target_guid:
            # Replace annotation with proper <relation>
            parent = ann.getparent() if hasattr(ann, "getparent") else None
            if parent is None:
                continue

            rel = ET.SubElement(
                parent, _lift_tag("relation")
            )
            rel.set("type", ref_type)
            rel.set("ref", target_guid)
            parent.remove(ann)
            resolved += 1
        else:
            # Mark as unresolved
            ann.set("type", "import-residue")
            ann.set("description", f"Unresolved cross-reference: {target_headword}")

    tree.write(lift_path, xml_declaration=True, encoding="UTF-8")
    return resolved


# ---------------------------------------------------------------------------
# Build LIFT from CSV
# ---------------------------------------------------------------------------


def _build_from_csv(
    root: ET.Element,
    data: CSVData,
    field_map: dict[str, dict],
    language_map: dict[str, str],
    cross_refs_raw: list[str],
) -> None:
    """Populate LIFT tree from CSVData.

    CSV rows are one-per-sense. The field_map is keyed by column header.
    """
    # Group rows by main entry identifier (e.g. "lx" column)
    entry_key_col = None
    for col, cfg in field_map.items():
        if cfg.get("is_key") and cfg.get("level") == "entry":
            entry_key_col = col
            break
    if entry_key_col is None:
        logger.warning("No entry key column found in CSV mapping; using all rows as separate entries")
        entry_key_col = field_map.get("lx", {}).get("lift_element") if False else None

    current_headword: Optional[str] = None
    current_entry_el: Optional[ET.Element] = None
    has_content = False

    for row in data.rows:
        headword = row.columns.get(entry_key_col or "")
        entry_key_col_for_real = entry_key_col or next(iter(row.columns.keys()), None)
        if entry_key_col_for_real:
            headword = row.columns.get(entry_key_col_for_real)
        else:
            headword = None

        if headword is not None and headword != current_headword:
            # Start a new entry
            if current_entry_el is not None and has_content:
                root.append(current_entry_el)
            current_headword = headword
            current_entry_el = ET.Element(_lift_tag("entry"))
            entry_guid = str(uuid.uuid4())
            current_entry_el.set("id", entry_guid)
            current_entry_el.set("guid", entry_guid)
            has_content = False

            # Apply entry-level fields from this row
            for col, value in row.columns.items():
                cfg = field_map.get(col)
                if cfg is None or cfg.get("level") != "entry":
                    continue
                has_content = True
                pf = ParsedField(marker=col, value=value)
                _apply_field(current_entry_el, pf, cfg, language_map)

        if current_entry_el is None:
            current_entry_el = ET.Element(_lift_tag("entry"))
            entry_guid = str(uuid.uuid4())
            current_entry_el.set("id", entry_guid)
            current_entry_el.set("guid", entry_guid)

        # Build sense element
        sense_el = ET.Element(_lift_tag("sense"))
        sense_el.set("id", str(uuid.uuid4()))
        sense_has = False
        for col, value in row.columns.items():
            cfg = field_map.get(col)
            if cfg is None or cfg.get("level") not in ("sense", "example"):
                continue
            sense_has = True
            pf = ParsedField(marker=col, value=value)
            _apply_field(sense_el, pf, cfg, language_map)

        if sense_has:
            current_entry_el.append(sense_el)
            has_content = True

    if current_entry_el is not None and has_content:
        root.append(current_entry_el)


# ---------------------------------------------------------------------------
# Apply a field to an element using its mapping config
# ---------------------------------------------------------------------------


def _apply_field(
    parent: ET.Element,
    field: ParsedField,
    cfg: dict,
    language_map: dict[str, str],
) -> None:
    """Apply a parsed field to a LIFT XML parent element."""
    lift_element: str = cfg.get("lift_element", "")
    level: str = cfg.get("level", "entry")
    lang: Optional[str] = cfg.get("lang")
    field_type: str = cfg.get("field_type", "normal")

    if field_type in ("cross-ref-source",):
        # Store as annotation for Phase 2 resolution
        ann = ET.SubElement(parent, _lift_tag("annotation"))
        ann.set("type", "x-cross-reference")
        ann.set("ref_type", field.value)
        return

    if field_type in ("cross-ref-target",):
        # Target headword — find preceding annotation and set text
        children = list(parent)
        for child in reversed(children):
            if child.tag == _lift_tag("annotation") and child.get("type") == "x-cross-reference":
                child.text = field.value
                break
        return

    if lift_element in ENTRY_ATTR_ELEMENTS:
        parent.set(lift_element, field.value)
        return

    # Resolve language
    resolved_lang = _resolve_lang(field, language_map)
    if lang and not resolved_lang:
        resolved_lang = lang

    if lift_element in ("example_form", "pronunciation_form", "variant_form", "etymology_form"):
        # <form lang="..."><text>value</text></form> directly under parent
        form = ET.SubElement(parent, _lift_tag("form"))
        if resolved_lang:
            form.set("lang", resolved_lang)
        text = ET.SubElement(form, _lift_tag("text"))
        text.text = field.value
    elif lift_element in FORM_ELEMENTS:
        tag = LIFT_ELEMENT_MAP.get(lift_element, (lift_element, level, level))[0]
        _make_form_element(parent, _lift_tag(tag), field.value, resolved_lang)
    elif lift_element in ("trait", "entry_trait", "sense_trait", "variant_trait"):
        _make_trait(parent, field.value, field.value)
    elif lift_element == "grammatical_info":
        gi = ET.SubElement(parent, _lift_tag("grammatical-info"))
        gi.set("value", field.value)
        if resolved_lang:
            gi.set("lang", resolved_lang)
    elif lift_element in ("note", "entry_note", "sense_note", "example_note", "variant_note"):
        note = ET.SubElement(parent, _lift_tag("note"))
        text_el = ET.SubElement(note, _lift_tag("text"))
        text_el.text = field.value
        if resolved_lang:
            note.set("lang", resolved_lang)
    elif lift_element in ("field", "entry_field", "sense_field", "variant_field"):
        el = ET.SubElement(parent, _lift_tag("field"))
        el.set("type", field.value)
    elif lift_element == "variant":
        pass
    elif lift_element == "sense_relation":
        rel = ET.SubElement(parent, _lift_tag("relation"))
        rel.set("type", field.value)
    elif lift_element == "reversal":
        rev = ET.SubElement(parent, _lift_tag("reversal"))
        if resolved_lang:
            rev.set("lang", resolved_lang)
        rev_form = ET.SubElement(rev, _lift_tag("form"))
        if resolved_lang:
            rev_form.set("lang", resolved_lang)
        text = ET.SubElement(rev_form, _lift_tag("text"))
        text.text = field.value
    elif lift_element == "illustration":
        ill = ET.SubElement(parent, _lift_tag("illustration"))
        ill.set("href", field.value)
        label = ET.SubElement(ill, _lift_tag("label"))
        label_form = ET.SubElement(label, _lift_tag("form"))
        if resolved_lang:
            label_form.set("lang", resolved_lang)
        text = ET.SubElement(label_form, _lift_tag("text"))
        text.text = field.value
    elif lift_element == "pronunciation_media":
        media = ET.SubElement(parent, _lift_tag("media"))
        media.set("href", field.value)
        label = ET.SubElement(media, _lift_tag("label"))
        label_form = ET.SubElement(label, _lift_tag("form"))
        if resolved_lang:
            label_form.set("lang", resolved_lang)
        text = ET.SubElement(label_form, _lift_tag("text"))
        text.text = field.value
    elif lift_element == "etymology_gloss":
        gloss_el = ET.SubElement(parent, _lift_tag("gloss"))
        if resolved_lang:
            gloss_el.set("lang", resolved_lang)
        gloss_form = ET.SubElement(gloss_el, _lift_tag("form"))
        if resolved_lang:
            gloss_form.set("lang", resolved_lang)
        text = ET.SubElement(gloss_form, _lift_tag("text"))
        text.text = field.value
    elif lift_element == "annotation":
        ann = ET.SubElement(parent, _lift_tag("annotation"))
        if resolved_lang:
            ann.set("lang", resolved_lang)
        ann_form = ET.SubElement(ann, _lift_tag("form"))
        if resolved_lang:
            ann_form.set("lang", resolved_lang)
        text = ET.SubElement(ann_form, _lift_tag("text"))
        text.text = field.value
    else:
        tag = LIFT_ELEMENT_MAP.get(lift_element, (lift_element, level, level))[0]
        _make_form_element(parent, _lift_tag(tag), field.value, resolved_lang)


# ---------------------------------------------------------------------------
# Orphaned fields and variant refs
# ---------------------------------------------------------------------------


def add_entry_level_orphans(
    entry_el: ET.Element,
    entry: ParsedEntry,
    field_map: dict[str, dict],
    language_map: dict[str, str],
) -> None:
    """Add fields that didn't match any configured mapping as <field> elements."""
    for f in entry.fields:
        if f.marker not in field_map:
            el = ET.SubElement(entry_el, _lift_tag("field"))
            el.set("type", f.marker)
            text = ET.SubElement(el, _lift_tag("text"))
            text.text = f.value
            resolved_lang = _resolve_lang(f, language_map)
            if resolved_lang:
                el.set("lang", resolved_lang)


def add_variant_refs(
    entry_el: ET.Element,
    entry: ParsedEntry,
) -> None:
    """Convert variant refs to LIFT <variant> elements."""
    from app.services.sfm_parser import ParsedVariantRef
    for vref in entry.variant_refs:
        if not vref.target_value:
            continue
        rel = ET.SubElement(entry_el, _lift_tag("relation"))
        rel.set("type", "variant")
        rel.set("ref", vref.target_value)
        if vref.type_value:
            rel.set("subtype", vref.type_value)


# ---------------------------------------------------------------------------
# Entry importer — builds temp LIFT file and passes it to DictionaryService
# ---------------------------------------------------------------------------


def import_parsed_document(
    doc: ParsedDocument | CSVData,
    field_map: dict[str, dict],
    language_map: dict[str, str],
    dict_service: DictionaryService,
    project_id: Optional[int] = None,
    mode: str = "merge",
    file_type: str = "sfm",
) -> dict:
    """Import a parsed document (SFM or CSV) into the dictionary.

    Args:
        doc: Parsed SFM (ParsedDocument) or CSV (CSVData) data.
        field_map: Field marker → field config.
        language_map: Source → target language mapping.
        dict_service: DictionaryService instance.
        project_id: Optional project ID.
        mode: "merge" or "replace".
        file_type: "sfm" or "csv".

    Returns:
        Dict with {imported: int, resolved_cross_refs: int, unresolved_cross_refs: list}.
    """
    root, cross_refs_raw = build_lift_tree(
        doc, field_map, language_map, file_type=file_type
    )

    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".lift", delete=False
    ) as f:
        lift_path = f.name
        tree = ET.ElementTree(root)
        tree.write(f, xml_declaration=True, encoding="UTF-8", pretty_print=True)

    try:
        imported = dict_service.import_lift(
            lift_path=lift_path,
            mode=mode,
            project_id=project_id,
        )
    except Exception:
        logger.exception("Error during lift import phase 1")
        raise
    finally:
        if os.path.exists(lift_path):
            os.unlink(lift_path)

    # Variant refs added directly in the LIFT tree already

    return {
        "imported": imported,
        "resolved_cross_refs": 0,
    }


def import_csv_data(
    data: CSVData,
    field_map: dict[str, dict],
    language_map: dict[str, str],
    dict_service: DictionaryService,
    project_id: Optional[int] = None,
    mode: str = "merge",
) -> dict:
    """Import CSV data into the dictionary.

    Args:
        data: Parsed CSV data.
        field_map: Column header → field config.
        language_map: Source → target language mapping.
        dict_service: DictionaryService instance.
        project_id: Optional project ID.
        mode: "merge" or "replace".

    Returns:
        Dict with {imported: int, ...}.
    """
    root, cross_refs_raw = build_lift_tree(
        data, field_map, language_map, file_type="csv"
    )

    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".lift", delete=False
    ) as f:
        lift_path = f.name
        tree = ET.ElementTree(root)
        tree.write(f, xml_declaration=True, encoding="UTF-8", pretty_print=True)

    try:
        imported = dict_service.import_lift(
            lift_path=lift_path,
            mode=mode,
            project_id=project_id,
        )
    except Exception:
        logger.exception("Error during CSV import phase 1")
        raise
    finally:
        if os.path.exists(lift_path):
            os.unlink(lift_path)

    return {
        "imported": imported,
    }
