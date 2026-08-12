"""
Unit tests for bulk operations API endpoints.
"""
import pytest
from unittest.mock import Mock, patch
from flask import Flask


class TestBulkOperationsAPI:
    """Tests for the bulk operations API blueprint."""

    def test_convert_traits_endpoint(self):
        """Bulk API should handle trait conversion requests."""
        from app.api.bulk_operations import bulk_bp

        app = Flask(__name__)
        app.register_blueprint(bulk_bp)

        mock_service = Mock()
        mock_service.convert_traits.return_value = {
            'results': [{'id': 'entry-1', 'status': 'success'}],
            'total': 1
        }

        with patch('app.api.bulk_operations.get_bulk_operations_service', return_value=mock_service):
            with app.test_client() as client:
                response = client.post('/bulk/traits/convert',
                    json={'entry_ids': ['entry-1'], 'from_trait': 'verb', 'to_trait': 'noun'},
                    content_type='application/json'
                )

                assert response.status_code == 200
                data = response.get_json()
                assert data['summary']['requested'] == 1
                assert 'operation_id' in data
                assert 'summary' in data
                assert 'results' in data

    def test_convert_traits_missing_fields(self, app):
        """Bulk API should return 400 when required fields are missing."""
        from app.api.bulk_operations import bulk_bp

        test_app = Flask(__name__)
        test_app.register_blueprint(bulk_bp)

        with test_app.test_client() as client:
            # Missing entry_ids
            response = client.post('/bulk/traits/convert',
                json={'from_trait': 'verb', 'to_trait': 'noun'},
                content_type='application/json'
            )
            assert response.status_code == 400

    def test_convert_traits_empty_entry_ids(self, app):
        """Bulk API should return 400 when entry_ids is empty."""
        from app.api.bulk_operations import bulk_bp

        test_app = Flask(__name__)
        test_app.register_blueprint(bulk_bp)

        with test_app.test_client() as client:
            response = client.post('/bulk/traits/convert',
                json={'entry_ids': [], 'from_trait': 'verb', 'to_trait': 'noun'},
                content_type='application/json'
            )
            assert response.status_code == 400

    def test_update_pos_bulk_endpoint(self):
        """Bulk API should handle POS update requests."""
        from app.api.bulk_operations import bulk_bp

        app = Flask(__name__)
        app.register_blueprint(bulk_bp)

        mock_service = Mock()
        mock_service.update_pos_bulk.return_value = {
            'results': [
                {'id': 'entry-1', 'status': 'success'},
                {'id': 'entry-2', 'status': 'success'}
            ],
            'total': 2
        }

        with patch('app.api.bulk_operations.get_bulk_operations_service', return_value=mock_service):
            with app.test_client() as client:
                response = client.post('/bulk/pos/update',
                    json={'entry_ids': ['entry-1', 'entry-2'], 'pos_tag': 'noun'},
                    content_type='application/json'
                )

                assert response.status_code == 200
                data = response.get_json()
                assert data['summary']['requested'] == 2
                assert 'operation_id' in data
                assert 'summary' in data
                assert 'results' in data

    def test_update_pos_bulk_missing_fields(self, app):
        """Bulk API should return 400 when POS update fields are missing."""
        from app.api.bulk_operations import bulk_bp

        test_app = Flask(__name__)
        test_app.register_blueprint(bulk_bp)

        with test_app.test_client() as client:
            # Missing pos_tag
            response = client.post('/bulk/pos/update',
                json={'entry_ids': ['entry-1']},
                content_type='application/json'
            )
            assert response.status_code == 400

    def test_convert_traits_returns_summary(self):
        """Bulk API should return a summary with success/failed counts."""
        from app.api.bulk_operations import bulk_bp

        app = Flask(__name__)
        app.register_blueprint(bulk_bp)

        mock_service = Mock()
        mock_service.convert_traits.return_value = {
            'results': [
                {'id': 'entry-1', 'status': 'success'},
                {'id': 'entry-2', 'status': 'error', 'error': 'Not found'}
            ],
            'total': 2
        }

        with patch('app.api.bulk_operations.get_bulk_operations_service', return_value=mock_service):
            with app.test_client() as client:
                response = client.post('/bulk/traits/convert',
                    json={'entry_ids': ['entry-1', 'entry-2'], 'from_trait': 'adj', 'to_trait': 'noun'},
                    content_type='application/json'
                )

                assert response.status_code == 200
                data = response.get_json()
                assert data['summary']['requested'] == 2
                assert data['summary']['success'] == 1
                assert data['summary']['failed'] == 1

    def test_convert_traits_no_json(self):
        """Bulk API should return 400 when no JSON data is provided."""
        from app.api.bulk_operations import bulk_bp

        app = Flask(__name__)
        app.register_blueprint(bulk_bp)

        with app.test_client() as client:
            response = client.post('/bulk/traits/convert',
                content_type='application/json'
            )

            assert response.status_code == 400

    def test_update_pos_bulk_no_json(self):
        """Bulk API should return 400 when no JSON data is provided for POS update."""
        from app.api.bulk_operations import bulk_bp

        app = Flask(__name__)
        app.register_blueprint(bulk_bp)

        with app.test_client() as client:
            response = client.post('/bulk/pos/update',
                content_type='application/json'
            )

            assert response.status_code == 400


# Pytest fixtures
@pytest.fixture
def app():
    """Create application for testing."""
    application = Flask(__name__)
    application.config['TESTING'] = True
    return application


class TestBulkExecuteConversionAndValidation:
    """/bulk/execute and /bulk/pipeline must convert dicts to BulkAction and validate.

    Regression: raw dicts were passed to execute_action (which requires a BulkAction
    object), so every real action errored with "'dict' object has no attribute
    'action'". Conversion + validate_action now gate the request.
    """

    def _app(self):
        from app.api.bulk_operations import bulk_bp

        app = Flask(__name__)
        app.register_blueprint(bulk_bp)
        return app

    def test_execute_rejects_invalid_range_value(self):
        from app.services.bulk_service import BulkAction  # noqa: F401

        mock_svc = Mock()
        mock_svc.validate_action.return_value = (
            False, ["Value 'adverb' not in allowed values for range 'part-of-speech'"]
        )

        with patch('app.api.bulk_operations.get_bulk_action_service', return_value=mock_svc), \
             patch('app.api.bulk_operations.get_bulk_query_service', return_value=Mock()), \
             patch('app.api.bulk_operations._snapshot_for_bulk_op', return_value='op-1'):
            with self._app().test_client() as client:
                resp = client.post('/bulk/execute', json={
                    'entry_ids': ['entry-1'],
                    'action': {
                        'type': 'set', 'field': 'grammatical_info.trait', 'value': 'adverb',
                        'ranges': {'range_id': 'part-of-speech'},
                    },
                })
                assert resp.status_code == 400
                assert 'not in allowed values for range' in resp.get_json()['error']
                mock_svc.execute_action.assert_not_called()

    def test_execute_converts_dict_to_bulkaction(self):
        from app.services.bulk_service import BulkAction

        mock_svc = Mock()
        mock_svc.validate_action.return_value = (True, [])
        mock_svc.execute_action.return_value = {'status': 'success', 'entry_id': 'entry-1'}

        with patch('app.api.bulk_operations.get_bulk_action_service', return_value=mock_svc), \
             patch('app.api.bulk_operations.get_bulk_query_service', return_value=Mock()), \
             patch('app.api.bulk_operations._snapshot_for_bulk_op', return_value='op-1'):
            with self._app().test_client() as client:
                resp = client.post('/bulk/execute', json={
                    'entry_ids': ['entry-1'],
                    'action': {'type': 'set', 'field': 'grammatical_info.trait', 'value': 'verb'},
                })
                assert resp.status_code == 200
                call = mock_svc.execute_action.call_args
                assert call is not None
                action = call.args[1]
                assert isinstance(action, BulkAction)  # converted, not the raw dict
                assert action.value == 'verb'

    def test_pipeline_validates_and_converts_steps(self):
        from app.services.bulk_service import BulkAction

        mock_svc = Mock()
        mock_svc.validate_action.return_value = (
            False, ["Value 'adverb' not in allowed values for range 'part-of-speech'"]
        )

        with patch('app.api.bulk_operations.get_bulk_action_service', return_value=mock_svc), \
             patch('app.api.bulk_operations.get_bulk_query_service', return_value=Mock()), \
             patch('app.api.bulk_operations._snapshot_for_bulk_op', return_value='op-1'):
            with self._app().test_client() as client:
                resp = client.post('/bulk/pipeline', json={
                    'entry_ids': ['entry-1'],
                    'steps': [{'type': 'set', 'field': 'grammatical_info.trait', 'value': 'adverb',
                               'ranges': {'range_id': 'part-of-speech'}}],
                })
                assert resp.status_code == 400
                assert 'Step 1 invalid' in resp.get_json()['error']
                mock_svc.execute_action.assert_not_called()

                mock_svc.validate_action.return_value = (True, [])
                mock_svc.execute_action.return_value = {'status': 'success', 'entry_id': 'entry-1'}
                resp2 = client.post('/bulk/pipeline', json={
                    'entry_ids': ['entry-1'],
                    'steps': [{'type': 'set', 'field': 'grammatical_info.trait', 'value': 'verb'}],
                })
                assert resp2.status_code == 200
                call = mock_svc.execute_action.call_args
                assert isinstance(call.args[1], BulkAction)
