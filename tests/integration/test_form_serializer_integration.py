"""
Integration Tests for Form Serializer

Tests the form serializer integration with the Flask app.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_serializer_integration_with_flask(client) -> None:
    """Test form serializer integration with Flask app."""
    # Test that the entry form page loads
    response = client.get('/entries/add')
    assert response.status_code == 200
    
    response_text = response.get_data(as_text=True)
    
    # Check that form-serializer.js is included
    assert 'form-serializer.js' in response_text, "Form serializer script should be included"
