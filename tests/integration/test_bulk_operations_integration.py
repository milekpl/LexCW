"""
Integration tests for bulk operations API endpoints.

Tests the full bulk operations flow with real services and test fixtures,
verifying operation_id, summary, and results structure.
"""

from __future__ import annotations

import pytest
import json
import logging

logger = logging.getLogger(__name__)


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
    def setup_bulk_test_data(self, dict_service_with_db: DictionaryService):
        """Initialize service and seed data for each bulk operation test."""
        self.dictionary_service = dict_service_with_db
        self._create_test_entries()
        yield
        # Cleanup: remove test entries after each test
        self._cleanup_test_entries()

    def _create_test_entries(self) -> None:
        """Create test entries for bulk operations testing."""
        # Import models locally to avoid circular imports
        from app.models.entry import Entry
        from app.models.sense import Sense

        # Clean up first in case previous test run failed
        self._cleanup_test_entries()

        # Create entries with traits for trait conversion testing
        for i in range(1, 4):
            entry = Entry(
                id_=f"bulk_trait_test_{i}",
                lexical_unit={"en": f"trait_test_word_{i}"},
                grammatical_info="verb" if i % 2 == 0 else "noun",
                traits={"part-of-speech": "verb" if i % 2 == 0 else "noun"},
            )
            entry.senses.append(Sense(id_=f"bulk_trait_sense_{i}", gloss={"en": f"Test sense {i}"}))
            self.dictionary_service.create_entry(entry)
            logger.info(f"Created test entry: bulk_trait_test_{i}")

        # Create entries for POS update testing
        for i in range(1, 4):
            entry = Entry(
                id_=f"bulk_pos_test_{i}",
                lexical_unit={"en": f"pos_test_word_{i}"},
                grammatical_info="noun",
            )
            entry.senses.append(Sense(id_=f"bulk_pos_sense_{i}", gloss={"en": f"POS test sense {i}"}))
            self.dictionary_service.create_entry(entry)
            logger.info(f"Created test entry: bulk_pos_test_{i}")

    def _cleanup_test_entries(self) -> None:
        """Remove test entries after tests."""
        for entry_id in self.BULK_TEST_ENTRY_IDS:
            try:
                if self.dictionary_service.entry_exists(entry_id):
                    self.dictionary_service.delete_entry(entry_id)
            except Exception as e:
                logger.warning(f"Failed to cleanup entry {entry_id}: {e}")

    @pytest.mark.integration
    def test_bulk_trait_conversion_api(self, client):
        """Test bulk trait conversion API endpoint with real entries."""
        entry_ids = ["bulk_trait_test_1", "bulk_trait_test_2", "bulk_trait_test_3"]

        response = client.post(
            '/bulk/traits/convert',
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
            '/bulk/pos/update',
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
            '/bulk/traits/convert',
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
            '/bulk/pos/update',
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
            '/bulk/traits/convert',
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
            '/bulk/pos/update',
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
            '/bulk/traits/convert',
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
            '/bulk/traits/convert',
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
            '/bulk/pos/update',
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
            '/bulk/traits/convert',
            data=json.dumps({
                'entry_ids': [],
                'from_trait': 'verb',
                'to_trait': 'noun'
            }),
            content_type='application/json'
        )
        assert response.status_code == 400

        response = client.post(
            '/bulk/pos/update',
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
            '/bulk/traits/convert',
            content_type='application/json'
        )
        assert response.status_code == 400

        response = client.post(
            '/bulk/pos/update',
            content_type='application/json'
        )
        assert response.status_code == 400


@pytest.mark.integration
class TestBulkOperationsServiceIntegration:
    """Integration tests for BulkOperationsService with real database."""

    SERVICE_TEST_ENTRY_IDS = [
        "service_trait_1",
        "service_trait_2",
        "service_pos_1",
        "service_pos_2",
    ]

    @pytest.fixture(autouse=True)
    def setup_service_test_data(self, dict_service_with_db: DictionaryService):
        """Initialize service and seed data for service integration tests."""
        self.dictionary_service = dict_service_with_db
        self._create_test_entries()
        yield
        self._cleanup_test_entries()

    def _create_test_entries(self) -> None:
        """Create test entries for service integration testing."""
        # Import models locally to avoid circular imports
        from app.models.entry import Entry
        from app.models.sense import Sense

        self._cleanup_test_entries()

        # Create entries for trait conversion testing
        for i in range(1, 3):
            entry = Entry(
                id_=f"service_trait_{i}",
                lexical_unit={"en": f"service_trait_word_{i}"},
                traits={"grammatical-category": "verb"},
            )
            entry.senses.append(Sense(id_=f"service_trait_sense_{i}", gloss={"en": f"Service trait sense {i}"}))
            self.dictionary_service.create_entry(entry)

        # Create entries for POS update testing
        for i in range(1, 3):
            entry = Entry(
                id_=f"service_pos_{i}",
                lexical_unit={"en": f"service_pos_word_{i}"},
                grammatical_info="adjective",
            )
            entry.senses.append(Sense(id_=f"service_pos_sense_{i}", gloss={"en": f"Service POS sense {i}"}))
            self.dictionary_service.create_entry(entry)

    def _cleanup_test_entries(self) -> None:
        """Remove test entries after tests."""
        for entry_id in self.SERVICE_TEST_ENTRY_IDS:
            try:
                if self.dictionary_service.entry_exists(entry_id):
                    self.dictionary_service.delete_entry(entry_id)
            except Exception:
                pass

    @pytest.mark.integration
    def test_convert_traits_service_integration(self):
        """Test BulkOperationsService.convert_traits with real dictionary service."""
        from app.services.bulk_operations_service import BulkOperationsService
        from unittest.mock import Mock

        # Create mock services with real dictionary service
        mock_workset = Mock()
        mock_history = Mock()

        service = BulkOperationsService(
            dictionary_service=self.dictionary_service,
            workset_service=mock_workset,
            history_service=mock_history
        )

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

        # Verify operation was recorded
        assert mock_history.record_operation.call_count == 2

    @pytest.mark.integration
    def test_update_pos_bulk_service_integration(self):
        """Test BulkOperationsService.update_pos_bulk with real dictionary service."""
        from app.services.bulk_operations_service import BulkOperationsService
        from unittest.mock import Mock

        mock_workset = Mock()
        mock_history = Mock()

        service = BulkOperationsService(
            dictionary_service=self.dictionary_service,
            workset_service=mock_workset,
            history_service=mock_history
        )

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

        # Verify operation was recorded
        assert mock_history.record_operation.call_count == 2

    @pytest.mark.integration
    def test_convert_traits_service_partial_failure(self):
        """Test BulkOperationsService handles partial failures correctly."""
        from app.services.bulk_operations_service import BulkOperationsService
        from unittest.mock import Mock

        mock_workset = Mock()
        mock_history = Mock()

        service = BulkOperationsService(
            dictionary_service=self.dictionary_service,
            workset_service=mock_workset,
            history_service=mock_history
        )

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
    def test_update_pos_bulk_service_partial_failure(self):
        """Test BulkOperationsService handles partial failures in POS update."""
        from app.services.bulk_operations_service import BulkOperationsService
        from unittest.mock import Mock

        mock_workset = Mock()
        mock_history = Mock()

        service = BulkOperationsService(
            dictionary_service=self.dictionary_service,
            workset_service=mock_workset,
            history_service=mock_history
        )

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
