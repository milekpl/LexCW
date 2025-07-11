#!/usr/bin/env python3
"""
Unit tests for etymology UI functionality.
Tests etymology object creation and manipulation using mocks.
"""

from app.models.entry import Entry, Etymology


class TestEtymologyUI:
    """Test etymology object creation and manipulation."""

    def test_etymology_object_creation(self):
        """Test creating etymology objects with form and gloss as dicts."""
        form = {"lang": "la", "text": "pater"}
        gloss = {"lang": "en", "text": "father"}
        etymology = Etymology(
            type="borrowing",
            source="Latin",
            form=form,
            gloss=gloss
        )
        assert etymology.type == "borrowing"
        assert etymology.source == "Latin"
        assert etymology.form["lang"] == "la"
        assert etymology.form["text"] == "pater"
        assert etymology.gloss["lang"] == "en"
        assert etymology.gloss["text"] == "father"

    def test_entry_model_supports_etymologies_list(self):
        """Test that Entry model properly handles etymologies list."""
        etymologies = [
            {
                "type": "inheritance", 
                "source": "Proto-Indo-European",
                "form": {"lang": "ine-pro", "text": "*ph₂tḗr"},
                "gloss": {"lang": "en", "text": "father"}
            }
        ]
        entry = Entry(
            lexical_unit={"en": "father"},
            etymologies=etymologies
        )
        assert len(entry.etymologies) == 1
        assert isinstance(entry.etymologies[0], Etymology)
        assert entry.etymologies[0].type == "inheritance"
        assert isinstance(entry.etymologies[0].form, dict)
        assert isinstance(entry.etymologies[0].gloss, dict)

    def test_etymology_serialization(self):
        """Test etymology serialization to dict."""
        etymology = Etymology(
            type="compound",
            source="Germanic",
            form={"lang": "gem-pro", "text": "*faðēr"},
            gloss={"lang": "en", "text": "protector"}
        )
        etymology_dict = etymology.to_dict()
        assert etymology_dict["type"] == "compound"
        assert etymology_dict["source"] == "Germanic"
        assert etymology_dict["form"]["lang"] == "gem-pro"
        assert etymology_dict["form"]["text"] == "*faðēr"
        assert etymology_dict["gloss"]["lang"] == "en"
        assert etymology_dict["gloss"]["text"] == "protector"

    def test_empty_etymologies_handling(self):
        """Test that entries handle empty etymologies properly."""
        entry = Entry(lexical_unit={"en": "test"})
        assert entry.etymologies == []
        assert len(entry.etymologies) == 0

    def test_add_etymology_method(self):
        """
        Test adding an etymology to an existing entry, ensuring correct
        object creation and attribute assignment.
        """
        # 1. Setup: Create an entry without etymologies
        entry = Entry(lexical_unit={"en": "water"})
        assert entry.etymologies == []

        # 2. Action: Add a new etymology
        entry.add_etymology(
            etymology_type="inheritance",
            source="Old English",
            form_lang="ang",
            form_text="wæter",
            gloss_lang="en",
            gloss_text="water"
        )

        # 3. Verification: Check the newly added etymology
        assert len(entry.etymologies) == 1
        new_etymology = entry.etymologies[0]

        # Verify the etymology object is of the correct type
        assert isinstance(new_etymology, Etymology)

        # Verify all attributes are correctly assigned
        assert new_etymology.type == "inheritance"
        assert new_etymology.source == "Old English"

        # Verify the 'form' dictionary is correctly created
        assert isinstance(new_etymology.form, dict)
        assert new_etymology.form["lang"] == "ang"
        assert new_etymology.form["text"] == "wæter"

        # Verify the 'gloss' dictionary is correctly created
        assert isinstance(new_etymology.gloss, dict)
        assert new_etymology.gloss["lang"] == "en"
        assert new_etymology.gloss["text"] == "water"

        # 4. Action: Add a second etymology to test list extension
        entry.add_etymology(
            etymology_type="borrowing",
            source="Old Norse",
            form_lang="non",
            form_text="vatn",
            gloss_lang="en",
            gloss_text="water"
        )

        # 5. Verification: Check the list of etymologies now has two items
        assert len(entry.etymologies) == 2
        second_etymology = entry.etymologies[1]
        assert second_etymology.type == "borrowing"
        assert second_etymology.source == "Old Norse"