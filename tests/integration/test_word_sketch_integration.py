"""
Integration smoke tests for the word sketch feature.

These tests are intentionally narrow and skip cleanly when the live services are
not available in the local environment.
"""
from __future__ import annotations

import os

import pytest

from app.services.word_sketch import WordSketchClient


pytestmark = pytest.mark.integration


def _service_url() -> str:
    return os.environ.get("LUCENE_WORD_SKETCH_URL", "http://localhost:8080")


def test_word_sketch_health_smoke() -> None:
    client = WordSketchClient(base_url=_service_url())
    health = client.health()

    assert "status" in health


def test_word_sketch_relation_smoke() -> None:
    client = WordSketchClient(base_url=_service_url())
    sketch = client.word_sketch("house", limit=5)

    if sketch is None:
        pytest.skip("word sketch service unavailable")

    assert sketch.lemma == "house"
    assert sketch.collocations is not None