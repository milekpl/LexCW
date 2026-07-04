"""
Unified Normalization Service.

Consolidates normalization functionality from across the codebase:
- IPAService.normalize_ipa() - IPA string normalization
- FieldLanguageDetector.normalize_lang_code() - Language code normalization
- LIFTParser._normalize_xml() - XML normalization
- LIFTParser._normalize_multilingual_dict() - Multilingual dict normalization
- NamespaceManager.normalize_lift_xml() - LIFT XML namespace normalization

Provides consistent, centralized normalization for:
- IPA (International Phonetic Alphabet) strings
- Language codes (ISO 639-1, 639-2, and variants)
- XML content (LIFT XML formatting)
- Multilingual dictionaries (text extraction standardization)
- Field paths and identifiers
"""

from __future__ import annotations

import re
import html
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Pattern
from enum import Enum, auto


def _xml_to_text(xml_string: str, separator: str = " ") -> str:
    """
    Extract text content from XML/HTML by stripping tags.

    Uses :func:`xml.etree.ElementTree.itertext` for well-formed input.
    Falls back to regex for malformed XML (e.g. fragments without a root
    element, stray tags in user content).

    Args:
        xml_string: XML or HTML string.
        separator: Glue inserted between adjacent text nodes (default space).

    Returns:
        Text content with tags removed, entities decoded, whitespace
        normalized, and leading/trailing whitespace stripped.
    """
    if not xml_string:
        return ""

    # Try proper XML parsing first — handles CDATA, comments, and tags
    # with special characters in attribute values correctly.
    try:
        root = ET.fromstring(
            f"<root>{xml_string}</root>"
            if not xml_string.strip().startswith("<")
            else xml_string
        )
        parts = list(root.itertext())
        if parts:
            text = separator.join(parts)
            text = html.unescape(text)
            text = re.sub(r"\s+", " ", text)
            return text.strip()
    except ET.ParseError:
        pass

    # Fallback: regex for malformed XML (fragments, partial markup, etc.)
    text = re.sub(r"<[^>]+>", separator, xml_string)
    text = html.unescape(text)
    text = re.sub(r"\s+", separator, text)
    return text.strip()


class NormalizationMode(Enum):
    """Normalization modes for different use cases."""
    STRICT = auto()      # Strict normalization (most aggressive)
    STANDARD = auto()   # Standard normalization (default)
    LENIENT = auto()    # Lenient normalization (minimal changes)
    COMPATIBILITY = auto()  # Compatibility mode (backward compatible)


class LanguageCodeFormat(Enum):
    """Language code format preferences."""
    ISO639_1 = auto()    # 2-letter codes (en, fr, de)
    ISO639_2 = auto()    # 3-letter codes (eng, fra, deu)
    BCP47 = auto()       # BCP 47 format (en-US, zh-Hans)
    DEFAULT = auto()     # Use default format


class NormalizationService:
    """
    Unified normalization service for strings, language codes, XML, and data structures.

    Consolidates normalization logic from IPAService, FieldLanguageDetector,
    LIFTParser, and NamespaceManager into a single, consistent interface.

    Features:
    - IPA string normalization (stress marks, diacritics, case)
    - Language code normalization (ISO 639 variants, BCP 47, special codes)
    - XML normalization (LIFT XML formatting, namespace handling)
    - Multilingual dictionary normalization (text extraction standardization)
    - Field path normalization (dot notation standardization)
    - Unicode normalization (NFC, NFD, NFKC, NFKD)

    Usage:
        # Normalize IPA
        normalized = NormalizationService.normalize_ipa("/hˈɛlo/")
        # "/helo/" (stress removed, normalized)

        # Normalize language code
        code = NormalizationService.normalize_language_code("en-US")
        # "en-US" (standardized BCP 47 format)

        # Normalize LIFT XML
        xml = NormalizationService.normalize_lift_xml(raw_xml)

        # Normalize multilingual dict
        dict_data = {"en": "hello", "fr": "bonjour"}
        normalized = NormalizationService.normalize_multilingual_dict(dict_data)

        # Create instance with custom settings
        service = NormalizationService(
            language_code_format=LanguageCodeFormat.BCP47,
            ipa_remove_stress=True,
            xml_strip_whitespace=True
        )
    """

    # IPA stress marks to remove during normalization
    IPA_STRESS_MARKS: Set[str] = {'ˈ', 'ˌ'}

    # IPA diacritics that may need special handling
    IPA_DIACRITICS: Set[str] = {
        'ʰ', 'ʱ', 'ʲ', 'ʳ', 'ʴ', 'ʵ', 'ʶ',  # superscript letters
        'ʷ', 'ʸ', 'ˠ', 'ˡ', 'ˢ', 'ˣ', 'ˤ',  # more superscripts
        '̀', '́', '̂', '̃', '̄', '̅', '̆',  # combining diacritics
        '̇', '̈', '̉', '̊', '̋', '̌', '̍',
        '̎', '̏', '̐', '̑', '̒', '̓', '̔',
        '̕', '̖', '̗', '̘', '̙', '̚', '̛',
        '̜', '̝', '̞', '̟', '̠', '̡', '̢',
        '̣', '̤', '̥', '̦', '̧', '̨', '̩',
        '̪', '̫', '̬', '̭', '̮', '̯', '̰',
        '̱', '̲', '̳', '̴', '̵', '̶', '̷',
        '̸', '̹', '̺', '̻', '̼', '̽', '̾',
        '̿',
    }

    # Language code mappings
    LANGUAGE_CODE_ALIASES: Dict[str, str] = {
        # Special IPA codes
        'ipa': 'seh-fonipa',
        'x-ipa': 'seh-fonipa',
        'x_ipa': 'seh-fonipa',

        # Common variants
        'iw': 'he',  # Hebrew (legacy)
        'in': 'id',  # Indonesian (legacy)
        'ji': 'yi',  # Yiddish (legacy)
        'mo': 'ro',  # Moldovan (now Romanian)
        'sh': 'sr',  # Serbo-Croatian

        # Common misspellings/variants
        'eng': 'en',
        'fra': 'fr',
        'deu': 'de',
        'spa': 'es',
        'ita': 'it',
        'por': 'pt',
        'rus': 'ru',
        'cmn': 'zh',
        'zho': 'zh',
        'ara': 'ar',
        'jpn': 'ja',
        'kor': 'ko',
        'nld': 'nl',
        'pol': 'pl',
        'tur': 'tr',
        'vie': 'vi',
        'hin': 'hi',
    }

    # Language codes with regions that should preserve case
    REGIONAL_CODES: Dict[str, List[str]] = {
        'zh': ['Hans', 'Hant', 'CN', 'TW', 'HK', 'MO', 'SG'],
        'sr': ['Latn', 'Cyrl'],
        'uz': ['Latn', 'Cyrl', 'Arab'],
        'az': ['Latn', 'Cyrl', 'Arab'],
    }

    # Compiled regex patterns
    _XML_DECLARATION_PATTERN: Pattern = re.compile(r'<\?xml[^>]*\?>')
    _XML_WHITESPACE_PATTERN: Pattern = re.compile(r'>\s+<')
    _XML_NAMESPACED_LIFT_PATTERN: Pattern = re.compile(r'^<(\w+:)?lift(\s|>)')

    def __init__(
        self,
        mode: NormalizationMode = NormalizationMode.STANDARD,
        language_code_format: LanguageCodeFormat = LanguageCodeFormat.DEFAULT,
        ipa_remove_stress: bool = True,
        ipa_remove_diacritics: bool = False,
        ipa_lowercase: bool = True,
        unicode_normalization: str = 'NFC',
        xml_strip_whitespace: bool = True,
        xml_add_namespace: bool = True,
        preserve_dialect_codes: bool = True,
        strict_language_codes: bool = False
    ):
        """
        Initialize normalization service with configuration.

        Args:
            mode: Overall normalization mode
            language_code_format: Preferred language code format
            ipa_remove_stress: Remove stress marks from IPA
            ipa_remove_diacritics: Remove diacritics from IPA
            ipa_lowercase: Convert IPA to lowercase
            unicode_normalization: Unicode normalization form (NFC, NFD, NFKC, NFKD)
            xml_strip_whitespace: Strip unnecessary whitespace from XML
            xml_add_namespace: Add LIFT namespace to XML
            preserve_dialect_codes: Preserve dialect/script subtags
            strict_language_codes: Enforce strict language code validation
        """
        self.mode = mode
        self.language_code_format = language_code_format
        self.ipa_remove_stress = ipa_remove_stress
        self.ipa_remove_diacritics = ipa_remove_diacritics
        self.ipa_lowercase = ipa_lowercase
        self.unicode_normalization = unicode_normalization
        self.xml_strip_whitespace = xml_strip_whitespace
        self.xml_add_namespace = xml_add_namespace
        self.preserve_dialect_codes = preserve_dialect_codes
        self.strict_language_codes = strict_language_codes

    # =====================================================================
    # IPA Normalization
    # =====================================================================

    def normalize_ipa(self, ipa: str, mode: Optional[NormalizationMode] = None) -> str:
        """
        Normalize an IPA string for comparison or storage.

        Consolidates normalization logic from IPAService.

        Args:
            ipa: IPA string to normalize
            mode: Optional normalization mode override

        Returns:
            Normalized IPA string
        """
        if not ipa:
            return ""

        mode = mode or self.mode
        result = ipa

        # Remove stress marks
        if self.ipa_remove_stress or mode == NormalizationMode.STRICT:
            result = self._remove_stress_marks(result)

        # Remove diacritics (strict mode only)
        if self.ipa_remove_diacritics or mode == NormalizationMode.STRICT:
            result = self._remove_ipa_diacritics(result)

        # Unicode normalization
        result = unicodedata.normalize(self.unicode_normalization, result)

        # Case normalization
        if self.ipa_lowercase:
            result = result.lower()

        # Strip whitespace
        result = result.strip()

        return result

    def strip_ipa_stress(self, ipa: str) -> str:
        """
        Remove stress marks from IPA string.

        Args:
            ipa: IPA string

        Returns:
            IPA without stress marks
        """
        return self._remove_stress_marks(ipa)

    def normalize_ipa_for_comparison(self, ipa_a: str, ipa_b: str) -> Tuple[str, str]:
        """
        Normalize two IPA strings for comparison.

        Args:
            ipa_a: First IPA string
            ipa_b: Second IPA string

        Returns:
            Tuple of (normalized_a, normalized_b)
        """
        return (
            self.normalize_ipa(ipa_a, mode=NormalizationMode.STRICT),
            self.normalize_ipa(ipa_b, mode=NormalizationMode.STRICT)
        )

    def ipa_equals(self, ipa_a: str, ipa_b: str) -> bool:
        """
        Check if two IPA strings are equivalent after normalization.

        Args:
            ipa_a: First IPA string
            ipa_b: Second IPA string

        Returns:
            True if equivalent
        """
        norm_a, norm_b = self.normalize_ipa_for_comparison(ipa_a, ipa_b)
        return norm_a == norm_b

    # =====================================================================
    # Language Code Normalization
    # =====================================================================

    def normalize_language_code(
        self,
        code: str,
        format: Optional[LanguageCodeFormat] = None
    ) -> str:
        """
        Normalize a language code to standard format.

        Consolidates logic from FieldLanguageDetector.

        Args:
            code: Input language code
            format: Target format (uses instance default if None)

        Returns:
            Normalized language code
        """
        if not code:
            return 'en'  # Default to English

        format = format or self.language_code_format
        original_code = code.strip()

        # Handle special IPA codes first
        code_lower = original_code.lower()
        if code_lower in self.LANGUAGE_CODE_ALIASES:
            # Check if it's a special alias (like 'ipa')
            if code_lower in ('ipa', 'x-ipa', 'x_ipa'):
                return self.LANGUAGE_CODE_ALIASES[code_lower]

        # Base normalization
        code = code_lower

        # Replace underscores with hyphens
        code = code.replace('_', '-')

        # Handle regional/script codes
        if '-' in code:
            parts = code.split('-')
            base = parts[0]
            subtags = parts[1:]

            # Check if base should preserve case for subtags
            if base in self.REGIONAL_CODES:
                valid_subtags = self.REGIONAL_CODES[base]
                normalized_subtags = []
                for subtag in subtags:
                    # Check for case-sensitive match
                    for valid in valid_subtags:
                        if subtag.lower() == valid.lower():
                            normalized_subtags.append(valid)
                            break
                    else:
                        # No match found, keep as-is
                        normalized_subtags.append(subtag)

                code = f"{base}-{'-'.join(normalized_subtags)}"
            else:
                # Standard BCP 47: base lowercase, region uppercase
                # Script codes (4 letters) are title case
                # Region codes (2 letters) are uppercase
                normalized_subtags = []
                for subtag in subtags:
                    if len(subtag) == 4:
                        # Script code (title case)
                        normalized_subtags.append(subtag.capitalize())
                    elif len(subtag) == 2:
                        # Region code (uppercase)
                        normalized_subtags.append(subtag.upper())
                    else:
                        # Variant or extension (lowercase)
                        normalized_subtags.append(subtag.lower())

                code = f"{base}-{'-'.join(normalized_subtags)}"

        # Handle common aliases
        if code in self.LANGUAGE_CODE_ALIASES and not self.strict_language_codes:
            code = self.LANGUAGE_CODE_ALIASES[code]

        return code

    def normalize_language_codes_in_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize all language codes in a multilingual dictionary.

        Args:
            data: Dictionary with language code keys

        Returns:
            Dictionary with normalized language codes
        """
        if not isinstance(data, dict):
            return data

        return {
            self.normalize_language_code(k): v
            for k, v in data.items()
        }

    # =====================================================================
    # XML Normalization
    # =====================================================================

    def normalize_xml(self, xml_string: str, mode: Optional[NormalizationMode] = None) -> str:
        """
        Normalize XML string (generic XML cleanup).

        Consolidates logic from LIFTParser.

        Args:
            xml_string: XML string to normalize
            mode: Optional normalization mode override

        Returns:
            Normalized XML string
        """
        if not xml_string:
            return ""

        mode = mode or self.mode
        result = xml_string

        # Remove XML declaration
        result = self._XML_DECLARATION_PATTERN.sub('', result).strip()

        # Strip extra whitespace
        if self.xml_strip_whitespace:
            result = result.strip()
            # Remove whitespace between tags
            result = self._XML_WHITESPACE_PATTERN.sub('><', result)
            # Normalize internal whitespace
            result = re.sub(r'\s+', ' ', result)

        # Decode HTML entities
        result = html.unescape(result)

        # Unicode normalization
        result = unicodedata.normalize(self.unicode_normalization, result)

        return result

    def normalize_lift_xml(
        self,
        xml_string: str,
        add_root: bool = True,
        mode: Optional[NormalizationMode] = None,
        strip_whitespace: bool = False,
        namespace: Optional[str] = None
    ) -> str:
        """
        Normalize LIFT XML string (specific to LIFT format).

        Consolidates logic from LIFTParser and NamespaceManager.

        Unlike normalize_xml(), this does NOT decode HTML entities,
        since the output is typically fed to an XML parser that handles
        entities natively.

        Args:
            xml_string: LIFT XML string
            add_root: Whether to wrap in <lift> root if missing
            mode: Optional normalization mode override
            strip_whitespace: Whether to strip unnecessary whitespace from XML
            namespace: Namespace URI for <lift> root element.
                       Defaults to "http://liftonario.org/"

        Returns:
            Normalized LIFT XML string
        """
        if not xml_string:
            return ""

        mode = mode or self.mode
        result = xml_string

        # Remove XML declaration (same pattern as normalize_xml but skip entity decoding)
        result = self._XML_DECLARATION_PATTERN.sub('', result).strip()

        # Strip whitespace if requested
        if strip_whitespace:
            result = re.sub(r'>\s+<', '><', result)

        # Wrap in <lift> root if needed
        if add_root and not self._XML_NAMESPACED_LIFT_PATTERN.match(result):
            ns_uri = namespace or "http://liftonario.org/"
            result = f'<lift xmlns="{ns_uri}" xmlns:lift="{ns_uri}">{result}</lift>'
        elif self.xml_add_namespace and 'xmlns' not in result:
            ns_uri = namespace or "http://liftonario.org/"
            if result.startswith('<'):
                # Add namespace to root element
                first_tag_end = result.find('>')
                if first_tag_end > 0:
                    result = (
                        result[:first_tag_end] +
                        f' xmlns="{ns_uri}" xmlns:lift="{ns_uri}"' +
                        result[first_tag_end:]
                    )

        return result

    def strip_xml_tags(self, xml_string: str) -> str:
        """
        Strip all XML/HTML tags, leaving only text content.

        Uses :func:`xml.etree.ElementTree.itertext` via ``_xml_to_text``
        for well-formed input, falling back to regex for malformed XML.

        Args:
            xml_string: XML string

        Returns:
            Text content without tags
        """
        return _xml_to_text(xml_string)

    # =====================================================================
    # Multilingual Dictionary Normalization
    # =====================================================================

    def normalize_multilingual_dict(
        self,
        data: Dict[str, Any],
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        Normalize multilingual dictionary structure.

        Consolidates logic from LIFTParser._normalize_multilingual_dict().
        Ensures all values are {"text": ...} dicts or recursively normalized.

        Args:
            data: Dictionary to normalize
            recursive: Whether to recursively normalize nested dicts

        Returns:
            Normalized dictionary
        """
        if not isinstance(data, dict):
            return data

        result = {}

        for key, value in data.items():
            normalized_key = self.normalize_language_code(key)

            if isinstance(value, dict):
                if recursive:
                    # Check if already in text format
                    if set(value.keys()) == {"text"} and isinstance(value["text"], str):
                        result[normalized_key] = value
                    else:
                        # Recursively normalize
                        result[normalized_key] = self.normalize_multilingual_dict(
                            value, recursive=True
                        )
                else:
                    result[normalized_key] = value
            elif isinstance(value, str):
                # Wrap string in text format
                result[normalized_key] = {"text": value}
            elif isinstance(value, (int, float)):
                # Convert to string and wrap
                result[normalized_key] = {"text": str(value)}
            else:
                # Keep other types as-is
                result[normalized_key] = value

        return result

    def flatten_multilingual_dict(
        self,
        data: Dict[str, Any],
        default_lang: str = 'en'
    ) -> str:
        """
        Flatten multilingual dictionary to a single string.

        Args:
            data: Multilingual dictionary
            default_lang: Default language to use if multiple available

        Returns:
            Single string value
        """
        if not isinstance(data, dict):
            return str(data) if data is not None else ""

        # Try default language first
        if default_lang in data:
            value = data[default_lang]
            if isinstance(value, dict) and 'text' in value:
                return value['text']
            return str(value)

        # Try English
        if 'en' in data:
            value = data['en']
            if isinstance(value, dict) and 'text' in value:
                return value['text']
            return str(value)

        # Use first available
        if data:
            key = list(data.keys())[0]
            value = data[key]
            if isinstance(value, dict) and 'text' in value:
                return value['text']
            return str(value)

        return ""

    # =====================================================================
    # Unicode Normalization
    # =====================================================================

    def normalize_unicode(self, text: str, form: Optional[str] = None) -> str:
        """
        Normalize Unicode string.

        Args:
            text: String to normalize
            form: Normalization form (NFC, NFD, NFKC, NFKD)

        Returns:
            Normalized string
        """
        if not text:
            return ""

        form = form or self.unicode_normalization
        return unicodedata.normalize(form, text)

    # =====================================================================
    # Private helper methods
    # =====================================================================

    def _remove_stress_marks(self, ipa: str) -> str:
        """Remove IPA stress marks."""
        return ''.join(c for c in ipa if c not in self.IPA_STRESS_MARKS)

    def _remove_ipa_diacritics(self, ipa: str) -> str:
        """Remove IPA diacritics."""
        return ''.join(c for c in ipa if c not in self.IPA_DIACRITICS)


# Module-level convenience functions using default instance
_default_service = NormalizationService()


def normalize_ipa(ipa: str) -> str:
    """Normalize IPA string using default settings."""
    return _default_service.normalize_ipa(ipa)


def normalize_language_code(code: str) -> str:
    """Normalize language code using default settings."""
    return _default_service.normalize_language_code(code)


def normalize_xml(xml_string: str) -> str:
    """Normalize XML string using default settings."""
    return _default_service.normalize_xml(xml_string)


def normalize_lift_xml(
    xml_string: str,
    add_root: bool = True,
    strip_whitespace: bool = False,
    namespace: Optional[str] = None
) -> str:
    """
    Normalize LIFT XML string using default settings.
    
    Args:
        xml_string: LIFT XML string to normalize
        add_root: Whether to wrap in <lift> root if missing
        strip_whitespace: Whether to strip unnecessary whitespace from XML
        namespace: Namespace URI for <lift> root element
    """
    return _default_service.normalize_lift_xml(
        xml_string, add_root=add_root, strip_whitespace=strip_whitespace, namespace=namespace
    )


def normalize_multilingual_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize multilingual dictionary using default settings."""
    return _default_service.normalize_multilingual_dict(data)


def normalize_unicode(text: str, form: str = 'NFC') -> str:
    """Normalize Unicode string."""
    return _default_service.normalize_unicode(text, form)


def strip_xml_tags(xml_string: str) -> str:
    """Strip XML tags from string."""
    return _default_service.strip_xml_tags(xml_string)
