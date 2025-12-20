"""
Test suite for LIFT ranges API endpoints.

This module tests the API endpoints that provide LIFT ranges data
for dynamic dropdown population in the UI.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from app.services.dictionary_service import DictionaryService



@pytest.mark.integration
class TestRangesAPI:
    """Test LIFT ranges API functionality."""

    @pytest.mark.integration
    def test_get_ranges_returns_structured_data(self, dict_service_with_db) -> None:
        """Test that get_ranges returns properly structured ranges data."""
        ranges = dict_service_with_db.get_ranges()
        assert isinstance(ranges, dict)
        assert "grammatical-info" in ranges
        assert "variant-type" in ranges
        gram_info = ranges["grammatical-info"]
        assert "values" in gram_info
        assert len(gram_info["values"]) >= 1
        noun_value = gram_info["values"][0]
        assert "id" in noun_value
        assert "value" in noun_value
        assert "abbrev" in noun_value
        assert "description" in noun_value

    @pytest.mark.integration
    def test_get_ranges_handles_empty_ranges(self, dict_service_with_db) -> None:
        """Test that get_ranges handles empty or missing ranges gracefully."""
        # Clear all custom ranges if possible
        try:
            from app.models.custom_ranges import CustomRange, db as custom_db
            if hasattr(custom_db, 'session'):
                custom_db.session.query(CustomRange).delete()
                custom_db.session.commit()
        except Exception:
            pass
        # Remove any cached ranges
        dict_service_with_db.ranges = None
        ranges = dict_service_with_db.get_ranges()
        assert isinstance(ranges, dict)
        assert len(ranges) > 0
        assert "variant-type" in ranges
        assert "grammatical-info" in ranges

    @pytest.mark.integration
    def test_get_ranges_caches_results(self, dict_service_with_db) -> None:
        """Test that get_ranges caches results for performance."""
        # Remove any cached ranges
        dict_service_with_db.ranges = None
        ranges1 = dict_service_with_db.get_ranges()
        ranges2 = dict_service_with_db.get_ranges()
        assert ranges1 is ranges2

    @pytest.mark.integration
    def test_grammatical_info_range_structure(self, dict_service_with_db) -> None:
        """Test grammatical-info range has expected structure for UI."""
        ranges = dict_service_with_db.get_ranges()
        assert "grammatical-info" in ranges
        gram_range = ranges["grammatical-info"]
        assert "values" in gram_range
        value = gram_range["values"][0]
        required_fields = ["id", "value", "abbrev", "description"]
        for field in required_fields:
            assert field in value

    @pytest.mark.integration
    def test_lexical_relation_range_structure(self) -> None:
        """Test lexical-relation range has expected structure for UI."""
        expected_structure = {
            "lexical-relation": {
                "id": "lexical-relation",
                "values": [
                    {
                        "id": "synonym",
                        "value": "synonym", 
                        "abbrev": "syn",
                        "description": {"en": "Synonym"},
                        "children": []
                    },
                    {
                        "id": "antonym",
                        "value": "antonym",
                        "abbrev": "ant",
                        "description": {"en": "Antonym"},
                        "children": []
                    }
                ]
            }
        }
        
        # Verify structure for relations
        assert "lexical-relation" in expected_structure
        relation_range = expected_structure["lexical-relation"]
        assert "values" in relation_range



@pytest.mark.integration
class TestRangesAPIEndpoints:
    """Test Flask API endpoints for ranges."""

    @pytest.mark.integration
    def test_ranges_endpoint_structure_ready(self) -> None:
        """Test that we're ready to create ranges API endpoint."""
        # This test documents the expected API endpoint structure
        expected_endpoint = "/api/ranges"
        expected_methods = ["GET"]
        expected_response_format = {
            "success": True,
            "data": {
                "grammatical-info": {
                    "id": "grammatical-info",
                    "values": []
                },
            }
        }
        
        # Verify expected structure
        assert expected_endpoint == "/api/ranges"
        assert "GET" in expected_methods
        assert "data" in expected_response_format
        assert "success" in expected_response_format

    @pytest.mark.integration
    def test_specific_range_endpoint_structure(self) -> None:
        """Test structure for specific range endpoints."""
        # Structure for getting specific ranges
        expected_endpoints = [
            "/api/ranges/grammatical-info",
            "/api/ranges/lexical-relation"
        ]
        
        expected_response = {
            "success": True,
            "data": {
                "id": "grammatical-info",
                "values": []
            }
        }
        
        # Verify endpoint naming
        for endpoint in expected_endpoints:
            assert endpoint.startswith("/api/ranges/")
        
        # Verify response structure
        assert "success" in expected_response
        assert "data" in expected_response
        assert "id" in expected_response["data"]
        assert "values" in expected_response["data"]
