"""
Text provider — converts plain text word lists to CLSF.

Tokenizes text, lemmatizes each word, and produces one entry per
unique lemma. Handles inflected forms, MWEs, and empty lines.
"""
from __future__ import annotations

import os
from typing import List

from app.services.coverage_check.models import (
    LexicalSenseFormat, Metadata, Entry, Sense,
)
from app.services.coverage_check.lemmatizer import Lemmatizer
from app.services.coverage_check.providers.base import ResourceProvider, ResourceType


class TextProvider(ResourceProvider):
    """Convert a plain-text word list to CLSF.

    Input format: one word per line, UTF-8.
    Each word is lemmatized and deduplicated.
    """

    def __init__(self, language: str = "en", target_language: str = None):
        self.language = language
        self.target_language = target_language
        self._lemmatizer = Lemmatizer(language)

    def to_clsf(self, source_path: str = None, **kwargs) -> LexicalSenseFormat:
        if not source_path or not os.path.isfile(source_path):
            raise FileNotFoundError(f"Text file not found: {source_path}")

        with open(source_path, "r", encoding="utf-8") as f:
            text = f.read()

        return self._text_to_clsf(text, source_name=os.path.basename(source_path) if source_path else "text-input")

    def _text_to_clsf(self, text: str, source_name: str = "text-input") -> LexicalSenseFormat:
        """Tokenize text, lemmatize each word, and produce CLSF entries."""
        import re
        tokens = re.findall(r"[a-zA-Z]+", text)

        seen = set()
        entries = []
        for token in tokens:
            lemma = self._lemmatizer.lemmatize(token)
            if lemma and lemma not in seen:
                seen.add(lemma)
                entries.append(
                    Entry(
                        headword=lemma,
                        language=self.language,
                        source="text",
                        senses=[Sense(definition="")],
                    )
                )

        return LexicalSenseFormat(
            metadata=Metadata(
                name=source_name,
                language=self.language,
            ),
            entries=entries,
        )

    def supported_formats(self) -> List[str]:
        return [".txt"]

    @property
    def resource_type(self) -> ResourceType:
        return ResourceType.TEXT
