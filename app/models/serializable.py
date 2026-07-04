"""
Serializable Mixin for standardized model serialization.

Provides consistent ``to_dict``/``from_dict`` functionality across all models,
eliminating the 50+ duplicate serialization implementations that were scattered
throughout the codebase.

The serialization direction (model → dict) uses a clean isinstance dispatch
without an artificial depth limit (**unlike the old ``_serialize_value``** which
silently truncated data past ``max_depth=10``).  The deserialization direction
(dict → model) uses type hints to reconstruct nested ``SerializableMixin``
instances automatically.
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

T = TypeVar("T", bound="SerializableMixin")


# ---------------------------------------------------------------------------
# Serialization helpers  (no depth-limit bugs — uses stdlib recursion)
# ---------------------------------------------------------------------------


def _is_serializable(obj: Any) -> bool:
    """Return True if *obj* has a ``to_dict`` method."""
    return hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict"))


def serialize_value(value: Any) -> Any:
    """
    Convert a Python value to a JSON-safe Python object.

    Unlike the previous ``_serialize_value`` there is **no** artificial
    recursion-depth limit — nested structures are traversed fully.  The
    stdlib does not silently truncate data, and neither should we.

    Handles:
    - Primitives (str, int, float, bool)
    - ``datetime`` / ``date`` → ISO-8601 string
    - ``uuid.UUID`` / ``Decimal`` → string
    - ``Enum`` → ``.value``
    - Objects with a ``to_dict()`` method (SerializableMixin subclasses)
    - ``dict``, ``list``, ``tuple``, ``set`` (recursed)
    - Objects with ``__dict__`` → dict of public attributes
    """
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return str(value)

    if isinstance(value, Enum):
        return value.value

    if _is_serializable(value):
        return value.to_dict()

    if isinstance(value, dict):
        return {serialize_value(k): serialize_value(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]

    if isinstance(value, set):
        return [serialize_value(item) for item in value]

    # Generic object — walk its public __dict__
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return {
            k: serialize_value(v)
            for k, v in value.__dict__.items()
            if not k.startswith("_")
        }

    # Last resort — convert to string
    try:
        return str(value)
    except Exception:
        return None


def serialize_list(items: List[Any]) -> List[Dict[str, Any]]:
    """
    Serialize a list of serializable objects.

    Args:
        items: List of objects.

    Returns:
        List of dictionaries.
    """
    return [
        item.to_dict() if _is_serializable(item) else serialize_value(item)
        for item in items
    ]


# ---------------------------------------------------------------------------
# JSON encoder (used by ``to_json()``)
# ---------------------------------------------------------------------------


class ModelJSONEncoder(json.JSONEncoder):
    """
    :class:`json.JSONEncoder` subclass that knows about model types.

    This can be used directly with ``json.dumps``::

        >>> json.dumps({"created": datetime.now()}, cls=ModelJSONEncoder)
    """

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, (uuid.UUID, Decimal)):
            return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, set):
            return list(obj)
        if _is_serializable(obj):
            return obj.to_dict()
        try:
            return str(obj)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# SerializableMixin
# ---------------------------------------------------------------------------


class SerializableMixin:
    """
    Mixin providing standardized serialization / deserialization.

    Supports both regular classes and dataclasses.  Automatically handles
    nested serializable objects, ``datetime``/``date``, ``UUID``,
    ``Decimal``, ``Enum`` values, and collection types.

    Usage::

        class MyModel(SerializableMixin):
            def __init__(self, name: str, created_at: datetime):
                self.name = name
                self.created_at = created_at

        data = model.to_dict()
        restored = MyModel.from_dict(data)
    """

    #: Fields to exclude from serialization.
    _exclude_fields: Set[str] = set()

    #: Fields that should be serialized even when ``None``.
    _include_none_fields: Set[str] = set()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(
        self,
        exclude: Optional[Set[str]] = None,
        include: Optional[Set[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Convert object to dictionary.

        Args:
            exclude: Additional fields to exclude (beyond ``_exclude_fields``).
            include: If specified, **only** these fields are included.
            **kwargs: Ignored (backward compatibility — previously accepted
                      ``depth`` and ``max_depth`` which have been removed).

        Returns:
            Dictionary representation of the object.
        """
        exclude_fields = self._exclude_fields | (exclude or set())

        # Gather source data
        if is_dataclass(self):
            data = {
                f.name: getattr(self, f.name)
                for f in dataclass_fields(self)
                if f.name not in exclude_fields
            }
        else:
            data = {
                k: v
                for k, v in self.__dict__.items()
                if not k.startswith("_") and k not in exclude_fields
            }

        if include:
            data = {k: v for k, v in data.items() if k in include}

        # Serialize each value
        result: Dict[str, Any] = {}
        for key, value in data.items():
            if value is None and key not in self._include_none_fields:
                continue
            result[key] = serialize_value(value)

        return result

    def to_json(
        self,
        exclude: Optional[Set[str]] = None,
        include: Optional[Set[str]] = None,
        indent: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        Convert object to JSON string.

        Args:
            exclude: Fields to exclude.
            include: If specified, only these fields.
            indent: JSON indentation level.
            **kwargs: Additional arguments forwarded to ``json.dumps``.

        Returns:
            JSON string.
        """
        return json.dumps(
            self.to_dict(exclude=exclude, include=include),
            cls=ModelJSONEncoder,
            indent=indent,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Deserialization
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create an instance from a dictionary.

        Nested ``SerializableMixin`` subclasses are reconstructed
        automatically via type hints and dataclass field types.

        Args:
            data: Dictionary containing object data.

        Returns:
            New instance of the class.

        Raises:
            ValueError: If *data* is not a dict or construction fails.
        """
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        try:
            type_hints = get_type_hints(cls)
        except Exception:
            type_hints = {}

        dc_fields = (
            {f.name: f for f in dataclass_fields(cls)} if is_dataclass(cls) else {}
        )

        kwargs: Dict[str, Any] = {}

        for key, value in data.items():
            target_type = type_hints.get(key)

            # If the field is typed as a SerializableMixin subclass and
            # the value is a dict, reconstruct the nested object.
            if key in dc_fields:
                field_type = dc_fields[key].type
                if (
                    isinstance(field_type, type)
                    and issubclass(field_type, SerializableMixin)
                    and isinstance(value, dict)
                ):
                    kwargs[key] = field_type.from_dict(value)
                    continue

            kwargs[key] = _deserialize_value(value, target_type)

        try:
            return cls(**kwargs)
        except TypeError as e:
            raise ValueError(f"Failed to create {cls.__name__} from dict: {e}") from e

    @classmethod
    def from_json(cls: Type[T], json_str: str, **kwargs: Any) -> T:
        """
        Create an instance from a JSON string.

        Args:
            json_str: JSON string.
            **kwargs: Additional arguments for ``json.loads``.

        Returns:
            New instance.
        """
        data = json.loads(json_str, **kwargs)
        return cls.from_dict(data)

    # ------------------------------------------------------------------
    # Copy / update
    # ------------------------------------------------------------------

    def copy(self: T) -> T:
        """
        Create a deep copy of the object via serialize-deserialize round trip.

        Returns:
            New instance with copied data.
        """
        return self.__class__.from_dict(self.to_dict())

    def update(self, **kwargs: Any) -> SerializableMixin:
        """
        Create a new instance with updated fields.

        Args:
            **kwargs: Fields to update.

        Returns:
            New instance with updated fields.
        """
        data = self.to_dict()
        data.update(kwargs)
        return self.__class__.from_dict(data)


# ---------------------------------------------------------------------------
# Deserialization helper
# ---------------------------------------------------------------------------


def _deserialize_value(value: Any, target_type: Optional[Type] = None) -> Any:
    """
    Deserialize a single value, optionally guided by *target_type*.

    The old ``_deserialize_value`` accepted ``depth`` and ``max_depth``
    parameters that were never used in practice — they are removed here.
    """
    if value is None:
        return None

    # SerializableMixin subclass
    if (
        target_type
        and isinstance(target_type, type)
        and issubclass(target_type, SerializableMixin)
        and isinstance(value, dict)
    ):
        return target_type.from_dict(value)

    # Datetime / date
    if target_type in (datetime, date) and isinstance(value, str):
        try:
            if target_type == datetime:
                return datetime.fromisoformat(value)
            elif target_type == date:
                return date.fromisoformat(value)
        except ValueError:
            pass
        return value

    # UUID
    if target_type == uuid.UUID and isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError:
            pass
        return value

    # Decimal
    if target_type == Decimal:
        if isinstance(value, (int, float, str)):
            try:
                return Decimal(str(value))
            except Exception as exc:
                logger.debug("Could not deserialize Decimal: %s", exc)
        return value

    # Generic type-origin handling (List[X], Dict[K,V], Set[X])
    if target_type and hasattr(target_type, "__origin__"):
        origin = getattr(target_type, "__origin__", None)
        args = getattr(target_type, "__args__", ())

        if origin in (list, List) and isinstance(value, list):
            item_type = args[0] if args else Any
            return [_deserialize_value(item, item_type) for item in value]

        if origin in (dict, Dict) and isinstance(value, dict):
            val_type = args[1] if len(args) > 1 else Any
            return {
                k: _deserialize_value(v, val_type) for k, v in value.items()
            }

        if origin in (set, Set) and isinstance(value, (list, set)):
            item_type = args[0] if args else Any
            return {_deserialize_value(item, item_type) for item in value}

    # Plain list / dict (no type info)
    if isinstance(value, list):
        return [_deserialize_value(item) for item in value]

    if isinstance(value, dict):
        return {k: _deserialize_value(v) for k, v in value.items()}

    return value


# ---------------------------------------------------------------------------
# Decorator: turn a dataclass into a serializable dataclass
# ---------------------------------------------------------------------------


def dataclass_serializable(
    _cls: Optional[Type[T]] = None,
    *,
    exclude: Optional[Set[str]] = None,
    include_none: Optional[Set[str]] = None,
    **dataclass_kwargs: Any,
) -> Union[Type[T], callable]:
    """
    Decorator that makes a dataclass serializable.

    Combines ``@dataclass`` with ``SerializableMixin`` automatically::

        @dataclass_serializable
        class MyModel:
            name: str
            items: List[Item]

        # With options:
        @dataclass_serializable(exclude={"internal_field"})
        class MyModel:
            name: str
            internal_field: str

    Args:
        _cls: Class to decorate (used without parentheses).
        exclude: Fields to exclude from serialization.
        include_none: Fields to include even when ``None``.
        **dataclass_kwargs: Additional arguments forwarded to ``@dataclass``.

    Returns:
        Decorated class.
    """

    def wrap(cls: Type[T]) -> Type[T]:
        if not is_dataclass(cls):
            cls = dataclass(cls, **dataclass_kwargs)

        class SerializableDataclass(cls, SerializableMixin):  # type: ignore[valid-type]
            pass

        SerializableDataclass._exclude_fields = exclude or set()
        SerializableDataclass._include_none_fields = include_none or set()

        SerializableDataclass.__name__ = cls.__name__
        SerializableDataclass.__qualname__ = cls.__qualname__
        SerializableDataclass.__module__ = cls.__module__
        SerializableDataclass.__doc__ = cls.__doc__

        return SerializableDataclass

    if _cls is None:
        return wrap
    return wrap(_cls)


def is_serializable_type(cls: Type) -> bool:
    """
    Return True if *cls* has both ``to_dict`` and ``from_dict`` class methods.

    Args:
        cls: Class to check.
    """
    return (
        hasattr(cls, "to_dict")
        and hasattr(cls, "from_dict")
        and callable(getattr(cls, "to_dict"))
        and callable(getattr(cls, "from_dict"))
    )


def deserialize_list(data: List[Dict[str, Any]], cls: Type[T]) -> List[T]:
    """
    Deserialize a list of dictionaries to model instances.

    Args:
        data: List of dictionaries.
        cls: Target class (must be serializable).

    Returns:
        List of deserialized objects.
    """
    return [
        cls.from_dict(item) if is_serializable_type(cls) else item
        for item in data
    ]
