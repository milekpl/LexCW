"""R8.2.2: unique language codes within multitext content (validation_engine)."""

import pytest

from app.services.validation_engine import ValidationEngine


@pytest.fixture
def engine():
    return ValidationEngine()


def _rule_config(**overrides):
    cfg = {
        "name": "Unique languages in multitext",
        "error_message": "Duplicate language code: {value}",
        "priority": "warning",
        "category": "language_validation",
        "validation": {"custom_function": "validate_unique_languages_in_multitext"},
    }
    cfg.update(overrides)
    return cfg


def test_duplicate_languages_in_list_shaped_glosses(engine):
    data = {
        "id": "e1",
        "senses": [{
            "id": "s1",
            "glosses": [
                {"lang": "en", "text": "tree"},
                {"lang": "pl", "text": "drzewo"},
                {"lang": "en", "text": "wood"},  # duplicate
            ],
        }],
    }
    errors = engine._validate_unique_languages_in_multitext("r8.2.2", _rule_config(), data)
    assert len(errors) == 1
    assert errors[0].path == "$.senses[0].glosses[2].lang"
    assert errors[0].value == "en"


def test_dict_shaped_multitext_is_inherently_unique(engine):
    data = {
        "id": "e1",
        "lexical_unit": {"en": "tree", "pl": "drzewo"},
        "senses": [{"id": "s1", "glosses": {"en": "tree"}, "definitions": {"en": "a plant"}}],
    }
    errors = engine._validate_unique_languages_in_multitext("r8.2.2", _rule_config(), data)
    assert errors == []


def test_example_forms_and_subsenses_are_walked(engine):
    data = {
        "id": "e1",
        "senses": [{
            "id": "s1",
            "examples": [{"forms": [{"lang": "en", "text": "x"}, {"lang": "en", "text": "y"}]}],
            "subsenses": [{
                "id": "s2",
                "glosses": [{"lang": "fr", "text": "a"}, {"lang": "fr", "text": "b"}],
            }],
        }],
    }
    errors = engine._validate_unique_languages_in_multitext("r8.2.2", _rule_config(), data)
    paths = {e.path for e in errors}
    assert paths == {
        "$.senses[0].examples[0].forms[1].lang",
        "$.senses[0].subsenses[0].glosses[1].lang",
    }


def test_field_filter_restricts_check(engine):
    data = {
        "id": "e1",
        "senses": [{
            "id": "s1",
            "glosses": [{"lang": "en", "text": "a"}, {"lang": "en", "text": "b"}],
            "definitions": [{"lang": "en", "text": "c"}, {"lang": "en", "text": "d"}],
        }],
    }
    cfg = _rule_config()
    cfg["validation"]["field"] = "definitions"
    errors = engine._validate_unique_languages_in_multitext("r8.2.2", cfg, data)
    assert len(errors) == 1
    assert "$.senses[0].definitions" in errors[0].path
