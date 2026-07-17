"""
Common Lexical Sense Format (CLSF) data classes.

A generalized format for representing lexical entries with senses,
designed for cross-dictionary comparison and gap analysis.

Language fields use Dict[str, str] maps (language code -> text)
instead of hardcoded language fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class UsageNote:
    """Usage note for a sense in arbitrary languages."""
    languages: Dict[str, str] = field(default_factory=dict)

    def __init__(self, languages: Dict[str, str] = None, **kwargs):
        # Support both new-style (languages={"en": "x"}) and
        # legacy keyword args (en="x", pl="y")
        self.languages = dict(languages) if languages else {}
        for k, v in kwargs.items():
            if v is not None and k not in ("languages",):
                self.languages[k] = v

    def to_dict(self) -> Dict[str, Any]:
        if not self.languages:
            return {}
        return {"languages": dict(self.languages)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UsageNote:
        if not data:
            return cls()
        if "languages" in data:
            return cls(languages=data["languages"])
        # Legacy: flat dict with language keys
        return cls(languages={k: v for k, v in data.items()})


@dataclass
class Example:
    """Example sentence with translations in arbitrary languages."""
    languages: Dict[str, str] = field(default_factory=dict)

    def __init__(self, languages: Dict[str, str] = None, **kwargs):
        self.languages = dict(languages) if languages else {}
        for k, v in kwargs.items():
            if v is not None and k not in ("languages",):
                self.languages[k] = v

    def to_dict(self) -> Dict[str, Any]:
        if not self.languages:
            return {}
        return {"languages": dict(self.languages)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Example:
        if not data:
            return cls()
        if "languages" in data:
            return cls(languages=data["languages"])
        return cls(languages={k: v for k, v in data.items()})


@dataclass
class Sense:
    """A single sense of a lexical entry."""
    id: Optional[str] = None
    definition: str = ""
    translations: List[str] = field(default_factory=list)
    usage_notes: Optional[UsageNote] = None
    examples: List[Example] = field(default_factory=list)
    semantic_domain: Optional[str] = None
    scientific_name: Optional[str] = None
    synset_id: Optional[str] = None
    confidence: float = 1.0
    status: str = "verified"

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.id:
            result["id"] = self.id
        result["definition"] = self.definition
        if self.translations:
            result["translations"] = list(self.translations)
        if self.usage_notes:
            notes = self.usage_notes.to_dict()
            if notes:
                result["usage_notes"] = notes
        if self.examples:
            result["examples"] = [
                e.to_dict() if hasattr(e, 'to_dict') else {"text": str(e)}
                for e in self.examples
                if (e.to_dict() if hasattr(e, 'to_dict') else str(e))
            ]
        if self.semantic_domain:
            result["semantic_domain"] = self.semantic_domain
        if self.scientific_name:
            result["scientific_name"] = self.scientific_name
        if self.synset_id:
            result["synset_id"] = self.synset_id
        if self.confidence != 1.0:
            result["confidence"] = round(self.confidence, 2)
        if self.status != "verified":
            result["status"] = self.status
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Sense:
        if not data:
            return cls()
        usage_notes = None
        if "usage_notes" in data:
            usage_notes = UsageNote.from_dict(data["usage_notes"])
        examples = []
        if "examples" in data:
            for ex_data in data["examples"]:
                if isinstance(ex_data, dict):
                    examples.append(Example.from_dict(ex_data))
                elif isinstance(ex_data, str):
                    examples.append(Example(languages={"und": ex_data}))
        return cls(
            id=data.get("id"),
            definition=data.get("definition", ""),
            translations=data.get("translations", []),
            usage_notes=usage_notes,
            examples=examples,
            semantic_domain=data.get("semantic_domain"),
            scientific_name=data.get("scientific_name"),
            synset_id=data.get("synset_id"),
            confidence=data.get("confidence", 1.0),
            status=data.get("status", "verified"),
        )


@dataclass
class Entry:
    """A lexical entry with headword, POS, and senses."""
    headword: str = ""
    part_of_speech: Optional[str] = None
    language: str = ""
    variants: List[str] = field(default_factory=list)
    abbreviations: List[str] = field(default_factory=list)
    source: Optional[str] = None
    senses: List[Sense] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"headword": self.headword}
        if self.part_of_speech:
            result["part_of_speech"] = self.part_of_speech
        result["language"] = self.language
        if self.variants:
            result["variants"] = list(self.variants)
        if self.abbreviations:
            result["abbreviations"] = list(self.abbreviations)
        if self.source:
            result["source"] = self.source
        if self.senses:
            result["senses"] = [s.to_dict() for s in self.senses]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Entry:
        if not data:
            return cls()
        senses = []
        if "senses" in data:
            for s_data in data["senses"]:
                if isinstance(s_data, dict):
                    senses.append(Sense.from_dict(s_data))
        return cls(
            headword=data.get("headword", ""),
            part_of_speech=data.get("part_of_speech"),
            language=data.get("language", ""),
            variants=data.get("variants", []),
            abbreviations=data.get("abbreviations", []),
            source=data.get("source"),
            senses=senses,
        )


@dataclass
class Metadata:
    """Metadata for a CLSF document."""
    name: str = ""
    version: str = ""
    language: str = ""
    description: Optional[str] = None
    source_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"name": self.name}
        if self.version:
            result["version"] = self.version
        if self.language:
            result["language"] = self.language
        if self.description:
            result["description"] = self.description
        if self.source_url:
            result["source_url"] = self.source_url
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Metadata:
        if not data:
            return cls()
        return cls(
            name=data.get("name", ""),
            version=data.get("version", ""),
            language=data.get("language", ""),
            description=data.get("description"),
            source_url=data.get("source_url"),
        )


@dataclass
class LexicalSenseFormat:
    """Top-level CLSF document containing metadata and entries."""
    metadata: Metadata = field(default_factory=Metadata)
    entries: List[Entry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LexicalSenseFormat:
        if not data:
            return cls()
        metadata = Metadata.from_dict(data.get("metadata", {}))
        entries = []
        for e_data in data.get("entries", []):
            entries.append(Entry.from_dict(e_data))
        return cls(metadata=metadata, entries=entries)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> LexicalSenseFormat:
        return cls.from_dict(json.loads(s))

    def to_yaml(self) -> str:
        try:
            import yaml
            return yaml.dump(self.to_dict(), allow_unicode=True, default_flow_style=False)
        except ImportError:
            raise ImportError("PyYAML is required for YAML serialization")

    @classmethod
    def from_yaml(cls, s: str) -> LexicalSenseFormat:
        try:
            import yaml
            return cls.from_dict(yaml.safe_load(s))
        except ImportError:
            raise ImportError("PyYAML is required for YAML deserialization")


# --- Gap analysis output structures ---

@dataclass
class GapSummary:
    """Summary statistics for a gap analysis."""
    date: str = ""
    baseline: str = ""
    baseline_version: str = ""
    flex_project: str = ""
    total_headwords_baseline: int = 0
    total_headwords_flex: int = 0
    headword_coverage: float = 0.0
    total_senses_baseline: int = 0
    total_senses_flex: int = 0
    sense_coverage: float = 0.0


@dataclass
class MissingHeadword:
    """A headword present in baseline but missing from the dictionary."""
    headword: str = ""
    pos: str = ""
    priority: str = "low"
    translations: List[str] = field(default_factory=list)


@dataclass
class MissingSense:
    """A sense gap for a headword that exists in both resources."""
    headword: str = ""
    baseline_senses: int = 0
    flex_senses: int = 0
    missing_translations: List[str] = field(default_factory=list)
    missing_senses: List[Dict] = field(default_factory=list)


@dataclass
class GapAnalysis:
    """Complete gap analysis result."""
    summary: GapSummary = field(default_factory=GapSummary)
    missing_headwords: List[MissingHeadword] = field(default_factory=list)
    missing_senses: List[MissingSense] = field(default_factory=list)
    translation_gaps: List[Dict] = field(default_factory=list)

    def generate_report(self, format: str = "markdown", show_all: bool = True) -> str:
        if format == "json":
            return self._generate_json()
        elif format == "markdown":
            return self._generate_markdown(show_all)
        else:
            return self._generate_text(show_all)

    def _generate_json(self) -> str:
        data = {
            "summary": asdict(self.summary),
            "missing_headwords": [asdict(mh) for mh in self.missing_headwords],
            "missing_senses": [asdict(ms) for ms in self.missing_senses],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _generate_markdown(self, show_all: bool = True) -> str:
        lines = [
            f"# Gap Analysis Report",
            f"",
            f"**Date:** {self.summary.date}",
            f"**Baseline:** {self.summary.baseline}",
            f"**Dictionary:** {self.summary.flex_project}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Headword Coverage | {self.summary.headword_coverage:.1f}% |",
            f"| Sense Coverage | {self.summary.sense_coverage:.1f}% |",
            f"| Missing Headwords | {len(self.missing_headwords)} |",
            f"| Missing Senses | {len(self.missing_senses)} |",
            f"",
        ]
        if self.missing_headwords:
            lines.append("## Missing Headwords")
            lines.append("")
            for mh in (self.missing_headwords if show_all else self.missing_headwords[:20]):
                trans = ", ".join(mh.translations[:3]) if mh.translations else "—"
                lines.append(f"- **{mh.headword}** ({mh.pos or '?'}) [{mh.priority}] → {trans}")
            lines.append("")
        if self.missing_senses:
            lines.append("## Sense Gaps")
            lines.append("")
            for ms in (self.missing_senses if show_all else self.missing_senses[:20]):
                line = (
                    f"- **{ms.headword}**: baseline {ms.baseline_senses} senses, "
                    f"dictionary {ms.flex_senses} senses"
                )
                if ms.missing_translations:
                    trans = ", ".join(ms.missing_translations[:5])
                    line += f" — missing: {trans}"
                lines.append(line)
            lines.append("")
        return "\n".join(lines)

    def _generate_text(self, show_all: bool = True) -> str:
        lines = [
            f"Gap Analysis: {self.summary.baseline} vs {self.summary.flex_project}",
            f"Headword coverage: {self.summary.headword_coverage:.1f}%",
            f"Sense coverage: {self.summary.sense_coverage:.1f}%",
            f"Missing headwords: {len(self.missing_headwords)}",
            f"Missing senses: {len(self.missing_senses)}",
        ]
        for mh in (self.missing_headwords if show_all else self.missing_headwords[:20]):
            lines.append(f"  MISSING: {mh.headword} ({mh.pos or '?'}) [{mh.priority}]")
        return "\n".join(lines)
