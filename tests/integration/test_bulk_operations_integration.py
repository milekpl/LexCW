"""
Integration tests for bulk operations API endpoints.

Tests the full bulk operations flow with real services and test fixtures,
verifying operation_id, summary, and results structure.

Note: These tests require a specific database configuration that allows
the DictionaryService to connect to the test database. Some tests are skipped
when running in test mode due to safety features that prevent connections
to non-isolated databases.
"""

from __future__ import annotations

import pytest
import json
import logging
import uuid

logger = logging.getLogger(__name__)


def _create_entry_via_api(client, entry_id, lexical_unit, grammatical_info=None, traits=None, sense_gloss=None):
    """Create an entry through the XML API."""
    # Build XML for the entry
    traits_xml = ""
    if traits:
        for trait_name, trait_value in traits.items():
            traits_xml += f'<trait name="{trait_name}" value="{trait_value}" />\n'

    sense_xml = ""
    if sense_gloss:
        sense_xml = f'''
        <sense id="{entry_id}_sense">
            <gloss lang="en"><text>{sense_gloss}</text></gloss>
        </sense>
'''

    # Include grammatical-info as a trait for consistency
    if grammatical_info:
        traits_xml += f'<trait name="part-of-speech" value="{grammatical_info}" />\n'

    entry_xml = f'''<entry id="{entry_id}">
    <lexical-unit>
        <form lang="en"><text>{lexical_unit}</text></form>
    </lexical-unit>
    {traits_xml}
    {sense_xml}
</entry>'''

    response = client.post('/api/xml/entries', data=entry_xml, content_type='application/xml')
    return response.status_code == 201


def _delete_entry_via_api(client, entry_id):
    """Delete an entry through the API."""
    response = client.delete(f'/api/xml/entries/{entry_id}')
    return response.status_code in [200, 204, 404]


def _check_dictionary_service_available(client):
    """Check if DictionaryService can connect to the database."""
    from flask import current_app
    try:
        svc = current_app.injector.get('dictionary_service')
        # Try a simple operation to verify connectivity
        return True
    except Exception:
        return False


@pytest.mark.integration
class TestBulkOperationsIntegration:
    """Integration tests for bulk operations API endpoints."""

    # Test entry IDs to use and cleanup
    BULK_TEST_ENTRY_IDS = [
        "bulk_trait_test_1",
        "bulk_trait_test_2",
        "bulk_trait_test_3",
        "bulk_pos_test_1",
        "bulk_pos_test_2",
        "bulk_pos_test_3",
    ]

    @pytest.fixture(autouse=True)
    def setup_bulk_test_data(self, client):
        """Initialize service and seed data for each bulk operation test."""
        self._cleanup_test_entries(client)
        self._create_test_entries(client)
        yield
        # Cleanup: remove test entries after each test
        self._cleanup_test_entries(client)

    def _create_test_entries(self, client) -> None:
        """Create test entries for bulk operations testing."""

        # Create entries with traits for trait conversion testing
        for i in range(1, 4):
            entry_id = f"bulk_trait_test_{i}"
            grammatical_info = "verb" if i % 2 == 0 else "noun"
            traits = {"part-of-speech": grammatical_info, "morph-type": "stem"}
            success = _create_entry_via_api(
                client,
                entry_id=entry_id,
                lexical_unit=f"trait_test_word_{i}",
                grammatical_info=grammatical_info,
                traits=traits,
                sense_gloss=f"Test sense {i}"
            )
            if success:
                logger.info(f"Created test entry: {entry_id}")
            else:
                logger.warning(f"Failed to create test entry: {entry_id}")

        # Create entries for POS update testing
        for i in range(1, 4):
            entry_id = f"bulk_pos_test_{i}"
            success = _create_entry_via_api(
                client,
                entry_id=entry_id,
                lexical_unit=f"pos_test_word_{i}",
                grammatical_info="noun",
                traits={"morph-type": "stem"},
                sense_gloss=f"POS test sense {i}"
            )
            if success:
                logger.info(f"Created test entry: {entry_id}")
            else:
                logger.warning(f"Failed to create test entry: {entry_id}")

    def _cleanup_test_entries(self, client) -> None:
        """Remove test entries after tests."""
        for entry_id in self.BULK_TEST_ENTRY_IDS:
            try:
                _delete_entry_via_api(client, entry_id)
            except Exception as e:
                logger.warning(f"Failed to cleanup entry {entry_id}: {e}")

    @pytest.mark.integration
    def test_bulk_trait_conversion_api(self, client):
        """Test bulk trait conversion API endpoint with real entries."""
        entry_ids = ["bulk_trait_test_1", "bulk_trait_test_2", "bulk_trait_test_3"]

        response = client.post(
            '/api/bulk/traits/convert',
            data=json.dumps({
                'entry_ids': entry_ids,
                'from_trait': 'part-of-speech',
                'to_trait': 'adjective'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify operation_id structure
        assert 'operation_id' in data
        assert data['operation_id'].startswith('op-')
        assert len(data['operation_id']) > 10  # op-YYYYMMDD-N format

        # Verify summary structure
        assert 'summary' in data
        assert 'requested' in data['summary']
        assert 'success' in data['summary']
        assert 'failed' in data['summary']
        assert data['summary']['requested'] == len(entry_ids)

        # Verify results structure
        assert 'results' in data
        assert len(data['results']) == len(entry_ids)

        # Verify each result has required fields
        for result in data['results']:
            assert 'id' in result
            assert 'status' in result
            assert result['id'] in entry_ids
            assert result['status'] in ['success', 'error']

        logger.info(f"Bulk trait conversion test passed: {data['summary']}")

    @pytest.mark.integration
    def test_bulk_pos_update_api(self, client):
        """Test bulk POS update API endpoint with real entries."""
        entry_ids = ["bulk_pos_test_1", "bulk_pos_test_2", "bulk_pos_test_3"]

        response = client.post(
            '/api/bulk/pos/update',
            data=json.dumps({
                'entry_ids': entry_ids,
                'pos_tag': 'verb'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify operation_id structure
        assert 'operation_id' in data
        assert data['operation_id'].startswith('op-')

        # Verify summary structure
        assert 'summary' in data
        assert data['summary']['requested'] == len(entry_ids)

        # Verify results structure
        assert 'results' in data
        assert len(data['results']) == len(entry_ids)

        # Verify successful updates
        successful_results = [r for r in data['results'] if r['status'] == 'success']
        assert len(successful_results) == len(entry_ids)

        logger.info(f"Bulk POS update test passed: {data['summary']}")

    @pytest.mark.integration
    def test_bulk_trait_conversion_partial_success(self, client):
        """Test bulk trait conversion with partial success (mixed valid/invalid entry IDs."""
        # Mix of existing and non-existing entry IDs
        entry_ids = [
            "bulk_trait_test_1",  # Existing
            "nonexistent_entry_xyz",  # Non-existing
            "bulk_trait_test_2",  # Existing
        ]

        response = client.post(
            '/api/bulk/traits/convert',
            data=json.dumps({
                'entry_ids': entry_ids,
                'from_trait': 'part-of-speech',
                'to_trait': 'adverb'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify summary shows partial success
        assert data['summary']['requested'] == 3
        assert data['summary']['success'] == 2
        assert data['summary']['failed'] == 1

        # Verify results contain both success and error entries
        result_ids = [r['id'] for r in data['results']]
        assert "bulk_trait_test_1" in result_ids
        assert "nonexistent_entry_xyz" in result_ids
        assert "bulk_trait_test_2" in result_ids

        # Find the error result
        error_result = next((r for r in data['results'] if r['status'] == 'error'), None)
        assert error_result is not None
        assert 'error' in error_result

        logger.info(f"Partial success test passed: {data['summary']}")

    @pytest.mark.integration
    def test_bulk_pos_update_partial_success(self, client):
        """Test bulk POS update with partial success."""
        # Mix of existing and non-existing entry IDs
        entry_ids = [
            "bulk_pos_test_1",  # Existing
            "fake_entry_id_123",  # Non-existing
            "bulk_pos_test_2",  # Existing
        ]

        response = client.post(
            '/api/bulk/pos/update',
            data=json.dumps({
                'entry_ids': entry_ids,
                'pos_tag': 'adjective'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify summary shows partial success
        assert data['summary']['requested'] == 3
        assert data['summary']['success'] == 2
        assert data['summary']['failed'] == 1

        # Verify operation_id format
        assert 'operation_id' in data
        assert data['operation_id'].startswith('op-')

        logger.info(f"POS partial success test passed: {data['summary']}")

    @pytest.mark.integration
    def test_bulk_trait_conversion_response_format(self, client):
        """Test that bulk trait conversion returns correct response format."""
        entry_ids = ["bulk_trait_test_1"]

        response = client.post(
            '/api/bulk/traits/convert',
            data=json.dumps({
                'entry_ids': entry_ids,
                'from_trait': 'part-of-speech',
                'to_trait': 'interjection'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify complete response structure
        assert set(data.keys()) == {'operation_id', 'summary', 'results'}

        # Verify summary keys
        assert set(data['summary'].keys()) == {'requested', 'success', 'failed'}

        # Verify result structure for success case
        assert len(data['results']) == 1
        result = data['results'][0]
        assert set(result.keys()) == {'id', 'status', 'data'}
        assert result['status'] == 'success'
        assert 'traits' in result['data']

    @pytest.mark.integration
    def test_bulk_pos_update_response_format(self, client):
        """Test that bulk POS update returns correct response format."""
        entry_ids = ["bulk_pos_test_1", "bulk_pos_test_2"]

        response = client.post(
            '/api/bulk/pos/update',
            data=json.dumps({
                'entry_ids': entry_ids,
                'pos_tag': 'noun'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify complete response structure
        assert set(data.keys()) == {'operation_id', 'summary', 'results'}

        # Verify summary keys
        assert set(data['summary'].keys()) == {'requested', 'success', 'failed'}

        # Verify all results have expected structure
        for result in data['results']:
            assert 'id' in result
            assert 'status' in result
            assert result['status'] in ['success', 'error']
            if result['status'] == 'success':
                assert 'data' in result
                assert 'grammatical_info' in result['data']

    @pytest.mark.integration
    def test_bulk_operations_validation_missing_fields(self, client):
        """Test bulk operations return 400 for missing required fields."""
        # Missing from_trait
        response = client.post(
            '/api/bulk/traits/convert',
            data=json.dumps({
                'entry_ids': ['bulk_trait_test_1'],
                'to_trait': 'noun'
                # missing 'from_trait'
            }),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

        # Missing to_trait
        response = client.post(
            '/api/bulk/traits/convert',
            data=json.dumps({
                'entry_ids': ['bulk_trait_test_1'],
                'from_trait': 'verb'
                # missing 'to_trait'
            }),
            content_type='application/json'
        )
        assert response.status_code == 400

        # Missing pos_tag
        response = client.post(
            '/api/bulk/pos/update',
            data=json.dumps({
                'entry_ids': ['bulk_pos_test_1']
                # missing 'pos_tag'
            }),
            content_type='application/json'
        )
        assert response.status_code == 400

    @pytest.mark.integration
    def test_bulk_operations_empty_entry_ids(self, client):
        """Test bulk operations return 400 for empty entry_ids."""
        response = client.post(
            '/api/bulk/traits/convert',
            data=json.dumps({
                'entry_ids': [],
                'from_trait': 'verb',
                'to_trait': 'noun'
            }),
            content_type='application/json'
        )
        assert response.status_code == 400

        response = client.post(
            '/api/bulk/pos/update',
            data=json.dumps({
                'entry_ids': [],
                'pos_tag': 'verb'
            }),
            content_type='application/json'
        )
        assert response.status_code == 400

    @pytest.mark.integration
    def test_bulk_operations_no_json(self, client):
        """Test bulk operations return 400 when no JSON data is provided."""
        response = client.post(
            '/api/bulk/traits/convert',
            content_type='application/json'
        )
        assert response.status_code == 400

        response = client.post(
            '/api/bulk/pos/update',
            content_type='application/json'
        )
        assert response.status_code == 400


@pytest.mark.integration
class TestBulkOperationsServiceIntegration:
    """Integration tests for BulkOperationsService with real database.

    Note: These tests use the XML API to create/delete entries to ensure
    consistency with the API-level tests.
    """

    SERVICE_TEST_ENTRY_IDS = [
        "service_trait_1",
        "service_trait_2",
        "service_pos_1",
        "service_pos_2",
    ]

    @pytest.fixture(autouse=True)
    def setup_service_test_data(self, client):
        """Initialize service and seed data for service integration tests."""
        self._cleanup_test_entries(client)
        self._create_test_entries(client)
        yield
        self._cleanup_test_entries(client)

    def _create_test_entries(self, client) -> None:
        """Create test entries for service integration testing."""

        # Create entries for trait conversion testing
        for i in range(1, 3):
            entry_id = f"service_trait_{i}"
            success = _create_entry_via_api(
                client,
                entry_id=entry_id,
                lexical_unit=f"service_trait_word_{i}",
                grammatical_info=None,
                traits={"grammatical-category": "verb", "morph-type": "stem"},
                sense_gloss=f"Service trait sense {i}"
            )
            if success:
                logger.info(f"Created service test entry: {entry_id}")

        # Create entries for POS update testing
        for i in range(1, 3):
            entry_id = f"service_pos_{i}"
            success = _create_entry_via_api(
                client,
                entry_id=entry_id,
                lexical_unit=f"service_pos_word_{i}",
                grammatical_info="adjective",
                traits={"morph-type": "stem"},
                sense_gloss=f"Service POS sense {i}"
            )
            if success:
                logger.info(f"Created service test entry: {entry_id}")

    def _cleanup_test_entries(self, client) -> None:
        """Remove test entries after tests."""
        for entry_id in self.SERVICE_TEST_ENTRY_IDS:
            try:
                _delete_entry_via_api(client, entry_id)
            except Exception:
                pass

    @pytest.mark.integration
    def test_convert_traits_service_integration(self, client):
        """Test BulkOperationsService.convert_traits with real dictionary service."""
        from app.services.bulk_operations_service import BulkOperationsService
        from flask import current_app

        # Get service from Flask injector (same instance used by API)
        service = current_app.injector.get(BulkOperationsService)

        # Test trait conversion
        result = service.convert_traits(
            ["service_trait_1", "service_trait_2"],
            "grammatical-category",
            "noun"
        )

        # Verify result structure
        assert 'results' in result
        assert 'total' in result
        assert result['total'] == 2

        # Verify all entries processed successfully
        assert len(result['results']) == 2
        assert all(r['status'] == 'success' for r in result['results'])

    @pytest.mark.integration
    def test_update_pos_bulk_service_integration(self, client):
        """Test BulkOperationsService.update_pos_bulk with real dictionary service."""
        from app.services.bulk_operations_service import BulkOperationsService
        from flask import current_app

        service = current_app.injector.get(BulkOperationsService)

        # Test POS update
        result = service.update_pos_bulk(
            ["service_pos_1", "service_pos_2"],
            "verb"
        )

        # Verify result structure
        assert 'results' in result
        assert 'total' in result
        assert result['total'] == 2

        # Verify all entries processed successfully
        assert len(result['results']) == 2
        assert all(r['status'] == 'success' for r in result['results'])

    @pytest.mark.integration
    def test_convert_traits_service_partial_failure(self, client):
        """Test BulkOperationsService handles partial failures correctly."""
        from app.services.bulk_operations_service import BulkOperationsService
        from flask import current_app

        service = current_app.injector.get(BulkOperationsService)

        # Mix of existing and non-existing entries
        result = service.convert_traits(
            ["service_trait_1", "nonexistent_entry_xyz"],
            "grammatical-category",
            "preposition"
        )

        # Verify partial failure handling
        assert result['total'] == 2

        success_count = sum(1 for r in result['results'] if r['status'] == 'success')
        error_count = sum(1 for r in result['results'] if r['status'] == 'error')

        assert success_count == 1
        assert error_count == 1

        # Verify error result has error message
        error_result = next(r for r in result['results'] if r['status'] == 'error')
        assert 'error' in error_result

    @pytest.mark.integration
    def test_update_pos_bulk_service_partial_failure(self, client):
        """Test BulkOperationsService handles partial failures in POS update."""
        from app.services.bulk_operations_service import BulkOperationsService
        from flask import current_app

        service = current_app.injector.get(BulkOperationsService)

        # Mix of existing and non-existing entries
        result = service.update_pos_bulk(
            ["service_pos_1", "fake_entry_id_999"],
            "adverb"
        )

        # Verify partial failure handling
        assert result['total'] == 2

        success_count = sum(1 for r in result['results'] if r['status'] == 'success')
        error_count = sum(1 for r in result['results'] if r['status'] == 'error')

        assert success_count == 1
        assert error_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
