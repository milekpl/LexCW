"""
Pandoc Markdown Exporter.

Produces a single Markdown file suitable for conversion to PDF
via pandoc.

Two modes:
1. Simple (default) — hardcoded rendering, no profile needed.
2. Profile-driven — uses a DisplayProfile for field selection,
   ordering, abbreviation, and entry hierarchy (lexeme-based or
   root-based, with subentries).
"""

from __future__ import annotations

import os
import logging
from datetime import date
from typing import Optional, List
from collections import defaultdict

from app.services.dictionary_service import DictionaryService
from app.services.css_mapping_service import CSSMappingService
from app.exporters.base_exporter import BaseExporter
from app.models.entry import Entry
from app.models.sense import Sense


logger = logging.getLogger(__name__)


# -- Simple renderer helpers (backward compat) ---------------------------

def _extract_text(d: dict[str, str] | str | None, lang: str = "en") -> str:
    if not d:
        return ""
    if isinstance(d, str):
        return d
    return d.get(lang) or next(iter(d.values()), "")


def _sense_lines(sense: Sense, index: int) -> list[str]:
    lines: list[str] = []
    parts = []

    gram = sense.grammatical_info or ""
    if gram:
        parts.append(f"*{gram}.*")

    defn = _extract_text(sense.definitions)
    gloss = _extract_text(sense.glosses)

    if defn:
        parts.append(defn)
    elif gloss:
        parts.append(gloss)

    if parts:
        lines.append(f"{index}.  {' '.join(parts)}")

    if defn and gloss:
        lines.append(f"    > Gloss: *{gloss}*")

    for ex in (sense.examples or []):
        ex_form = _extract_text(ex.get("form") if isinstance(ex, dict) else getattr(ex, "form", None))
        if ex_form:
            lines.append(f'    > "{ex_form}"')
        if isinstance(ex, dict):
            ex_tr = _extract_text(ex.get("translations"))
        else:
            ex_tr = _extract_text(getattr(ex, "translations", None))
        if ex_tr:
            lines.append(f"    > {ex_tr}")

    return lines


def _entry_markdown(entry: Entry) -> list[str]:
    lines: list[str] = []

    heading = _extract_text(entry.lexical_unit)
    if entry.homograph_number:
        heading += f"<sub>{entry.homograph_number}</sub>"
    lines.append(f"## {heading}")

    info_parts = []
    pronoun = _extract_text(entry.pronunciations)
    if pronoun:
        info_parts.append(f"/{pronoun}/")
    if entry.grammatical_info:
        g = entry.grammatical_info
        if isinstance(g, str):
            info_parts.append(f"*{g}*")
        elif hasattr(g, "part_of_speech"):
            info_parts.append(f"*{g.part_of_speech}*")
    if info_parts:
        lines.append(f"**{_extract_text(entry.lexical_unit)}** {' '.join(info_parts)}")
        lines.append("")

    senses = getattr(entry, "senses", []) or []
    sense_idx = 0
    for sense in senses:
        sl = _sense_lines(sense, sense_idx + 1)
        if sl:
            lines.extend(sl)
            sense_idx += 1

    if sense_idx == 0:
        lines.append("*No definitions.*")

    variants = getattr(entry, "variants", []) or []
    variant_forms = []
    for v in variants:
        vf = _extract_text(v.form if hasattr(v, "form") else v.get("form", {}) if isinstance(v, dict) else "")
        if vf:
            label = ""
            if hasattr(v, "grammatical_info") and v.grammatical_info:
                label = f" ({v.grammatical_info})"
            variant_forms.append(f"{vf}{label}")
    if variant_forms:
        lines.append("")
        lines.append("    *Variants:* " + ", ".join(variant_forms))

    rels: list[str] = []
    for rel in (entry.relations or []):
        rtype = getattr(rel, "type", rel.get("type", "") if isinstance(rel, dict) else "")
        rref = getattr(rel, "ref", rel.get("ref", "") if isinstance(rel, dict) else "")
        label = rtype.replace("_", " ").replace("-", " ").strip().title()
        if rref:
            rels.append(f"*{label}:* {rref}")
    if rels:
        lines.append("")
        lines.append("    *Related:* " + "; ".join(rels))

    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


# -- Main exporter -------------------------------------------------------

class MarkdownExporter(BaseExporter):
    """Export entries as a single Pandoc-compatible Markdown file."""

    def __init__(self, dictionary_service: DictionaryService):
        super().__init__(dictionary_service)

    def export(
        self,
        output_path: str,
        entries: Optional[List[Entry]] = None,
        title: str = "Dictionary",
        profile_id: Optional[int] = None,
        css_service: Optional[CSSMappingService] = None,
        **kwargs,
    ) -> str:
        if entries is None:
            entries, _ = self.dictionary_service.list_entries(limit=None)

        if not entries:
            raise ValueError("No entries to export")

        if profile_id is not None:
            md, warnings = self._build_profile_markdown(
                entries, title, profile_id, css_service
            )
            if warnings:
                logger.info(
                    "Markdown export completed with %d unmapped elements: %s",
                    len(warnings),
                    "; ".join(
                        f"{w.element_type}='{w.value}' in '{w.entry_headword}'"
                        for w in warnings[:5]
                    ),
                )
        else:
            entries.sort(key=lambda e: (
                _extract_text(e.lexical_unit).lower(),
                e.homograph_number or 0,
            ))
            md = self._build_simple_markdown(entries, title)
            warnings = []

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)

        logger.info("Markdown export created: %s", output_path)

        # Store warnings on the instance so callers can retrieve them
        self._last_warnings = warnings

        return output_path

    @property
    def last_warnings(self) -> list:
        """Warnings from the most recent profile-driven export."""
        return getattr(self, "_last_warnings", [])

    # -- Simple mode ----------------------------------------------------

    def _build_simple_markdown(self, entries: list[Entry], title: str) -> str:
        lines: list[str] = []
        today = date.today().isoformat()

        lines.append("---")
        lines.append(f'title: "{title}"')
        lines.append(f'date: "{today}"')
        lines.append("...")
        lines.append("")

        grouped: dict[str, list[Entry]] = defaultdict(list)
        for entry in entries:
            hw = _extract_text(entry.lexical_unit).strip()
            letter = hw[0].upper() if hw else "#"
            grouped[letter].append(entry)

        for letter in sorted(grouped):
            lines.append(f"# {letter}")
            lines.append("")
            for entry in grouped[letter]:
                lines.extend(_entry_markdown(entry))

        return "\n".join(lines)

    # -- Profile-driven mode --------------------------------------------

    def _build_profile_markdown(
        self,
        entries: list[Entry],
        title: str,
        profile_id: int,
        css_service: Optional[CSSMappingService] = None,
    ) -> tuple[str, list]:
        from app.services.css_mapping_service import CSSMappingService as _CSS
        from app.services.display_profile_service import DisplayProfileService
        from app.exporters.profile_markdown_renderer import (
            ProfileDrivenMarkdownRenderer,
        )

        css_svc = css_service or _CSS()

        profile_svc = DisplayProfileService()
        profile = profile_svc.get_profile(profile_id)
        if not profile:
            raise ValueError(f"DisplayProfile with id={profile_id} not found")

        renderer = ProfileDrivenMarkdownRenderer(
            self.dictionary_service, css_svc
        )

        md, warnings = renderer.render(entries, profile)

        today = date.today().isoformat()
        full = [
            "---",
            f'title: "{title}"',
            f'date: "{today}"',
            "---",
            "",
            md,
        ]

        return "\n".join(full), warnings
