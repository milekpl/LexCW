"""
Language-aware lemmatizer using spaCy.

Supports any language with a spaCy model installed.
Falls back to simple lowercase normalization for unsupported languages.
"""
from __future__ import annotations

import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# Language → spaCy model name mapping
_SPACY_MODELS = {
    "en": "en_core_web_sm",
    "pl": "pl_core_news_lg",
    "de": "de_core_news_sm",
    "fr": "fr_core_news_sm",
    "es": "es_core_news_sm",
    "it": "it_core_news_sm",
    "pt": "pt_core_news_sm",
    "nl": "nl_core_news_sm",
    "ru": "ru_core_news_sm",
    "ja": "ja_core_news_sm",
    "zh": "zh_core_web_sm",
}


class Lemmatizer:
    """Language-aware lemmatizer using spaCy with fallback."""

    def __init__(self, language: str = "en"):
        self.language = language
        self._nlp = None
        self._fallback = False
        self._init_model()

    def _init_model(self) -> None:
        model_name = _SPACY_MODELS.get(self.language)
        if not model_name:
            logger.info(
                "No spaCy model mapped for language '%s'; using fallback lemmatizer",
                self.language,
            )
            self._fallback = True
            return
        try:
            import spacy
            self._nlp = spacy.load(model_name, disable=["parser", "ner"])
            logger.info("Loaded spaCy model %s for language '%s'", model_name, self.language)
        except OSError:
            logger.warning(
                "spaCy model %s not found for language '%s'; using fallback. "
                "Install with: python -m spacy download %s",
                model_name,
                self.language,
                model_name,
            )
            self._fallback = True

    def lemmatize(self, word: str) -> str:
        """Lemmatize a single word.

        Returns the lemma (lowercase). For unknown words, returns lowercase input.
        """
        if not word or not word.strip():
            return word or ""

        word = word.strip()

        if self._fallback or self._nlp is None:
            return word.lower()

        doc = self._nlp(word)
        if doc and doc[0].lemma_:
            return doc[0].lemma_.lower()
        return word.lower()

    def get_all_analyses(self, word: str) -> List[Tuple[str, str]]:
        """Get all possible (lemma, POS) analyses for a word.

        Returns list of (lemma, pos_tag) tuples. For spaCy, this is a single
        analysis. For fallback, returns the input as-is.
        """
        if not word or not word.strip():
            return []

        word = word.strip()

        if self._fallback or self._nlp is None:
            return [(word.lower(), "")]

        doc = self._nlp(word)
        if doc:
            token = doc[0]
            return [(token.lemma_.lower(), token.pos_)]
        return [(word.lower(), "")]
