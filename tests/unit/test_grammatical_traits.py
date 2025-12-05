"""
Unit tests for Grammatical Info Traits (Day 29-30).

Tests grammatical-info elements with nested trait elements for morphological features.
Following TDD approach - these tests define the expected behavior.
"""

from __future__ import annotations

import pytest
from app.models.sense import Sense
from app.models.entry import Variant


class TestGrammaticalInfoTraits:
    """Test grammatical-info with trait elements."""
    
    def test_sense_has_grammatical_traits_attribute(self) -> None:
        """Test that Sense model has grammatical_traits attribute."""
        sense = Sense(
            id="s1",
            grammatical_info="Noun",
            grammatical_traits={"gender": "masculine", "number": "plural"}
        )
        assert hasattr(sense, 'grammatical_traits')
        assert sense.grammatical_traits == {"gender": "masculine", "number": "plural"}
    
    def test_sense_grammatical_traits_defaults_to_none(self) -> None:
        """Test that grammatical_traits defaults to None."""
        sense = Sense(id="s1")
        assert sense.grammatical_traits is None
    
    def test_sense_grammatical_traits_is_dict(self) -> None:
        """Test that grammatical_traits stores as dictionary."""
        sense = Sense(
            id="s1",
            grammatical_info="Verb",
            grammatical_traits={"tense": "past", "aspect": "perfective"}
        )
        assert isinstance(sense.grammatical_traits, dict)
        assert sense.grammatical_traits["tense"] == "past"
        assert sense.grammatical_traits["aspect"] == "perfective"
    
    def test_sense_supports_common_morphological_features(self) -> None:
        """Test common morphological traits: gender, number, case."""
        sense = Sense(
            id="s1",
            grammatical_info="Noun",
            grammatical_traits={
                "gender": "feminine",
                "number": "singular",
                "case": "genitive"
            }
        )
        assert sense.grammatical_traits["gender"] == "feminine"
        assert sense.grammatical_traits["number"] == "singular"
        assert sense.grammatical_traits["case"] == "genitive"
    
    def test_sense_supports_verb_features(self) -> None:
        """Test verb-specific traits: tense, aspect, mood."""
        sense = Sense(
            id="s1",
            grammatical_info="Verb",
            grammatical_traits={
                "tense": "present",
                "aspect": "imperfective",
                "mood": "indicative"
            }
        )
        assert sense.grammatical_traits["tense"] == "present"
        assert sense.grammatical_traits["aspect"] == "imperfective"
        assert sense.grammatical_traits["mood"] == "indicative"
    
    def test_sense_supports_custom_traits(self) -> None:
        """Test arbitrary custom trait key-value pairs."""
        sense = Sense(
            id="s1",
            grammatical_info="Adjective",
            grammatical_traits={
                "animacy": "animate",
                "comparison": "comparative",
                "custom_feature": "custom_value"
            }
        )
        assert sense.grammatical_traits["animacy"] == "animate"
        assert sense.grammatical_traits["comparison"] == "comparative"
        assert sense.grammatical_traits["custom_feature"] == "custom_value"
    
    def test_sense_grammatical_traits_can_be_empty_dict(self) -> None:
        """Test that grammatical_traits can be empty dict."""
        sense = Sense(
            id="s1",
            grammatical_info="Noun",
            grammatical_traits={}
        )
        assert sense.grammatical_traits == {}
        assert len(sense.grammatical_traits) == 0


class TestVariantGrammaticalTraits:
    """Test grammatical-info traits in variant elements."""
    
    def test_variant_has_grammatical_traits_attribute(self) -> None:
        """Test that Variant model has grammatical_traits attribute."""
        variant = Variant(
            form={"en": "running"},
            grammatical_info="Noun",
            grammatical_traits={"gender": "neuter"}
        )
        assert hasattr(variant, 'grammatical_traits')
        assert variant.grammatical_traits == {"gender": "neuter"}
    
    def test_variant_grammatical_traits_defaults_to_none(self) -> None:
        """Test that variant grammatical_traits defaults to None."""
        variant = Variant(form={"en": "walked"})
        assert variant.grammatical_traits is None
    
    def test_variant_supports_morphological_traits(self) -> None:
        """Test that variants can have grammatical traits."""
        variant = Variant(
            form={"en": "jumped"},
            grammatical_info="Adjective",
            grammatical_traits={
                "gender": "masculine",
                "number": "plural",
                "case": "accusative"
            }
        )
        assert variant.grammatical_traits["gender"] == "masculine"
        assert variant.grammatical_traits["number"] == "plural"
        assert variant.grammatical_traits["case"] == "accusative"


class TestGrammaticalTraitsIntegration:
    """Test grammatical traits in complex scenarios."""
    
    def test_multiple_senses_with_different_traits(self) -> None:
        """Test multiple senses with different grammatical traits."""
        sense1 = Sense(
            id="s1",
            grammatical_info="Noun",
            grammatical_traits={"gender": "masculine", "number": "singular"}
        )
        sense2 = Sense(
            id="s2",
            grammatical_info="Noun",
            grammatical_traits={"gender": "feminine", "number": "plural"}
        )
        
        assert sense1.grammatical_traits["gender"] == "masculine"
        assert sense2.grammatical_traits["gender"] == "feminine"
        assert sense1.grammatical_traits["number"] == "singular"
        assert sense2.grammatical_traits["number"] == "plural"
    
    def test_grammatical_info_without_traits(self) -> None:
        """Test that grammatical_info can exist without traits."""
        sense = Sense(
            id="s1",
            grammatical_info="Adverb",
            grammatical_traits=None
        )
        assert sense.grammatical_info == "Adverb"
        assert sense.grammatical_traits is None
    
    def test_traits_without_grammatical_info(self) -> None:
        """Test that traits require grammatical_info."""
        # This should be valid - traits can exist independently
        sense = Sense(
            id="s1",
            grammatical_info=None,
            grammatical_traits={"custom": "value"}
        )
        assert sense.grammatical_info is None
        assert sense.grammatical_traits == {"custom": "value"}
    
    def test_update_grammatical_traits(self) -> None:
        """Test updating grammatical traits."""
        sense = Sense(
            id="s1",
            grammatical_info="Noun",
            grammatical_traits={"gender": "masculine"}
        )
        
        # Update traits
        sense.grammatical_traits["number"] = "plural"
        sense.grammatical_traits["case"] = "nominative"
        
        assert len(sense.grammatical_traits) == 3
        assert sense.grammatical_traits["gender"] == "masculine"
        assert sense.grammatical_traits["number"] == "plural"
        assert sense.grammatical_traits["case"] == "nominative"
