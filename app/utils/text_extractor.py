"""
Unified Text Extraction Utility.

Consolidates text extraction functionality from multiple sources:
- HunspellValidator.extract_words() - Basic word extraction
- ValidationCacheService._extract_text_from_entry() - Entry text extraction  
- BaseValidator.extract_words() - Base validator extraction
- LayeredHunspellValidator field-specific extraction

Provides consistent, language-aware text extraction with support for:
- Word tokenization with configurable boundaries
- Multi-language support (Latin, Cyrillic, CJK, Arabic, etc.)
- XML/HTML tag stripping
- Special character handling
- Entry structure navigation
"""

from __future__ import annotations

import re
import html
from typing import Any, Dict, List, Optional, Set, Callable, Union
from enum import Enum, auto


class TextExtractionMode(Enum):
    """Modes for text extraction."""
    WORDS = auto()        # Extract individual words
    PHRASES = auto()      # Extract phrases/sentences
    ALL_TEXT = auto()     # Extract all text as single string
    UNIQUE = auto()       # Extract unique words only


class WordBoundaryType(Enum):
    """Types of word boundaries for different languages."""
    UNICODE = auto()      # Unicode word boundaries (default)
    LATIN = auto()         # Latin script [a-zA-Z]
    CYRILLIC = auto()      # Cyrillic script
    CJK = auto()           # Chinese/Japanese/Korean
    ARABIC = auto()        # Arabic script
    HEBREW = auto()        # Hebrew script
    DEVANAGARI = auto()    # Devanagari script (Hindi, etc.)
    THAI = auto()          # Thai script
    CUSTOM = auto()        # Custom regex pattern


class TextExtractor:
    """
    Unified text extraction utility.

    Consolidates text extraction from multiple validators and services
    into a single, consistent interface with language-aware tokenization.

    Usage:
        # Basic word extraction
        extractor = TextExtractor()
        words = extractor.extract_words("Hello world!")
        # ['hello', 'world']

        # From entry data
        entry = {'lexical_unit': {'en': 'test'}, 'senses': [...]}
        text = extractor.extract_from_entry(entry)
        # 'test ...'

        # Language-aware extraction
        extractor = TextExtractor.for_language('ru')  # Russian
        words = extractor.extract_words(u'Привет мир')
        # ['привет', 'мир']

        # XML text extraction
        xml_text = extractor.extract_from_xml('<entry><text>Hello</text></entry>')
        # 'Hello'
    """

    # Regex patterns for different scripts
    PATTERNS: Dict[WordBoundaryType, str] = {
        WordBoundaryType.LATIN: r"[a-zA-Z]+",
        WordBoundaryType.CYRILLIC: r"[\u0400-\u04FF\u0500-\u052F]+",
        WordBoundaryType.CJK: r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]+",
        WordBoundaryType.ARABIC: r"[\u0600-\u06FF\u0750-\u077F]+",
        WordBoundaryType.HEBREW: r"[\u0590-\u05FF]+",
        WordBoundaryType.DEVANAGARI: r"[\u0900-\u097F]+",
        WordBoundaryType.THAI: r"[\u0E00-\u0E7F]+",
        WordBoundaryType.UNICODE: r"\b\w+\b",  # Unicode word characters
    }

    # Default fields to extract from entries
    DEFAULT_ENTRY_FIELDS: List[str] = [
        'lexical_unit',
        'citation',
        'citation_forms',
        'note',
        'notes',
        'pronunciations',
        'etymologies',
        'relations',
        'variants',
        'main_entry',
    ]

    # Sense-level fields (comprehensive for spell-checking)
    DEFAULT_SENSE_FIELDS: List[str] = [
        'definition',
        'gloss',
        'note',
        'scientific_name',
        'usage_notes',
        'anthropology_notes',
        'sociolinguistics_notes',
        'literal_meaning',
        'exemplar',
        'subsenses',  # Nested senses for hierarchical structure
    ]
    
    # Fields to extract from relation dicts
    RELATION_TEXT_FIELDS: List[str] = ['ref', 'display', 'type']
    
    # Fields to extract from variant dicts  
    VARIANT_TEXT_FIELDS: List[str] = ['form', 'comment']

    # Example-level fields
    DEFAULT_EXAMPLE_FIELDS: List[str] = [
        'form',
        'translation',
        'notes',
    ]

    def __init__(
        self,
        mode: TextExtractionMode = TextExtractionMode.WORDS,
        boundary_type: WordBoundaryType = WordBoundaryType.UNICODE,
        min_word_length: int = 2,
        max_word_length: int = 100,
        to_lowercase: bool = True,
        remove_punctuation: bool = True,
        strip_html: bool = True,
        custom_pattern: Optional[str] = None,
        include_numbers: bool = False,
        stop_words: Optional[Set[str]] = None
    ):
        """
        Initialize text extractor.

        Args:
            mode: Extraction mode (words, phrases, all_text, unique)
            boundary_type: Type of word boundaries to use
            min_word_length: Minimum word length to include
            max_word_length: Maximum word length to include
            to_lowercase: Convert words to lowercase
            remove_punctuation: Remove punctuation characters
            strip_html: Remove HTML/XML tags
            custom_pattern: Custom regex pattern (for CUSTOM boundary_type)
            include_numbers: Include numeric tokens
            stop_words: Set of words to exclude
        """
        self.mode = mode
        self.boundary_type = boundary_type
        self.min_word_length = min_word_length
        self.max_word_length = max_word_length
        self.to_lowercase = to_lowercase
        self.remove_punctuation = remove_punctuation
        self.strip_html = strip_html
        self.custom_pattern = custom_pattern
        self.include_numbers = include_numbers
        self.stop_words = stop_words or set()

        # Compile pattern
        self._pattern = self._compile_pattern()

    @classmethod
    def for_language(cls, language_code: str, **kwargs) -> TextExtractor:
        """
        Create extractor configured for a specific language.

        Args:
            language_code: ISO 639-1 or 639-2 language code
            **kwargs: Additional configuration options

        Returns:
            Configured TextExtractor instance
        """
        # Map language codes to boundary types
        lang_to_boundary: Dict[str, WordBoundaryType] = {
            # Latin script languages
            'en': WordBoundaryType.LATIN,
            'de': WordBoundaryType.LATIN,
            'fr': WordBoundaryType.LATIN,
            'es': WordBoundaryType.LATIN,
            'it': WordBoundaryType.LATIN,
            'pt': WordBoundaryType.LATIN,
            'nl': WordBoundaryType.LATIN,
            'pl': WordBoundaryType.LATIN,

            # Cyrillic script
            'ru': WordBoundaryType.CYRILLIC,
            'uk': WordBoundaryType.CYRILLIC,
            'bg': WordBoundaryType.CYRILLIC,
            'sr': WordBoundaryType.CYRILLIC,

            # CJK
            'zh': WordBoundaryType.CJK,
            'ja': WordBoundaryType.CJK,
            'ko': WordBoundaryType.CJK,

            # Arabic
            'ar': WordBoundaryType.ARABIC,
            'fa': WordBoundaryType.ARABIC,

            # Hebrew
            'he': WordBoundaryType.HEBREW,
            'iw': WordBoundaryType.HEBREW,  # legacy code

            # Devanagari (Hindi, etc.)
            'hi': WordBoundaryType.DEVANAGARI,
            'mr': WordBoundaryType.DEVANAGARI,
            'ne': WordBoundaryType.DEVANAGARI,

            # Thai
            'th': WordBoundaryType.THAI,
        }

        boundary_type = lang_to_boundary.get(language_code, WordBoundaryType.UNICODE)
        return cls(boundary_type=boundary_type, **kwargs)

    def extract_words(self, text: Union[str, Any]) -> List[str]:
        """
        Extract words from text.

        Args:
            text: Text to extract from (string or any object convertible to string)

        Returns:
            List of extracted words
        """
        if text is None:
            return []

        text_str = str(text)

        if not text_str.strip():
            return []

        # Preprocess
        text_str = self._preprocess(text_str)

        # Extract tokens
        if self.mode == TextExtractionMode.ALL_TEXT:
            return [text_str] if text_str.strip() else []

        tokens = self._extract_tokens(text_str)

        # Postprocess
        words = self._postprocess(tokens)

        # Remove duplicates if in UNIQUE mode
        if self.mode == TextExtractionMode.UNIQUE:
            seen: Set[str] = set()
            unique_words = []
            for word in words:
                if word not in seen and word not in self.stop_words:
                    seen.add(word)
                    unique_words.append(word)
            return unique_words

        return words

    def extract_from_entry(
        self,
        entry: Dict[str, Any],
        fields: Optional[List[str]] = None,
        include_senses: bool = True,
        include_examples: bool = True,
        include_etymologies: bool = False,
        include_relations: bool = False,
        include_pronunciations: bool = False,
        max_depth: int = 5
    ) -> str:
        """
        Extract all text from an entry dictionary.

        Consolidates text extraction from ValidationCacheService.

        Args:
            entry: Entry data dictionary
            fields: Specific fields to extract (uses defaults if None)
            include_senses: Include sense-level text
            include_examples: Include example-level text
            include_etymologies: Include etymology text
            include_relations: Include relation text
            include_pronunciations: Include pronunciation text
            max_depth: Maximum recursion depth for nested structures

        Returns:
            Concatenated text from all fields
        """
        if not entry or not isinstance(entry, dict):
            return ""

        text_parts: List[str] = []

        # Use specified fields or defaults
        fields_to_extract = fields or self.DEFAULT_ENTRY_FIELDS

        for field in fields_to_extract:
            value = entry.get(field)
            if value is None:
                continue

            extracted = self._extract_value_text(value, depth=0, max_depth=max_depth)
            if extracted:
                text_parts.append(extracted)

        # Extract from senses
        if include_senses:
            for sense in entry.get('senses', []):
                if isinstance(sense, dict):
                    for field in self.DEFAULT_SENSE_FIELDS:
                        value = sense.get(field)
                        if value:
                            extracted = self._extract_value_text(value, depth=0, max_depth=max_depth)
                            if extracted:
                                text_parts.append(extracted)

                    # Extract from examples
                    if include_examples:
                        for example in sense.get('examples', []):
                            if isinstance(example, dict):
                                for field in self.DEFAULT_EXAMPLE_FIELDS:
                                    value = example.get(field)
                                    if value:
                                        extracted = self._extract_value_text(value, depth=0, max_depth=max_depth)
                                        if extracted:
                                            text_parts.append(extracted)
                    
                    # Extract from sense-level relations
                    if include_relations:
                        for relation in sense.get('relations', []):
                            if isinstance(relation, dict):
                                for key in self.RELATION_TEXT_FIELDS:
                                    value = relation.get(key)
                                    if value:
                                        text_parts.append(str(value))

        # Extract from etymologies
        if include_etymologies:
            for etymology in entry.get('etymologies', []):
                if isinstance(etymology, dict):
                    for key in ['source', 'form', 'gloss', 'note']:
                        value = etymology.get(key)
                        if value:
                            extracted = self._extract_value_text(value, depth=0, max_depth=max_depth)
                            if extracted:
                                text_parts.append(extracted)

        # Extract from relations
        if include_relations:
            for relation in entry.get('relations', []):
                if isinstance(relation, dict):
                    for key in ['ref', 'note']:
                        value = relation.get(key)
                        if value:
                            extracted = self._extract_value_text(value, depth=0, max_depth=max_depth)
                            if extracted:
                                text_parts.append(extracted)

        # Extract from pronunciations
        if include_pronunciations:
            for pronunciation in entry.get('pronunciations', []):
                if isinstance(pronunciation, dict):
                    value = pronunciation.get('ipa') or pronunciation.get('text')
                    if value:
                        text_parts.append(str(value))

        return ' '.join(text_parts)

    def extract_from_xml(self, xml_string: str) -> str:
        """
        Extract text from XML string (strips tags).

        Args:
            xml_string: XML/HTML string

        Returns:
            Text content without tags
        """
        if not xml_string:
            return ""

        # Remove XML/HTML tags
        text = re.sub(r'<[^>]+>', ' ', xml_string)

        # Decode HTML entities
        text = html.unescape(text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def extract_unique_words(self, text: Union[str, Any]) -> Set[str]:
        """
        Extract unique words from text.

        Args:
            text: Text to extract from

        Returns:
            Set of unique words
        """
        return set(self.extract_words(text))

    def count_words(self, text: Union[str, Any]) -> int:
        """
        Count words in text.

        Args:
            text: Text to count words in

        Returns:
            Word count
        """
        return len(self.extract_words(text))

    def is_valid_word(self, word: str) -> bool:
        """
        Check if a word meets extraction criteria.

        Args:
            word: Word to check

        Returns:
            True if word is valid according to current settings
        """
        if not word:
            return False

        if len(word) < self.min_word_length:
            return False

        if len(word) > self.max_word_length:
            return False

        if word in self.stop_words:
            return False

        if not self.include_numbers and word.isdigit():
            return False

        return True

    def _compile_pattern(self) -> re.Pattern:
        """Compile the word extraction pattern."""
        if self.boundary_type == WordBoundaryType.CUSTOM and self.custom_pattern:
            pattern = self.custom_pattern
        else:
            pattern = self.PATTERNS.get(
                self.boundary_type,
                self.PATTERNS[WordBoundaryType.UNICODE]
            )

        return re.compile(pattern, re.UNICODE)

    def _preprocess(self, text: str) -> str:
        """Preprocess text before extraction."""
        if self.strip_html:
            text = self.extract_from_xml(text)

        if self.remove_punctuation:
            # Keep word characters and whitespace
            text = re.sub(r'[^\w\s]', ' ', text, flags=re.UNICODE)

        return text

    def _extract_tokens(self, text: str) -> List[str]:
        """Extract raw tokens from text."""
        return self._pattern.findall(text)

    def _postprocess(self, tokens: List[str]) -> List[str]:
        """Postprocess extracted tokens."""
        words = []

        for token in tokens:
            # Clean whitespace
            token = token.strip()

            # Apply length filters
            if len(token) < self.min_word_length:
                continue

            if len(token) > self.max_word_length:
                continue

            # Case normalization
            if self.to_lowercase:
                token = token.lower()

            # Skip stop words
            if token in self.stop_words:
                continue

            # Skip pure numbers if not allowed
            if not self.include_numbers and token.isdigit():
                continue

            words.append(token)

        return words

    def _extract_value_text(
        self,
        value: Any,
        depth: int = 0,
        max_depth: int = 5
    ) -> str:
        """Recursively extract text from a value."""
        if depth > max_depth:
            return ""

        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            # Handle multilingual dicts like {'en': 'text', 'fr': 'texte'}
            parts = []
            for v in value.values():
                if isinstance(v, str):
                    parts.append(v)
                elif isinstance(v, (list, dict)):
                    nested = self._extract_value_text(v, depth + 1, max_depth)
                    if nested:
                        parts.append(nested)
            return ' '.join(parts)

        if isinstance(value, list):
            parts = []
            for item in value:
                extracted = self._extract_value_text(item, depth + 1, max_depth)
                if extracted:
                    parts.append(extracted)
            return ' '.join(parts)

        return str(value)


# Convenience functions for common use cases

def extract_words(text: str, language: Optional[str] = None, **kwargs) -> List[str]:
    """
    Convenience function to extract words from text.

    Args:
        text: Text to extract from
        language: Optional language code for language-aware extraction
        **kwargs: Additional TextExtractor options

    Returns:
        List of words
    """
    if language:
        extractor = TextExtractor.for_language(language, **kwargs)
    else:
        extractor = TextExtractor(**kwargs)

    return extractor.extract_words(text)


def extract_from_entry(entry: Dict[str, Any], **kwargs) -> str:
    """
    Convenience function to extract text from entry.

    Args:
        entry: Entry dictionary
        **kwargs: Additional options for extract_from_entry

    Returns:
        Concatenated text
    """
    extractor = TextExtractor()
    return extractor.extract_from_entry(entry, **kwargs)


def strip_html_tags(html_text: str) -> str:
    """
    Strip HTML/XML tags from text.

    Args:
        html_text: HTML/XML string

    Returns:
        Text without tags
    """
    extractor = TextExtractor()
    return extractor.extract_from_xml(html_text)
