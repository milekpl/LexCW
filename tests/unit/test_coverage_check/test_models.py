"""
Unit tests for CLSF data models.

Tests the generalized Common Lexical Sense Format with dynamic language maps.
"""
import pytest
from app.services.coverage_check.models import (
    LexicalSenseFormat, Metadata, Entry, Sense, Example, UsageNote,
    GapAnalysis, GapSummary, MissingHeadword, MissingSense,
)


class TestMetadata:
    def test_creation(self):
        m = Metadata(name="test", version="1.0", language="en")
        assert m.name == "test"
        assert m.language == "en"

    def test_defaults(self):
        m = Metadata(name="test")
        assert m.version == ""
        assert m.language == ""
        assert m.description is None

    def test_to_dict(self):
        m = Metadata(name="test", version="1.0", language="en")
        d = m.to_dict()
        assert d["name"] == "test"
        assert d["language"] == "en"
        assert "description" not in d  # None excluded

    def test_from_dict(self):
        d = {"name": "x", "version": "2.0", "language": "pl"}
        m = Metadata.from_dict(d)
        assert m.name == "x"
        assert m.language == "pl"


class TestUsageNote:
    def test_dynamic_language_map(self):
        un = UsageNote(languages={"en": "formal", "pl": "oficjalny", "de": "formell"})
        assert un.languages["en"] == "formal"
        assert un.languages["de"] == "formell"

    def test_empty(self):
        un = UsageNote()
        assert un.languages == {}

    def test_to_dict(self):
        un = UsageNote(languages={"en": "formal"})
        d = un.to_dict()
        assert d == {"languages": {"en": "formal"}}

    def test_from_dict(self):
        d = {"languages": {"en": "colloquial"}}
        un = UsageNote.from_dict(d)
        assert un.languages["en"] == "colloquial"

    def test_backward_compat_kwargs(self):
        """Legacy keyword args (en=, pl=) should work."""
        un = UsageNote(en="hello", pl="cześć")
        assert un.languages["en"] == "hello"
        assert un.languages["pl"] == "cześć"


class TestExample:
    def test_dynamic_language_map(self):
        ex = Example(languages={"en": "Hello!", "pl": "Cześć!"})
        assert ex.languages["en"] == "Hello!"
        assert ex.languages["pl"] == "Cześć!"

    def test_to_dict_excludes_empty(self):
        ex = Example(languages={"en": "test"})
        d = ex.to_dict()
        assert d == {"languages": {"en": "test"}}

    def test_from_dict(self):
        d = {"languages": {"fr": "Bonjour"}}
        ex = Example.from_dict(d)
        assert ex.languages["fr"] == "Bonjour"

    def test_backward_compat_kwargs(self):
        ex = Example(en="Hi", pl="Hej")
        assert ex.languages["en"] == "Hi"
        assert ex.languages["pl"] == "Hej"


class TestSense:
    def test_creation(self):
        s = Sense(id="s1", definition="a greeting", translations=["halo"])
        assert s.id == "s1"
        assert s.definition == "a greeting"
        assert s.translations == ["halo"]

    def test_defaults(self):
        s = Sense()
        assert s.id is None
        assert s.definition == ""
        assert s.translations == []
        assert s.synset_id is None

    def test_to_dict_minimal(self):
        s = Sense(definition="test")
        d = s.to_dict()
        assert d["definition"] == "test"
        assert "id" not in d  # None excluded
        assert "synset_id" not in d

    def test_to_dict_full(self):
        s = Sense(
            id="s1", definition="test", translations=["t"],
            synset_id="wn:001", semantic_domain="body",
            confidence=0.8, status="uncertain",
        )
        d = s.to_dict()
        assert d["synset_id"] == "wn:001"
        assert d["confidence"] == 0.8
        assert d["status"] == "uncertain"

    def test_from_dict(self):
        d = {"definition": "x", "translations": ["y"], "synset_id": "wn:123"}
        s = Sense.from_dict(d)
        assert s.definition == "x"
        assert s.synset_id == "wn:123"


class TestEntry:
    def test_creation(self):
        e = Entry(headword="cat", language="en")
        assert e.headword == "cat"
        assert e.language == "en"
        assert e.senses == []

    def test_to_dict(self):
        e = Entry(
            headword="dog", part_of_speech="noun", language="en",
            variants=["hound"],
            senses=[Sense(id="s1", definition="canine")],
        )
        d = e.to_dict()
        assert d["headword"] == "dog"
        assert d["variants"] == ["hound"]
        assert len(d["senses"]) == 1

    def test_from_dict(self):
        d = {
            "headword": "run", "part_of_speech": "verb", "language": "en",
            "senses": [{"definition": "move fast"}],
        }
        e = Entry.from_dict(d)
        assert e.headword == "run"
        assert len(e.senses) == 1


class TestLexicalSenseFormat:
    def test_creation(self):
        lsf = LexicalSenseFormat(
            metadata=Metadata(name="test", language="en"),
            entries=[Entry(headword="a", language="en")],
        )
        assert lsf.metadata.name == "test"
        assert len(lsf.entries) == 1

    def test_roundtrip_json(self, minimal_clsf):
        import json
        d = minimal_clsf.to_dict()
        s = json.dumps(d)
        d2 = json.loads(s)
        lsf2 = LexicalSenseFormat.from_dict(d2)
        assert lsf2.metadata.name == "test-dictionary"
        assert len(lsf2.entries) == 1
        assert lsf2.entries[0].headword == "hello"

    def test_roundtrip_yaml(self, minimal_clsf):
        yaml_str = minimal_clsf.to_yaml()
        lsf2 = LexicalSenseFormat.from_yaml(yaml_str)
        assert lsf2.entries[0].headword == "hello"
        assert lsf2.entries[0].senses[0].translations == ["halo", "cześć"]

    def test_empty(self):
        lsf = LexicalSenseFormat()
        assert lsf.entries == []
        assert lsf.metadata.name == ""


class TestGapAnalysis:
    def test_creation(self):
        summary = GapSummary(
            date="2025-01-01", baseline="wordnet", flex_project="test",
            headword_coverage=85.0, sense_coverage=70.0,
        )
        ga = GapAnalysis(summary=summary, missing_headwords=[], missing_senses=[])
        assert ga.summary.headword_coverage == 85.0

    def test_generate_markdown_report(self):
        summary = GapSummary(
            date="2025-01-01", baseline="wordnet", flex_project="test",
            headword_coverage=50.0, sense_coverage=33.3,
        )
        missing_h = [MissingHeadword(headword="car", priority="high")]
        missing_s = [
            MissingSense(headword="cat", baseline_senses=3, flex_senses=1,
                         missing_translations=["автомобиль"])
        ]
        ga = GapAnalysis(summary=summary, missing_headwords=missing_h, missing_senses=missing_s)
        report = ga.generate_report(format="markdown")
        assert "50.0" in report
        assert "car" in report
        assert "автомобиль" in report
