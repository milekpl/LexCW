"""Regression: ensure FastCorpusProcessor + models stay removed."""

from __future__ import annotations

import importlib
from pathlib import Path
import pytest


def test_removed_fast_corpus_modules_are_unimportable() -> None:
    """Importing the removed modules must raise ImportError (prevents accidental re-use)."""
    with pytest.raises(ImportError):
        importlib.import_module("app.services.fast_corpus_processor")

    with pytest.raises(ImportError):
        importlib.import_module("app.models.corpus_batch")


def test_no_production_imports_of_fast_corpus_symbols() -> None:
    """Scan production `app/` code for references to the removed symbols.

    This is a lightweight safeguard — the test fails if a production file
    still contains an import or reference to the removed API.
    """
    banned = ("fast_corpus_processor", "CorpusBatch", "ProcessingStats", "CorpusCache", "ProcessingConfig")
    app_dir = Path(__file__).resolve().parents[1] / "app"

    occurrences = []
    for p in app_dir.rglob("*.py"):
        # ignore the two stub files we intentionally left in place
        if p.name in ("fast_corpus_processor.py", "corpus_batch.py"):
            continue
        try:
            txt = p.read_text(encoding="utf8")
        except OSError:
            continue
        for token in banned:
            if token in txt:
                occurrences.append(f"{p.relative_to(app_dir.parent)}: contains '{token}'")

    assert not occurrences, "Found production references to removed fast-corpus API:\n" + "\n".join(occurrences)
