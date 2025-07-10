#!/usr/bin/env python3
"""
Unit tests for etymology UI functionality.
Tests etymology object creation and manipulation using mocks.
"""

import pytest
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
        """Test adding etymology to existing entry."""
        entry = Entry(lexical_unit={"en": "water"})
        entry.add_etymology(
            etymology_type="inheritance",
            source="Old English", 
            form_lang="ang",
            form_text="wæter",
            gloss_lang="en",
            gloss_text="water"
        )
        assert len(entry.etymologies) == 1
        assert entry.etymologies[0].type == "inheritance" 
        assert entry.etymologies[0].source == "Old English"
        assert isinstance(entry.etymologies[0].form, dict)
        assert entry.etymologies[0].form["lang"] == "ang"
        assert entry.etymologies[0].form["text"] == "wæter"