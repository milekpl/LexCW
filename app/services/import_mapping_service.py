"""CRUD service for ImportMapping configurations."""

from __future__ import annotations

import json
import logging
from typing import Optional

from app.models.import_mapping import (
    ImportMapping,
    ImportFieldMapping,
    ImportLanguageMapping,
    ImportPOSMapping,
)
from app.models.workset_models import db
from app.utils.db_utils import safe_commit

logger = logging.getLogger(__name__)


class ImportMappingService:
    """Manage ImportMapping records."""

    def get_all(self) -> list[ImportMapping]:
        return ImportMapping.query.order_by(ImportMapping.updated_at.desc()).all()

    def get_by_id(self, mapping_id: int) -> Optional[ImportMapping]:
        return ImportMapping.query.get(mapping_id)

    def get_by_name(self, name: str) -> Optional[ImportMapping]:
        return ImportMapping.query.filter_by(name=name).first()

    def delete(self, mapping_id: int) -> bool:
        mapping = ImportMapping.query.get(mapping_id)
        if mapping is None:
            return False
        db.session.delete(mapping)
        safe_commit(db, "import_mapping_service")
        return True

    def create(
        self,
        name: str,
        file_type: str = "sfm",
        description: Optional[str] = None,
        field_mappings: Optional[list[dict]] = None,
        language_mappings: Optional[list[dict]] = None,
        owner_id: Optional[int] = None,
    ) -> ImportMapping:
        mapping = ImportMapping(
            name=name,
            file_type=file_type,
            description=description,
            owner_id=owner_id,
        )
        db.session.add(mapping)
        db.session.flush()

        if field_mappings:
            for fm in field_mappings:
                mapping.field_mappings.append(ImportFieldMapping(
                    mapping_id=mapping.id,
                    field_marker=fm["field_marker"],
                    lift_element=fm.get("lift_element", ""),
                    level=fm.get("level", "entry"),
                    lang=fm.get("lang"),
                    is_key=fm.get("is_key", False),
                    field_type=fm.get("field_type", "normal"),
                ))

        if language_mappings:
            for lm in language_mappings:
                mapping.language_mappings.append(ImportLanguageMapping(
                    mapping_id=mapping.id,
                    source_lang=lm["source_lang"],
                    target_lang=lm["target_lang"],
                ))

        if "pos_mappings" in kwargs:
            for pm in kwargs["pos_mappings"]:
                mapping.pos_mappings.append(ImportPOSMapping(
                    mapping_id=mapping.id,
                    source_value=pm["source_value"],
                    target_value=pm["target_value"],
                    note=pm.get("note"),
                ))

        safe_commit(db, "import_mapping_service")
        return mapping

    def update(
        self,
        mapping_id: int,
        **kwargs,
    ) -> Optional[ImportMapping]:
        mapping = ImportMapping.query.get(mapping_id)
        if mapping is None:
            return None

        for key in ("name", "file_type", "description", "owner_id"):
            if key in kwargs:
                setattr(mapping, key, kwargs[key])

        if "field_mappings" in kwargs:
            # Replace all field mappings
            ImportFieldMapping.query.filter_by(mapping_id=mapping.id).delete()
            for fm in kwargs["field_mappings"]:
                db.session.add(ImportFieldMapping(
                    mapping_id=mapping.id,
                    field_marker=fm["field_marker"],
                    lift_element=fm.get("lift_element", ""),
                    level=fm.get("level", "entry"),
                    lang=fm.get("lang"),
                    is_key=fm.get("is_key", False),
                    field_type=fm.get("field_type", "normal"),
                ))

        if "language_mappings" in kwargs:
            ImportLanguageMapping.query.filter_by(mapping_id=mapping.id).delete()
            for lm in kwargs["language_mappings"]:
                db.session.add(ImportLanguageMapping(
                    mapping_id=mapping.id,
                    source_lang=lm["source_lang"],
                    target_lang=lm["target_lang"],
                ))

        if "pos_mappings" in kwargs:
            # Bulk replace all POS mappings for this profile
            ImportPOSMapping.query.filter_by(mapping_id=mapping.id).delete()
            for pm in kwargs["pos_mappings"]:
                db.session.add(ImportPOSMapping(
                    mapping_id=mapping.id,
                    source_value=pm["source_value"],
                    target_value=pm["target_value"],
                    note=pm.get("note"),
                ))

        safe_commit(db, "import_mapping_service")
        return mapping

    def to_field_map_dict(self, mapping: ImportMapping) -> dict[str, dict]:
        """Convert an ImportMapping to a plain dict keyed by field_marker.

        Returns:
            {marker: {lift_element, level, lang, is_key, field_type}}
        """
        return {
            fm.field_marker: {
                "lift_element": fm.lift_element,
                "level": fm.level,
                "lang": fm.lang,
                "is_key": fm.is_key,
                "field_type": fm.field_type,
            }
            for fm in mapping.field_mappings
        }

    def to_language_map_dict(self, mapping: ImportMapping) -> dict[str, str]:
        """Convert language mappings to a source→target dict."""
        return {
            lm.source_lang: lm.target_lang
            for lm in mapping.language_mappings
        }

    def to_pos_map_dict(self, mapping: ImportMapping) -> dict[str, str]:
        """Return user-defined POS mappings as {source_value: target_value}.

        Pass this to ``import_converter.import_parsed_document`` as
        ``user_pos_map`` so user definitions take precedence over built-in hints.
        Returns an empty dict when no POS mappings are configured, which
        means the built-in SHOEBOX_POS_MAP hints will be used as fallback.
        """
        return {
            pm.source_value: pm.target_value
            for pm in mapping.pos_mappings
        }

    # ------------------------------------------------------------------
    # POS mapping CRUD helpers
    # ------------------------------------------------------------------

    def set_pos_mapping(
        self,
        mapping_id: int,
        source_value: str,
        target_value: str,
        note: Optional[str] = None,
    ) -> ImportPOSMapping:
        """Upsert a single POS mapping row (source_value is the unique key)."""
        mapping = ImportMapping.query.get(mapping_id)
        if mapping is None:
            raise ValueError(f"ImportMapping {mapping_id} not found")
        existing = ImportPOSMapping.query.filter_by(
            mapping_id=mapping_id, source_value=source_value
        ).first()
        if existing:
            existing.target_value = target_value
            existing.note = note
            pm = existing
        else:
            pm = ImportPOSMapping(
                mapping_id=mapping_id,
                source_value=source_value,
                target_value=target_value,
                note=note,
            )
            db.session.add(pm)
        safe_commit(db, "import_mapping_service")
        return pm

    def delete_pos_mapping(self, pos_mapping_id: int) -> bool:
        """Delete a single ImportPOSMapping row by its own PK."""
        pm = ImportPOSMapping.query.get(pos_mapping_id)
        if pm is None:
            return False
        db.session.delete(pm)
        safe_commit(db, "import_mapping_service")
        return True

    def get_pos_mappings(self, mapping_id: int) -> list[ImportPOSMapping]:
        """Return all POS mappings for a given ImportMapping."""
        return ImportPOSMapping.query.filter_by(mapping_id=mapping_id).all()

    def detect_unmapped_pos_values(
        self,
        mapping_id: int,
        sfm_text: str,
        pos_marker: str = "ps",
    ) -> list[dict]:
        """Scan SFM text for \\ps values not yet covered by user mappings.

        Returns a list of {source_value, suggested, count} dicts sorted by
        count descending, for use in the POS mapping UI.
        """
        from app.services.sfm_parser import _parse_marker_line
        from app.services.import_converter import SHOEBOX_POS_MAP
        from collections import Counter

        user_map = self.to_pos_map_dict(
            ImportMapping.query.get(mapping_id) or ImportMapping()
        )
        counts: Counter = Counter()
        for line in sfm_text.split("\n"):
            marker, _, value = _parse_marker_line(line)
            if marker == pos_marker and value:
                counts[value.strip()] += 1

        result = []
        for val, count in counts.most_common():
            if val in user_map:
                continue  # already mapped
            suggested = SHOEBOX_POS_MAP.get(val.lower())
            result.append({
                "source_value": val,
                "suggested": suggested,
                "count": count,
            })
        return result

    def auto_detect_mapping_from_sfm(
        self,
        text: str,
        name: str = "Auto-detected",
        owner_id: Optional[int] = None,
    ) -> ImportMapping:
        """Auto-detect field markers and create a new ImportMapping.

        Uses the SFMParser's auto_detect logic plus heuristic field->LIFT
        element mapping.
        """
        from app.services.sfm_parser import SFMParser

        parser = SFMParser.auto_detect(text)
        all_keys: set[str] = set()

        # Collect all markers from the text
        import re
        from app.services.sfm_parser import MARKER_RE, _parse_marker_line
        for line in text.split("\n"):
            marker, lang, _ = _parse_marker_line(line)
            if marker:
                all_keys.add(marker)

        field_mappings = []
        for marker in sorted(all_keys):
            cfg: dict = {"field_marker": marker}
            if marker in parser.entry_keys:
                cfg["level"] = "entry"
                cfg["is_key"] = True
                cfg["lift_element"] = _guess_lift_element(marker, "entry")
            elif marker in parser.sense_keys:
                cfg["level"] = "sense"
                cfg["lift_element"] = _guess_lift_element(marker, "sense")
            elif marker in parser.example_keys:
                cfg["level"] = "example"
                cfg["lift_element"] = _guess_lift_element(marker, "example")
            elif marker in parser.pronun_keys:
                cfg["level"] = "pronunciation"
                cfg["lift_element"] = _guess_lift_element(marker, "pronunciation")
            else:
                cfg["level"] = "entry"
                cfg["lift_element"] = "field"

            if marker in parser.cross_ref_source:
                cfg["field_type"] = "cross-ref-source"
            elif marker in parser.cross_ref_target:
                cfg["field_type"] = "cross-ref-target"
            elif marker in parser.variant_target:
                cfg["field_type"] = "variant-target"
            elif marker in parser.variant_type:
                cfg["field_type"] = "variant-type"

            field_mappings.append(cfg)

        return self.create(
            name=name,
            file_type="sfm",
            field_mappings=field_mappings,
            owner_id=owner_id,
        )


def _guess_lift_element(marker: str, level: str) -> str:
    """Heuristic guess of LIFT element from an SFM marker name."""
    marker_lower = marker.lower()

    # Common MDF / Toolbox markers
    guess_map = {
        "lx": "lexeme",
        "lc": "citation",
        "ph": "pronunciation_form",
        "pn": "pronunciation_form",
        "ps": "grammatical_info",
        "sn": "sense_trait",
        "se": "sense_trait",
        "de": "definition",
        "dn": "definition",
        "ge": "gloss",
        "gl": "gloss",
        "re": "reversal",
        "rf": "reversal",
        "xv": "example_form",
        "xe": "example_form",
        "xv_en": "example_translation",
        "xe_en": "example_translation",
        "ex": "example_form",
        "am": "variant_form",
        "al": "variant_form",
        "mn": "variant_form",
        "vt": "variant_form",
        "va": "variant_form",
        "lf": "field",
        "lv": "field",
        "et": "etymology_form",
        "eg": "etymology_gloss",
        "il": "illustration",
        "md": "pronunciation_media",
        "an": "annotation",
        "so": "sense_relation",
        "cf": "sense_relation",
        "nt": "entry_note",
        "xn": "example_note",
        "xr": "example_note",
    }

    if marker_lower in guess_map:
        return guess_map[marker_lower]

    if level == "entry":
        return "entry_field"
    elif level == "sense" and marker_lower.startswith("x"):
        return "example_form"
    elif level == "sense":
        return "sense_trait"
    elif level == "example":
        return "example_form"
    elif level == "pronunciation":
        return "pronunciation_form"
    elif level == "variant":
        return "variant_form"

    return "entry_field"
