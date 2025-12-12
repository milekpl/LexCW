"""
Service for handling merge and split operations on dictionary entries.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid
import copy

from app.models.merge_split_operations import MergeSplitOperation, SenseTransfer, MergeSplitResult
from app.models.entry import Entry
from app.models.sense import Sense
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.services.operation_history_service import OperationHistoryService

class MergeSplitService:
    """
    Service for performing merge and split operations on dictionary entries.

    This service handles the complex logic of merging and splitting entries
    while maintaining data integrity and handling conflicts.
    """

    def __init__(self, dictionary_service, history_service: OperationHistoryService = None):
        """
        Initialize the merge/split service.

        Args:
            dictionary_service: DictionaryService instance for database operations
            history_service: Service for persisting operation history
        """
        self.dictionary_service = dictionary_service
        self.history_service = history_service or OperationHistoryService()

    def split_entry(
        self,
        source_entry_id: str,
        sense_ids: List[str],
        new_entry_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> MergeSplitOperation:
        """
        Split an entry by moving specified senses to a new entry.

        Args:
            source_entry_id: ID of the source entry
            sense_ids: List of sense IDs to move to the new entry
            new_entry_data: Data for the new entry (lexical_unit, etc.)
            user_id: ID of the user performing the operation

        Returns:
            MergeSplitOperation object representing the completed operation

        Raises:
            NotFoundError: If source entry doesn't exist
            ValidationError: If sense IDs are invalid or operation fails validation
            DatabaseError: If database operations fail
        """
        # Create operation record
        operation = MergeSplitOperation(
            operation_type="split_entry",
            source_id=source_entry_id,
            sense_ids=sense_ids,
            user_id=user_id
        )
        
        try:
            # Get the source entry
            source_entry = self.dictionary_service.get_entry(source_entry_id)
            if not source_entry:
                operation.mark_failed("Source entry not found")
                self.history_service.save_operation(operation)
                raise NotFoundError(f"Source entry {source_entry_id} not found")

            # Validate sense IDs
            self._validate_sense_ids(source_entry, sense_ids)

            # Create new entry with the specified senses
            new_entry = self._create_new_entry_from_senses(
                source_entry, sense_ids, new_entry_data
            )

            # Remove senses from source entry
            self._remove_senses_from_entry(source_entry, sense_ids)

            # Save changes to database
            self.dictionary_service.create_entry(new_entry)
            self.dictionary_service.update_entry(source_entry)

            # Record sense transfers
            for sense_id in sense_ids:
                transfer = SenseTransfer(
                    sense_id=sense_id,
                    original_entry_id=source_entry_id,
                    new_entry_id=new_entry.id
                )
                self.history_service.save_transfer(transfer)

            # Mark operation as completed
            operation.target_id = new_entry.id
            operation.mark_completed()
            self.history_service.save_operation(operation)

            return operation

        except Exception as e:
            operation.mark_failed(str(e))
            self.history_service.save_operation(operation)
            raise

    def merge_entries(
        self,
        target_entry_id: str,
        source_entry_id: str,
        sense_ids: List[str],
        user_id: Optional[str] = None,
        conflict_resolution: Optional[Dict[str, str]] = None
    ) -> MergeSplitOperation:
        """
        Merge senses from source entry into target entry.

        Args:
            target_entry_id: ID of the target entry
            source_entry_id: ID of the source entry
            sense_ids: List of sense IDs to merge
            user_id: ID of the user performing the operation
            conflict_resolution: Strategy for resolving conflicts

        Returns:
            MergeSplitOperation object representing the completed operation

        Raises:
            NotFoundError: If source or target entry doesn't exist
            ValidationError: If sense IDs are invalid or operation fails validation
            DatabaseError: If database operations fail
        """
        # Create operation record
        operation = MergeSplitOperation(
            operation_type="merge_entries",
            source_id=source_entry_id,
            target_id=target_entry_id,
            sense_ids=sense_ids,
            user_id=user_id
        )

        try:
            # Get both entries
            target_entry = self.dictionary_service.get_entry(target_entry_id)
            if not target_entry:
                operation.mark_failed("Target entry not found")
                self.history_service.save_operation(operation)
                raise NotFoundError(f"Target entry {target_entry_id} not found")
            
            source_entry = self.dictionary_service.get_entry(source_entry_id)
            if not source_entry:
                operation.mark_failed("Source entry not found")
                self.history_service.save_operation(operation)
                raise NotFoundError(f"Source entry {source_entry_id} not found")

            # Validate sense IDs
            self._validate_sense_ids(source_entry, sense_ids)

            # Get senses to transfer
            senses_to_transfer = []
            for sense_id in sense_ids:
                sense = self._find_sense_by_id(source_entry, sense_id)
                if sense:
                    senses_to_transfer.append(sense)

            # Transfer senses to target entry
            self._transfer_senses_to_entry(target_entry, senses_to_transfer, conflict_resolution)

            # Remove senses from source entry
            self._remove_senses_from_entry(source_entry, sense_ids)

            # Save changes to database
            self.dictionary_service.update_entry(target_entry)
            
            if source_entry.senses:
                self.dictionary_service.update_entry(source_entry)
            else:
                self.dictionary_service.delete_entry(source_entry.id)


            # Record sense transfers
            for sense_id in sense_ids:
                transfer = SenseTransfer(
                    sense_id=sense_id,
                    original_entry_id=source_entry_id,
                    new_entry_id=target_entry_id
                )
                self.history_service.save_transfer(transfer)

            # Mark operation as completed
            operation.mark_completed()
            self.history_service.save_operation(operation)

            return operation

        except Exception as e:
            operation.mark_failed(str(e))
            self.history_service.save_operation(operation)
            raise

    def merge_senses(
        self,
        entry_id: str,
        target_sense_id: str,
        source_sense_ids: List[str],
        user_id: Optional[str] = None,
        merge_strategy: str = "combine_all"
    ) -> MergeSplitOperation:
        """
        Merge multiple senses within the same entry into a target sense.

        Args:
            entry_id: ID of the entry containing the senses
            target_sense_id: ID of the target sense
            source_sense_ids: List of sense IDs to merge into the target
            user_id: ID of the user performing the operation
            merge_strategy: Strategy for merging content

        Returns:
            MergeSplitOperation object representing the completed operation

        Raises:
            NotFoundError: If entry doesn't exist
            ValidationError: If sense IDs are invalid or operation fails validation
            DatabaseError: If database operations fail
        """
        # Create operation record
        operation = MergeSplitOperation(
            operation_type="merge_senses",
            source_id=entry_id,
            target_id=target_sense_id,
            sense_ids=source_sense_ids,
            user_id=user_id
        )

        try:
            # Get the entry
            entry = self.dictionary_service.get_entry(entry_id)
            if not entry:
                operation.mark_failed("Entry not found")
                self.history_service.save_operation(operation)
                raise NotFoundError(f"Entry {entry_id} not found")

            # Validate all sense IDs exist in the entry
            all_sense_ids = [target_sense_id] + source_sense_ids
            self._validate_sense_ids(entry, all_sense_ids)

            # Get target sense and source senses
            target_sense = self._find_sense_by_id(entry, target_sense_id)
            source_senses = []
            for sense_id in source_sense_ids:
                sense = self._find_sense_by_id(entry, sense_id)
                if sense:
                    source_senses.append(sense)

            if not target_sense:
                operation.mark_failed("Target sense not found")
                self.history_service.save_operation(operation)
                raise ValidationError(f"Target sense {target_sense_id} not found in entry")

            # Merge source senses into target sense
            self._merge_senses_into_target(target_sense, source_senses, merge_strategy)

            # Remove source senses from entry
            self._remove_senses_from_entry(entry, source_sense_ids)

            # Save changes to database
            self.dictionary_service.update_entry(entry)

            # Mark operation as completed
            operation.mark_completed()
            self.history_service.save_operation(operation)

            return operation

        except Exception as e:
            operation.mark_failed(str(e))
            self.history_service.save_operation(operation)
            raise

    def _validate_sense_ids(self, entry: Entry, sense_ids: List[str]) -> None:
        """
        Validate that all sense IDs exist in the given entry.

        Args:
            entry: Entry to validate against
            sense_ids: List of sense IDs to validate

        Raises:
            ValidationError: If any sense ID is not found
        """
        entry_sense_ids = [sense.id for sense in entry.senses if hasattr(sense, 'id')]
        entry_sense_ids += [sense.get('id') for sense in entry.senses if isinstance(sense, dict) and sense.get('id')]

        for sense_id in sense_ids:
            if sense_id not in entry_sense_ids:
                raise ValidationError(f"Sense ID {sense_id} not found in source entry")

    def _find_sense_by_id(self, entry: Entry, sense_id: str) -> Optional[Sense]:
        """
        Find a sense by ID in an entry.

        Args:
            entry: Entry to search
            sense_id: ID of the sense to find

        Returns:
            Sense object if found, None otherwise
        """
        for sense in entry.senses:
            if isinstance(sense, Sense) and hasattr(sense, 'id') and sense.id == sense_id:
                return sense
            elif isinstance(sense, dict) and sense.get('id') == sense_id:
                # Convert dict to Sense object
                return Sense(**sense)
        return None

    def _create_new_entry_from_senses(
        self,
        source_entry: Entry,
        sense_ids: List[str],
        new_entry_data: Dict[str, Any]
    ) -> Entry:
        """
        Create a new entry containing the specified senses.

        Args:
            source_entry: Source entry
            sense_ids: List of sense IDs to include in new entry
            new_entry_data: Data for the new entry

        Returns:
            New Entry object
        """
        # Create new entry ID
        new_entry_id = f"{source_entry.id}_split_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Get senses for new entry
        new_senses = []
        for sense_id in sense_ids:
            sense = self._find_sense_by_id(source_entry, sense_id)
            if sense:
                new_senses.append(sense)

        # Create new entry
        new_entry = Entry(
            id_=new_entry_id,
            lexical_unit=new_entry_data.get('lexical_unit', source_entry.lexical_unit),
            pronunciations=new_entry_data.get('pronunciations', {}),
            grammatical_info=new_entry_data.get('grammatical_info', source_entry.grammatical_info),
            senses=new_senses,
            # Copy other relevant fields
            date_created=datetime.now().isoformat(),
            date_modified=datetime.now().isoformat()
        )

        return new_entry

    def _remove_senses_from_entry(self, entry: Entry, sense_ids: List[str]) -> None:
        """
        Remove specified senses from an entry.

        Args:
            entry: Entry to modify
            sense_ids: List of sense IDs to remove
        """
        # Filter out senses to remove
        entry.senses = [
            sense for sense in entry.senses
            if not (isinstance(sense, Sense) and hasattr(sense, 'id') and sense.id in sense_ids)
            and not (isinstance(sense, dict) and sense.get('id') in sense_ids)
        ]

    def _transfer_senses_to_entry(
        self,
        target_entry: Entry,
        senses: List[Sense],
        conflict_resolution: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Transfer senses to a target entry, handling conflicts.

        Args:
            target_entry: Target entry to receive senses
            senses: List of senses to transfer
            conflict_resolution: Strategy for resolving conflicts
        """
        # Add senses to target entry
        for sense in senses:
            # Check for conflicts (e.g., duplicate sense IDs)
            existing_sense_ids = [s.id for s in target_entry.senses if hasattr(s, 'id')]
            if hasattr(sense, 'id') and sense.id in existing_sense_ids:
                # Handle conflict based on resolution strategy
                if conflict_resolution and conflict_resolution.get('duplicate_senses') == 'rename':
                    # Rename the sense with a suffix
                    sense.id = f"{sense.id}_transferred"
                elif conflict_resolution and conflict_resolution.get('duplicate_senses') == 'skip':
                    continue
                # Default: overwrite existing sense

            target_entry.senses.append(sense)

    def _merge_senses_into_target(
        self,
        target_sense: Sense,
        source_senses: List[Sense],
        merge_strategy: str = "combine_all"
    ) -> None:
        """
        Merge source senses into a target sense.

        Args:
            target_sense: Target sense to receive merged content
            source_senses: List of senses to merge
            merge_strategy: Strategy for merging content
        """
        for source_sense in source_senses:
            # Merge glosses
            for lang, gloss in source_sense.glosses.items():
                if lang not in target_sense.glosses:
                    target_sense.glosses[lang] = gloss
                elif merge_strategy == "combine_all":
                    # Combine glosses with separator
                    target_sense.glosses[lang] = f"{target_sense.glosses[lang]}; {gloss}"

            # Merge definitions
            for lang, definition in source_sense.definitions.items():
                if lang not in target_sense.definitions:
                    target_sense.definitions[lang] = definition
                elif merge_strategy == "combine_all":
                    # Combine definitions with separator
                    target_sense.definitions[lang] = f"{target_sense.definitions[lang]}; {definition}"

            # Merge examples
            target_sense.examples.extend(source_sense.examples)

            # Merge relations
            target_sense.relations.extend(source_sense.relations)

            # Merge other attributes as needed
            if source_sense.grammatical_info and not target_sense.grammatical_info:
                target_sense.grammatical_info = source_sense.grammatical_info

    def get_operation_history(self) -> List[MergeSplitOperation]:
        """
        Get the history of all merge/split operations.

        Returns:
            List of MergeSplitOperation objects
        """
        return self.history_service.get_all_operations()

    def get_sense_transfer_history(self) -> List[SenseTransfer]:
        """
        Get the history of all sense transfers.

        Returns:
            List of SenseTransfer objects
        """
        return self.history_service.get_all_transfers()

    def get_operation_by_id(self, operation_id: str) -> Optional[MergeSplitOperation]:
        """
        Get a specific operation by ID.

        Args:
            operation_id: ID of the operation

        Returns:
            MergeSplitOperation object if found, None otherwise
        """
        operations = self.history_service.get_all_operations()
        for operation in operations:
            if operation.id == operation_id:
                return operation
        return None

    def get_transfers_by_sense_id(self, sense_id: str) -> List[SenseTransfer]:
        """
        Get all transfers involving a specific sense.

        Args:
            sense_id: ID of the sense

        Returns:
            List of SenseTransfer objects
        """
        transfers = self.history_service.get_all_transfers()
        return [transfer for transfer in transfers if transfer.sense_id == sense_id]

    def get_transfers_by_entry_id(self, entry_id: str) -> List[SenseTransfer]:
        """
        Get all transfers involving a specific entry (as source or target).

        Args:
            entry_id: ID of the entry

        Returns:
            List of SenseTransfer objects
        """
        transfers = self.history_service.get_all_transfers()
        return [
            transfer for transfer in transfers
            if transfer.original_entry_id == entry_id or transfer.new_entry_id == entry_id
        ]