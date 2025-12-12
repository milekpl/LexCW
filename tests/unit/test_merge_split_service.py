"""
Unit tests for merge/split operation services.
"""
import os
import tempfile
import pytest
from unittest.mock import Mock, patch
from app.services.merge_split_service import MergeSplitService
from app.services.operation_history_service import OperationHistoryService
from app.models.merge_split_operations import MergeSplitOperation, SenseTransfer
from app.models.entry import Entry
from app.models.sense import Sense
from app.utils.exceptions import ValidationError, NotFoundError

@pytest.fixture
def history_file():
    """Create a temporary history file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8') as f:
        # Write initial empty history to the file
        import json
        json.dump({'operations': [], 'transfers': []}, f)
        f.flush()
        file_path = f.name
    
    yield file_path
    
    # Cleanup: remove the temporary file
    os.unlink(file_path)


@pytest.fixture
def mock_dict_service():
    """Create a mock dictionary service."""
    return Mock()


@pytest.fixture
def service(mock_dict_service, history_file):
    """Create a MergeSplitService instance with a temporary history file."""
    history_service = OperationHistoryService(history_file_path=history_file)
    return MergeSplitService(mock_dict_service, history_service=history_service)


def test_merge_split_service_initialization(service: MergeSplitService):
    """Test MergeSplitService initialization."""
    assert service.dictionary_service is not None
    assert service.history_service is not None


def test_split_entry_operation(service: MergeSplitService, mock_dict_service: Mock):
    """Test split entry operation."""
    # Create a source entry with multiple senses
    source_entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "test"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "first sense"}),
            Sense(id_="sense_002", glosses={"en": "second sense"}),
            Sense(id_="sense_003", glosses={"en": "third sense"})
        ]
    )

    # Mock the dictionary service methods
    mock_dict_service.get_entry.return_value = source_entry
    mock_dict_service.create_entry.return_value = "entry_002"
    mock_dict_service.update_entry.return_value = None

    # Perform split operation
    operation = service.split_entry(
        source_entry_id="entry_001",
        sense_ids=["sense_002", "sense_003"],
        new_entry_data={"lexical_unit": {"en": "test split"}}
    )

    # Verify operation was created
    assert operation.operation_type == "split_entry"
    assert operation.source_id == "entry_001"
    assert operation.sense_ids == ["sense_002", "sense_003"]
    assert operation.status == "completed"

    # Verify dictionary service calls
    mock_dict_service.get_entry.assert_called_once_with("entry_001")
    mock_dict_service.create_entry.assert_called_once()
    mock_dict_service.update_entry.assert_called_once()


def test_merge_entries_operation(service: MergeSplitService, mock_dict_service: Mock):
    """Test merge entries operation."""
    # Create source and target entries
    source_entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "source"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "source sense 1"}),
            Sense(id_="sense_002", glosses={"en": "source sense 2"})
        ]
    )

    target_entry = Entry(
        id_="entry_002",
        lexical_unit={"en": "target"},
        senses=[
            Sense(id_="sense_003", glosses={"en": "target sense 1"})
        ]
    )

    # Mock the dictionary service methods
    def get_entry_side_effect(eid):
        if eid == "entry_001":
            return source_entry
        if eid == "entry_002":
            return target_entry
        return None
    
    mock_dict_service.get_entry.side_effect = get_entry_side_effect
    mock_dict_service.update_entry.return_value = None

    # Perform merge operation
    operation = service.merge_entries(
        target_entry_id="entry_002",
        source_entry_id="entry_001",
        sense_ids=["sense_001"]
    )

    # Verify operation was created
    assert operation.operation_type == "merge_entries"
    assert operation.source_id == "entry_001"
    assert operation.target_id == "entry_002"
    assert operation.sense_ids == ["sense_001"]
    assert operation.status == "completed"

    # Verify dictionary service calls
    assert mock_dict_service.get_entry.call_count == 2
    assert mock_dict_service.update_entry.call_count == 2 # one for target, one for source


def test_merge_senses_operation(service: MergeSplitService, mock_dict_service: Mock):
    """Test merge senses operation."""
    # Create an entry with multiple senses
    entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "test"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "first sense"}),
            Sense(id_="sense_002", glosses={"en": "second sense"}),
            Sense(id_="sense_003", glosses={"en": "third sense"})
        ]
    )

    # Mock the dictionary service methods
    mock_dict_service.get_entry.return_value = entry
    mock_dict_service.update_entry.return_value = None

    # Perform merge senses operation
    operation = service.merge_senses(
        entry_id="entry_001",
        target_sense_id="sense_001",
        source_sense_ids=["sense_002", "sense_003"]
    )

    # Verify operation was created
    assert operation.operation_type == "merge_senses"
    assert operation.source_id == "entry_001"
    assert operation.target_id == "sense_001"
    assert operation.sense_ids == ["sense_002", "sense_003"]
    assert operation.status == "completed"

    # Verify dictionary service calls
    mock_dict_service.get_entry.assert_called_once_with("entry_001")
    mock_dict_service.update_entry.assert_called_once()


def test_split_entry_with_invalid_sense_ids(service: MergeSplitService, mock_dict_service: Mock):
    """Test split entry operation with invalid sense IDs."""
    # Create a source entry with senses
    source_entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "test"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "first sense"})
        ]
    )

    # Mock the dictionary service methods
    mock_dict_service.get_entry.return_value = source_entry

    # Try to split with invalid sense ID
    with pytest.raises(ValidationError, match="Sense ID .* not found in source entry"):
        service.split_entry(
            source_entry_id="entry_001",
            sense_ids=["sense_002"],  # This sense doesn't exist
            new_entry_data={"lexical_unit": {"en": "test split"}}
        )


def test_merge_entries_with_nonexistent_source(service: MergeSplitService, mock_dict_service: Mock):
    """Test merge entries operation with nonexistent source entry."""
    # Mock the dictionary service to raise NotFoundError for the source entry
    def get_entry_side_effect(eid):
        if eid == "entry_999":
            return None
        return Entry(id_=eid)

    mock_dict_service.get_entry.side_effect = get_entry_side_effect
    
    # Try to merge with nonexistent source
    with pytest.raises(NotFoundError, match="Source entry entry_999 not found"):
        service.merge_entries(
            target_entry_id="entry_002",
            source_entry_id="entry_999",  # Nonexistent
            sense_ids=["sense_001"]
        )

def test_get_operation_history(service: MergeSplitService):
    """Test getting operation history."""
    # Add some operations to the service
    operation1 = MergeSplitOperation(
        operation_type="split_entry",
        source_id="entry_001",
        sense_ids=["sense_001"]
    )
    operation1.mark_completed()

    operation2 = MergeSplitOperation(
        operation_type="merge_entries",
        source_id="entry_002",
        target_id="entry_003",
        sense_ids=["sense_002"]
    )
    operation2.mark_completed()

    service.history_service.save_operation(operation1)
    service.history_service.save_operation(operation2)

    # Get operation history
    history = service.get_operation_history()

    assert len(history) == 2
    assert all(op.status == "completed" for op in history)


def test_get_sense_transfer_history(service: MergeSplitService):
    """Test getting sense transfer history."""
    # Add some transfers to the service
    transfer1 = SenseTransfer(
        sense_id="sense_001",
        original_entry_id="entry_001",
        new_entry_id="entry_002"
    )

    transfer2 = SenseTransfer(
        sense_id="sense_002",
        original_entry_id="entry_003",
        new_entry_id="entry_004"
    )

    service.history_service.save_transfer(transfer1)
    service.history_service.save_transfer(transfer2)

    # Get transfer history
    history = service.get_sense_transfer_history()

    assert len(history) == 2
    assert history[0].sense_id == "sense_001"
    assert history[1].sense_id == "sense_002"
