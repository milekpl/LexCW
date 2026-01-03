"""Bidirectional relation management service."""

from __future__ import annotations
import logging
from typing import Dict, List, Optional, Tuple, Union, Any

from app.database.basex_connector import BaseXConnector
from app.database.mock_connector import MockDatabaseConnector
from app.models.entry import Entry, Relation
from app.services.entry_service import EntryService
from app.services.database_utils import get_db_name
from app.utils.bidirectional_relations import (
    is_relation_bidirectional,
    get_reverse_relation_type
)


logger = logging.getLogger(__name__)


class BidirectionalService:
    """Service for managing bidirectional lexical relations."""

    def __init__(
        self,
        entry_service: EntryService,
        db_connector: Union[BaseXConnector, MockDatabaseConnector],
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the bidirectional service.

        Args:
            entry_service: Entry service for CRUD operations.
            db_connector: Database connector for querying.
            logger: Optional logger instance.
        """
        self.entry_service = entry_service
        self.db_connector = db_connector
        self.logger = logger or logging.getLogger(__name__)

    def handle_bidirectional_relations(
        self,
        entry: Entry,
        project_id: Optional[int] = None
    ) -> None:
        """Handle bidirectional relations by creating reverse relations for target entries.

        When an entry has a bidirectional relation (e.g., 'synonym'), this method
        creates the reverse relation in the target entry (e.g., if A is synonym of B,
        then B should also have A as synonym in its relations).

        Args:
            entry: The entry being updated that may contain bidirectional relations.
            project_id: Optional project ID for database resolution.
        """
        # Process entry-level relations
        for relation in entry.relations:
            rel_type = getattr(relation, 'type', relation.get('type', '') if isinstance(relation, dict) else '')
            rel_ref = getattr(relation, 'ref', relation.get('ref', '') if isinstance(relation, dict) else '')

            if is_relation_bidirectional(rel_type, self.entry_service):
                self._create_reverse_relation(entry, rel_type, rel_ref, project_id)

        # Process sense-level relations
        for sense_idx, sense in enumerate(entry.senses):
            if hasattr(sense, 'relations') and sense.relations:
                for relation in sense.relations:
                    rel_type = getattr(relation, 'type', relation.get('type', '') if isinstance(relation, dict) else '')
                    rel_ref = getattr(relation, 'ref', relation.get('ref', '') if isinstance(relation, dict) else '')

                    if is_relation_bidirectional(rel_type, self.entry_service):
                        self._create_sense_reverse_relation(entry, rel_type, rel_ref, project_id)

    def _create_reverse_relation(
        self,
        entry: Entry,
        rel_type: str,
        rel_ref: str,
        project_id: Optional[int] = None
    ) -> None:
        """Create reverse relation for entry-level relations.

        Args:
            entry: The source entry.
            rel_type: The relation type.
            rel_ref: The target entry ID.
            project_id: Optional project ID.
        """
        try:
            # Get the target entry that should receive the reverse relation
            target_entry = self.entry_service.get_entry(rel_ref, project_id=project_id)

            # Determine the reverse relation type
            reverse_rel_type = get_reverse_relation_type(rel_type, self.entry_service)

            # Check if the reverse relation already exists to avoid duplication
            reverse_relation_exists = False
            for target_rel in target_entry.relations:
                target_rel_type = getattr(target_rel, 'type', target_rel.get('type', '') if isinstance(target_rel, dict) else '')
                target_rel_ref = getattr(target_rel, 'ref', target_rel.get('ref', '') if isinstance(target_rel, dict) else '')
                if target_rel_type == reverse_rel_type and target_rel_ref == entry.id:
                    reverse_relation_exists = True
                    break

            # Add reverse relation if it doesn't already exist
            if not reverse_relation_exists:
                reverse_relation = Relation(type=reverse_rel_type, ref=entry.id)
                target_entry.relations.append(reverse_relation)

                # Save the target entry with the new reverse relation
                # Skip validation and skip bidirectional processing to avoid recursion
                self.entry_service.update_entry(
                    target_entry,
                    project_id=project_id,
                    skip_validation=True
                )

                self.logger.info(
                    "Added reverse relation '%s' from '%s' to '%s'",
                    reverse_rel_type, rel_ref, entry.id
                )

        except Exception as e:
            self.logger.warning(
                "Could not create reverse relation for type '%s' from '%s' to '%s': %s",
                rel_type, entry.id, rel_ref, str(e)
            )

    def _create_sense_reverse_relation(
        self,
        entry: Entry,
        rel_type: str,
        sense_ref: str,
        project_id: Optional[int] = None
    ) -> None:
        """Create reverse relation for sense-level relations.

        Args:
            entry: The source entry.
            rel_type: The relation type.
            sense_ref: The target sense ID.
            project_id: Optional project ID.
        """
        try:
            # For sense relations, the ref might be the target sense ID
            # We need to find which entry contains the target sense
            target_entry = self._find_entry_by_sense_id(sense_ref, project_id=project_id)

            if target_entry:
                # For sense-to-sense relations, we add it to the target entry as a general relation
                reverse_rel_type = get_reverse_relation_type(rel_type, self.entry_service)

                # Check if reverse relation already exists (avoid duplication)
                reverse_relation_exists = False
                for target_rel in target_entry.relations:
                    target_rel_type = getattr(target_rel, 'type', target_rel.get('type', '') if isinstance(target_rel, dict) else '')
                    target_rel_ref = getattr(target_rel, 'ref', target_rel.get('ref', '') if isinstance(target_rel, dict) else '')
                    if target_rel_type == reverse_rel_type and target_rel_ref == entry.id:
                        reverse_relation_exists = True
                        break

                if not reverse_relation_exists:
                    reverse_relation = Relation(type=reverse_rel_type, ref=entry.id)
                    target_entry.relations.append(reverse_relation)

                    # Save the target entry
                    self.entry_service.update_entry(
                        target_entry,
                        project_id=project_id,
                        skip_validation=True
                    )

                    self.logger.info(
                        "Added reverse sense relation '%s' to entry '%s' for sense relation from '%s'",
                        reverse_rel_type, target_entry.id, entry.id
                    )

        except Exception as e:
            self.logger.warning(
                "Could not create reverse sense relation for type '%s' from sense in '%s' to target '%s': %s",
                rel_type, entry.id, sense_ref, str(e)
            )

    def _find_entry_by_sense_id(
        self,
        sense_id: str,
        project_id: Optional[int] = None
    ) -> Optional[Entry]:
        """Find an entry that contains a specific sense ID.

        Args:
            sense_id: The ID of the sense to search for.
            project_id: Optional project ID for database resolution.

        Returns:
            Entry object that contains the specified sense, or None.
        """
        # First, try the direct approach - if sense_id is in expected format entry_id_sense_guid
        # The sense_id format in LIFT is often: entry_guid_sense_guid
        if '_' in sense_id:
            # Try to extract entry ID (first part before last underscore)
            parts = sense_id.rsplit('_', 1)
            potential_entry_id = parts[0]

            try:
                entry = self.entry_service.get_entry(potential_entry_id, project_id=project_id)

                # Verify the sense exists in this entry
                for sense in entry.senses:
                    if hasattr(sense, 'id') and sense.id == sense_id:
                        return entry
                    # Also check if the sense guid matches
                    if hasattr(sense, 'guid') and sense.guid == sense_id:
                        return entry

            except Exception:
                pass  # Fall through to search approach

        # If direct approach failed, search through all entries
        # This is expensive but necessary for some LIFT formats
        try:
            db_name = get_db_name(self.db_connector, project_id, self.logger)
            if not db_name:
                return None

            # Search for entries containing the sense ID
            from app.services.search_service import SearchService
            from app.services.xml_processing_service import XMLProcessingService

            search_service = SearchService(self.db_connector, self.entry_service)

            entries, _ = search_service.list_entries(project_id=project_id, limit=1000)

            for entry in entries:
                for sense in entry.senses:
                    if hasattr(sense, 'id') and sense.id == sense_id:
                        return entry
                    if hasattr(sense, 'guid') and sense.guid == sense_id:
                        return entry

        except Exception as e:
            self.logger.warning("Error searching for sense ID %s: %s", sense_id, e)

        return None

    def remove_bidirectional_relations(
        self,
        entry: Entry,
        project_id: Optional[int] = None
    ) -> None:
        """Remove bidirectional relations when source relation is deleted.

        Args:
            entry: The entry being updated that had bidirectional relations removed.
            project_id: Optional project ID for database resolution.
        """
        # This would be called when a relation is removed from an entry
        # For now, this is a placeholder for future implementation
        self.logger.debug(
            "remove_bidirectional_relations called for entry %s (not yet implemented)",
            entry.id
        )
