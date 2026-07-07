# encoding: UTF-8
"""Unit tests for IPAAnomalyService discovery and sidecar bundle loading."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

if __package__ in (None, ""):
    sys.path.insert(0, ".")

from app.services.ipa_anomaly_service import (  # noqa: E402
    IPAAnomalyService,
    decompress_ipa,
)

# Trainer/transformer are heavy; build a minimal but valid model artifact
# directly from the g2p package for fast, deterministic tests.
G2P_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "scripts",
    "ipa_training",
)
sys.path.insert(0, G2P_ROOT)


def _write_bundle(directory: Path, ws: str, pairs) -> Path:
    """Create a self-contained sidecar bundle in ``directory``."""
    from g2p import (  # type: ignore
        G2PModel,
        ModelConfig,
        G2PTokenizer,
        build_vocab_from_data,
    )

    gv, pv = build_vocab_from_data(pairs)
    tok = G2PTokenizer(grapheme_vocab=gv, phoneme_vocab=pv)
    cfg = ModelConfig(
        grapheme_vocab_size=len(gv),
        phoneme_vocab_size=len(pv),
        pad_token_id=tok.PAD_ID,
        bos_token_id=tok.BOS_ID,
        eos_token_id=tok.EOS_ID,
    )
    model = G2PModel(cfg)
    safe_ws = ws.replace(os.sep, "_")
    pt_path = directory / f"ipa_anomaly_{safe_ws}.pt"
    json_path = directory / f"ipa_anomaly_{safe_ws}.json"
    import torch

    torch.save({"model_state_dict": model.state_dict()}, str(pt_path))
    bundle = {
        "ipa_writing_system": ws,
        "model_config": cfg.__dict__,
        "grapheme_vocab": tok.grapheme_vocab,
        "phoneme_vocab": tok.phoneme_vocab,
    }
    json_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    return directory


@pytest.fixture
def bundle_dir():
    with tempfile.TemporaryDirectory(prefix="ipa_svc_") as d:
        _write_bundle(Path(d), "seh-fonipa", [("cat", "ˈkæt"), ("dog", "ˈdɒɡ")])
        yield d


def test_discovery_finds_matching_writing_system(bundle_dir):
    svc = IPAAnomalyService(model_dir=bundle_dir, ipa_ws="seh-fonipa")
    assert svc.is_available() is True


def test_discovery_rejects_non_matching_writing_system(bundle_dir):
    # Only seh-fonipa is bundled; a different writing system must NOT match.
    svc = IPAAnomalyService(model_dir=bundle_dir, ipa_ws="en-fonipa")
    assert svc.is_available() is False


def test_no_model_directory_is_unavailable():
    svc = IPAAnomalyService(model_dir="/nonexistent/ipa_models", ipa_ws="seh-fonipa")
    assert svc.is_available() is False


def test_bundle_loads_with_weights_only_and_detects(bundle_dir):
    svc = IPAAnomalyService(model_dir=bundle_dir, ipa_ws="seh-fonipa")
    assert svc.is_available()
    # Decompression always happens before model comparison.
    result = svc.detect("cat", "ˈskɒtɪˌsɪz(ə)m")
    assert result is not None
    assert result["stored_ipa"] == decompress_ipa("ˈskɒtɪˌsɪz(ə)m")
    assert "(ə)" not in result["stored_ipa"]


def test_env_override_selects_directory(monkeypatch, bundle_dir):
    monkeypatch.setenv("IPA_MODEL_DIR", bundle_dir)
    svc = IPAAnomalyService(ipa_ws="seh-fonipa")
    assert svc.is_available() is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
