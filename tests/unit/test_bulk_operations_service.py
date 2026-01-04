"""
Unit tests for BulkOperationsService.
"""
import pytest
from unittest.mock import Mock, MagicMock
from app.services.bulk_operations_service import BulkOperationsService


class TestBulkOperationsService:
    """Test cases for BulkOperationsService."""

    def test_convert_traits(self):
        """BulkOperationsService should convert traits across entries."""
        mock_dict = Mock()
        mock_dict.get_entry.return_value = Mock(
            traits={'part-of-speech': 'verb'},
            lexical_unit={'en': 'test'}
        )
        mock_dict.update_entry.return_value = Mock(
            traits={'part-of-speech': 'phrasal-verb'},
            lexical_unit={'en': 'test'}
        )

        mock_history = Mock()
        mock_workset = Mock()

        service = BulkOperationsService(
            dictionary_service=mock_dict,
            workset_service=mock_workset,
            history_service=mock_history
        )

        result = service.convert_traits(['entry-1', 'entry-2'], 'part-of-speech', 'phrasal-verb')

        assert result['total'] == 2
        assert all(r['status'] == 'success' for r in result['results'])
        assert mock_history.record_operation.call_count == 2

    def test_convert_traits_without_history_service(self):
        """BulkOperationsService should work without history service."""
        mock_dict = Mock()
        mock_dict.get_entry.return_value = Mock(
            traits={'part-of-speech': 'verb'},
            lexical_unit={'en': 'test'}
        )
        mock_dict.update_entry.return_value = Mock(
            traits={'part-of-speech': 'phrasal-verb'},
            lexical_unit={'en': 'test'}
        )

        mock_workset = Mock()

        service = BulkOperationsService(
            dictionary_service=mock_dict,
            workset_service=mock_workset,
            history_service=None
        )

        result = service.convert_traits(['entry-1'], 'part-of-speech', 'phrasal-verb')

        assert result['total'] == 1
        assert result['results'][0]['status'] == 'success'

    def test_convert_traits_entry_not_found(self):
        """BulkOperationsService should handle missing entries."""
        mock_dict = Mock()
        mock_dict.get_entry.return_value = None
        mock_dict.update_entry.return_value = Mock()

        mock_history = Mock()
        mock_workset = Mock()

        service = BulkOperationsService(
            dictionary_service=mock_dict,
            workset_service=mock_workset,
            history_service=mock_history
        )

        result = service.convert_traits(['nonexistent-entry'], 'part-of-speech', 'verb')

        assert result['total'] == 1
        assert result['results'][0]['status'] == 'error'
        assert 'not found' in result['results'][0]['error'].lower()

    def test_convert_traits_handles_exception(self):
        """BulkOperationsService should handle exceptions gracefully."""
        mock_dict = Mock()
        mock_dict.get_entry.side_effect = Exception("Database error")

        mock_history = Mock()
        mock_workset = Mock()

        service = BulkOperationsService(
            dictionary_service=mock_dict,
            workset_service=mock_workset,
            history_service=mock_history
        )

        result = service.convert_traits(['entry-1'], 'part-of-speech', 'verb')

        assert result['total'] == 1
        assert result['results'][0]['status'] == 'error'
        assert 'Database error' in result['results'][0]['error']

    def test_update_pos_bulk(self):
        """BulkOperationsService should update POS across entries."""
        mock_dict = Mock()
        mock_dict.get_entry.return_value = Mock(
            grammatical_info='noun',
            lexical_unit={'en': 'test'}
        )
        mock_dict.update_entry.return_value = Mock(
            grammatical_info='verb',
            lexical_unit={'en': 'test'}
        )

        mock_history = Mock()
        mock_workset = Mock()

        service = BulkOperationsService(
            dictionary_service=mock_dict,
            workset_service=mock_workset,
            history_service=mock_history
        )

        result = service.update_pos_bulk(['entry-1', 'entry-2'], 'verb')

        assert result['total'] == 2
        assert all(r['status'] == 'success' for r in result['results'])
        assert mock_history.record_operation.call_count == 2

    def test_update_pos_bulk_without_history_service(self):
        """BulkOperationsService should update POS without history service."""
        mock_dict = Mock()
        mock_dict.get_entry.return_value = Mock(
            grammatical_info='noun',
            lexical_unit={'en': 'test'}
        )
        mock_dict.update_entry.return_value = Mock(
            grammatical_info='verb',
            lexical_unit={'en': 'test'}
        )

        mock_workset = Mock()

        service = BulkOperationsService(
            dictionary_service=mock_dict,
            workset_service=mock_workset,
            history_service=None
        )

        result = service.update_pos_bulk(['entry-1'], 'verb')

        assert result['total'] == 1
        assert result['results'][0]['status'] == 'success'

    def test_update_pos_bulk_entry_not_found(self):
        """BulkOperationsService should handle missing entries in POS update."""
        mock_dict = Mock()
        mock_dict.get_entry.return_value = None

        mock_history = Mock()
        mock_workset = Mock()

        service = BulkOperationsService(
            dictionary_service=mock_dict,
            workset_service=mock_workset,
            history_service=mock_history
        )

        result = service.update_pos_bulk(['nonexistent-entry'], 'verb')

        assert result['total'] == 1
        assert result['results'][0]['status'] == 'error'

    def test_update_pos_bulk_handles_exception(self):
        """BulkOperationsService should handle exceptions in POS update."""
        mock_dict = Mock()
        mock_dict.get_entry.side_effect = Exception("Connection failed")

        mock_history = Mock()
        mock_workset = Mock()

        service = BulkOperationsService(
            dictionary_service=mock_dict,
            workset_service=mock_workset,
            history_service=mock_history
        )

        result = service.update_pos_bulk(['entry-1'], 'verb')

        assert result['total'] == 1
        assert result['results'][0]['status'] == 'error'
        assert 'Connection failed' in result['results'][0]['error']

    def test_empty_entry_list(self):
        """BulkOperationsService should handle empty entry lists."""
        mock_dict = Mock()
        mock_history = Mock()
        mock_workset = Mock()

        service = BulkOperationsService(
            dictionary_service=mock_dict,
            workset_service=mock_workset,
            history_service=mock_history
        )

        convert_result = service.convert_traits([], 'part-of-speech', 'verb')
        pos_result = service.update_pos_bulk([], 'verb')

        assert convert_result['total'] == 0
        assert convert_result['results'] == []
        assert pos_result['total'] == 0
        assert pos_result['results'] == []
        mock_dict.get_entry.assert_not_called()
