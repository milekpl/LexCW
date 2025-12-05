"""
Unit tests for LIFT 0.13 General Traits (Flexible Metadata).
Tests arbitrary key-value trait support on various LIFT elements.
"""

import pytest
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example


class TestEntryTraits:
    """Test general trait support on entry elements."""
    
    def test_entry_has_traits_attribute(self) -> None:
        """Test that Entry model has traits attribute."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            traits={"morph-type": "stem"}
        )
        assert hasattr(entry, 'traits')
        assert entry.traits == {"morph-type": "stem"}
    
    def test_entry_traits_defaults_to_empty_dict(self) -> None:
        """Test that entry traits defaults to empty dict if not provided."""
        entry = Entry(
            id_="test2",
            lexical_unit={"en": "word"}
        )
        assert entry.traits == {}
    
    def test_entry_supports_multiple_traits(self) -> None:
        """Test that entry can have multiple traits."""
        entry = Entry(
            id_="test3",
            lexical_unit={"en": "compound"},
            traits={
                "morph-type": "phrase",
                "status": "checked",
                "source": "imported"
            }
        )
        assert entry.traits["morph-type"] == "phrase"
        assert entry.traits["status"] == "checked"
        assert entry.traits["source"] == "imported"


class TestExampleTraits:
    """Test general trait support on example elements."""
    
    def test_example_has_traits_attribute(self) -> None:
        """Test that Example model has traits attribute."""
        example = Example(
            id_="ex1",
            form={"en": "example sentence"},
            traits={"source": "corpus"}
        )
        assert hasattr(example, 'traits')
        assert example.traits == {"source": "corpus"}
    
    def test_example_traits_defaults_to_empty_dict(self) -> None:
        """Test that example traits defaults to empty dict."""
        example = Example(
            id_="ex2",
            form={"en": "another example"}
        )
        assert example.traits == {}
    
    def test_example_supports_custom_traits(self) -> None:
        """Test that example supports arbitrary custom traits."""
        example = Example(
            id_="ex3",
            form={"en": "test sentence"},
            traits={
                "register": "formal",
                "frequency": "common",
                "verified": "true"
            }
        )
        assert example.traits["register"] == "formal"
        assert example.traits["frequency"] == "common"
        assert example.traits["verified"] == "true"


class TestSenseGeneralTraits:
    """Test general trait support on sense elements (beyond grammatical traits)."""
    
    def test_sense_has_general_traits_attribute(self) -> None:
        """Test that Sense model has general traits attribute separate from grammatical_traits."""
        sense = Sense(
            id_="s1",
            glosses={"en": "test"},
            traits={"status": "reviewed"}
        )
        assert hasattr(sense, 'traits')
        assert sense.traits == {"status": "reviewed"}
    
    def test_sense_general_traits_defaults_to_empty_dict(self) -> None:
        """Test that sense general traits defaults to empty dict."""
        sense = Sense(
            id_="s2",
            glosses={"en": "word"}
        )
        assert sense.traits == {}
    
    def test_sense_can_have_both_grammatical_and_general_traits(self) -> None:
        """Test that sense can have both grammatical_traits and general traits."""
        sense = Sense(
            id_="s3",
            glosses={"en": "noun"},
            grammatical_info="Noun",
            grammatical_traits={"gender": "masculine"},
            traits={"status": "verified", "source": "native-speaker"}
        )
        # Grammatical traits (nested in grammatical-info)
        assert sense.grammatical_traits["gender"] == "masculine"
        # General traits (direct children of sense)
        assert sense.traits["status"] == "verified"
        assert sense.traits["source"] == "native-speaker"


class TestTraitIntegration:
    """Test trait integration across multiple elements."""
    
    def test_entry_with_sense_and_example_all_have_traits(self) -> None:
        """Test that entry, sense, and example can all have traits simultaneously."""
        example = Example(
            id_="ex1",
            form={"en": "Test this."},
            traits={"source": "textbook"}
        )
        
        sense = Sense(
            id_="s1",
            glosses={"en": "to check"},
            examples=[example.to_dict()],
            traits={"confidence": "high"}
        )
        
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[sense],
            traits={"morph-type": "stem", "import-date": "2024-01-01"}
        )
        
        assert entry.traits["morph-type"] == "stem"
        assert entry.traits["import-date"] == "2024-01-01"
        assert sense.traits["confidence"] == "high"
        # Note: example is stored as dict, so we check the dict structure
        assert example.traits["source"] == "textbook"
    
    def test_update_traits(self) -> None:
        """Test updating traits on an element."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "word"},
            traits={"status": "draft"}
        )
        
        # Update existing trait
        entry.traits["status"] = "reviewed"
        assert entry.traits["status"] == "reviewed"
        
        # Add new trait
        entry.traits["reviewer"] = "john_doe"
        assert entry.traits["reviewer"] == "john_doe"
    
    def test_empty_traits_dict(self) -> None:
        """Test that empty traits dict is allowed."""
        sense = Sense(
            id_="s1",
            glosses={"en": "test"},
            traits={}
        )
        assert sense.traits == {}
        assert len(sense.traits) == 0
