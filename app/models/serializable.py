"""
Serializable Mixin for standardized model serialization.

Provides consistent to_dict/from_dict functionality across all models,
eliminating the 50+ duplicate implementations scattered throughout the codebase.

Features:
- Works with regular classes and dataclasses
- Automatic handling of nested serializable objects
- Proper serialization of dates, UUIDs, and other special types
- Type-aware deserialization
- Custom field inclusion/exclusion
- Configurable depth limiting for nested objects
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, fields as dataclass_fields, is_dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Union, get_type_hints

logger = logging.getLogger(__name__)


T = TypeVar('T', bound='SerializableMixin')


# Types that should be converted to strings in serialization
STRING_SERIALIZABLE_TYPES = (uuid.UUID, Decimal)

# Types that should be converted to ISO format strings
DATETIME_SERIALIZABLE_TYPES = (datetime, date)


def _is_serializable(obj: Any) -> bool:
    """Check if object is serializable (has to_dict method)."""
    return hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict'))


def _serialize_value(value: Any, depth: int = 0, max_depth: int = 10) -> Any:
    """
    Serialize a single value.

    Args:
        value: Value to serialize
        depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        Serialized value
    """
    if depth > max_depth:
        return None

    # None handling
    if value is None:
        return None

    # Primitives
    if isinstance(value, (str, int, float, bool)):
        return value

    # String-serializable types (UUID, Decimal)
    if isinstance(value, STRING_SERIALIZABLE_TYPES):
        return str(value)

    # Datetime types
    if isinstance(value, DATETIME_SERIALIZABLE_TYPES):
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    # Enum types
    if isinstance(value, Enum):
        return value.value

    # Serializable objects
    if _is_serializable(value):
        return value.to_dict(depth=depth + 1, max_depth=max_depth)

    # Lists
    if isinstance(value, (list, tuple)):
        return [
            _serialize_value(item, depth=depth + 1, max_depth=max_depth)
            for item in value
        ]

    # Sets
    if isinstance(value, set):
        return [
            _serialize_value(item, depth=depth + 1, max_depth=max_depth)
            for item in sorted(value) if isinstance(item, (int, float, str))
        ] or list(value)

    # Dicts
    if isinstance(value, dict):
        return {
            _serialize_value(k, depth=depth + 1, max_depth=max_depth): _serialize_value(v, depth=depth + 1, max_depth=max_depth)
            for k, v in value.items()
        }

    # Fallback: convert to string or dict
    if hasattr(value, '__dict__'):
        return {
            k: _serialize_value(v, depth=depth + 1, max_depth=max_depth)
            for k, v in value.__dict__.items()
            if not k.startswith('_')
        }

    return str(value)


def _deserialize_value(
    value: Any,
    target_type: Optional[Type] = None,
    depth: int = 0,
    max_depth: int = 10
) -> Any:
    """
    Deserialize a single value.

    Args:
        value: Value to deserialize
        target_type: Target type hint for deserialization
        depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        Deserialized value
    """
    if depth > max_depth:
        return value

    if value is None:
        return None

    # If target type is specified and is a SerializableMixin subclass
    if target_type and isinstance(target_type, type) and issubclass(target_type, SerializableMixin):
        if isinstance(value, dict):
            return target_type.from_dict(value)
        return value

    # Handle datetime types
    if target_type in DATETIME_SERIALIZABLE_TYPES:
        if isinstance(value, str):
            try:
                if target_type == datetime:
                    return datetime.fromisoformat(value)
                elif target_type == date:
                    return date.fromisoformat(value)
            except ValueError:
                pass
        return value

    # Handle UUID
    if target_type == uuid.UUID:
        if isinstance(value, str):
            try:
                return uuid.UUID(value)
            except ValueError:
                pass
        return value

    # Handle Decimal
    if target_type == Decimal:
        if isinstance(value, (int, float, str)):
            try:
                return Decimal(str(value))
            except Exception as e:
                logger.debug(f"Could not deserialize Decimal: {e}")
        return value

    # Handle lists with type hints
    if target_type and hasattr(target_type, '__origin__'):
        origin = getattr(target_type, '__origin__', None)
        args = getattr(target_type, '__args__', ())

        if origin in (list, List) and isinstance(value, list):
            item_type = args[0] if args else Any
            return [
                _deserialize_value(item, item_type, depth=depth + 1, max_depth=max_depth)
                for item in value
            ]

        if origin in (dict, Dict) and isinstance(value, dict):
            key_type = args[0] if len(args) > 0 else Any
            val_type = args[1] if len(args) > 1 else Any
            return {
                _deserialize_value(k, key_type, depth=depth + 1, max_depth=max_depth): _deserialize_value(v, val_type, depth=depth + 1, max_depth=max_depth)
                for k, v in value.items()
            }

        if origin in (set, Set) and isinstance(value, (list, set)):
            item_type = args[0] if args else Any
            return {
                _deserialize_value(item, item_type, depth=depth + 1, max_depth=max_depth)
                for item in value
            }

    # Handle basic list deserialization
    if isinstance(value, list):
        return [
            _deserialize_value(item, None, depth=depth + 1, max_depth=max_depth)
            for item in value
        ]

    # Handle basic dict deserialization
    if isinstance(value, dict):
        return {
            k: _deserialize_value(v, None, depth=depth + 1, max_depth=max_depth)
            for k, v in value.items()
        }

    return value


class SerializableMixin:
    """
    Mixin providing standardized serialization/deserialization.

    Supports both regular classes and dataclasses. Automatically handles:
    - Nested serializable objects
    - DateTime/Date objects
    - UUID and Decimal
    - Enum values
    - Lists and dicts containing serializable types

    Usage:
        class MyModel(SerializableMixin):
            def __init__(self, name: str, created_at: datetime):
                self.name = name
                self.created_at = created_at

        # Serialization
        model = MyModel("test", datetime.now())
        data = model.to_dict()

        # Deserialization
        restored = MyModel.from_dict(data)

        # With dataclasses
        @dataclass
        class MyDataclass(SerializableMixin):
            name: str
            items: List[Item]

        data = instance.to_dict()
        restored = MyDataclass.from_dict(data)
    """

    # Fields to exclude from serialization
    _exclude_fields: Set[str] = set()

    # Fields that should be serialized even if None
    _include_none_fields: Set[str] = set()

    def to_dict(
        self,
        exclude: Optional[Set[str]] = None,
        include: Optional[Set[str]] = None,
        depth: int = 0,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """
        Convert object to dictionary.

        Args:
            exclude: Additional fields to exclude (beyond _exclude_fields)
            include: If specified, only include these fields
            depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            Dictionary representation of the object
        """
        # Determine fields to process
        exclude_fields = self._exclude_fields | (exclude or set())

        # Get source data
        if is_dataclass(self):
            # Dataclass - use dataclass fields
            data = {
                f.name: getattr(self, f.name)
                for f in dataclass_fields(self)
                if f.name not in exclude_fields
            }
        else:
            # Regular class - use __dict__
            data = {
                k: v
                for k, v in self.__dict__.items()
                if not k.startswith('_') and k not in exclude_fields
            }

        # Apply include filter if specified
        if include:
            data = {k: v for k, v in data.items() if k in include}

        # Serialize each value
        result = {}
        for key, value in data.items():
            # Skip None values unless explicitly included
            if value is None and key not in self._include_none_fields:
                continue

            result[key] = _serialize_value(value, depth=depth, max_depth=max_depth)

        return result

    def to_json(
        self,
        exclude: Optional[Set[str]] = None,
        include: Optional[Set[str]] = None,
        indent: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Convert object to JSON string.

        Args:
            exclude: Fields to exclude
            include: Fields to include (if specified, only these)
            indent: JSON indentation
            **kwargs: Additional arguments for json.dumps

        Returns:
            JSON string representation
        """
        return json.dumps(
            self.to_dict(exclude=exclude, include=include),
            indent=indent,
            **kwargs
        )

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create instance from dictionary.

        Args:
            data: Dictionary containing object data

        Returns:
            New instance of the class

        Raises:
            ValueError: If data is invalid
        """
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        # Get type hints for proper deserialization
        try:
            type_hints = get_type_hints(cls)
        except Exception:
            type_hints = {}

        # Get dataclass fields if applicable
        dc_fields = {f.name: f for f in dataclass_fields(cls)} if is_dataclass(cls) else {}

        # Prepare kwargs for constructor
        kwargs = {}

        for key, value in data.items():
            # Get target type
            target_type = type_hints.get(key)

            # Check if field has a from_dict method (nested serializable)
            if key in dc_fields:
                field_type = dc_fields[key].type
                if isinstance(field_type, type) and issubclass(field_type, SerializableMixin):
                    if isinstance(value, dict):
                        value = field_type.from_dict(value)
                        kwargs[key] = value
                        continue

            # Deserialize value
            deserialized = _deserialize_value(value, target_type)
            kwargs[key] = deserialized

        # Create instance
        try:
            return cls(**kwargs)
        except TypeError as e:
            # Handle missing required fields
            raise ValueError(f"Failed to create {cls.__name__} from dict: {e}")

    @classmethod
    def from_json(cls: Type[T], json_str: str, **kwargs) -> T:
        """
        Create instance from JSON string.

        Args:
            json_str: JSON string
            **kwargs: Additional arguments for json.loads

        Returns:
            New instance of the class
        """
        data = json.loads(json_str, **kwargs)
        return cls.from_dict(data)

    def copy(self: T) -> T:
        """
        Create a deep copy of the object.

        Returns:
            New instance with copied data
        """
        return self.__class__.from_dict(self.to_dict())

    def update(self, **kwargs) -> 'SerializableMixin':
        """
        Create a new instance with updated fields.

        Args:
            **kwargs: Fields to update

        Returns:
            New instance with updated fields
        """
        data = self.to_dict()
        data.update(kwargs)
        return self.__class__.from_dict(data)


def dataclass_serializable(
    _cls: Optional[Type[T]] = None,
    *,
    exclude: Optional[Set[str]] = None,
    include_none: Optional[Set[str]] = None,
    **dataclass_kwargs
) -> Union[Type[T], callable]:
    """
    Decorator to make a dataclass serializable.

    Combines @dataclass with SerializableMixin automatically.

    Args:
        _cls: Class to decorate (if used without parentheses)
        exclude: Fields to exclude from serialization
        include_none: Fields to include even when None
        **dataclass_kwargs: Additional arguments for @dataclass decorator

    Returns:
        Decorated class

    Example:
        @dataclass_serializable
        class MyModel:
            name: str
            items: List[Item]

        # Or with options:
        @dataclass_serializable(exclude={'internal_field'})
        class MyModel:
            name: str
            internal_field: str
    """
    def wrap(cls: Type[T]) -> Type[T]:
        # First, apply dataclass decorator if not already a dataclass
        if not is_dataclass(cls):
            cls = dataclass(cls, **dataclass_kwargs)

        # Create a new class that mixes in SerializableMixin
        # Don't add _exclude_fields/_include_none_fields as dataclass fields
        # because they would require default_factory
        class SerializableDataclass(cls, SerializableMixin):
            pass

        # Set class attributes for field exclusion
        SerializableDataclass._exclude_fields = exclude or set()
        SerializableDataclass._include_none_fields = include_none or set()

        SerializableDataclass.__name__ = cls.__name__
        SerializableDataclass.__qualname__ = cls.__qualname__
        SerializableDataclass.__module__ = cls.__module__
        SerializableDataclass.__doc__ = cls.__doc__

        return SerializableDataclass

    if _cls is None:
        # Used with parentheses: @dataclass_serializable()
        return wrap

    # Used without parentheses: @dataclass_serializable
    return wrap(_cls)


def is_serializable_type(cls: Type) -> bool:
    """
    Check if a class is serializable (has to_dict and from_dict).

    Args:
        cls: Class to check

    Returns:
        True if class is serializable
    """
    return (
        hasattr(cls, 'to_dict') and
        hasattr(cls, 'from_dict') and
        callable(getattr(cls, 'to_dict')) and
        callable(getattr(cls, 'from_dict'))
    )


def serialize_list(
    items: List[Any],
    max_depth: int = 10
) -> List[Dict[str, Any]]:
    """
    Serialize a list of serializable objects.

    Args:
        items: List of objects
        max_depth: Maximum recursion depth

    Returns:
        List of dictionaries
    """
    return [
        item.to_dict(max_depth=max_depth) if _is_serializable(item) else _serialize_value(item, max_depth=max_depth)
        for item in items
    ]


def deserialize_list(
    data: List[Dict[str, Any]],
    cls: Type[T],
    max_depth: int = 10
) -> List[T]:
    """
    Deserialize a list of dictionaries to objects.

    Args:
        data: List of dictionaries
        cls: Target class
        max_depth: Maximum recursion depth

    Returns:
        List of deserialized objects
    """
    return [
        cls.from_dict(item) if is_serializable_type(cls) else item
        for item in data
    ]
