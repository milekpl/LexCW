"""
Unit test suite for Spreadsheet View & /bulk/batch-update endpoint.
"""
import json
import pytest
from unittest.mock import Mock, patch
from app.models.entry import Entry
from app.models.sense import Sense


class TestSpreadsheetViewAPI:
    """Test suite for /bulk/batch-update API endpoint."""

    def test_batch_update_missing_payload(self, client):
        response = client.post('/api/bulk/batch-update', data=json.dumps({}), content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_batch_update_empty_updates_list(self, client):
        response = client.post('/api/bulk/batch-update', data=json.dumps({'updates': []}), content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_batch_update_success(self, client, app):
        with app.app_context():
            mock_dict_service = Mock()

            dummy_entry = Entry(
                id="test-entry-1",
                lexical_unit={"en": "old word"},
                citation_form="old cf",
                grammatical_info={"part_of_speech": "noun"},
                pronunciations={"seh-fonipa": "old-ipa"},
                senses=[Sense(id="test-entry-1-s1", definitions={"en": "old def", "pl": "stary op"})]
            )

            mock_dict_service.get_entry.return_value = dummy_entry
            mock_dict_service.update_entry.return_value = True

            orig_get = app.injector.get
            def mock_get(cls):
                if cls.__name__ == 'DictionaryService':
                    return mock_dict_service
                return orig_get(cls)

            with patch.object(app.injector, 'get', side_effect=mock_get):
                payload = {
                    "updates": [
                        {
                            "id": "test-entry-1",
                            "changes": {
                                "lexical_unit": "new word",
                                "pos": "verb",
                                "citation_form": "new cf",
                                "pronunciation": "new-ipa",
                                "definition_en": "new def en",
                                "definition_pl": "nowy opis"
                            }
                        }
                    ]
                }

                response = client.post('/api/bulk/batch-update', data=json.dumps(payload), content_type='application/json')
                assert response.status_code == 200
                data = response.get_json()
                assert "summary" in data
                assert data["summary"]["success"] == 1
                assert data["summary"]["failed"] == 0
                assert mock_dict_service.update_entry.called

    def test_spreadsheet_route_renders(self, client):
        response = client.get('/workbench/spreadsheet')
        assert response.status_code == 200
        assert b'Spreadsheet Grid View' in response.data
        assert b'spreadsheet-table' in response.data

    def test_list_entries_parameter_aliases(self, client, app):
        with app.app_context():
            mock_dict_service = Mock()
            mock_dict_service.list_entries.return_value = ([], 0)

            orig_get = app.injector.get
            def mock_get(cls):
                if cls.__name__ == 'DictionaryService':
                    return mock_dict_service
                return orig_get(cls)

            with patch.object(app.injector, 'get', side_effect=mock_get):
                response = client.get('/api/entries?search=test&sort=lexical_unit&order=desc')
                assert response.status_code == 200
                assert mock_dict_service.list_entries.called
                _, kwargs = mock_dict_service.list_entries.call_args
                assert kwargs.get('filter_text') == 'test'
                assert kwargs.get('sort_by') == 'lexical_unit'
                assert kwargs.get('sort_order') == 'desc'

