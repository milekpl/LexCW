# encoding: UTF-8
"""Unit tests for the IPA pronunciation anomaly validation rule (R4.3.1)."""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

# Ensure the app package is importable when run directly.
if __package__ in (None, ""):
    sys.path.insert(0, ".")

from app.services.validation_engine import ValidationEngine  # noqa: E402
from app.services.ipa_anomaly_service import (  # noqa: E402
    IPAAnomalyService,
    decompress_ipa,
    decompress_ipa_variants,
)


class _StubService:
    """Minimal stand-in for IPAAnomalyService used by the rule tests."""

    _last_instance: Optional["_StubService"] = None

    def __init__(self, ipa_ws: str = "seh-fonipa", confidence_threshold: float = 0.5):
        self.ipa_ws = ipa_ws
        self.confidence_threshold = confidence_threshold
        self.calls: List[Dict[str, Any]] = []
        _StubService._last_instance = self

    @classmethod
    def get_instance(cls, model_dir=None, ipa_ws="seh-fonipa", confidence_threshold=0.5):
        return cls(ipa_ws=ipa_ws, confidence_threshold=confidence_threshold)

    def is_available(self) -> bool:
        return True

    def detect(self, headword: str, ipa: str) -> Optional[Dict[str, Any]]:
        self.calls.append({"headword": headword, "ipa": ipa})
        # ``ˈkæt`` is perfectly predicted; everything else is anomalous.
        if ipa == "ˈkæt":
            return {
                "is_anomaly": False,
                "stored_ipa": ipa,
                "predicted_ipa": ipa,
                "confidence_score": 1.0,
                "anomaly_type": None,
                "per": 0.0,
            }
        return {
            "is_anomaly": True,
            "stored_ipa": ipa,
            "predicted_ipa": "ˈprɛdɪkt",
            "confidence_score": 0.1,
            "anomaly_type": "confidence",
            "per": 0.9,
        }


def _engine() -> ValidationEngine:
    return ValidationEngine(project_id="test-ipa-rule")


def _entry(headword: str, ipa: str) -> Dict[str, Any]:
    return {
        "id": "e1",
        "lexical_unit": {"en": headword},
        "pronunciations": {"seh-fonipa": ipa},
    }


# --------------------------------------------------------------------------- #
# decompress_ipa
# --------------------------------------------------------------------------- #
def test_decompress_single_group():
    assert decompress_ipa("ˈskɒtɪˌsɪz(ə)m") == "ˈskɒtɪˌsɪzm"
    variants = decompress_ipa_variants("ˈskɒtɪˌsɪz(ə)m")
    assert set(variants) == {"ˈskɒtɪˌsɪzm", "ˈskɒtɪˌsɪzəm"}


def test_decompress_no_parens_is_identity():
    assert decompress_ipa("ˈkæt") == "ˈkæt"


def test_decompress_is_shortest_variant():
    # Two adjacent optional groups -> 4 variants; shortest has neither optional.
    variants = decompress_ipa_variants("a(b)c(d)")
    assert set(variants) == {"ac", "acd", "abc", "abcd"}
    assert decompress_ipa("a(b)c(d)") == "ac"


# --------------------------------------------------------------------------- #
# rule R4.3.1
# --------------------------------------------------------------------------- #
def test_rule_flags_anomaly_when_model_detects():
    with patch(
        "app.services.ipa_anomaly_service.IPAAnomalyService", _StubService
    ):
        engine = _engine()
        res = engine.validate_json(_entry("scotsism", "ˈskɒtɪˌsɪz(ə)m"), "save")
    anomaly = [w for w in res.warnings if w.rule_id == "R4.3.1"]
    assert anomaly, "expected an R4.3.1 warning"
    assert "ˈprɛdɪkt" in anomaly[0].message
    assert anomaly[0].path == "$.pronunciations.seh-fonipa"
    # The engine passes the raw (parenthetical) IPA; decompression happens
    # inside the service before model comparison.
    assert _StubService._last_instance.calls[0]["ipa"] == "ˈskɒtɪˌsɪz(ə)m"


def test_rule_passes_when_prediction_matches():
    with patch(
        "app.services.ipa_anomaly_service.IPAAnomalyService", _StubService
    ):
        engine = _engine()
        res = engine.validate_json(_entry("cat", "ˈkæt"), "save")
    anomaly = [w for w in res.warnings if w.rule_id == "R4.3.1"]
    assert not anomaly


def test_rule_is_noop_without_model():
    class _Unavailable(_StubService):
        def is_available(self) -> bool:
            return False

    with patch(
        "app.services.ipa_anomaly_service.IPAAnomalyService", _Unavailable
    ):
        engine = _engine()
        res = engine.validate_json(_entry("scotsism", "ˈskɒtɪˌsɪz(ə)m"), "save")
    anomaly = [w for w in res.warnings if w.rule_id == "R4.3.1"]
    assert not anomaly


def test_rule_skips_non_ipa_writing_systems():
    with patch(
        "app.services.ipa_anomaly_service.IPAAnomalyService", _StubService
    ):
        engine = _engine()
        entry = {
            "id": "e2",
            "lexical_unit": {"en": "scotsism"},
            "pronunciations": {"en-fonipa": "ˈskɒtɪˌsɪz(ə)m"},
        }
        res = engine.validate_json(entry, "save")
    anomaly = [w for w in res.warnings if w.rule_id == "R4.3.1"]
    assert not anomaly


def test_service_detect_decompresses_before_model():
    """The service must feed decompressed (parenthesis-free) IPA to the model
    and return the best-matching decompressed variant as ``stored_ipa``."""
    service = IPAAnomalyService(ipa_ws="seh-fonipa")

    class _StubDetector:
        def detect(self, headword: str, ipa: str):
            class _R:
                is_anomaly = False
                predicted_ipa = ipa
                confidence_score = 1.0
                anomaly_type = None
                details = {}

            return _R()

    # Force availability without touching the filesystem.
    service._detector = _StubDetector()
    service._available = True

    # Both decompressed variants score equally well, so the canonical
    # (shortest) variant 'ˈskɒtɪˌsɪzm' is returned as the stored IPA.
    result = service.detect("scotsism", "ˈskɒtɪˌsɪz(ə)m")
    assert result is not None
    assert result["stored_ipa"] == "ˈskɒtɪˌsɪzm"
    assert "(ə)" not in result["stored_ipa"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
