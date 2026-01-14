# Merge/Split Operations Implementation

This document provides comprehensive documentation for the merge and split operations implementation in the Lexicographic Curation Workbench (LCW).

## Overview

The merge/split operations feature enables lexicographers to reorganize and restructure dictionary content by:

1. **Splitting entries**: Moving senses from one entry to create a new entry
2. **Merging entries**: Combining senses from one entry into another
3. **Merging senses**: Consolidating multiple senses within the same entry

## Architecture

### Data Models

#### MergeSplitOperation

Represents a merge or split operation with the following attributes:

- `operation_type`: Type of operation (`split_entry`, `merge_entries`, `merge_senses`)
- `source_id`: ID of the source entry
- `target_id`: ID of the target entry (optional for split operations)
- `sense_ids`: List of sense IDs involved in the operation
- `timestamp`: When the operation was created
- `user_id`: ID of the user who initiated the operation
- `status`: Current status (`pending`, `completed`, `failed`)
- `metadata`: Additional operation metadata

#### SenseTransfer

Tracks individual sense transfers between entries:

- `sense_id`: ID of the sense being transferred
- `original_entry_id`: ID of the original entry
- `new_entry_id`: ID of the new entry
- `transfer_date`: When the transfer occurred
- `metadata`: Additional transfer metadata

#### MergeSplitResult

Represents the result of a merge/split operation:

- `operation_id`: ID of the operation
- `success`: Whether the operation was successful
- `source_entry`: Source entry after operation
- `target_entry`: Target entry after operation (if applicable)
- `transferred_senses`: List of transferred sense IDs
- `conflicts_resolved`: Number of conflicts resolved
- `warnings`: List of warning messages
- `errors`: List of error messages

### Service Layer

The `MergeSplitService` class handles the core business logic:

#### Key Methods

1. **`split_entry()`**: Split an entry by moving specified senses to a new entry
2. **`merge_entries()`**: Merge senses from source entry into target entry
3. **`merge_senses()`**: Merge multiple senses within the same entry
4. **`get_operation_history()`**: Retrieve history of all operations
5. **`get_sense_transfer_history()`**: Retrieve history of all sense transfers

#### Validation and Error Handling

- Validates that all sense IDs exist in the source entry
- Handles conflicts during merging (duplicate senses, etc.)
- Provides comprehensive error messages
- Maintains operation status tracking

### API Endpoints

All endpoints are prefixed with `/api/merge-split/`

#### GET `/operations`

Get all merge/split operations.

**Response**:
```json
[
    {
        "operation_type": "split_entry",
        "source_id": "entry_001",
        "sense_ids": ["sense_001"],
        "status": "completed",
        "timestamp": "2023-01-01T00:00:00"
    }
]
```

#### GET `/operations/<operation_id>`

Get a specific operation by ID.

**Response**:
```json
{
    "operation_type": "split_entry",
    "source_id": "entry_001",
    "sense_ids": ["sense_001"],
    "status": "completed",
    "timestamp": "2023-01-01T00:00:00"
}
```

#### POST `/entries/<entry_id>/split`

Split an entry by moving senses to a new entry.

**Request**:
```json
{
    "sense_ids": ["sense_001", "sense_002"],
    "new_entry_data": {
        "lexical_unit": {"en": "new lexical unit"},
        "pronunciations": {"seh-fonipa": "/ipa/"},
        "grammatical_info": "noun"
    }
}
```

**Response**:
```json
{
    "success": true,
    "operation": {
        "operation_type": "split_entry",
        "source_id": "entry_001",
        "sense_ids": ["sense_001", "sense_002"],
        "status": "completed"
    },
    "message": "Entry split successfully"
}
```

#### POST `/entries/<target_id>/merge`

Merge senses from source entry into target entry.

**Request**:
```json
{
    "source_entry_id": "entry_001",
    "sense_ids": ["sense_001"],
    "conflict_resolution": {
        "duplicate_senses": "rename"
    }
}
```

**Response**:
```json
{
    "success": true,
    "operation": {
        "operation_type": "merge_entries",
        "source_id": "entry_001",
        "target_id": "entry_002",
        "sense_ids": ["sense_001"],
        "status": "completed"
    },
    "message": "Entries merged successfully"
}
```

#### POST `/entries/<entry_id>/senses/<target_sense_id>/merge`

Merge senses within the same entry.

**Request**:
```json
{
    "source_sense_ids": ["sense_002", "sense_003"],
    "merge_strategy": "combine_all"
}
```

**Response**:
```json
{
    "success": true,
    "operation": {
        "operation_type": "merge_senses",
        "source_id": "entry_001",
        "target_id": "sense_001",
        "sense_ids": ["sense_002", "sense_003"],
        "status": "completed"
    },
    "message": "Senses merged successfully"
}
```

#### GET `/transfers`

Get all sense transfers.

**Response**:
```json
[
    {
        "sense_id": "sense_001",
        "original_entry_id": "entry_001",
        "new_entry_id": "entry_002",
        "transfer_date": "2023-01-01T00:00:00"
    }
]
```

#### GET `/transfers/sense/<sense_id>`

Get transfers for a specific sense.

#### GET `/transfers/entry/<entry_id>`

Get transfers involving a specific entry.

#### GET `/operations/<operation_id>/status`

Get the status of a specific operation.

## Implementation Details

### Conflict Resolution Strategies

The system supports several conflict resolution strategies:

1. **`rename`**: Rename conflicting senses with a suffix
2. **`skip`**: Skip conflicting senses
3. **`overwrite`**: Overwrite existing senses with new ones

### Merge Strategies

For sense merging within entries:

1. **`combine_all`**: Combine all content from source senses
2. **`keep_target`**: Keep only target sense content
3. **`keep_source`**: Keep only source sense content

### Data Integrity

The implementation ensures data integrity through:

- **Validation**: Comprehensive validation of all inputs
- **Transaction Safety**: Database operations are atomic
- **Audit Trail**: Complete history of all operations
- **Error Recovery**: Graceful handling of errors with rollback

## Testing

### Unit Tests

- `test_merge_split_models.py`: Tests for data models
- `test_merge_split_service.py`: Tests for service layer

### Integration Tests

- `test_merge_split_api.py`: Tests for API endpoints

### Test Coverage

The implementation includes comprehensive test coverage for:

- Model initialization and serialization
- Service methods and business logic
- API endpoints and error handling
- Edge cases and validation scenarios

## Usage Examples

### Splitting an Entry

```python
# Create service instance
service = MergeSplitService(dictionary_service)

# Split entry
operation = service.split_entry(
    source_entry_id="entry_001",
    sense_ids=["sense_002", "sense_003"],
    new_entry_data={
        "lexical_unit": {"en": "split entry"},
        "grammatical_info": "noun"
    }
)

# Operation is automatically recorded in history
```

### Merging Entries

```python
# Merge entries with conflict resolution
operation = service.merge_entries(
    target_entry_id="entry_002",
    source_entry_id="entry_001",
    sense_ids=["sense_001"],
    conflict_resolution={
        "duplicate_senses": "rename"
    }
)
```

### Merging Senses

```python
# Merge senses within an entry
operation = service.merge_senses(
    entry_id="entry_001",
    target_sense_id="sense_001",
    source_sense_ids=["sense_002", "sense_003"],
    merge_strategy="combine_all"
)
```

## Error Handling

The implementation handles various error scenarios:

- **NotFoundError**: When entries or senses don't exist
- **ValidationError**: When inputs are invalid
- **DatabaseError**: When database operations fail
- **ConflictErrors**: When conflicts cannot be resolved

## Performance Considerations

- Operations are optimized for large dictionaries
- Database queries use efficient XQuery expressions
- Memory usage is minimized through streaming where possible
- Operations can be batched for better performance

## Future Enhancements

Potential future improvements:

1. **Batch Operations**: Support for batch merge/split operations
2. **Undo/Redo**: Full undo/redo functionality
3. **Preview Mode**: Preview changes before committing
4. **Conflict Resolution UI**: Interactive conflict resolution interface
5. **Performance Monitoring**: Track operation performance metrics

## Integration with LIFT Standard

The implementation fully supports the LIFT (Lexicon Interchange Format) standard:

- Preserves all LIFT XML structure
- Maintains sense hierarchies and relationships
- Handles all LIFT element types
- Supports LIFT 0.13 features

## Security Considerations

- All operations require authentication
- Input validation prevents injection attacks
- Database operations use parameterized queries
- Audit logging tracks all changes

## Documentation

This implementation includes comprehensive documentation:

- **API Documentation**: Swagger/OpenAPI documentation
- **User Guide**: Step-by-step instructions for lexicographers
- **Technical Reference**: Detailed technical specifications
- **Error Reference**: Complete list of error codes and messages
- **UI Architecture**: Complete UI/UX specification in [MERGE_SPLIT_UI_ARCHITECTURE.md](MERGE_SPLIT_UI_ARCHITECTURE.md)
- **Wireframes & Components**: Visual design and component diagrams in [MERGE_SPLIT_WIREFRAMES.md](MERGE_SPLIT_WIREFRAMES.md)

## 🎨 User Interface

The implementation includes a comprehensive UI architecture that replaces the redundant eye icon with intuitive merge/split operations:

- **Merge Entries**: Search-based target selection with sense checkboxes and conflict resolution
- **Split Entries**: Sense selection with new entry data form
- **Merge Senses**: Target sense selection with multiple merge strategy options
- **Accessibility**: Full keyboard navigation, ARIA attributes, and screen reader support

## Conclusion

The merge/split operations feature provides a robust, well-tested solution for reorganizing dictionary content while maintaining data integrity and providing a comprehensive audit trail. The implementation follows best practices for software development, including:

- Test-Driven Development (TDD)
- Comprehensive error handling
- Clean architecture with separation of concerns
- Full documentation and examples
- Performance optimization
- Security best practices

This feature significantly enhances the lexicographic workflow by enabling efficient reorganization of dictionary content without data loss or corruption.