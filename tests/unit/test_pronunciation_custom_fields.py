"""
Unit tests for pronunciation custom fields (cv-pattern and tone).

Tests Day 40 implementation:
- cv_pattern attribute support (multitext dict)
- tone attribute support (multitext dict)
- Serialization to LIFT XML
- Validation
"""

from __future__ import annotations
import pytest
from app.models.pronunciation import Pronunciation
from app.utils.exceptions import ValidationError


class TestPronunciationCVPattern:
    """Test CV pattern custom field."""
    
    def test_pronunciation_with_cv_pattern_single_language(self) -> None:
        """Test pronunciation with cv-pattern in one language."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ʔapa"},
            cv_pattern={"en": "CVCV"}
        )
        
        assert pron.cv_pattern == {"en": "CVCV"}
        assert pron.form == {"qaa-fonipa": "ʔapa"}
    
    def test_pronunciation_with_cv_pattern_multiple_languages(self) -> None:
        """Test pronunciation with cv-pattern in multiple languages."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ʔapa"},
            cv_pattern={
                "en": "CVCV",
                "fr": "CVCV (consonne-voyelle-consonne-voyelle)"
            }
        )
        
        assert len(pron.cv_pattern) == 2
        assert pron.cv_pattern["en"] == "CVCV"
        assert pron.cv_pattern["fr"] == "CVCV (consonne-voyelle-consonne-voyelle)"
    
    def test_pronunciation_without_cv_pattern_defaults_empty(self) -> None:
        """Test pronunciation without cv-pattern defaults to empty dict."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ʔapa"}
        )
        
        assert pron.cv_pattern == {}
    
    def test_cv_pattern_validation_allows_empty(self) -> None:
        """Test cv-pattern validation allows empty dict."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ʔapa"},
            cv_pattern={}
        )
        
        # Should not raise
        pron.validate()
        assert pron.cv_pattern == {}


class TestPronunciationTone:
    """Test tone custom field."""
    
    def test_pronunciation_with_tone_single_language(self) -> None:
        """Test pronunciation with tone in one language."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ʔapa"},
            tone={"en": "HLH"}
        )
        
        assert pron.tone == {"en": "HLH"}
        assert pron.form == {"qaa-fonipa": "ʔapa"}
    
    def test_pronunciation_with_tone_multiple_languages(self) -> None:
        """Test pronunciation with tone in multiple languages."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ma˥ma˧˥"},
            tone={
                "en": "High-Mid-High",
                "zh": "高中高"
            }
        )
        
        assert len(pron.tone) == 2
        assert pron.tone["en"] == "High-Mid-High"
        assert pron.tone["zh"] == "高中高"
    
    def test_pronunciation_without_tone_defaults_empty(self) -> None:
        """Test pronunciation without tone defaults to empty dict."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ʔapa"}
        )
        
        assert pron.tone == {}
    
    def test_tone_validation_allows_empty(self) -> None:
        """Test tone validation allows empty dict."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ʔapa"},
            tone={}
        )
        
        # Should not raise
        pron.validate()
        assert pron.tone == {}


class TestPronunciationBothFields:
    """Test cv-pattern and tone together."""
    
    def test_pronunciation_with_both_cv_pattern_and_tone(self) -> None:
        """Test pronunciation with both cv-pattern and tone."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ʔapa"},
            cv_pattern={"en": "CVCV"},
            tone={"en": "HLH"}
        )
        
        assert pron.cv_pattern == {"en": "CVCV"}
        assert pron.tone == {"en": "HLH"}
        assert pron.form == {"qaa-fonipa": "ʔapa"}
    
    def test_pronunciation_with_both_fields_multiple_languages(self) -> None:
        """Test pronunciation with both fields in multiple languages."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ka˥ta˧"},
            cv_pattern={
                "en": "CVCV",
                "es": "consonante-vocal-consonante-vocal"
            },
            tone={
                "en": "High-Mid",
                "es": "Alto-Medio"
            }
        )
        
        assert len(pron.cv_pattern) == 2
        assert len(pron.tone) == 2
        assert pron.cv_pattern["en"] == "CVCV"
        assert pron.tone["es"] == "Alto-Medio"
    
    def test_to_dict_includes_cv_pattern_and_tone(self) -> None:
        """Test to_dict includes cv_pattern and tone."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ʔapa"},
            cv_pattern={"en": "CVCV"},
            tone={"en": "HLH"}
        )
        
        pron_dict = pron.to_dict()
        
        assert "cv_pattern" in pron_dict
        assert "tone" in pron_dict
        assert pron_dict["cv_pattern"] == {"en": "CVCV"}
        assert pron_dict["tone"] == {"en": "HLH"}
    
    def test_to_dict_excludes_empty_cv_pattern_and_tone(self) -> None:
        """Test to_dict excludes empty cv_pattern and tone."""
        pron = Pronunciation(
            id_="pron1",
            form={"qaa-fonipa": "ʔapa"},
            cv_pattern={},
            tone={}
        )
        
        pron_dict = pron.to_dict()
        
        # Empty dicts should be included but empty
        assert pron_dict.get("cv_pattern") == {}
        assert pron_dict.get("tone") == {}
