# encoding: UTF-8
"""
ByT5-based IPA drafting service.

Loads a fine-tuned HuggingFace ByT5 model that an administrator has placed in
the server's model directory and uses it to *generate* (draft) high-quality
IPA pronunciations from a headword. This complements the lightweight anomaly
detector (``ipa_anomaly_service``): the simple model flags suspicious IPA, while
ByT5 proposes a high-quality IPA that an editor can accept.

Discovery is entirely server-side and mirrors ``IPAAnomalyService``:
  * Model directories are named ``ipa_byt5_<writing-system>`` and live in
    ``instance/ipa_models/`` (or the ``IPA_MODEL_DIR`` env override).
  * No path is ever supplied by a user/request.
  * Models are loaded with ``local_files_only=True`` and
    ``trust_remote_code=False``, so a placed model cannot execute arbitrary
    code and no network access is required at inference time.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import sys
import threading
from typing import Any, List, Optional

import torch

logger = logging.getLogger(__name__)

DEFAULT_IPA_WS = "seh-fonipa"


class IPAByT5Service:
    """Process-wide singleton wrapping the deployed ByT5 IPA drafting model."""

    _instance: Optional["IPAByT5Service"] = None
    _instance_lock = threading.Lock()

    def __init__(
        self,
        model_dir: Optional[str] = None,
        ipa_ws: str = DEFAULT_IPA_WS,
    ) -> None:
        self.ipa_ws = ipa_ws
        self._model_dir = model_dir or self._resolve_model_dir()
        self._model: Optional[Any] = None  # type: ignore[name-defined]
        self._tokenizer: Optional[Any] = None  # type: ignore[name-defined]
        self._source_prefix: str = ""
        self._device = torch.device("cpu")
        self._available: Optional[bool] = None
        self._load_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Configuration / model resolution
    # ------------------------------------------------------------------ #
    @staticmethod
    def _resolve_model_dir() -> Optional[str]:
        """Locate the directory holding trained model bundles."""
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
        return os.path.join("instance", "ipa_models")

    @classmethod
    def get_instance(
        cls,
        model_dir: Optional[str] = None,
        ipa_ws: str = DEFAULT_IPA_WS,
    ) -> "IPAByT5Service":
        """Return the process-wide singleton, creating it on first use."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls(model_dir=model_dir, ipa_ws=ipa_ws)
        return cls._instance

    def _discover_dir(self) -> Optional[str]:
        """Find the ByT5 model directory matching this service's writing system.

        Scans for ``ipa_byt5_*`` directories, reads each ``metadata.json`` for
        ``ipa_writing_system`` (falling back to the directory name), and returns
        the one whose writing system matches ``self.ipa_ws``. Strict matching:
        a model trained for a different language is never used.
        """
        if not self._model_dir or not os.path.isdir(self._model_dir):
            return None

        matches: List[Tuple[str, Optional[str]]] = []
        for d in sorted(glob.glob(os.path.join(self._model_dir, "ipa_byt5_*"))):
            if not os.path.isdir(d):
                continue
            ws: Optional[str] = None
            meta_path = os.path.join(d, "metadata.json")
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as fh:
                        meta = json.load(fh)
                    ws = meta.get("ipa_writing_system")
                    self._source_prefix = meta.get("source_prefix", "") or ""
                except Exception:
                    pass
            if not ws:
                ws = os.path.basename(d)[len("ipa_byt5_"):]
            matches.append((d, ws))

        exact = [m for m in matches if m[1] == self.ipa_ws]
        if exact:
            return exact[0][0]
        return None

    def is_available(self) -> bool:
        """Return True only if a usable ByT5 model is loaded for this ws."""
        if self._available is not None:
            return self._available
        with self._load_lock:
            if self._available is not None:
                return self._available
            d = self._discover_dir()
            if not d:
                self._available = False
                return False
            try:
                self._load_detector(d)
                self._available = True
            except Exception as exc:  # pragma: no cover - environment dependent
                logger.warning("ByT5 IPA draft model unavailable: %s", exc)
                self._available = False
            return self._available

    def _load_detector(self, model_dir: str) -> None:
        """Lazily import transformers and load the model (server-side only)."""
        import transformers  # noqa: F401

        # local_files_only: never hit the network. trust_remote_code=False:
        # never execute custom modeling code from a placed model.
        self._tokenizer = transformers.AutoTokenizer.from_pretrained(
            model_dir, local_files_only=True, trust_remote_code=False
        )
        self._model = transformers.AutoModelForSeq2SeqLM.from_pretrained(
            model_dir, local_files_only=True, trust_remote_code=False
        )
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        self._model.eval()

    # ------------------------------------------------------------------ #
    # Drafting
    # ------------------------------------------------------------------ #
    def draft_ipa(
        self,
        headword: str,
        num_return_sequences: int = 1,
        num_beams: int = 4,
        max_length: int = 128,
    ) -> List[str]:
        """Generate candidate IPA pronunciations for ``headword``.

        The headword is prefixed with the same ``source_prefix`` used during
        training. Returns a de-duplicated list of candidate IPA strings (empty
        if the model is unavailable).
        """
        if not headword:
            return []
        if not self.is_available():
            return []

        text = (self._source_prefix or "") + headword
        inputs = self._tokenizer(text, return_tensors="pt").to(self._device)  # type: ignore[union-attr]
        with torch.no_grad():
            generated = self._model.generate(  # type: ignore[union-attr]
                **inputs,
                num_beams=num_beams,
                num_return_sequences=num_return_sequences,
                max_length=max_length,
                early_stopping=True,
            )

        candidates: List[str] = []
        for seq in generated:
            ipa = self._tokenizer.decode(seq, skip_special_tokens=True).strip()  # type: ignore[union-attr]
            if ipa:
                candidates.append(ipa)

        # De-duplicate while preserving order.
        seen: set = set()
        unique: List[str] = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique


__all__ = ["IPAByT5Service"]
