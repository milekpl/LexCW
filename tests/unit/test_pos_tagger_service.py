"""
Unit tests for POSTaggerService.
"""

from __future__ import annotations

import pytest
from app.services.pos_tagger_service import POSTaggerService, get_pos_tagger_service


def test_pos_tagger_singleton() -> None:
    svc1 = get_pos_tagger_service()
    svc2 = get_pos_tagger_service()
    assert svc1 is svc2


def test_tag_text() -> None:
    svc = POSTaggerService()
    tokens = svc.tag_text("The quick brown fox jumps over the lazy dog")
    assert len(tokens) > 0
    assert "text" in tokens[0]
    assert "pos" in tokens[0]
    assert "normalized_pos" in tokens[0]


def test_predict_entry_pos_existing() -> None:
    svc = POSTaggerService()
    entry = {
        "id": "entry-1",
        "headword": "run",
        "grammatical_info": "Verb",
    }
    result = svc.predict_entry_pos(entry)
    assert result["predicted_pos"] == "Verb"
    assert result["confidence"] == 0.95


def test_predict_entry_pos_definition_rule() -> None:
    svc = POSTaggerService()
    entry = {
        "id": "entry-2",
        "headword": "to walk",
        "senses": [{"definition": "to move on foot at a regular pace"}],
    }
    result = svc.predict_entry_pos(entry)
    assert result["predicted_pos"] == "Verb"
    assert result["confidence"] == 0.85


def test_predict_entry_pos_suffix_rule() -> None:
    svc = POSTaggerService()
    entry = {
        "id": "entry-3",
        "headword": "kindness",
        "senses": [],
    }
    result = svc.predict_entry_pos(entry)
    assert result["predicted_pos"] == "Noun"
    assert result["confidence"] == 0.70


def test_tag_entries_batch() -> None:
    svc = POSTaggerService()
    entries = [
        {"id": "e1", "headword": "quickness"},
        {"id": "e2", "headword": "to sleep", "senses": [{"definition": "to rest in a state of sleep"}]},
    ]
    results = svc.tag_entries_batch(entries)
    assert len(results) == 2
    assert results[0]["entry_id"] == "e1"
    assert results[1]["entry_id"] == "e2"


def test_normalize_tag_penn_and_custom() -> None:
    svc = POSTaggerService()
    # Penn Treebank tags
    assert svc.normalize_tag("NNS", lang="en") == "Noun"
    assert svc.normalize_tag("VBD", lang="en") == "Verb"
    assert svc.normalize_tag("JJR", lang="en") == "Adjective"
    # Polish NKJP tags
    assert svc.normalize_tag("subst", lang="pl") == "Noun"
    assert svc.normalize_tag("fin", lang="pl") == "Verb"
    # Custom user map override
    custom_map = {"CUSTOM_TAG": "Adverb"}
    assert svc.normalize_tag("CUSTOM_TAG", user_map=custom_map) == "Adverb"


def test_save_tagset_mappings() -> None:
    svc = POSTaggerService()
    custom = {"my_n": "Noun", "my_v": "Verb"}
    updated = svc.save_tagset_mappings("test_lang", custom)
    assert updated["my_n"] == "Noun"
    retrieved = svc.get_tagset_mappings("test_lang")
    assert retrieved["my_v"] == "Verb"


def test_analyze_definition_phrases_segments_coherent() -> None:
    """All comma-separated segments share the same phrase type -> no contradictions."""
    svc = POSTaggerService()
    definition = "a red apple, a green pear, a small plum"
    analysis = svc.analyze_definition_phrases(definition, lang="en")
    assert "segments" in analysis
    assert len(analysis["segments"]) == 3
    assert "contradictions" in analysis
    # Every segment is a Noun Phrase -> internally coherent.
    assert analysis["is_consistent"] is True
    assert len(analysis["contradictions"]) == 0
    assert all(s["phrase_category"] == "Noun Phrase" for s in analysis["segments"])


def test_analyze_definition_phrases_segments_incoherent() -> None:
    """Segments of differing phrase types should be flagged as contradictions."""
    svc = POSTaggerService()
    definition = "a small domesticated feline mammal, to hunt mice, very playful"
    analysis = svc.analyze_definition_phrases(definition, lang="en")
    assert len(analysis["segments"]) == 3
    # Mix of Noun Phrase / Verb Phrase / Adjective Phrase -> incoherent.
    assert analysis["is_consistent"] is False
    assert len(analysis["contradictions"]) > 0
    for contra in analysis["contradictions"]:
        assert "Noun Phrase" in (contra["found_pos"], contra["expected_pos"])
        assert "Phrase" in contra["found_pos"]


def test_analyze_definition_phrases_expected_pos_override() -> None:
    """An explicit expected_pos still anchors the comparison (API tool use)."""
    svc = POSTaggerService()
    definition = "a red apple, a green pear"
    analysis = svc.analyze_definition_phrases(definition, lang="en", expected_pos="Noun")
    # Both segments are Noun Phrases -> consistent against expected Noun.
    assert analysis["is_consistent"] is True
    assert len(analysis["contradictions"]) == 0


