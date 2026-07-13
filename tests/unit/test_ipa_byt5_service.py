# encoding: UTF-8
"""Unit tests for the ByT5 IPA drafting service (discovery + generation)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

if __package__ in (None, ""):
    sys.path.insert(0, ".")

from app.services.ipa_byt5_service import IPAByT5Service  # noqa: E402


class _FakeBatchEncoding(dict):
    def to(self, device):
        return self


class _FakeTokenizer:
    def __init__(self, *args, **kwargs):
        self._prefix_seen = None

    def __call__(self, text, return_tensors=None, **kwargs):
        self._prefix_seen = text
        return _FakeBatchEncoding({"input_ids": [[1, 2, 3]]})

    def decode(self, seq, skip_special_tokens=True):
        # Deterministic "generation" that echoes a fixed IPA.
        return "ˈkæt"


class _FakeModel:
    def __init__(self, *args, **kwargs):
        self.eval_called = False

    def to(self, device):
        return self

    def eval(self):
        self.eval_called = True
        return self

    def generate(self, **kwargs):
        return [[4, 5, 6]]


@pytest.fixture
def byt5_dir():
    with tempfile.TemporaryDirectory(prefix="byt5_svc_") as d:
        model_dir = Path(d) / "ipa_byt5_seh-fonipa"
        model_dir.mkdir()
        (model_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "ipa_writing_system": "seh-fonipa",
                    "source_prefix": "ipa: ",
                    "base_model": "google/byt5-small",
                }
            ),
            encoding="utf-8",
        )
        # Placeholder weight files so the dir looks like a real HF model.
        (model_dir / "config.json").write_text("{}", encoding="utf-8")
        (model_dir / "pytorch_model.bin").write_text("", encoding="utf-8")
        yield d


@pytest.fixture(autouse=True)
def stub_transformers(monkeypatch):
    """Avoid downloading/loading a real HF model in unit tests."""
    import transformers

    monkeypatch.setattr(transformers, "AutoModelForSeq2SeqLM",
                        type("M", (), {"from_pretrained": staticmethod(lambda *a, **k: _FakeModel())}))
    monkeypatch.setattr(transformers, "AutoTokenizer",
                        type("T", (), {"from_pretrained": staticmethod(lambda *a, **k: _FakeTokenizer())}))
    yield


def test_discovery_finds_matching_writing_system(byt5_dir):
    svc = IPAByT5Service(model_dir=byt5_dir, ipa_ws="seh-fonipa")
    assert svc.is_available() is True


def test_discovery_rejects_non_matching_writing_system(byt5_dir):
    svc = IPAByT5Service(model_dir=byt5_dir, ipa_ws="en-fonipa")
    assert svc.is_available() is False


def test_no_model_directory_is_unavailable():
    svc = IPAByT5Service(model_dir="/nonexistent/byt5", ipa_ws="seh-fonipa")
    assert svc.is_available() is False


def test_draft_applies_source_prefix_and_returns_candidate(byt5_dir):
    svc = IPAByT5Service(model_dir=byt5_dir, ipa_ws="seh-fonipa")
    assert svc.is_available()
    candidates = svc.draft_ipa("cat", num_return_sequences=1)
    assert candidates == ["ˈkæt"]
    # The service must have passed the training source_prefix to the tokenizer.
    assert svc._source_prefix == "ipa: "


def test_draft_empty_headword_returns_nothing(byt5_dir):
    svc = IPAByT5Service(model_dir=byt5_dir, ipa_ws="seh-fonipa")
    assert svc.draft_ipa("") == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
