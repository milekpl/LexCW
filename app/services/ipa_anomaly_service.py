# encoding: UTF-8
"""
IPA pronunciation anomaly detection service.

Loads the trained G2P (grapheme-to-phoneme) model produced by
``scripts/ipa_training/train_ipa_model.py`` and exposes it as a validation
helper. For a given headword + stored IPA pair, it predicts the expected IPA
from the headword and flags the stored pronunciation as anomalous when the
prediction diverges sharply (low confidence).

Parenthetical IPA notation (e.g. ``ˈskɒtɪˌsɪz(ə)m``) is expanded into all of
its decompressed variants before comparison, so optional segments never cause
false positives. The model was trained on decompressed IPA, so the comparison
is apples-to-apples.

The model is loaded lazily and cached at the process level. If no trained model
is available the service reports itself as unavailable and callers simply skip
the check (it never blocks validation/saving).
"""

from __future__ import annotations

import glob
import json
import logging
import os
import sys
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_IPA_WS = "seh-fonipa"


def _expand_parenthetical(ipa: str) -> List[str]:
    """Return all expansions of ``ipa`` with parenthetical groups removed.

    Each ``(...)`` group is treated as optional, so a string with one group
    yields two variants (with and without the inner text). Groups may nest and
    repeat. Unbalanced parentheses are kept literally.
    """
    idx = ipa.find("(")
    if idx == -1:
        return [ipa]

    depth = 0
    close = -1
    for i in range(idx, len(ipa)):
        if ipa[i] == "(":
            depth += 1
        elif ipa[i] == ")":
            depth -= 1
            if depth == 0:
                close = i
                break

    # Unbalanced -> treat the '(' as a literal character.
    if close == -1:
        return [ipa]

    before = ipa[:idx]
    inside = ipa[idx + 1 : close]
    after = ipa[close + 1 :]

    variants: List[str] = []
    for expanded in (before + inside + after, before + after):
        variants.extend(_expand_parenthetical(expanded))
    return variants


def decompress_ipa_variants(ipa: str) -> List[str]:
    """Return every decompressed (parenthesis-free) variant of ``ipa``."""
    if not ipa:
        return []
    variants = sorted({v for v in _expand_parenthetical(ipa) if v != ""})
    return variants


def decompress_ipa(ipa: str) -> str:
    """Return a single canonical decompressed form (shortest variant)."""
    variants = decompress_ipa_variants(ipa)
    if not variants:
        return ipa
    # Shortest, then lexicographic, for determinism.
    return min(variants, key=lambda s: (len(s), s))


class IPAAnomalyService:
    """Process-wide singleton wrapping the trained G2P anomaly detector."""

    _instance: Optional["IPAAnomalyService"] = None
    _instance_lock = threading.Lock()

    def __init__(
        self,
        model_dir: Optional[str] = None,
        ipa_ws: str = DEFAULT_IPA_WS,
        confidence_threshold: float = 0.5,
    ) -> None:
        self.ipa_ws = ipa_ws
        self.confidence_threshold = confidence_threshold
        self._model_dir = model_dir or self._resolve_model_dir()
        self._detector: Any = None
        self._available: Optional[bool] = None
        self._load_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Configuration / model resolution
    # ------------------------------------------------------------------ #
    @staticmethod
    def _resolve_model_dir() -> Optional[str]:
        """Locate the directory holding the trained model bundle(s).

        Resolution order:
          1. ``IPA_MODEL_DIR`` env var (admin-configured, server-side only).
          2. ``instance/ipa_models`` (the canonical discoverability directory).
          3. Legacy fallbacks (single-model directory layouts).
        """
        env = os.environ.get("IPA_MODEL_DIR")
        if env:
            return env

        candidates = [
            os.path.join("instance", "ipa_models"),
            os.path.join("instance", "ipa_model"),
            os.path.join("scripts", "ipa_training", "ipa_model"),
            "ipa_model",
        ]
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
        # Default even if not yet present: discovery will simply find nothing.
        return os.path.join("instance", "ipa_models")

    @classmethod
    def get_instance(
        cls,
        model_dir: Optional[str] = None,
        ipa_ws: str = DEFAULT_IPA_WS,
        confidence_threshold: float = 0.5,
    ) -> "IPAAnomalyService":
        """Return the process-wide singleton, creating it on first use."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls(
                        model_dir=model_dir,
                        ipa_ws=ipa_ws,
                        confidence_threshold=confidence_threshold,
                    )
        return cls._instance

    def _discover_bundle(self) -> Optional[Tuple[str, str]]:
        """Find the sidecar bundle matching this service's IPA writing system.

        Scans the model directory for ``ipa_anomaly_*.pt`` files, reads each
        companion ``.json`` for its ``ipa_writing_system``, and returns the
        ``(pt_path, json_path)`` whose writing system matches ``self.ipa_ws``.
        If no exact match exists but exactly one bundle is present, it is used
        (lenient, single-model deployments).
        """
        if not self._model_dir or not os.path.isdir(self._model_dir):
            return None

        matches: List[Tuple[str, str, Optional[str]]] = []
        for pt_path in sorted(
            glob.glob(os.path.join(self._model_dir, "ipa_anomaly_*.pt"))
        ):
            json_path = pt_path[:-3] + ".json"
            if not os.path.isfile(json_path):
                continue
            try:
                with open(json_path, "r", encoding="utf-8") as fh:
                    meta = json.load(fh)
            except Exception:
                continue
            matches.append((pt_path, json_path, meta.get("ipa_writing_system")))

        if not matches:
            return None

        # Strict per-writing-system matching: never silently apply a model
        # trained for a different language/writing system.
        exact = [m for m in matches if m[2] == self.ipa_ws]
        if exact:
            return (exact[0][0], exact[0][1])
        return None

    def is_available(self) -> bool:
        """Return True only if a usable trained model is loaded."""
        if self._available is not None:
            return self._available
        with self._load_lock:
            if self._available is not None:
                return self._available
            if not self._model_dir:
                self._available = False
                return False

            # Only fall back to the legacy four-file layout when NO sidecar
            # bundles are present at all. If sidecars exist but none match the
            # requested writing system, we must not silently apply a model
            # whose language is unknown.
            any_sidecar = bool(
                glob.glob(os.path.join(self._model_dir, "ipa_anomaly_*.pt"))
            )
            bundle = self._discover_bundle() if any_sidecar else None
            legacy_ok = (not any_sidecar) and all(
                os.path.isfile(os.path.join(self._model_dir, rel))
                for rel in (
                    os.path.join("checkpoints", "best_model.pt"),
                    "model_config.json",
                    "grapheme_vocab.json",
                    "phoneme_vocab.json",
                )
            )
            if not bundle and not legacy_ok:
                self._available = False
                return False
            try:
                self._load_detector(bundle)
                self._available = True
            except Exception as exc:  # pragma: no cover - environment dependent
                logger.warning("IPA anomaly detector unavailable: %s", exc)
                self._available = False
            return self._available

    def _load_detector(self, bundle: Optional[Tuple[str, str]] = None) -> None:
        """Lazily import the G2P package and build the detector.

        Prefers the self-contained sidecar ``bundle``; falls back to the legacy
        four-file directory layout when no bundle is discovered.
        """
        import json

        g2p_root = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "scripts",
            "ipa_training",
        )
        # Prefer an explicit env path if it points somewhere real.
        env = os.environ.get("IPA_MODEL_DIR")
        if env and os.path.isdir(env):
            g2p_root_candidate = os.path.dirname(env)
            if os.path.isdir(os.path.join(g2p_root_candidate, "g2p")):
                g2p_root = g2p_root_candidate
        if g2p_root not in sys.path:
            sys.path.insert(0, g2p_root)

        from g2p import G2PModel, ModelConfig, G2PTokenizer  # noqa: E402
        from g2p.anomaly_detector import (  # noqa: E402
            create_anomaly_detector,
            create_anomaly_detector_from_bundle,
        )

        if bundle:
            self._detector = create_anomaly_detector_from_bundle(
                bundle[0],
                bundle[1],
                confidence_threshold=self.confidence_threshold,
            )
            return

        with open(
            os.path.join(self._model_dir, "model_config.json"), encoding="utf-8"
        ) as fh:
            config = ModelConfig(**json.load(fh))

        tokenizer = G2PTokenizer.load_vocab(
            os.path.join(self._model_dir, "grapheme_vocab.json"),
            os.path.join(self._model_dir, "phoneme_vocab.json"),
        )

        self._detector = create_anomaly_detector(
            os.path.join(self._model_dir, "checkpoints", "best_model.pt"),
            config,
            tokenizer,
            confidence_threshold=self.confidence_threshold,
        )

    # ------------------------------------------------------------------ #
    # Detection
    # ------------------------------------------------------------------ #
    def detect(self, headword: str, ipa: str) -> Optional[Dict[str, Any]]:
        """Run anomaly detection for a single headword/IPA pair.

        The IPA is decompressed into all of its parenthetical variants and the
        best-matching variant (highest confidence) is returned. Returns ``None``
        when the model is unavailable or inputs are empty.
        """
        if not headword or not ipa:
            return None
        if not self.is_available():
            return None

        variants = decompress_ipa_variants(ipa)
        if not variants:
            variants = [ipa]

        best: Optional[Dict[str, Any]] = None
        for variant in variants:
            try:
                result = self._detector.detect(headword, variant)
            except Exception as exc:  # pragma: no cover - model edge cases
                logger.debug("IPA anomaly detect failed for %r: %s", headword, exc)
                continue

            candidate = {
                "is_anomaly": result.is_anomaly,
                "stored_ipa": variant,
                "predicted_ipa": result.predicted_ipa,
                "confidence_score": result.confidence_score,
                "anomaly_type": result.anomaly_type,
                "per": (result.details or {}).get("per"),
            }
            if best is None or candidate["confidence_score"] > best["confidence_score"]:
                best = candidate

        return best


__all__ = [
    "IPAAnomalyService",
    "decompress_ipa",
    "decompress_ipa_variants",
]
