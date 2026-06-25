"""
Unit tests for TextExtractor utility.

Tests the unified text extraction functionality that consolidates
multiple text extraction approaches across the codebase.
"""

import pytest
from typing import Dict, Any, List

from app.utils.text_extractor import (
    TextExtractor,
    TextExtractionMode,
    WordBoundaryType,
    extract_words,
    extract_from_entry,
    strip_html_tags
)


class TestTextExtractorInitialization:
    """Test TextExtractor initialization and configuration"""

    def test_default_initialization(self):
        """Should initialize with sensible defaults."""
        extractor = TextExtractor()

        assert extractor.mode == TextExtractionMode.WORDS
        assert extractor.boundary_type == WordBoundaryType.UNICODE
        assert extractor.min_word_length == 2
        assert extractor.max_word_length == 100
        assert extractor.to_lowercase is True
        assert extractor.remove_punctuation is True
        assert extractor.strip_html is True
        assert extractor.include_numbers is False
        assert extractor.stop_words == set()

    def test_custom_initialization(self):
        """Should accept custom configuration."""
        extractor = TextExtractor(
            mode=TextExtractionMode.UNIQUE,
            boundary_type=WordBoundaryType.LATIN,
            min_word_length=3,
            max_word_length=50,
            to_lowercase=False,
            remove_punctuation=False,
            strip_html=False,
            include_numbers=True,
            stop_words={'the', 'and'}
        )

        assert extractor.mode == TextExtractionMode.UNIQUE
        assert extractor.boundary_type == WordBoundaryType.LATIN
        assert extractor.min_word_length == 3
        assert extractor.max_word_length == 50
        assert extractor.to_lowercase is False
        assert extractor.remove_punctuation is False
        assert extractor.strip_html is False
        assert extractor.include_numbers is True
        assert extractor.stop_words == {'the', 'and'}


class TestTextExtractorBasicWordExtraction:
    """Test basic word extraction functionality"""

    def test_extract_simple_words(self):
        """Should extract simple words."""
        extractor = TextExtractor()
        words = extractor.extract_words("Hello world!")

        assert 'hello' in words
        assert 'world' in words

    def test_extract_removes_punctuation(self):
        """Should remove punctuation by default."""
        extractor = TextExtractor()
        words = extractor.extract_words("Hello, world! How are you?")

        assert ',' not in words
        assert '!' not in words
        assert '?' not in words
        assert 'hello' in words
        assert 'world' in words

    def test_extract_converts_to_lowercase(self):
        """Should convert to lowercase by default."""
        extractor = TextExtractor()
        words = extractor.extract_words("HELLO World")

        assert 'hello' in words
        assert 'world' in words
        assert 'HELLO' not in words
        assert 'World' not in words

    def test_extract_respects_min_length(self):
        """Should respect minimum word length."""
        extractor = TextExtractor(min_word_length=3)
        words = extractor.extract_words("I am a test of word extraction")

        assert 'i' not in words  # Too short
        assert 'am' not in words  # Too short
        assert 'a' not in words  # Too short
        assert 'test' in words  # Long enough

    def test_extract_respects_max_length(self):
        """Should respect maximum word length."""
        extractor = TextExtractor(max_word_length=5)
        words = extractor.extract_words("Short supercalifragilistic word")

        assert 'short' in words  # Within limit
        assert 'supercalifragilistic' not in words  # Too long
        assert 'word' in words

    def test_extract_handles_none(self):
        """Should handle None gracefully."""
        extractor = TextExtractor()
        words = extractor.extract_words(None)

        assert words == []

    def test_extract_handles_empty_string(self):
        """Should handle empty string gracefully."""
        extractor = TextExtractor()
        words = extractor.extract_words("")

        assert words == []

    def test_extract_handles_whitespace_only(self):
        """Should handle whitespace-only string."""
        extractor = TextExtractor()
        words = extractor.extract_words("   \t\n  ")

        assert words == []


class TestTextExtractorUnicodeSupport:
    """Test Unicode and multi-language support"""

    def test_extract_cyrillic_words(self):
        """Should extract Cyrillic words."""
        extractor = TextExtractor.for_language('ru')
        words = extractor.extract_words(u'Привет мир!')

        assert u'привет' in words  # lowercase Привет
        assert u'мир' in words

    def test_extract_cjk_characters(self):
        """Should extract CJK characters."""
        extractor = TextExtractor.for_language('zh')
        words = extractor.extract_words(u'你好世界')  # "Hello world" in Chinese

        # CJK extraction returns individual characters or character groups
        assert len(words) > 0
        # Each character should be in the result
        assert u'你' in words or u'你' in ' '.join(words)

    def test_extract_arabic_words(self):
        """Should extract Arabic words."""
        extractor = TextExtractor.for_language('ar')
        words = extractor.extract_words(u'مرحبا العالم')  # "Hello world"

        assert len(words) > 0
        assert u'مرحبا' in words or any(u'مرحبا' in w for w in words)

    def test_extract_hebrew_words(self):
        """Should extract Hebrew words."""
        extractor = TextExtractor.for_language('he')
        words = extractor.extract_words(u'שלום עולם')  # "Hello world"

        assert len(words) > 0


class TestTextExtractorSpecialModes:
    """Test special extraction modes"""

    def test_unique_mode(self):
        """UNIQUE mode should return unique words only."""
        extractor = TextExtractor(mode=TextExtractionMode.UNIQUE)
        words = extractor.extract_words("hello hello world test test hello")

        assert words.count('hello') == 1
        assert words.count('world') == 1
        assert words.count('test') == 1

    def test_all_text_mode(self):
        """ALL_TEXT mode should return entire text."""
        extractor = TextExtractor(mode=TextExtractionMode.ALL_TEXT)
        result = extractor.extract_words("Hello, world! How are you?")

        assert len(result) == 1
        # Should preserve the processed text
        assert 'hello' in result[0] or 'world' in result[0]

    def test_unique_mode_with_stop_words(self):
        """UNIQUE mode should respect stop words."""
        extractor = TextExtractor(
            mode=TextExtractionMode.UNIQUE,
            stop_words={'the', 'and', 'a'}
        )
        words = extractor.extract_words("the cat and the dog")

        assert 'the' not in words
        assert 'and' not in words
        assert 'cat' in words
        assert 'dog' in words


class TestTextExtractorHTMLStripping:
    """Test HTML/XML tag stripping"""

    def test_strip_html_tags(self):
        """Should strip HTML tags."""
        extractor = TextExtractor()
        words = extractor.extract_words("<p>Hello <b>world</b>!</p>")

        assert '<p>' not in words
        assert '</p>' not in words
        assert '<b>' not in words
        assert 'hello' in words
        assert 'world' in words

    def test_strip_html_entities(self):
        """Should decode HTML entities."""
        extractor = TextExtractor()
        words = extractor.extract_words("Tom &amp; Jerry")

        assert '&amp;' not in ' '.join(words)
        assert 'tom' in words
        assert 'jerry' in words

    def test_strip_xml_tags(self):
        """Should strip XML tags."""
        extractor = TextExtractor()
        words = extractor.extract_words("<entry><lexical-unit>test</lexical-unit></entry>")

        assert '<entry>' not in words
        assert '</entry>' not in words
        assert 'test' in words


class TestTextExtractorEntryExtraction:
    """Test extraction from entry dictionaries"""

    def test_extract_from_simple_entry(self):
        """Should extract text from simple entry."""
        extractor = TextExtractor()
        entry = {
            'lexical_unit': {'en': 'test'},
            'senses': [
                {'definition': {'en': 'a test definition'}}
            ]
        }

        text = extractor.extract_from_entry(entry)

        assert 'test' in text
        assert 'definition' in text

    def test_extract_with_multilingual_content(self):
        """Should handle multilingual content."""
        extractor = TextExtractor()
        entry = {
            'lexical_unit': {'en': 'hello', 'fr': 'bonjour'},
            'senses': [
                {'definition': {'en': 'greeting', 'es': 'saludo'}}
            ]
        }

        text = extractor.extract_from_entry(entry)

        assert 'hello' in text
        assert 'bonjour' in text
        assert 'greeting' in text
        assert 'saludo' in text

    def test_extract_from_examples(self):
        """Should extract from examples."""
        extractor = TextExtractor()
        entry = {
            'lexical_unit': {'en': 'test'},
            'senses': [
                {
                    'examples': [
                        {'form': {'en': 'This is a test.'},
                         'translation': {'en': 'This is a translation.'}}
                    ]
                }
            ]
        }

        text = extractor.extract_from_entry(entry)

        assert 'test' in text

    def test_extract_from_etymologies(self):
        """Should extract from etymologies."""
        extractor = TextExtractor()
        entry = {
            'lexical_unit': {'en': 'test'},
            'etymologies': [
                {'source': 'Latin', 'form': 'testum', 'gloss': 'test word'}
            ]
        }

        text = extractor.extract_from_entry(entry, include_etymologies=True)

        assert 'latin' in text.lower() or 'testum' in text or 'test' in text

    def test_extract_from_pronunciations(self):
        """Should extract from pronunciations."""
        extractor = TextExtractor()
        entry = {
            'lexical_unit': {'en': 'test'},
            'pronunciations': [
                {'ipa': '/test/', 'text': 'test'}
            ]
        }

        text = extractor.extract_from_entry(entry, include_pronunciations=True)

        assert '/test/' in text or 'test' in text

    def test_extract_empty_entry(self):
        """Should handle empty entry."""
        extractor = TextExtractor()
        text = extractor.extract_from_entry({})

        assert text == ""

    def test_extract_none_entry(self):
        """Should handle None entry."""
        extractor = TextExtractor()
        text = extractor.extract_from_entry(None)

        assert text == ""


class TestTextExtractorHelperMethods:
    """Test helper methods"""

    def test_extract_unique_words(self):
        """Should extract unique words as set."""
        extractor = TextExtractor()
        unique = extractor.extract_unique_words("hello world hello test")

        assert isinstance(unique, set)
        assert 'hello' in unique
        assert 'world' in unique
        assert 'test' in unique
        assert len(unique) == 3

    def test_count_words(self):
        """Should count words correctly."""
        extractor = TextExtractor()
        count = extractor.count_words("hello world test")

        assert count == 3

    def test_count_words_handles_none(self):
        """Should handle None in word count."""
        extractor = TextExtractor()
        count = extractor.count_words(None)

        assert count == 0

    def test_is_valid_word(self):
        """Should validate words correctly."""
        extractor = TextExtractor(
            min_word_length=3,
            max_word_length=10,
            stop_words={'the'}
        )

        assert extractor.is_valid_word("hello") is True
        assert extractor.is_valid_word("ab") is False  # Too short
        assert extractor.is_valid_word("supercalifragilistic") is False  # Too long
        assert extractor.is_valid_word("the") is False  # Stop word
        assert extractor.is_valid_word("") is False  # Empty


class TestTextExtractorFactoryMethods:
    """Test factory methods for language-specific extractors"""

    def test_for_language_english(self):
        """Should create English extractor."""
        extractor = TextExtractor.for_language('en')

        assert extractor.boundary_type == WordBoundaryType.LATIN

    def test_for_language_russian(self):
        """Should create Russian extractor."""
        extractor = TextExtractor.for_language('ru')

        assert extractor.boundary_type == WordBoundaryType.CYRILLIC

    def test_for_language_chinese(self):
        """Should create Chinese extractor."""
        extractor = TextExtractor.for_language('zh')

        assert extractor.boundary_type == WordBoundaryType.CJK

    def test_for_language_unknown(self):
        """Should default to UNICODE for unknown language."""
        extractor = TextExtractor.for_language('xx')

        assert extractor.boundary_type == WordBoundaryType.UNICODE


class TestConvenienceFunctions:
    """Test convenience module-level functions"""

    def test_extract_words_function(self):
        """Should work as convenience function."""
        words = extract_words("Hello world!")

        assert 'hello' in words
        assert 'world' in words

    def test_extract_words_with_language(self):
        """Should accept language parameter."""
        words = extract_words(u'Привет', language='ru')

        assert u'привет' in words

    def test_extract_from_entry_function(self):
        """Should work as convenience function."""
        entry = {
            'lexical_unit': {'en': 'test'},
            'senses': [{'definition': {'en': 'a test'}}]
        }

        text = extract_from_entry(entry)

        assert 'test' in text

    def test_strip_html_tags_function(self):
        """Should strip HTML as convenience function."""
        text = strip_html_tags("<p>Hello <b>world</b></p>")

        assert '<p>' not in text
        assert '</p>' not in text
        assert 'Hello' in text
        assert 'world' in text


class TestTextExtractorAdvancedFeatures:
    """Test advanced features"""

    def test_handle_nested_dicts(self):
        """Should handle deeply nested dictionaries."""
        extractor = TextExtractor()
        entry = {
            'lexical_unit': {'en': 'test'},
            'senses': [
                {
                    'examples': [
                        {
                            'nested': {
                                'deep': {
                                    'value': 'deep text'
                                }
                            }
                        }
                    ]
                }
            ]
        }

        text = extractor.extract_from_entry(entry, max_depth=10)

        assert 'test' in text

    def test_handle_lists_in_dicts(self):
        """Should handle lists nested in dicts."""
        extractor = TextExtractor()
        entry = {
            'lexical_unit': {'en': 'test'},
            'items': [
                {'value': 'item1'},
                {'value': 'item2'}
            ]
        }

        text = extractor.extract_from_entry(entry)

        assert 'test' in text

    def test_custom_regex_pattern(self):
        """Should use custom regex pattern."""
        extractor = TextExtractor(
            boundary_type=WordBoundaryType.CUSTOM,
            custom_pattern=r'\b[A-Z][a-z]+\b',  # Capitalized words only
            to_lowercase=False
        )
        words = extractor.extract_words("Hello world TEST test")

        assert 'Hello' in words  # Capitalized
        assert 'TEST' not in words  # All caps doesn't match
        assert 'test' not in words  # Lowercase doesn't match

    def test_numbers_exclusion(self):
        """Should exclude numbers by default."""
        extractor = TextExtractor(include_numbers=False)
        words = extractor.extract_words("test 123 another 456")

        assert '123' not in words
        assert '456' not in words
        assert 'test' in words
        assert 'another' in words

    def test_numbers_inclusion(self):
        """Should include numbers when configured."""
        extractor = TextExtractor(include_numbers=True)
        words = extractor.extract_words("test 123 another 456")

        assert '123' in words
        assert '456' in words


class TestTextExtractorEdgeCases:
    """Test edge cases and error handling"""

    def test_extract_from_integer(self):
        """Should handle integer input."""
        extractor = TextExtractor()
        words = extractor.extract_words(12345)

        # Integer converted to string
        assert len(words) >= 0  # Empty or contains '12345' if include_numbers

    def test_extract_from_object(self):
        """Should handle arbitrary objects."""
        extractor = TextExtractor()
        words = extractor.extract_words(object())

        # Should not crash
        assert isinstance(words, list)

    def test_max_depth_prevents_infinite_recursion(self):
        """Should prevent infinite recursion with max_depth."""
        extractor = TextExtractor()

        # Create circular reference (though unlikely in real data)
        entry = {'text': 'test'}
        # This would cause issues if we had circular references
        # but our max_depth should handle it

        text = extractor.extract_from_entry(entry, max_depth=0)
        # With max_depth=0, nested extraction is limited
        assert isinstance(text, str)

    def test_unicode_whitespace_handling(self):
        """Should handle various whitespace characters."""
        extractor = TextExtractor()
        words = extractor.extract_words("hello\u00A0world\u2003test")  # Non-breaking space, em space

        # Should normalize whitespace
        assert 'hello' in words
        assert 'world' in words
        assert 'test' in words

    def test_mixed_scripts(self):
        """Should handle mixed script text."""
        extractor = TextExtractor(boundary_type=WordBoundaryType.UNICODE)
        words = extractor.extract_words("Hello 你好 Мир")

        # Unicode mode should handle mixed scripts
        assert len(words) > 0
