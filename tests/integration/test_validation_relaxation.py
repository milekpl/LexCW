
import pytest
import json
from app import create_app
from app.services.dictionary_service import DictionaryService
from app.services.validation_engine import ValidationEngine
from app.models.entry import Entry

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def validation_engine():
    return ValidationEngine()

def test_get_ranges_crash(client):
    """
    Test that /api/ranges does not crash even if DB is empty/missing.
    This reproduces the 500 error caused by missing _get_default_ranges.
    """
    response = client.get('/api/ranges')
    # We expect 200 if fixed, or at least a handled 404/500 with proper error message, 
    # but definitely not a crash due to missing method.
    # Currently it returns 500 due to AttributeError.
    
    # If it returns 500, check if it's the specific AttributeError we expect?
    # For now, just asserting 200 is the goal of the fix.
    assert response.status_code == 200, f"Response was {response.status_code}: {response.json}"
    data = response.json
    assert data['success'] is True

def test_validation_allows_empty_source_definition(validation_engine):
    """
    Test that validation allows entries with ONLY target language definitions.
    Source language (English) definitions should be optional.
    """
    # Create entry data with only Polish (target) definition, no English (source) definition
    entry_data = {
        "id": "test_entry_pl_only",
        "lexical_unit": {"en": "test word"},  # English is the source language
        "senses": [
            {
                "id": "sense1",
                "definition": {
                    "pl": "test definition in Polish",
                    # No "en" definition here - this should be allowed
                }
            }
        ]
    }
    
    # Validate the entry
    result = validation_engine.validate_entry(entry_data)
    
    # Filter for R2.1.2 errors (sense must have definition/gloss/variant)
    r212_errors = [e for e in result.errors if e.rule_id == 'R2.1.2']
    
    # There should be NO R2.1.2 errors because we have a Polish definition
    assert len(r212_errors) == 0, f"Expected no R2.1.2 errors, but got: {[e.message for e in r212_errors]}"
    
def test_validation_rejects_empty_all_definitions(validation_engine):
    """
    Test that validation still rejects entries with NO definitions at all.
    """
    entry_data = {
        "id": "test_entry_no_def",
        "lexical_unit": {"en": "test word"},
        "senses": [
            {
                "id": "sense1",
                "definition": {
                    # Empty English definition is OK, but we need SOME non-source definition
                }
            }
        ]
    }
    
    result = validation_engine.validate_entry(entry_data)
    r212_errors = [e for e in result.errors if e.rule_id == 'R2.1.2']
    
    # There SHOULD be an R2.1.2 error because there's no definition at all
    assert len(r212_errors) > 0, "Expected R2.1.2 error for entry with no definitions"

def test_validation_allows_empty_source_with_gloss(validation_engine):
    """
    Test that validation allows entries with empty source definition but a gloss.
    """
    entry_data = {
        "id": "test_entry_gloss_only",
        "lexical_unit": {"en": "test word"},
        "senses": [
            {
                "id": "sense1",
                "definition": {},  # No definitions
                "gloss": {"pl": "test gloss"}  # But has a gloss
            }
        ]
    }
    
    result = validation_engine.validate_entry(entry_data)
    r212_errors = [e for e in result.errors if e.rule_id == 'R2.1.2']
    
    # No R2.1.2 error because gloss is present
    assert len(r212_errors) == 0, f"Expected no R2.1.2 errors with gloss, but got: {[e.message for e in r212_errors]}"
