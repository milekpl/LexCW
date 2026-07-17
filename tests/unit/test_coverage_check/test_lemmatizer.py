"""
Unit tests for language-aware lemmatizer.

Tests spaCy-based lemmatization with fallback for unknown words.
"""
import pytest
from app.services.coverage_check.lemmatizer import Lemmatizer


@pytest.fixture
def en_lemmatizer():
    return Lemmatizer("en")


@pytest.fixture
def pl_lemmatizer():
    return Lemmatizer("pl")


class TestLemmatizerInit:
    def test_english(self, en_lemmatizer):
        assert en_lemmatizer.language == "en"

    def test_unknown_language_falls_back(self):
        # Unsupported language should still create (fallback mode)
        lem = Lemmatizer("xx")
        assert lem.language == "xx"


class TestEnglishLemmatization:
    def test_noun_plural(self, en_lemmatizer):
        assert en_lemmatizer.lemmatize("cats") == "cat"

    def test_verb_past(self, en_lemmatizer):
        assert en_lemmatizer.lemmatize("running") == "run"

    def test_verb_past_tense(self, en_lemmatizer):
        assert en_lemmatizer.lemmatize("went") == "go"

    def test_adjective_comparative(self, en_lemmatizer):
        assert en_lemmatizer.lemmatize("bigger") == "big"

    def test_already_lemma(self, en_lemmatizer):
        assert en_lemmatizer.lemmatize("cat") == "cat"

    def test_empty_string(self, en_lemmatizer):
        assert en_lemmatizer.lemmatize("") == ""

    def test_uppercase_input(self, en_lemmatizer):
        result = en_lemmatizer.lemmatize("Running")
        assert result == "run"

    def test_get_all_analyses_returns_list(self, en_lemmatizer):
        results = en_lemmatizer.get_all_analyses("running")
        assert isinstance(results, list)
        assert len(results) >= 1
        assert any("run" in r[0] for r in results)


class TestFallbackMode:
    def test_fallback_lowercase(self):
        lem = Lemmatizer("xx")
        result = lem.lemmatize("Running")
        assert result == "running"

    def test_fallback_empty(self):
        lem = Lemmatizer("xx")
        assert lem.lemmatize("") == ""
