"""
Service for atomic bulk operations on dictionary entries.

This module provides bulk operations for dictionary entries including:
- Trait conversion across multiple entries
- Part-of-speech bulk updates
- Operation history recording for undo/redo support
"""
import logging
from typing import List, Dict, Any, Optional
from app.services.dictionary_service import DictionaryService
from app.services.workset_service import WorksetService
from app.services.operation_history_service import OperationHistoryService
from app.utils.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class BulkOperationsService:
    """Service for atomic bulk operations on dictionary entries."""

    def __init__(self,
                 dictionary_service: DictionaryService,
                 workset_service: WorksetService,
                 history_service: Optional[OperationHistoryService] = None):
        """
        Initialize the BulkOperationsService.

        Args:
            dictionary_service: Service for dictionary entry operations.
            workset_service: Service for workset management.
            history_service: Optional service for recording operation history.
        """
        self.dictionary = dictionary_service
        self.workset = workset_service
        self.history = history_service

    def convert_traits(self, entry_ids: List[str], from_trait: str, to_trait: str) -> Dict[str, Any]:
        """
        Convert a trait value across multiple entries atomically.

        Args:
            entry_ids: List of entry IDs to modify.
            from_trait: Trait key to convert (e.g., 'part-of-speech').
            to_trait: New trait value to set.

        Returns:
            Dictionary containing:
                - 'results': List of result dicts for each entry
                - 'total': Total number of entries processed
        """
        results = []

        for entry_id in entry_ids:
            print(f"=== DEBUG: Processing entry_id={entry_id} ===")
            try:
                entry = self.dictionary.get_entry(entry_id)
                print(f"=== DEBUG: get_entry returned type={type(entry).__name__} for {entry_id} ===")
            except NotFoundError:
                print(f"=== DEBUG: NotFoundError for {entry_id} ===")
                results.append({
                    'id': entry_id,
                    'status': 'error',
                    'error': 'Entry not found'
                })
                continue

            print(f"=== DEBUG: entry={entry}, id(entry)={id(entry) if entry else None} ===")
            try:
                if entry:
                    old_value = entry.traits.get(from_trait)
                    # Apply trait conversion
                    entry.convert_trait(from_trait, old_value, to_trait)
                    self.dictionary.update_entry(entry)
                    # update_entry returns None but modifies entry in place
                    results.append({
                        'id': entry_id,
                        'status': 'success',
                        'data': {'traits': entry.traits}
                    })

                    # Record operation for undo/redo
                    if self.history:
                        self.history.record_operation(
                            operation_type='bulk_trait_conversion',
                            data={
                                'entry_id': entry_id,
                                'trait': from_trait,
                                'old_value': old_value,
                                'new_value': to_trait
                            },
                            entry_id=entry_id
                        )
                else:
                    results.append({
                        'id': entry_id,
                        'status': 'error',
                        'error': 'Entry not found'
                    })
            except Exception as e:
                logger.error(f"Error converting trait for entry {entry_id}: {e}")
                results.append({
                    'id': entry_id,
                    'status': 'error',
                    'error': str(e)
                })

        return {'results': results, 'total': len(results)}

    def update_pos_bulk(self, entry_ids: List[str], pos_tag: str) -> Dict[str, Any]:
        """
        Update part-of-speech tag across multiple entries.

        Args:
            entry_ids: List of entry IDs to modify.
            pos_tag: New POS tag (e.g., 'noun', 'verb').

        Returns:
            Dictionary containing:
                - 'results': List of result dicts for each entry
                - 'total': Total number of entries processed
        """
        results = []

        for entry_id in entry_ids:
            try:
                entry = self.dictionary.get_entry(entry_id)
            except NotFoundError:
                results.append({
                    'id': entry_id,
                    'status': 'error',
                    'error': 'Entry not found'
                })
                continue

            try:
                if entry:
                    old_pos = entry.grammatical_info
                    # Apply POS update
                    entry.update_grammatical_info(pos_tag)
                    self.dictionary.update_entry(entry)
                    # update_entry returns None but modifies entry in place
                    results.append({
                        'id': entry_id,
                        'status': 'success',
                        'data': {'grammatical_info': entry.grammatical_info}
                    })

                    # Record operation for undo/redo
                    if self.history:
                        self.history.record_operation(
                            operation_type='bulk_pos_update',
                            data={
                                'entry_id': entry_id,
                                'old_value': old_pos,
                                'new_value': pos_tag
                            },
                            entry_id=entry_id
                        )
                else:
                    results.append({
                        'id': entry_id,
                        'status': 'error',
                        'error': 'Entry not found'
                    })
            except Exception as e:
                logger.error(f"Error updating POS for entry {entry_id}: {e}")
                results.append({
                    'id': entry_id,
                    'status': 'error',
                    'error': str(e)
                })

        return {'results': results, 'total': len(results)}
