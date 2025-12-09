"""
Unit tests for merge/split operation models.
"""

import pytest
from datetime import datetime
from app.models.merge_split_operations import MergeSplitOperation, SenseTransfer

def test_merge_split_operation_initialization():
    """Test MergeSplitOperation model initialization."""
    operation = MergeSplitOperation(
        operation_type="split_entry",
        source_id="entry_001",
        target_id="entry_002",
        sense_ids=["sense_001", "sense_002"]
    )

    assert operation.operation_type == "split_entry"
    assert operation.source_id == "entry_001"
    assert operation.target_id == "entry_002"
    assert operation.sense_ids == ["sense_001", "sense_002"]
    assert operation.status == "pending"
    assert isinstance(operation.timestamp, datetime)

def test_sense_transfer_initialization():
    """Test SenseTransfer model initialization."""
    transfer = SenseTransfer(
        sense_id="sense_001",
        original_entry_id="entry_001",
        new_entry_id="entry_002"
    )

    assert transfer.sense_id == "sense_001"
    assert transfer.original_entry_id == "entry_001"
    assert transfer.new_entry_id == "entry_002"
    assert isinstance(transfer.transfer_date, datetime)

def test_merge_split_operation_to_dict():
    """Test MergeSplitOperation to_dict method."""
    operation = MergeSplitOperation(
        operation_type="merge_entries",
        source_id="entry_001",
        target_id="entry_002",
        sense_ids=["sense_001"]
    )

    operation_dict = operation.to_dict()
    assert operation_dict["operation_type"] == "merge_entries"
    assert operation_dict["source_id"] == "entry_001"
    assert operation_dict["target_id"] == "entry_002"
    assert operation_dict["sense_ids"] == ["sense_001"]
    assert operation_dict["status"] == "pending"
    assert "timestamp" in operation_dict

def test_sense_transfer_to_dict():
    """Test SenseTransfer to_dict method."""
    transfer = SenseTransfer(
        sense_id="sense_001",
        original_entry_id="entry_001",
        new_entry_id="entry_002"
    )

    transfer_dict = transfer.to_dict()
    assert transfer_dict["sense_id"] == "sense_001"
    assert transfer_dict["original_entry_id"] == "entry_001"
    assert transfer_dict["new_entry_id"] == "entry_002"
    assert "transfer_date" in transfer_dict

def test_merge_split_operation_status_update():
    """Test updating MergeSplitOperation status."""
    operation = MergeSplitOperation(
        operation_type="merge_senses",
        source_id="entry_001",
        target_id="sense_001",
        sense_ids=["sense_002", "sense_003"]
    )

    operation.status = "completed"
    assert operation.status == "completed"

def test_merge_split_operation_without_target():
    """Test MergeSplitOperation without target_id (for split operations)."""
    operation = MergeSplitOperation(
        operation_type="split_entry",
        source_id="entry_001",
        sense_ids=["sense_001"]
    )

    assert operation.operation_type == "split_entry"
    assert operation.source_id == "entry_001"
    assert operation.target_id is None
    assert operation.sense_ids == ["sense_001"]