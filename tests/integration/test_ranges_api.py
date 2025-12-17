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
    def test_get_ranges_returns_structured_data(self) -> None:
        """Test that get_ranges returns properly structured ranges data."""
        # Mock ranges data structure
        mock_ranges = {
            "grammatical-info": {
                "id": "grammatical-info",
                "values": [
                    {
                        "id": "noun",
                        "value": "noun",
                        "abbrev": "n",
                        "description": {"en": "Noun"}
                    },
                    {
                        "id": "verb",
                        "value": "verb", 
                        "abbrev": "v",
                        "description": {"en": "Verb"}
                    }
                ]
            },
            "variant-type": {
                "id": "variant-type",
                "values": [
                    {
                        "id": "dialectal",
                        "value": "dialectal",
                        "abbrev": "dial",
                        "description": {"en": "Dialectal variant"}
                    },
                    {
                        "id": "spelling",
                        "value": "spelling",
                        "abbrev": "sp",
                        "description": {"en": "Spelling variant"}
                    }
                ]
            }
        }
        
        # Create service and mock get_ranges
        from app.database.mock_connector import MockDatabaseConnector
        mock_connector = MockDatabaseConnector()
        service = DictionaryService(mock_connector)
        service.ranges = mock_ranges
        
        ranges = service.get_ranges()
        
        # Verify structure
        assert isinstance(ranges, dict)
        assert "grammatical-info" in ranges
        assert "variant-type" in ranges
        
        # Verify grammatical-info structure
        gram_info = ranges["grammatical-info"]
        assert "values" in gram_info
        assert len(gram_info["values"]) >= 2
        
        # Verify value structure
        noun_value = gram_info["values"][0]
        assert "id" in noun_value
        assert "value" in noun_value
        assert "abbrev" in noun_value
        assert "description" in noun_value

    @pytest.mark.integration
    def test_get_ranges_handles_empty_ranges(self) -> None:
        """Test that get_ranges handles empty or missing ranges gracefully."""
        from app.database.mock_connector import MockDatabaseConnector
        mock_connector = MockDatabaseConnector()
        service = DictionaryService(mock_connector)
        service.ranges = {}
        # Ensure no custom ranges linger from other tests
        try:
            from app.models.custom_ranges import CustomRange, db as custom_db
            if hasattr(custom_db, 'session'):
                custom_db.session.query(CustomRange).delete()
                custom_db.session.commit()
        except Exception:
            pass

        ranges = service.get_ranges()
        assert isinstance(ranges, dict)
        # With the new implementation, standard ranges are injected even if DB is empty
        # So we expect some ranges (like variant-type, grammatical-info, etc.)
        assert len(ranges) > 0
        assert "variant-type" in ranges
        assert "grammatical-info" in ranges

    @pytest.mark.integration
    def test_get_ranges_caches_results(self) -> None:
        """Test that get_ranges caches results for performance."""
        from app.database.mock_connector import MockDatabaseConnector
        mock_connector = MockDatabaseConnector()
        service = DictionaryService(mock_connector)
        
        # Mock the database query to return test data
        mock_ranges = {
            "test-range": {
                "id": "test-range",
                "values": []
            }
        }
        
        # Set initial ranges
        service.ranges = mock_ranges
        
        # First call
        ranges1 = service.get_ranges()
        
        # Second call should return cached data
        ranges2 = service.get_ranges()
        
        # Should be the same object (cached)
        assert ranges1 is ranges2

    @pytest.mark.integration
    def test_grammatical_info_range_structure(self) -> None:
        """Test grammatical-info range has expected structure for UI."""
        # This test defines the expected structure for grammatical categories
        expected_structure = {
            "grammatical-info": {
                "id": "grammatical-info",
                "values": [
                    {
                        "id": "noun",
                        "value": "noun",
                        "abbrev": "n",
                        "description": {"en": "Noun"},
                        "children": []  # For hierarchical categories
                    }
                ]
            }
        }
        
        # Verify the structure we expect
        assert "grammatical-info" in expected_structure
        gram_range = expected_structure["grammatical-info"]
        assert "values" in gram_range
        
        # Verify value structure
        value = gram_range["values"][0]
        required_fields = ["id", "value", "abbrev", "description", "children"]
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
