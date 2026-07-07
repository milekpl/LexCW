"""
Unit tests for the validation rules API endpoint merge behavior.

These tests verify that `GET /api/projects/<id>/validation-rules` merges
default rules (e.g. R3.2.2 definition_phrase_coherence) into the response when
`include_defaults=true`, even when the project already has its own stored rule
set. They isolate the endpoint by faking the ValidationRulesService so no
database is required.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock

from flask import Flask


def _make_rule(rule_id: str, name: str, **extra: Any) -> Dict[str, Any]:
    rule = {"rule_id": rule_id, "name": name}
    rule.update(extra)
    return rule


def _fake_service(
    project_rules: List[Dict[str, Any]],
    default_rules: List[Dict[str, Any]],
) -> MagicMock:
    service = MagicMock()
    service.get_project_rules.return_value = project_rules
    service.get_default_rules.return_value = default_rules
    return service


def _call_endpoint(app: Flask, project_id: int, include_defaults: bool) -> Dict[str, Any]:
    from app.api import validation_rules_api as vr

    service = _fake_service(
        project_rules=[
            _make_rule("R1.1.1", "entry_id_required"),
            _make_rule("R6.1.1", "pos_consistency"),
        ],
        default_rules=[
            # Default rule NOT present in the project's stored rule set.
            _make_rule("R3.2.2", "definition_phrase_coherence"),
            # Default rule that the project overrides.
            _make_rule("R1.1.1", "entry_id_required"),
        ],
    )

    original = vr.get_service
    vr.get_service = lambda: service  # type: ignore[assignment]
    try:
        with app.test_request_context(
            f"/api/projects/{project_id}/validation-rules"
            f"?include_defaults={'true' if include_defaults else 'false'}"
        ):
            response = vr.get_project_validation_rules(project_id)
            return response.get_json()
    finally:
        vr.get_service = original  # type: ignore[assignment]


def test_include_defaults_merges_default_rules_with_project_rules() -> None:
    """Default rules must appear in the response alongside project rules."""
    app = Flask(__name__)
    data = _call_endpoint(app, 1, include_defaults=True)

    rule_ids = {r["rule_id"] for r in data["rules"]}
    # The default-only rule must now be present in the dropdown payload.
    assert "R3.2.2" in rule_ids
    # Project rules are still present.
    assert "R1.1.1" in rule_ids
    assert "R6.1.1" in rule_ids
    # No duplicate rule_ids (project override wins).
    assert len(rule_ids) == len(data["rules"])
    assert data["source"] == "merged"


def test_include_defaults_false_returns_only_project_rules() -> None:
    """Without include_defaults, default-only rules must be excluded."""
    app = Flask(__name__)
    data = _call_endpoint(app, 1, include_defaults=False)

    rule_ids = {r["rule_id"] for r in data["rules"]}
    assert "R3.2.2" not in rule_ids
    assert "R1.1.1" in rule_ids
    assert "R6.1.1" in rule_ids
    assert data["source"] == "project"


def test_include_defaults_with_empty_project_rules_falls_back_to_defaults() -> None:
    """When the project has no rules, defaults alone are returned."""
    from app.api import validation_rules_api as vr

    service = _fake_service(
        project_rules=[],
        default_rules=[_make_rule("R3.2.2", "definition_phrase_coherence")],
    )
    original = vr.get_service
    vr.get_service = lambda: service  # type: ignore[assignment]
    try:
        app = Flask(__name__)
        with app.test_request_context(
            "/api/projects/1/validation-rules?include_defaults=true"
        ):
            data = vr.get_project_validation_rules(1).get_json()
    finally:
        vr.get_service = original  # type: ignore[assignment]

    rule_ids = {r["rule_id"] for r in data["rules"]}
    assert rule_ids == {"R3.2.2"}
