"""
Unit tests for resource providers.

Tests the ResourceProvider ABC, TextProvider, and SubtlexProvider.
"""
import os
import tempfile
import pytest
from app.services.coverage_check.providers.base import ResourceProvider, ResourceType
from app.services.coverage_check.providers.text_provider import TextProvider
from app.services.coverage_check.providers.subtlex_provider import SubtlexProvider
from app.services.coverage_check.providers.wordnet_provider import WordNetProvider


class TestResourceProviderABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            ResourceProvider()

    def test_resource_type_enum(self):
        assert ResourceType.DICTIONARY.value == "dictionary"
        assert ResourceType.FREQUENCY_LIST.value == "frequency_list"
        assert ResourceType.TEXT.value == "text"


class TestTextProvider:
    def test_single_word_per_line(self, tmp_path):
        words = "cat\ndog\nbird\n"
        f = tmp_path / "words.txt"
        f.write_text(words, encoding="utf-8")

        provider = TextProvider(language="en")
        lsf = provider.to_clsf(str(f))
        assert len(lsf.entries) == 3
        headwords = {e.headword for e in lsf.entries}
        assert headwords == {"cat", "dog", "bird"}

    def test_lemmatizes_inflected_forms(self, tmp_path):
        words = "cats\nrunning\nbigger\n"
        f = tmp_path / "words.txt"
        f.write_text(words, encoding="utf-8")

        provider = TextProvider(language="en")
        lsf = provider.to_clsf(str(f))
        headwords = {e.headword for e in lsf.entries}
        assert "cat" in headwords
        assert "run" in headwords
        assert "big" in headwords

    def test_empty_lines_skipped(self, tmp_path):
        words = "\n\ncat\n\n\ndog\n\n"
        f = tmp_path / "words.txt"
        f.write_text(words, encoding="utf-8")

        provider = TextProvider(language="en")
        lsf = provider.to_clsf(str(f))
        assert len(lsf.entries) == 2

    def test_supported_formats(self):
        p = TextProvider(language="en")
        assert ".txt" in p.supported_formats()

    def test_resource_type(self):
        p = TextProvider(language="en")
        assert p.resource_type == ResourceType.TEXT

    def test_metadata(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello\n", encoding="utf-8")
        provider = TextProvider(language="en")
        lsf = provider.to_clsf(str(f))
        assert lsf.metadata.language == "en"
        assert "text" in lsf.metadata.name.lower() or "test" in lsf.metadata.name.lower()

    def test_target_language(self, tmp_path):
        words = "cat\n"
        f = tmp_path / "words.txt"
        f.write_text(words, encoding="utf-8")
        provider = TextProvider(language="en", target_language="pl")
        lsf = provider.to_clsf(str(f))
        assert lsf.metadata.language == "en"


class TestSubtlexProvider:
    def test_tab_separated(self, tmp_path):
        content = "word\tLgCount\tCd\nthe\t50000\t1.0\ncat\t5000\t0.8\ndog\t3000\t0.5\n"
        f = tmp_path / "subtlex.txt"
        f.write_text(content, encoding="utf-8")

        provider = SubtlexProvider(language="en")
        lsf = provider.to_clsf(str(f))
        assert len(lsf.entries) == 3
        # Entries should be sorted by frequency (the has highest count)
        assert lsf.entries[0].headword == "the"

    def test_frequency_in_senses(self, tmp_path):
        content = "word\tLgCount\tCd\nbank\t2000\t1.5\n"
        f = tmp_path / "subtlex.txt"
        f.write_text(content, encoding="utf-8")

        provider = SubtlexProvider(language="en")
        lsf = provider.to_clsf(str(f))
        assert len(lsf.entries) == 1
        entry = lsf.entries[0]
        assert entry.headword == "bank"
        assert len(entry.senses) == 1
        # Frequency stored in semantic_domain field
        assert entry.senses[0].semantic_domain == "frequency"

    def test_supported_formats(self):
        p = SubtlexProvider(language="en")
        assert ".txt" in p.supported_formats()

    def test_resource_type(self):
        p = SubtlexProvider(language="en")
        assert p.resource_type == ResourceType.FREQUENCY_LIST

    def test_skip_header_row(self, tmp_path):
        content = "word\tLgCount\tCd\nthe\t50000\t1.0\n"
        f = tmp_path / "subtlex.txt"
        f.write_text(content, encoding="utf-8")
        provider = SubtlexProvider(language="en")
        lsf = provider.to_clsf(str(f))
        assert len(lsf.entries) == 1

    def test_comma_separated(self, tmp_path):
        content = "word,LgCount,Cd\nthe,50000,1.0\ncat,5000,0.8\n"
        f = tmp_path / "subtlex.csv"
        f.write_text(content, encoding="utf-8")
        provider = SubtlexProvider(language="en")
        lsf = provider.to_clsf(str(f))
        assert len(lsf.entries) == 2


class TestWordNetProvider:
    def test_basic_entry(self):
        provider = WordNetProvider(language="en")
        lsf = provider.to_clsf()  # No file needed for WordNet

        # WordNet has thousands of entries
        assert len(lsf.entries) > 10000
        assert lsf.metadata.language == "en"

    def test_entry_has_senses(self):
        provider = WordNetProvider(language="en")
        lsf = provider.to_clsf()
        # Find "bank" - should have multiple senses
        bank_entries = [e for e in lsf.entries if e.headword == "bank"]
        assert len(bank_entries) >= 1
        # Each POS grouping of bank should have senses
        for entry in bank_entries:
            assert len(entry.senses) >= 1

    def test_sense_has_synset_id(self):
        provider = WordNetProvider(language="en")
        lsf = provider.to_clsf()
        for entry in lsf.entries[:50]:
            for sense in entry.senses:
                assert sense.synset_id is not None
                assert sense.synset_id.startswith("wn:")

    def test_translations_from_omw(self):
        provider = WordNetProvider(language="en", target_language="pl")
        lsf = provider.to_clsf()
        # Some entries should have Polish translations via OMW
        entries_with_trans = [e for e in lsf.entries if any(s.translations for s in e.senses)]
        assert len(entries_with_trans) > 0

    def test_supported_formats(self):
        p = WordNetProvider(language="en")
        assert p.supported_formats() == []  # WordNet doesn't need input files

    def test_resource_type(self):
        p = WordNetProvider(language="en")
        assert p.resource_type == ResourceType.DICTIONARY

    def test_get_word_entry(self):
        provider = WordNetProvider(language="en")
        entry = provider.get_word_entry("bank")
        assert entry is not None
        assert entry.headword == "bank"
        assert len(entry.senses) > 0

    def test_get_word_synset_count(self):
        provider = WordNetProvider(language="en")
        count = provider.get_synset_count("bank")
        assert count >= 5  # bank has many senses in WordNet

    def test_get_synsets_for_language(self):
        provider = WordNetProvider(language="en")
        synsets = provider.get_synsets_for_language("bank", target_language="pl")
        # May or may not have Polish translations depending on OMW
        assert isinstance(synsets, list)
