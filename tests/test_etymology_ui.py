#!/usr/bin/env python3
"""
Test suite for etymology UI functionality.
Tests etymology editing with proper Form/Gloss object support and LIFT compliance.
"""

import pytest
from unittest.mock import Mock
from app import create_app, injector
from app.models.entry import Entry, Etymology, Form, Gloss
from app.services.dictionary_service import DictionaryService
from app.database.mock_connector import MockDatabaseConnector


class TestEtymologyUI:
    """Test etymology object creation and manipulation."""

    def test_etymology_object_creation(self):
        """Test creating etymology objects with Form and Gloss."""
        form = Form(lang="la", text="pater")
        gloss = Gloss(lang="en", text="father")
        etymology = Etymology(
            type="borrowing",
            source="Latin",
            form=form,
            gloss=gloss
        )
        
        assert etymology.type == "borrowing"
        assert etymology.source == "Latin"
        assert etymology.form.lang == "la"
        assert etymology.form.text == "pater"
        assert etymology.gloss.lang == "en" 
        assert etymology.gloss.text == "father"

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
        assert isinstance(entry.etymologies[0].form, Form)
        assert isinstance(entry.etymologies[0].gloss, Gloss)

    def test_etymology_serialization(self):
        """Test etymology serialization to dict."""
        etymology = Etymology(
            type="compound",
            source="Germanic",
            form=Form(lang="gem-pro", text="*faðēr"),
            gloss=Gloss(lang="en", text="protector")
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
        assert entry.etymologies[0].form.lang == "ang"
        assert entry.etymologies[0].form.text == "wæter"


class TestEtymologyAPISupport:
    """Test API support for etymology management."""
    
    @pytest.fixture
    def app(self):
        """Create test app with mock connector."""
        app = create_app('testing')
        
        # Inject mock connector
        mock_connector = MockDatabaseConnector()
        injector.binder.bind(DictionaryService, 
                           lambda: DictionaryService(mock_connector))
        
        return app

    def test_api_entry_creation_with_etymologies(self, app):
        """Test creating entries with etymologies via API."""
        with app.app_context():
            dict_service = injector.get(DictionaryService)
            
            entry_data = {
                "lexical_unit": {"en": "water"},
                "etymologies": [
                    {
                        "type": "inheritance",
                        "source": "Old English", 
                        "form": {"lang": "ang", "text": "wæter"},
                        "gloss": {"lang": "en", "text": "water"}
                    }
                ]
            }
            
            entry = Entry.from_dict(entry_data)
            result_id = dict_service.create_entry(entry)
            
            assert result_id is not None
            assert len(entry.etymologies) == 1
            assert entry.etymologies[0].type == "inheritance"

    def test_api_entry_update_with_etymologies(self, app):
        """Test updating entry etymologies via API."""
        with app.app_context():
            dict_service = injector.get(DictionaryService)
            
            # Create entry
            entry = Entry(lexical_unit={"en": "book"})
            entry_id = dict_service.create_entry(entry)
            
            # Get the entry from database to ensure we have the correct object
            entry = dict_service.get_entry(entry_id)
            
            # Update with etymologies
            entry.add_etymology(
                etymology_type="borrowing",
                source="Old French",
                form_lang="fro", 
                form_text="livre",
                gloss_lang="en",
                gloss_text="book"
            )
            entry.add_etymology(
                etymology_type="inheritance", 
                source="Latin",
                form_lang="la",
                form_text="liber", 
                gloss_lang="en",
                gloss_text="book, writing"
            )
            
            dict_service.update_entry(entry)
            
            # Verify update
            updated_entry = dict_service.get_entry(entry_id)
            assert len(updated_entry.etymologies) == 2


class TestEtymologyRangesIntegration:
    """Test integration with LIFT ranges for etymology types."""
    
    @pytest.fixture
    def app(self):
        """Create test app."""
        return create_app('testing')
    
    def test_etymology_types_from_ranges(self, app):
        """Test that etymology types can be retrieved from ranges."""
        with app.app_context():
            dict_service = injector.get(DictionaryService)
            ranges = dict_service.get_ranges()
            
            # Should have etymology-types in ranges
            # (This will use fallback defaults for testing)
            assert isinstance(ranges, dict)
            
            # For now, just verify ranges work
            # TODO: Add etymology-types to default ranges

    def test_etymology_validation_ready(self, app):
        """Test that etymology validation system is ready."""
        with app.app_context():
            # Create etymology with standard type
            etymology = Etymology(
                type="borrowing",
                source="Latin",
                form=Form(lang="la", text="pater"),
                gloss=Gloss(lang="en", text="father")
            )
            
            # Basic validation should pass
            assert etymology.type is not None
            assert etymology.source is not None
            assert etymology.form is not None
            assert etymology.gloss is not None


class TestEtymologyLifecycle:
    """Test complete etymology lifecycle operations."""
    
    @pytest.fixture
    def app(self):
        """Create test app with mock connector."""
        app = create_app('testing')
        
        # Inject mock connector  
        mock_connector = MockDatabaseConnector()
        injector.binder.bind(DictionaryService,
                           lambda: DictionaryService(mock_connector))
        
        return app

    def test_add_etymology_to_existing_entry(self, app):
        """Test adding an etymology to an existing entry."""
        with app.app_context():
            dict_service = injector.get(DictionaryService)
            
            # Create base entry
            entry = Entry(lexical_unit={"en": "house"})
            entry_id = dict_service.create_entry(entry)
            
            # Get the entry from database to ensure we have the correct object
            entry = dict_service.get_entry(entry_id)
            
            # Add etymology
            entry.add_etymology(
                etymology_type="inheritance",
                source="Old English",
                form_lang="ang",
                form_text="hūs", 
                gloss_lang="en",
                gloss_text="house"
            )
            dict_service.update_entry(entry)
            
            # Verify
            updated = dict_service.get_entry(entry_id)
            assert len(updated.etymologies) == 1
            assert updated.etymologies[0].type == "inheritance"
            assert updated.etymologies[0].source == "Old English"

    def test_remove_etymology_from_entry(self, app):
        """Test removing an etymology from an entry."""
        with app.app_context():
            dict_service = injector.get(DictionaryService)
            
            # Create entry with etymologies
            entry = Entry(
                lexical_unit={"en": "test"}, 
                etymologies=[
                    {
                        "type": "inheritance",
                        "source": "keep_source",
                        "form": {"lang": "en", "text": "keep_form"},
                        "gloss": {"lang": "en", "text": "keep_gloss"}
                    },
                    {
                        "type": "borrowing", 
                        "source": "remove_source",
                        "form": {"lang": "en", "text": "remove_form"},
                        "gloss": {"lang": "en", "text": "remove_gloss"}
                    }
                ]
            )
            entry_id = dict_service.create_entry(entry)
            
            # Get the entry from database to ensure we have the correct object
            entry = dict_service.get_entry(entry_id)
            
            # Remove one etymology
            entry.etymologies = [e for e in entry.etymologies if e.source != "remove_source"]
            dict_service.update_entry(entry)
            
            # Verify
            updated = dict_service.get_entry(entry_id)
            assert len(updated.etymologies) == 1
            assert updated.etymologies[0].source == "keep_source"

    def test_modify_etymology_in_entry(self, app):
        """Test modifying an existing etymology."""
        with app.app_context():
            dict_service = injector.get(DictionaryService)
            
            # Create entry with etymology
            entry = Entry(
                lexical_unit={"en": "test"},
                etymologies=[{
                    "type": "borrowing",
                    "source": "old_source", 
                    "form": {"lang": "en", "text": "old_form"},
                    "gloss": {"lang": "en", "text": "old_gloss"}
                }]
            )
            entry_id = dict_service.create_entry(entry)
            
            # Get the entry from database to ensure we have the correct object
            entry = dict_service.get_entry(entry_id)
            
            # Modify etymology
            entry.etymologies[0].type = "inheritance"
            entry.etymologies[0].source = "new_source"
            entry.etymologies[0].form.text = "new_form"
            entry.etymologies[0].gloss.text = "new_gloss"
            dict_service.update_entry(entry)
            
            # Verify
            updated = dict_service.get_entry(entry_id)
            assert len(updated.etymologies) == 1
            assert updated.etymologies[0].type == "inheritance"
            assert updated.etymologies[0].source == "new_source"
            assert updated.etymologies[0].form.text == "new_form"
            assert updated.etymologies[0].gloss.text == "new_gloss"
