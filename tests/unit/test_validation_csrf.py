"""
Unit test to verify API validation endpoints handle POST requests and CSRF cleanly.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient


def test_validation_batch_csrf_endpoint(client: FlaskClient) -> None:
    entries = [
        {
            "id": "e1",
            "lexical_unit": {"en": "test"},
            "senses": [{"id": "s1", "definition": {"en": "a test entry"}}],
        }
    ]
    response = client.post(
        "/api/validation/batch",
        json={"entries": entries, "priority_filter": "all"},
        headers={"Content-Type": "application/json", "X-CSRFToken": "test_token"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list) or isinstance(data, dict)
