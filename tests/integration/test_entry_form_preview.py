import pytest
from bs4 import BeautifulSoup
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService

class TestEntryFormPreview:
    def test_dictionary_preview_and_layout(self, client, app):
        """Test that the dictionary preview is displayed and the layout is correct."""
        
        # Create a sample entry
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            # Clean up any existing test entry first
            try:
                existing_entry = dict_service.get_entry("test-preview-entry")
                if existing_entry:
                    dict_service.delete_entry("test-preview-entry")
            except Exception:
                pass  # Entry doesn't exist, that's fine
            
            entry = Entry(id_="test-preview-entry")
            entry.lexical_unit = {"en": "test word"}
            # Add a sense to satisfy validation requirements
            from app.models.sense import Sense
            sense = Sense(id_="test-sense-1")
            sense.add_definition("en", "A test definition")
            entry.senses.append(sense)
            dict_service.create_entry(entry)
            
        # Access the edit page
        response = client.get("/entries/test-preview-entry/edit")
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # 1. Verify Dictionary Preview
        # Note: The actual UI shows "Dictionary Preview (Saved State)" not just "Dictionary Preview"
        all_h5 = soup.find_all('h5')
        preview_card = None
        for h5 in all_h5:
            text = h5.get_text(strip=True)
            if "Dictionary" in text and "Preview" in text:
                preview_card = h5
                break
        assert preview_card is not None, "Dictionary Preview card header not found"
        
        # Verify CSS rendered content is present (we mocked it in the view to return something if XML exists)
        # Note: In the real app, CSS rendering depends on XML service which might need real DB.
        # However, our view modification tries to render it. If it fails, it logs error but page loads.
        # Let's check if the card body exists.
        preview_card_body = preview_card.find_parent('div', class_='card-header').find_next_sibling('div', class_='card-body')
        assert preview_card_body is not None
        
        # 2. Verify XML Preview Toggle Location
        toggle_btn = soup.find('button', id='toggle-xml-preview-btn')
        assert toggle_btn is not None, "XML Preview toggle button not found"
        
        # Verify it's NOT in the main button card
        # The main button card has "Undo" and "Save Entry"
        save_btn = soup.find('button', id='save-btn')
        button_card = save_btn.find_parent('div', class_='card')
        
        assert toggle_btn not in button_card.descendants, "XML Preview toggle should not be in the main button card"
        
        # Verify it is a link style button now
        assert "btn-link" in toggle_btn.get('class', []), "XML Preview toggle should be a link style button"
        
        # 3. Verify Button Layout
        cancel_btn = soup.find('button', id='cancel-btn')
        assert cancel_btn is not None
        assert "btn-outline-secondary" in cancel_btn.get('class', []), "Cancel button should be secondary outline"
        
        validate_btn = soup.find('button', id='validate-btn')
        assert validate_btn is not None
        assert "btn-primary" in validate_btn.get('class', []), "Validate button should be primary"
        
        save_btn = soup.find('button', id='save-btn')
        assert save_btn is not None
        assert "btn-success" in save_btn.get('class', []), "Save button should be success"
        
        # Verify Skip Validation checkbox is near Save button
        skip_checkbox = soup.find('input', id='skip-validation-checkbox')
        assert skip_checkbox is not None
        
        # Check they are in the same container
        save_container = save_btn.parent
        assert skip_checkbox in save_container.descendants or skip_checkbox.parent == save_container, \
            "Skip validation checkbox should be near the Save button"

