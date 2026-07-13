# encoding: UTF-8
"""Unit tests for the POST /api/pronunciation/draft endpoint."""

from __future__ import annotations

import sys

import pytest

if __package__ in (None, ""):
    sys.path.insert(0, ".")


class _StubService:
    def __init__(self, available: bool, candidates):
        self._available = available
        self._candidates = candidates

    def is_available(self) -> bool:
        return self._available

    def draft_ipa(self, headword, num_return_sequences=1):
        return self._candidates


def test_draft_endpoint_returns_candidates(monkeypatch):
    from app import create_app
    import app.api.pronunciation as pron
    import app.services.ipa_byt5_service as byt5mod

    monkeypatch.setattr(pron, "_check_api_key_auth", lambda scope: True)
    monkeypatch.setattr(
        byt5mod.IPAByT5Service,
        "get_instance",
        staticmethod(lambda *a, **k: _StubService(True, ["ˈkæt", "ˈkat"])),
    )

    app = create_app()
    client = app.test_client()
    resp = client.post(
        "/api/pronunciation/draft",
        json={"headword": "cat", "writing_system": "seh-fonipa", "num_candidates": 2},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["available"] is True
    assert body["candidates"] == ["ˈkæt", "ˈkat"]


def test_draft_endpoint_unavailable_is_200_empty(monkeypatch):
    from app import create_app
    import app.api.pronunciation as pron
    import app.services.ipa_byt5_service as byt5mod

    monkeypatch.setattr(pron, "_check_api_key_auth", lambda scope: True)
    monkeypatch.setattr(
        byt5mod.IPAByT5Service,
        "get_instance",
        staticmethod(lambda *a, **k: _StubService(False, [])),
    )

    app = create_app()
    client = app.test_client()
    resp = client.post("/api/pronunciation/draft", json={"headword": "cat"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["available"] is False
    assert body["candidates"] == []


def test_draft_endpoint_requires_headword(monkeypatch):
    from app import create_app
    import app.api.pronunciation as pron
    import app.services.ipa_byt5_service as byt5mod

    monkeypatch.setattr(pron, "_check_api_key_auth", lambda scope: True)
    monkeypatch.setattr(
        byt5mod.IPAByT5Service,
        "get_instance",
        staticmethod(lambda *a, **k: _StubService(True, ["ˈkæt"])),
    )

    app = create_app()
    client = app.test_client()
    resp = client.post("/api/pronunciation/draft", json={"headword": "  "})
    assert resp.status_code == 400


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
