from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

from app.models.entry import Entry
from app.models.sense import Sense


def test_list_entries_displays_definitions_correctly(client: FlaskClient) -> None:
    """
    Test that the /entries endpoint returns definitions as strings, not objects.
    """
    # 1. Arrange: Create a test entry object
    sense_obj = Sense.from_dict(
        {
            "id": "sense1",
            "definition": {"en": {"text": "A test definition."}},
            "gloss": {"en": {"text": "a test"}},
        }
    )

    entry_obj = Entry.from_dict(
        {"id": "test_entry_for_display", "lexical_unit": {"en": "test"}, "senses": [sense_obj]}
    )

    # 2. Arrange: Mock the dictionary service
    mock_dict_service = MagicMock()
    mock_dict_service.list_entries.return_value = ([entry_obj], 1)

    # Use patch to replace the service with our mock
    with patch("app.api.entries.get_dictionary_service", return_value=mock_dict_service):
        # 3. Act: Request the list of entries
        response = client.get("/api/entries/")

    # 4. Assert: Check the response
    assert response.status_code == 200
    response_data = response.get_json()

    entries = response_data.get("entries", [])
    assert len(entries) == 1

    test_entry_json = entries[0]
    assert test_entry_json is not None

    senses = test_entry_json.get("senses", [])
    assert len(senses) == 1

    sense = senses[0]
    assert "definition" in sense
    # This is the assertion that should fail
    assert isinstance(sense["definition"], str)
    assert sense["definition"] == "A test definition."