"""
Unit tests for ValidationEngine definition phrase coherence rule (R3.2.2).

The rule splits a definition at the configured delimiter and checks that the
comma-separated segments share a consistent phrase category (noun phrase,
verb phrase, adjective phrase, ...). It does NOT compare the definition's POS
against the headword / entry POS.
"""

from __future__ import annotations

import pytest
from app.services.validation_engine import ValidationEngine


def _coherence_warnings(result: object) -> list:
    return [
        w
        for w in result.warnings
        if w.rule_name == "definition_phrase_coherence" or w.rule_id == "R3.2.2"
    ]


def test_validation_engine_definition_phrase_coherence_comma() -> None:
    engine = ValidationEngine()
    # grammatical_info is intentionally a Verb: the rule must NOT use it as a
    # reference. The segments mix Noun/Verb/Adjective phrase types -> incoherent.
    entry = {
        "id": "entry-test-1",
        "lexical_unit": {"en": "cat"},
        "grammatical_info": "Verb",
        "senses": [
            {
                "id": "sense-1",
                "definition": {"en": "a small feline mammal, to catch mice, very playful"},
            }
        ],
    }

    result = engine.validate_json(entry)
    warnings = _coherence_warnings(result)
    assert len(warnings) > 0
    assert warnings[0].rule_id == "R3.2.2"
    assert "delimiter: ','" in warnings[0].message
    assert "Phrase" in warnings[0].message


def test_validation_engine_definition_phrase_coherence_ignores_headword_pos() -> None:
    """Coherent (all Noun Phrase) segments produce no warning, even if the
    headword POS (Verb) would have conflicted under the old behaviour."""
    engine = ValidationEngine()
    entry = {
        "id": "entry-test-2",
        "lexical_unit": {"en": "run"},
        "grammatical_info": "Verb",
        "senses": [
            {
                "id": "sense-2",
                "definition": {"en": "a small feline mammal, a tiny household pet"},
            }
        ],
    }

    result = engine.validate_json(entry)
    assert len(_coherence_warnings(result)) == 0


def test_validation_engine_definition_phrase_coherence_semicolon() -> None:
    engine = ValidationEngine()

    # Override rule R3.2.2 to use semicolon delimiter
    custom_rules = {
        "R3.2.2": {
            "name": "definition_phrase_coherence",
            "description": "Validates phrase-category coherence across definition segments split by configurable delimiter",
            "category": "sense_level",
            "priority": "warning",
            "path": "$.senses[*]",
            "condition": "custom",
            "validation": {
                "custom_function": "validate_definition_phrase_coherence",
                "delimiter": ";",
            },
            "error_message": "Definition segments have inconsistent phrase categories",
            "client_side": True,
        }
    }
    engine.set_project_rules("test_proj_semicolon", custom_rules)
    engine_proj = ValidationEngine(project_id="test_proj_semicolon")

    entry = {
        "id": "entry-test-3",
        "lexical_unit": {"en": "run"},
        "grammatical_info": "Verb",
        "senses": [
            {
                "id": "sense-3",
                "definition": {"en": "to move fast on foot; a rapid movement; very energetic"},
            }
        ],
    }

    result = engine_proj.validate_json(entry)
    warnings = _coherence_warnings(result)
    assert len(warnings) > 0
    assert "delimiter: ';'" in warnings[0].message
    assert "Phrase" in warnings[0].message
