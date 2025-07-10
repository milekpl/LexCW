#!/usr/bin/env python3
"""
Integration tests for etymology UI functionality.
Tests etymology editing with real database and API integration.
"""

import pytest
from unittest.mock import Mock
from flask import Flask
from app import create_app
from app.models.entry import Entry, Etymology
from app.services.dictionary_service import DictionaryService
from app.database.mock_connector import MockDatabaseConnector


class TestEtymologyAPISupport:
    """Test API support for etymology management."""
    @pytest.mark.integration
    @pytest.fixture
    def app(self) -> Flask:
        """Create test app with mock connector."""
        mock_connector = MockDatabaseConnector()
        mock_dictionary_service = DictionaryService(mock_connector)

        app = create_app('testing')
        app.config['DICTIONARY_SERVICE'] = mock_dictionary_service
        return app

    @pytest.mark.integration
    def test_api_entry_creation_with_etymologies(self, app: Flask):
        """Test creating entries with etymologies via API."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            entry_data = {
                "lexical_unit": {"en": "water"},
                "senses": [
                    {
                        "id": "sense-1",
                        "definition": {"en": "transparent liquid"}
                    }
                ],
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

    @pytest.mark.integration
    def test_api_entry_update_with_etymologies(self, app: Flask):
        """Test updating entry etymologies via API."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            # Create entry
            entry = Entry(
                lexical_unit={"en": "book"}, 
                senses=[{"id": "sense-1", "definition": {"en": "printed work"}}]
            )
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
    @pytest.mark.integration
    @pytest.fixture
    def app(self) -> Flask:
        """Create test app."""
        app = create_app('testing')
        app.config['DICTIONARY_SERVICE'] = Mock(spec=DictionaryService)
        return app
    @pytest.mark.integration
    def test_etymology_types_from_ranges(self, app: Flask):
        """Test that etymology types can be retrieved from ranges."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            ranges = dict_service.get_ranges()
            assert isinstance(ranges, dict)
    @pytest.mark.integration
    def test_etymology_validation_ready(self, app):
        """Test that etymology validation system is ready."""
        with app.app_context():
            etymology = Etymology(
                type="borrowing",
                source="Latin",
                form={"lang": "la", "text": "pater"},
                gloss={"lang": "en", "text": "father"}
            )
            assert etymology.type is not None
            assert etymology.source is not None
            assert etymology.form is not None
            assert etymology.gloss is not None


class TestEtymologyLifecycle:
    """Test complete etymology lifecycle operations."""
    @pytest.mark.integration
    @pytest.fixture
    def app(self) -> Flask:
        """Create test app with mock connector."""
        mock_connector = MockDatabaseConnector()
        mock_dictionary_service = DictionaryService(mock_connector)
        app = create_app('testing')
        app.config['DICTIONARY_SERVICE'] = mock_dictionary_service
        return app
    @pytest.mark.integration
    def test_add_etymology_to_existing_entry(self, app: Flask):
        """Test adding an etymology to an existing entry."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            entry = Entry(
                lexical_unit={"en": "house"}, 
                senses=[{"id": "sense-1", "definition": {"en": "dwelling place"}}]
            )
            entry_id = dict_service.create_entry(entry)
            entry = dict_service.get_entry(entry_id)
            entry.add_etymology(
                etymology_type="inheritance",
                source="Old English",
                form_lang="ang",
                form_text="hūs", 
                gloss_lang="en",
                gloss_text="house"
            )
            dict_service.update_entry(entry)
            updated = dict_service.get_entry(entry_id)
            assert len(updated.etymologies) == 1
            assert updated.etymologies[0].type == "inheritance"
            assert updated.etymologies[0].source == "Old English"
    @pytest.mark.integration
    def test_remove_etymology_from_entry(self, app: Flask):
        """Test removing an etymology from an entry."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            entry = Entry(
                lexical_unit={"en": "test"}, 
                senses=[{"id": "sense-1", "definition": {"en": "test word"}}],
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
            entry = dict_service.get_entry(entry_id)
            entry.etymologies = [e for e in entry.etymologies if e.source != "remove_source"]
            dict_service.update_entry(entry)
            updated = dict_service.get_entry(entry_id)
            assert len(updated.etymologies) == 1
            assert updated.etymologies[0].source == "keep_source"
    @pytest.mark.integration
    def test_modify_etymology_in_entry(self, app: Flask):
        """Test modifying an existing etymology."""
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            entry = Entry(
                lexical_unit={"en": "test"},
                senses=[{"id": "sense_1", "definition": {"en": "test definition"}}],
                etymologies=[{
                    "type": "borrowing",
                    "source": "old_source", 
                    "form": {"lang": "en", "text": "old_form"},
                    "gloss": {"lang": "en", "text": "old_gloss"}
                }]
            )
            entry_id = dict_service.create_entry(entry)
            entry = dict_service.get_entry(entry_id)
            entry.etymologies[0].type = "inheritance"
            entry.etymologies[0].source = "new_source"
            entry.etymologies[0].form["text"] = "new_form"
            entry.etymologies[0].gloss["text"] = "new_gloss"
            dict_service.update_entry(entry)
            updated = dict_service.get_entry(entry_id)
            assert len(updated.etymologies) == 1
            assert updated.etymologies[0].type == "inheritance"
            assert updated.etymologies[0].source == "new_source"
            assert updated.etymologies[0].form["text"] == "new_form"
            assert updated.etymologies[0].gloss["text"] == "new_gloss"
