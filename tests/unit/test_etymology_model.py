#!/usr/bin/env python3
"""
Unit tests for the Etymology data model.
"""

import pytest
from app.models.entry import Etymology


@pytest.mark.unit
class TestEtymologyModel:
    """Test the Etymology model's internal logic."""

    def test_etymology_model_creation(self):
        """Test that a basic Etymology object can be created correctly."""
        etymology = Etymology(
            type="borrowing",
            source="Latin",
            form={"lang": "la", "text": "pater"},
            gloss={"lang": "en", "text": "father"}
        )
        assert etymology.type == "borrowing"
        assert etymology.source == "Latin"
        assert etymology.form is not None
        assert etymology.gloss is not None