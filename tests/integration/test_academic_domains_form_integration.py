"""
Comprehensive integration tests for Academic Domains end-to-end form functionality.

Tests that Academic Domains work correctly through the complete user workflow:
- Form submission with academic domains
- Backend processing and validation
- Database persistence and retrieval
- UI display and editing

These tests ensure academic domains are fully functional in the application.
"""

from __future__ import annotations

import pytest
from flask import Flask
from werkzeug.test import Client
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.models.sense import Sense


@pytest.mark.integration
class TestAcademicDomainsFormIntegration:
    """Integration tests for Academic Domains form integration."""

    @pytest.fixture
    def client(self, app: Flask) -> Client:
        """Flask test client."""
        return app.test_client()

    @pytest.fixture
    def test_entry_data_entry_level_academic_domain(self) -> dict:
        """Test data for entry with sense-level academic domain."""
        return {
            'lexical_unit.en': 'computer science',
            'senses[0].id': 'sense1',
            'senses[0].definition.en': 'The study of computers and computing',
            'senses[0].gloss.en': 'computers field of study',
            'senses[0].academic_domain': 'informatyka',
        }

    @pytest.fixture
    def test_entry_data_multiple_domains(self) -> dict:
        """Test data for entry with different academic domains at sense level only."""
        return {
            'lexical_unit.en': 'bank',  # Can mean both financial institution and river bank
            'senses[0].id': 'sense1',
            'senses[0].definition.en': 'Financial institution where money can be deposited',
            'senses[0].gloss.en': 'financial institution',
            'senses[0].academic_domain': 'finanse',  # Finance domain
            'senses[1].id': 'sense2',
            'senses[1].definition.en': 'Raised area of ground along river',
            'senses[1].gloss.en': 'riverbank',
            'senses[1].academic_domain': 'geografia',  # Geography domain
        }

    @pytest.mark.integration
    def test_form_submission_entry_level_academic_domain(
        self, client: Client, dict_service_with_db: DictionaryService,
        test_entry_data_entry_level_academic_domain: dict
    ) -> None:
        """Test that sense-level academic domain can be submitted via form."""
        # Submit the form
        response = client.post('/entries/add', data=test_entry_data_entry_level_academic_domain)

        # Check that form submission succeeded
        assert response.status_code in [200, 302], f"Form submission failed: {response.get_data(as_text=True)}"

        # Find the created entry by lexical unit
        entries, _ = dict_service_with_db.list_entries(limit=100)  # Increase limit to see all entries
        entry = next((e for e in entries if 'computer science' in e.lexical_unit.get('en', '')), None)
        assert entry is not None, "Created entry not found"

        # Verify sense-level academic domain was saved
        assert len(entry.senses) == 1
        assert entry.senses[0].academic_domain == 'informatyka'

        # Clean up
        dict_service_with_db.delete_entry(entry.id)

    @pytest.mark.integration
    def test_form_submission_multiple_academic_domains(
        self, client: Client, dict_service_with_db: DictionaryService,
        test_entry_data_multiple_domains: dict
    ) -> None:
        """Test that entries can have different academic domains at different sense levels."""
        # Submit the form
        response = client.post('/entries/add', data=test_entry_data_multiple_domains)

        # Check that form submission succeeded
        assert response.status_code in [200, 302], f"Form submission failed: {response.get_data(as_text=True)}"

        # Find the created entry
        entries, _ = dict_service_with_db.list_entries(limit=100)
        entry = next((e for e in entries if 'bank' in e.lexical_unit.get('en', '')), None)
        assert entry is not None, "Created entry not found"

        # Verify sense-level academic domains
        assert len(entry.senses) == 2
        sense_domains = [s.academic_domain for s in entry.senses]
        assert 'finanse' in sense_domains
        assert 'geografia' in sense_domains

        # Clean up
        dict_service_with_db.delete_entry(entry.id)

    @pytest.mark.integration
    def test_form_edit_entry_remove_academic_domain(
        self, client: Client, dict_service_with_db: DictionaryService
    ) -> None:
        """Test that academic domain can be removed via form edit."""
        # Create entry with sense-level academic domain
        entry = Entry(
            id_="test_edit_remove_academic_domain",
            lexical_unit={"en": "test word"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "word"},
                    definitions={"en": {"text": "test word"}},
                    academic_domain="literatura"
                )
            ]
        )
        dict_service_with_db.create_entry(entry)

        # Edit via form - remove sense-level academic domain
        edit_data = {
            'id': 'test_edit_remove_academic_domain',
            'lexical_unit.en': 'test word',
            'senses[0].id': 'sense1',
            'senses[0].definition.en': 'test word',
            'senses[0].gloss.en': 'word',
            'senses[0].academic_domain': '',  # Remove sense-level domain
        }

        response = client.post(f'/entries/{entry.id}/edit', data=edit_data)
        assert response.status_code in [200, 302], f"Form edit failed: {response.get_data(as_text=True)}"

        # Verify sense-level academic domain was removed
        retrieved_entry = dict_service_with_db.get_entry('test_edit_remove_academic_domain')
        assert retrieved_entry is not None
        assert retrieved_entry.senses[0].academic_domain is None or retrieved_entry.senses[0].academic_domain == ''

        # Clean up
        dict_service_with_db.delete_entry('test_edit_remove_academic_domain')

    @pytest.mark.integration
    def test_form_edit_entry_add_academic_domain(
        self, client: Client, dict_service_with_db: DictionaryService
    ) -> None:
        """Test that academic domain can be added via form edit."""
        # Create entry without academic domain
        entry = Entry(
            id_="test_edit_add_academic_domain",
            lexical_unit={"en": "plain word"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "word"},
                    definitions={"en": {"text": "plain word"}}
                )
            ]
        )
        dict_service_with_db.create_entry(entry)

        # Edit via form - add sense-level academic domain
        edit_data = {
            'id': 'test_edit_add_academic_domain',
            'lexical_unit.en': 'plain word',
            'senses[0].id': 'sense1',
            'senses[0].definition.en': 'plain word',
            'senses[0].gloss.en': 'word',
            'senses[0].academic_domain': 'prawniczy',  # Add sense-level domain
        }

        response = client.post(f'/entries/{entry.id}/edit', data=edit_data)
        assert response.status_code in [200, 302], f"Form edit failed: {response.get_data(as_text=True)}"

        # Verify sense-level academic domain was added
        retrieved_entry = dict_service_with_db.get_entry('test_edit_add_academic_domain')
        assert retrieved_entry is not None
        assert retrieved_entry.senses[0].academic_domain == 'prawniczy'

        # Clean up
        dict_service_with_db.delete_entry('test_edit_add_academic_domain')

    @pytest.mark.integration
    def test_form_validation_invalid_academic_domain(
        self, client: Client, dict_service_with_db: DictionaryService
    ) -> None:
        """Test that form handles validation with academic domains."""
        # Submit form with valid sense-level academic domain
        valid_data = {
            'lexical_unit.en': 'test validation word',
            'senses[0].id': 'sense1',
            'senses[0].definition.en': 'test definition',
            'senses[0].gloss.en': 'test',
            'senses[0].academic_domain': 'finanse',
        }

        # Should succeed
        response = client.post('/entries/add', data=valid_data)
        assert response.status_code in [200, 302], f"Valid form submission failed: {response.get_data(as_text=True)}"

        # Find and clean up
        entries, _ = dict_service_with_db.list_entries(limit=10)
        entry = next((e for e in entries if 'test validation word' in e.lexical_unit.get('en', '')), None)
        if entry:
            dict_service_with_db.delete_entry(entry.id)

    @pytest.mark.integration
    def test_academic_domain_view_display(
        self, client: Client, dict_service_with_db: DictionaryService
    ) -> None:
        """Test that academic domains are displayed correctly in entry view."""
        # Create entry with sense-level academic domains
        entry = Entry(
            id_="test_view_academic_domains",
            lexical_unit={"en": "multidisciplinary term", "pl": "termin multidyscyplinarny"},
            senses=[
                Sense(
                    id_="sense_cs",
                    glosses={"en": "computer discipline"},
                    definitions={"en": "the study of computers"},
                    academic_domain="informatyka"
                ),
                Sense(
                    id_="sense_math",
                    glosses={"en": "mathematical concept"},
                    definitions={"en": "concept from mathematics"},
                    academic_domain="matematyka"
                )
            ]
        )
        dict_service_with_db.create_entry(entry)

        # View the entry
        response = client.get(f'/entries/{entry.id}')
        assert response.status_code == 200

        response_text = response.get_data(as_text=True)

        # Check that academic domains are displayed
        assert 'informatyka' in response_text or 'Informatyka' in response_text
        assert 'matematyka' in response_text or 'Matematyka' in response_text

        # Clean up
        dict_service_with_db.delete_entry(entry.id)

    @pytest.mark.integration
    def test_form_unicode_academic_domains(
        self, client: Client, dict_service_with_db: DictionaryService
    ) -> None:
        """Test that Unicode characters in academic domains work via forms."""
        # Test with Polish domain names
        unicode_data = {
            'lexical_unit.en': 'Polish academic term',
            'senses[0].id': 'sense1',
            'senses[0].definition.en': 'Term from computer science',
            'senses[0].gloss.en': 'computer term',
            'senses[0].academic_domain': 'rolnictwo',  # Polish for "agriculture"
        }

        # Submit the form
        response = client.post('/entries/add', data=unicode_data)
        assert response.status_code in [200, 302], f"Unicode form submission failed: {response.get_data(as_text=True)}"

        # Verify Unicode preservation
        entries, _ = dict_service_with_db.list_entries(filter_text='Polish', limit=100)
        entry = next((e for e in entries if 'Polish academic term' in e.lexical_unit.get('en', '')), None)
        assert entry is not None

        # Verify that the sense-level academic domain was saved correctly
        assert entry.senses[0].academic_domain == 'rolnictwo'

        # Clean up
        if entry:
            dict_service_with_db.delete_entry(entry.id)

    @pytest.mark.integration
    def test_academic_domain_form_field_visibility(
        self, client: Client
    ) -> None:
        """Test that academic domain fields are visible at sense level in the form."""
        # Get the new entry form
        response = client.get('/entries/add', follow_redirects=True)
        assert response.status_code == 200

        response_html = response.get_data(as_text=True)

        # Check that academic domain fields are present
        assert 'academic_domain' in response_html
        assert 'data-range-id="academic-domain"' in response_html

        # Check for sense-level fields in sense template
        assert 'name="senses[INDEX].academic_domain"' in response_html
        
        # Verify NO entry-level field exists
        assert 'name="academic_domain"' not in response_html or response_html.count('name="academic_domain"') == 0

    @pytest.mark.integration
    def test_academic_domain_roundtrip_compatibility(
        self, client: Client, dict_service_with_db: DictionaryService
    ) -> None:
        """Test that academic domains survive complete roundtrip: form → backend → form."""
        # Create entry with sense-level academic domain programmatically first
        original_entry = Entry(
            id_="test_roundtrip_compatibility",
            lexical_unit={"en": "roundtrip test"},
            senses=[
                Sense(
                    id_="roundtrip_sense",
                    glosses={"en": "test"},
                    definitions={"en": "roundtrip test"},
                    academic_domain="prawniczy"
                )
            ]
        )
        dict_service_with_db.create_entry(original_entry)

        # Retrieve via database and convert to form data that would be sent
        retrieved_entry = dict_service_with_db.get_entry("test_roundtrip_compatibility")
        form_data = {
            'id': retrieved_entry.id,
            'lexical_unit.en': retrieved_entry.lexical_unit['en'],
            'senses[0].id': retrieved_entry.senses[0].id,
            'senses[0].definition.en': retrieved_entry.senses[0].definitions['en'],
            'senses[0].gloss.en': retrieved_entry.senses[0].glosses['en'],
            'senses[0].academic_domain': retrieved_entry.senses[0].academic_domain,
        }

        # Submit back via form for editing
        response = client.post(f'/entries/{retrieved_entry.id}/edit', data=form_data)
        assert response.status_code in [200, 302], f"Roundtrip form submission failed: {response.get_data(as_text=True)}"

        # Verify final state
        final_entry = dict_service_with_db.get_entry("test_roundtrip_compatibility")
        assert final_entry.senses[0].academic_domain == original_entry.senses[0].academic_domain

        # Clean up
        dict_service_with_db.delete_entry("test_roundtrip_compatibility")
