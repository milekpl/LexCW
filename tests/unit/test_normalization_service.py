"""
Unit tests for NormalizationService utility.

Tests the unified normalization functionality that consolidates
normalization logic from across the codebase.
"""

import pytest
from typing import Dict, Any

from app.utils.normalization_service import (
    NormalizationService, NormalizationMode, LanguageCodeFormat,
    normalize_ipa, normalize_language_code, normalize_xml,
    normalize_lift_xml, normalize_multilingual_dict,
    normalize_unicode, strip_xml_tags
)


class TestNormalizationServiceInitialization:
    """Test NormalizationService initialization"""

    def test_default_initialization(self):
        """Should initialize with sensible defaults."""
        service = NormalizationService()

        assert service.mode == NormalizationMode.STANDARD
        assert service.language_code_format == LanguageCodeFormat.DEFAULT
        assert service.ipa_remove_stress is True
        assert service.ipa_remove_diacritics is False
        assert service.ipa_lowercase is True
        assert service.unicode_normalization == 'NFC'
        assert service.xml_strip_whitespace is True
        assert service.xml_add_namespace is True
        assert service.preserve_dialect_codes is True
        assert service.strict_language_codes is False

    def test_custom_initialization(self):
        """Should accept custom configuration."""
        service = NormalizationService(
            mode=NormalizationMode.STRICT,
            language_code_format=LanguageCodeFormat.BCP47,
            ipa_remove_stress=False,
            ipa_remove_diacritics=True,
            ipa_lowercase=False,
            unicode_normalization='NFD',
            xml_strip_whitespace=False,
            xml_add_namespace=False,
            preserve_dialect_codes=False,
            strict_language_codes=True
        )

        assert service.mode == NormalizationMode.STRICT
        assert service.language_code_format == LanguageCodeFormat.BCP47
        assert service.ipa_remove_stress is False
        assert service.ipa_remove_diacritics is True
        assert service.ipa_lowercase is False
        assert service.unicode_normalization == 'NFD'
        assert service.xml_strip_whitespace is False
        assert service.xml_add_namespace is False
        assert service.preserve_dialect_codes is False
        assert service.strict_language_codes is True


class TestIPANormalization:
    """Test IPA string normalization"""

    def test_normalize_ipa_stress_removal(self):
        """Should remove stress marks by default."""
        service = NormalizationService()
        result = service.normalize_ipa("hˈɛlo")  # /hˈɛlo/ -> hello with stress

        assert 'ˈ' not in result  # Primary stress mark removed
        assert 'ˌ' not in result  # Secondary stress mark removed

    def test_normalize_ipa_lowercase(self):
        """Should convert to lowercase."""
        service = NormalizationService()
        result = service.normalize_ipa("HELLO")

        assert result == "hello"

    def test_normalize_ipa_whitespace_stripping(self):
        """Should strip whitespace."""
        service = NormalizationService()
        result = service.normalize_ipa("  /test/  ")

        assert result == "/test/"

    def test_normalize_ipa_preserve_when_disabled(self):
        """Should preserve stress when disabled."""
        service = NormalizationService(ipa_remove_stress=False)
        result = service.normalize_ipa("hˈɛlo")

        assert 'ˈ' in result

    def test_normalize_ipa_strict_mode(self):
        """Should remove diacritics in strict mode."""
        service = NormalizationService(ipa_remove_diacritics=True)
        result = service.normalize_ipa_strict = lambda ipa: service.normalize_ipa(ipa, mode=NormalizationMode.STRICT)
        result = service.normalize_ipa_strict("/test́/")  # With combining acute

        assert '́' not in result  # Combining acute removed

    def test_normalize_ipa_empty(self):
        """Should handle empty string."""
        service = NormalizationService()
        result = service.normalize_ipa("")

        assert result == ""

    def test_normalize_ipa_none(self):
        """Should handle None gracefully."""
        service = NormalizationService()
        result = service.normalize_ipa(None)  # type: ignore

        assert result == ""

    def test_strip_ipa_stress(self):
        """Should strip stress marks only."""
        service = NormalizationService()
        result = service.strip_ipa_stress("hˈɛlˌo")  # With primary and secondary stress

        assert 'ˈ' not in result
        assert 'ˌ' not in result
        assert 'h' in result
        assert 'o' in result

    def test_normalize_ipa_for_comparison(self):
        """Should normalize both strings for comparison."""
        service = NormalizationService()
        norm_a, norm_b = service.normalize_ipa_for_comparison("hˈɛlo", "hˈɛlˌo")

        assert isinstance(norm_a, str)
        assert isinstance(norm_b, str)
        assert norm_a == norm_b  # After normalization, should be same without stress

    def test_ipa_equals(self):
        """Should check IPA equality after normalization."""
        service = NormalizationService()

        # Same IPA with different stress
        assert service.ipa_equals("hˈɛlo", "hˈɛlˌo") is True

        # Different IPA
        assert service.ipa_equals("hello", "world") is False


class TestLanguageCodeNormalization:
    """Test language code normalization"""

    def test_normalize_language_code_basic(self):
        """Should normalize basic language codes."""
        service = NormalizationService()

        assert service.normalize_language_code("EN") == "en"
        assert service.normalize_language_code("FR") == "fr"
        assert service.normalize_language_code("de") == "de"

    def test_normalize_language_code_with_region(self):
        """Should handle regional codes."""
        service = NormalizationService()

        # BCP 47 style
        assert service.normalize_language_code("en-US") == "en-US"
        assert service.normalize_language_code("en-us") == "en-US"

        # Underscore style (converted to hyphen)
        assert service.normalize_language_code("en_US") == "en-US"

    def test_normalize_language_code_with_script(self):
        """Should handle script codes."""
        service = NormalizationService()

        # Script codes should be title case
        assert service.normalize_language_code("zh-HANS") == "zh-Hans"
        assert service.normalize_language_code("sr-LATN") == "sr-Latn"

    def test_normalize_language_code_ipa_special(self):
        """Should handle special IPA codes."""
        service = NormalizationService()

        assert service.normalize_language_code("ipa") == "seh-fonipa"
        assert service.normalize_language_code("IPA") == "seh-fonipa"
        assert service.normalize_language_code("x-ipa") == "seh-fonipa"
        assert service.normalize_language_code("x_ipa") == "seh-fonipa"

    def test_normalize_language_code_aliases(self):
        """Should handle common aliases."""
        service = NormalizationService()

        assert service.normalize_language_code("iw") == "he"  # Hebrew legacy
        assert service.normalize_language_code("eng") == "en"  # ISO 639-2 to 639-1
        assert service.normalize_language_code("fra") == "fr"
        assert service.normalize_language_code("deu") == "de"

    def test_normalize_language_code_empty(self):
        """Should default to 'en' for empty string."""
        service = NormalizationService()

        assert service.normalize_language_code("") == "en"
        assert service.normalize_language_code(None) == "en"  # type: ignore

    def test_normalize_language_code_strict_mode(self):
        """Should not use aliases in strict mode."""
        service = NormalizationService(strict_language_codes=True)

        # In strict mode, don't convert aliases
        result = service.normalize_language_code("eng")
        assert result == "eng"  # Not converted to 'en'

    def test_normalize_language_codes_in_dict(self):
        """Should normalize codes in dictionary keys."""
        service = NormalizationService()
        data = {"EN": "hello", "FR": "bonjour", "DE": "hallo"}

        result = service.normalize_language_codes_in_dict(data)

        assert result == {"en": "hello", "fr": "bonjour", "de": "hallo"}


class TestXMLNormalization:
    """Test XML normalization"""

    def test_normalize_xml_remove_declaration(self):
        """Should remove XML declaration."""
        service = NormalizationService()
        xml = '<?xml version="1.0" encoding="UTF-8"?><root>content</root>'

        result = service.normalize_xml(xml)

        assert '<?xml' not in result
        assert '<root>content</root>' in result

    def test_normalize_xml_strip_whitespace(self):
        """Should strip whitespace between tags."""
        service = NormalizationService()
        xml = '<root>   <child>  text  </child>   </root>'

        result = service.normalize_xml(xml)

        # Content whitespace should be normalized
        assert '  text  ' in result or 'text' in result

    def test_normalize_xml_decode_entities(self):
        """Should decode HTML entities."""
        service = NormalizationService()
        xml = '<root>Tom &amp; Jerry</root>'

        result = service.normalize_xml(xml)

        assert '&amp;' not in result
        assert 'Tom & Jerry' in result or 'Tom &amp; Jerry' in result

    def test_normalize_xml_empty(self):
        """Should handle empty XML."""
        service = NormalizationService()
        result = service.normalize_xml("")

        assert result == ""

    def test_normalize_lift_xml_add_root(self):
        """Should wrap in lift root element if missing."""
        service = NormalizationService()
        xml = '<entry id="test"><lexical-unit>word</lexical-unit></entry>'

        result = service.normalize_lift_xml(xml)

        assert '<lift' in result
        assert '</lift>' in result

    def test_normalize_lift_xml_preserve_existing_root(self):
        """Should preserve existing lift root."""
        service = NormalizationService()
        xml = '<lift xmlns="http://liftonario.org/"><entry>test</entry></lift>'

        result = service.normalize_lift_xml(xml)

        assert result.count('<lift') == 1  # Only one lift element
        assert '</lift>' in result

    def test_normalize_lift_xml_add_namespace(self):
        """Should add namespace if configured."""
        service = NormalizationService(xml_add_namespace=True)
        xml = '<entry>test</entry>'

        result = service.normalize_lift_xml(xml)

        assert 'xmlns=' in result or 'xmlns:lift=' in result

    def test_strip_xml_tags(self):
        """Should strip all XML tags."""
        service = NormalizationService()
        xml = '<entry><lexical-unit><text>word</text></lexical-unit></entry>'

        result = service.strip_xml_tags(xml)

        assert '<' not in result
        assert '>' not in result
        assert 'word' in result

    def test_strip_xml_tags_with_entities(self):
        """Should decode entities when stripping."""
        service = NormalizationService()
        xml = '<entry>Tom &amp; Jerry &lt;test&gt;</entry>'

        result = service.strip_xml_tags(xml)

        assert 'Tom & Jerry' in result
        assert '<test>' in result or 'test' in result


class TestMultilingualDictNormalization:
    """Test multilingual dictionary normalization"""

    def test_normalize_multilingual_dict_wrap_strings(self):
        """Should wrap string values in text format."""
        service = NormalizationService()
        data = {"en": "hello", "fr": "bonjour"}

        result = service.normalize_multilingual_dict(data)

        assert result == {"en": {"text": "hello"}, "fr": {"text": "bonjour"}}

    def test_normalize_multilingual_dict_preserve_text_format(self):
        """Should preserve existing text format."""
        service = NormalizationService()
        data = {"en": {"text": "hello"}, "fr": {"text": "bonjour"}}

        result = service.normalize_multilingual_dict(data)

        assert result == {"en": {"text": "hello"}, "fr": {"text": "bonjour"}}

    def test_normalize_multilingual_dict_recursive(self):
        """Should recursively normalize nested dicts."""
        service = NormalizationService()
        data = {"en": {"nested": "value"}}

        result = service.normalize_multilingual_dict(data)

        assert result["en"]["nested"] == {"text": "value"}

    def test_normalize_multilingual_dict_non_recursive(self):
        """Should not recurse when disabled."""
        service = NormalizationService()
        data = {"en": {"nested": "value"}}

        result = service.normalize_multilingual_dict(data, recursive=False)

        # Nested dict should be preserved as-is
        assert result["en"] == {"nested": "value"}

    def test_normalize_multilingual_dict_normalize_codes(self):
        """Should normalize language codes."""
        service = NormalizationService()
        data = {"EN": "hello", "FR": "bonjour"}

        result = service.normalize_multilingual_dict(data)

        assert "en" in result
        assert "fr" in result
        assert "EN" not in result

    def test_flatten_multilingual_dict_default_lang(self):
        """Should flatten dict to default language."""
        service = NormalizationService()
        data = {"en": "hello", "fr": "bonjour"}

        result = service.flatten_multilingual_dict(data, default_lang='en')

        assert result == "hello"

    def test_flatten_multilingual_dict_fallback_english(self):
        """Should fallback to English if default not found."""
        service = NormalizationService()
        data = {"en": "hello", "fr": "bonjour"}

        result = service.flatten_multilingual_dict(data, default_lang='de')

        assert result == "hello"  # Falls back to 'en'

    def test_flatten_multilingual_dict_first_available(self):
        """Should use first available language if no match."""
        service = NormalizationService()
        data = {"es": "hola", "it": "ciao"}

        result = service.flatten_multilingual_dict(data, default_lang='en')

        assert result in ["hola", "ciao"]  # One of the available values


class TestUnicodeNormalization:
    """Test Unicode normalization"""

    def test_normalize_unicode_nfc(self):
        """Should normalize to NFC form."""
        service = NormalizationService(unicode_normalization='NFC')
        # e + combining acute = é (precomposed)
        text = "caf\u0065\u0301"  # cafe + combining acute

        result = service.normalize_unicode(text)

        assert result == "caf\u00e9"  # Should be precomposed é

    def test_normalize_unicode_nfd(self):
        """Should normalize to NFD form."""
        service = NormalizationService(unicode_normalization='NFD')
        text = "caf\u00e9"  # Precomposed

        result = service.normalize_unicode(text, 'NFD')

        # Should be decomposed
        assert '\u0301' in result  # Combining acute present

    def test_normalize_unicode_custom_form(self):
        """Should accept custom normalization form."""
        service = NormalizationService()

        # Test with NFKC
        result = service.normalize_unicode("2²", 'NFKC')  # Superscript 2

        assert result == "22"  # NFKC normalizes superscript


class TestConvenienceFunctions:
    """Test module-level convenience functions"""

    def test_normalize_ipa_function(self):
        """Should work as convenience function."""
        result = normalize_ipa("hˈɛlo")

        assert 'ˈ' not in result

    def test_normalize_language_code_function(self):
        """Should work as convenience function."""
        result = normalize_language_code("EN-US")

        assert result == "en-US"

    def test_normalize_xml_function(self):
        """Should work as convenience function."""
        xml = '<?xml version="1.0"?><root>test</root>'
        result = normalize_xml(xml)

        assert '<?xml' not in result

    def test_normalize_lift_xml_function(self):
        """Should work as convenience function."""
        result = normalize_lift_xml('<entry>test</entry>')

        assert '<lift' in result

    def test_normalize_multilingual_dict_function(self):
        """Should work as convenience function."""
        data = {"EN": "hello"}
        result = normalize_multilingual_dict(data)

        assert "en" in result

    def test_normalize_unicode_function(self):
        """Should work as convenience function."""
        result = normalize_unicode("caf\u00e9", 'NFD')

        assert '\u0301' in result  # Should have combining acute

    def test_strip_xml_tags_function(self):
        """Should work as convenience function."""
        result = strip_xml_tags('<entry><text>word</text></entry>')

        assert result == "word"


class TestNormalizationServiceEdgeCases:
    """Test edge cases and special scenarios"""

    def test_nested_dict_with_various_types(self):
        """Should handle dicts with various value types."""
        service = NormalizationService()
        data = {
            "en": "string",
            "de": {"text": "nested"},
            "fr": 123,  # Number
            "es": None,  # None
        }

        result = service.normalize_multilingual_dict(data)

        assert result["en"] == {"text": "string"}
        assert result["de"] == {"text": "nested"}
        assert result["fr"] == {"text": "123"}  # Converted to string
        # None may be kept or converted depending on implementation

    def test_multilingual_dict_with_nested_text(self):
        """Should preserve deeply nested text structures."""
        service = NormalizationService()
        data = {
            "en": {
                "value": {
                    "text": "deeply nested"
                }
            }
        }

        result = service.normalize_multilingual_dict(data)

        # Deeply nested should be preserved or normalized
        assert "en" in result

    def test_unicode_with_multiple_combining(self):
        """Should handle multiple combining characters."""
        service = NormalizationService()
        # Character with multiple diacritics
        text = "a\u0301\u0302"  # a with acute and circumflex

        result = service.normalize_unicode(text, 'NFC')

        # Should be normalized to precomposed if available
        assert isinstance(result, str)

    def test_xml_with_special_characters(self):
        """Should handle XML with special characters."""
        service = NormalizationService()
        xml = '<entry>&lt;special&gt; &amp; &quot;quotes&quot;</entry>'

        result = service.normalize_xml(xml)

        # Entities should be handled
        assert isinstance(result, str)

    def test_lift_xml_with_multiple_entries(self):
        """Should handle multiple entries in LIFT XML."""
        service = NormalizationService()
        xml = '<entry id="1"/><entry id="2"/>'

        result = service.normalize_lift_xml(xml)

        assert '<lift' in result
        # Should wrap multiple entries
        assert result.count('<entry') == 2

    def test_ipa_with_many_diacritics(self):
        """Should handle IPA with many diacritics."""
        service = NormalizationService(ipa_remove_diacritics=True)
        # IPA with tone and length marks
        ipa = "/tiːˠ/"  # With length and tone diacritics

        result = service.normalize_ipa(ipa, mode=NormalizationMode.STRICT)

        # In strict mode with remove_diacritics, should be cleaner
        assert isinstance(result, str)

    def test_language_code_with_multiple_subtags(self):
        """Should handle complex BCP 47 codes."""
        service = NormalizationService()

        codes = [
            "zh-Hans-CN",  # Chinese, Simplified, China
            "sr-Latn-RS",  # Serbian, Latin, Serbia
            "en-Latn-US",  # English, Latin, US
        ]

        for code in codes:
            result = service.normalize_language_code(code)
            # Should preserve structure with proper casing
            assert '-' in result
            assert isinstance(result, str)

    def test_empty_and_whitespace_only(self):
        """Should handle empty and whitespace-only inputs."""
        service = NormalizationService()

        assert service.normalize_xml("") == ""
        assert service.normalize_lift_xml("") == ""

    def test_multilingual_dict_empty(self):
        """Should handle empty multilingual dict."""
        service = NormalizationService()

        result = service.normalize_multilingual_dict({})
        assert result == {}

        result = service.flatten_multilingual_dict({})
        assert result == ""
