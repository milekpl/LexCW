"""
Unified Data Copier Utility.

Consolidates deep copy patterns from across the codebase.
Provides controlled, documented deep copying with special handling
for model objects and common data patterns.

Replaces scattered copy.deepcopy() calls with:
- Type-aware copying
- Safe handling of circular references
- Special handling for model objects (Entry, Sense, etc.)
- Configurable copy strategies
- Performance optimizations for common patterns
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Union, Callable
from dataclasses import is_dataclass, fields as dataclass_fields


T = TypeVar('T')


class CopyStrategy:
    """Strategy for copying different types of objects."""

    DEEP = "deep"           # Full deep copy
    SHALLOW = "shallow"     # Shallow copy only
    REFERENCE = "reference"  # Return same object (no copy)
    CUSTOM = "custom"       # Use custom copy function


class DataCopier:
    """
    Unified data copying utility.

    Provides consistent deep copying across the codebase with:
    - Type-aware copying strategies
    - Safe handling of model objects
    - Circular reference protection
    - Configurable copy depth
    - Performance optimizations

    Usage:
        copier = DataCopier()

        # Simple deep copy
        copy = copier.copy(data)

        # Copy with depth limit
        copy = copier.copy(data, max_depth=3)

        # Copy model object
        entry_copy = copier.copy_entry(entry)

        # Copy with custom strategy
        copy = copier.copy(data, strategy={SomeClass: CopyStrategy.SHALLOW})
    """

    def __init__(
        self,
        max_depth: int = 10,
        preserve_ids: bool = True,
        handle_circular: bool = True
    ):
        """
        Initialize data copier.

        Args:
            max_depth: Maximum recursion depth for copying
            preserve_ids: Whether to preserve ID fields during copy
            handle_circular: Whether to handle circular references
        """
        self.max_depth = max_depth
        self.preserve_ids = preserve_ids
        self.handle_circular = handle_circular
        self._memo: Dict[int, Any] = {}

    def copy(
        self,
        obj: T,
        max_depth: Optional[int] = None,
        preserve_ids: Optional[bool] = None,
        custom_copiers: Optional[Dict[Type, Callable[[Any], Any]]] = None,
        current_depth: int = 0
    ) -> T:
        """
        Create a deep copy of an object.

        Args:
            obj: Object to copy
            max_depth: Maximum recursion depth (uses default if None)
            preserve_ids: Whether to preserve ID fields (uses default if None)
            custom_copiers: Dict of type -> copy function for custom handling
            current_depth: Current recursion depth (internal use)

        Returns:
            Deep copy of the object
        """
        max_depth = max_depth if max_depth is not None else self.max_depth
        preserve_ids = preserve_ids if preserve_ids is not None else self.preserve_ids

        # Depth limit check
        if current_depth > max_depth:
            # Return shallow copy at max depth
            return self._shallow_copy(obj)

        # Handle None
        if obj is None:
            return None  # type: ignore

        # Handle primitives
        if isinstance(obj, (int, float, bool, str, bytes)):
            return obj

        # Handle circular references
        if self.handle_circular:
            obj_id = id(obj)
            if obj_id in self._memo:
                return self._memo[obj_id]

        # Custom copiers take precedence
        if custom_copiers:
            for type_, copier_func in custom_copiers.items():
                if isinstance(obj, type_):
                    return copier_func(obj)

        # Type-specific copying
        if isinstance(obj, dict):
            return self._copy_dict(obj, max_depth, preserve_ids, custom_copiers, current_depth)

        if isinstance(obj, list):
            return self._copy_list(obj, max_depth, preserve_ids, custom_copiers, current_depth)

        if isinstance(obj, (set, frozenset)):
            return self._copy_set(obj, max_depth, preserve_ids, custom_copiers, current_depth)

        if isinstance(obj, tuple):
            return self._copy_tuple(obj, max_depth, preserve_ids, custom_copiers, current_depth)

        # Dataclass handling
        if is_dataclass(obj) and not isinstance(obj, type):
            return self._copy_dataclass(obj, max_depth, preserve_ids, custom_copiers, current_depth)

        # Object with copy method
        if hasattr(obj, 'copy') and callable(getattr(obj, 'copy')):
            try:
                return obj.copy()
            except (TypeError, AttributeError):
                pass

        # Object with __copy__ method
        if hasattr(obj, '__copy__') and callable(getattr(obj, '__copy__')):
            try:
                return obj.__copy__()
            except (TypeError, AttributeError):
                pass

        # Object with to_dict/from_dict (serializable)
        if hasattr(obj, 'to_dict') and hasattr(obj, 'from_dict'):
            try:
                return self._copy_serializable(obj, max_depth, preserve_ids, custom_copiers, current_depth)
            except (TypeError, AttributeError):
                pass

        # Fall back to copy.deepcopy for anything else
        try:
            result = copy.deepcopy(obj)
            if self.handle_circular:
                self._memo[id(obj)] = result
            return result
        except (TypeError, AttributeError):
            # If deepcopy fails, return as-is
            return obj

    def copy_entry(
        self,
        entry: Dict[str, Any],
        copy_senses: bool = True,
        copy_examples: bool = True,
        copy_relations: bool = True,
        copy_pronunciations: bool = True,
        copy_etymologies: bool = False,
        copy_notes: bool = False
    ) -> Dict[str, Any]:
        """
        Copy an entry dictionary with controlled depth.

        Specialized method for the common pattern of copying dictionary entries
        with specific fields that need deep copying vs reference copying.

        Args:
            entry: Entry dictionary to copy
            copy_senses: Whether to deep copy senses
            copy_examples: Whether to deep copy examples within senses
            copy_relations: Whether to deep copy relations
            copy_pronunciations: Whether to deep copy pronunciations
            copy_etymologies: Whether to deep copy etymologies
            copy_notes: Whether to deep copy notes

        Returns:
            Copied entry dictionary
        """
        if not isinstance(entry, dict):
            raise TypeError(f"Expected dict, got {type(entry).__name__}")

        result = {}

        # Copy all fields
        for key, value in entry.items():
            if key == 'id' and self.preserve_ids:
                # Keep ID as-is
                result[key] = value
            elif key == 'senses' and copy_senses and isinstance(value, list):
                result[key] = [
                    self.copy_sense(sense, copy_examples=copy_examples)
                    if isinstance(sense, dict) else self.copy(sense)
                    for sense in value
                ]
            elif key == 'relations' and copy_relations:
                result[key] = self.copy(value)
            elif key == 'pronunciations' and copy_pronunciations:
                result[key] = self.copy(value)
            elif key == 'etymologies' and copy_etymologies:
                result[key] = self.copy(value)
            elif key == 'notes' and copy_notes:
                result[key] = self.copy(value)
            elif key == 'examples' and copy_examples:
                result[key] = self.copy(value)
            else:
                # Default: deep copy
                result[key] = self.copy(value)

        return result

    def copy_sense(
        self,
        sense: Dict[str, Any],
        copy_examples: bool = True,
        copy_definitions: bool = True,
        copy_glosses: bool = True,
        copy_relations: bool = True,
        copy_subsenses: bool = True
    ) -> Dict[str, Any]:
        """
        Copy a sense dictionary with controlled depth.

        Args:
            sense: Sense dictionary to copy
            copy_examples: Whether to deep copy examples
            copy_definitions: Whether to deep copy definitions
            copy_glosses: Whether to deep copy glosses
            copy_relations: Whether to deep copy relations
            copy_subsenses: Whether to deep copy subsenses

        Returns:
            Copied sense dictionary
        """
        if not isinstance(sense, dict):
            raise TypeError(f"Expected dict, got {type(sense).__name__}")

        result = {}

        for key, value in sense.items():
            if key == 'id' and self.preserve_ids:
                result[key] = value
            elif key == 'examples' and copy_examples:
                result[key] = self.copy(value)
            elif key == 'definitions' and copy_definitions:
                result[key] = self.copy(value)
            elif key == 'glosses' and copy_glosses:
                result[key] = self.copy(value)
            elif key == 'relations' and copy_relations:
                result[key] = self.copy(value)
            elif key == 'subsenses' and copy_subsenses and isinstance(value, list):
                result[key] = [
                    self.copy_sense(sub, copy_examples=copy_examples)
                    if isinstance(sub, dict) else self.copy(sub)
                    for sub in value
                ]
            else:
                result[key] = self.copy(value)

        return result

    def copy_list(
        self,
        items: List[T],
        item_copier: Optional[Callable[[T], T]] = None
    ) -> List[T]:
        """
        Copy a list with optional item-specific copier.

        Args:
            items: List to copy
            item_copier: Optional function to copy each item

        Returns:
            Copied list
        """
        if item_copier:
            return [item_copier(item) for item in items]
        return [self.copy(item) for item in items]

    def copy_dict(
        self,
        data: Dict[str, Any],
        key_copier: Optional[Callable[[str], str]] = None,
        value_copier: Optional[Callable[[Any], Any]] = None
    ) -> Dict[str, Any]:
        """
        Copy a dictionary with optional key and value copiers.

        Args:
            data: Dictionary to copy
            key_copier: Optional function to copy keys
            value_copier: Optional function to copy values

        Returns:
            Copied dictionary
        """
        if key_copier is None:
            key_copier = lambda k: k  # Keys are usually strings, copy as-is

        if value_copier is None:
            value_copier = self.copy

        return {key_copier(k): value_copier(v) for k, v in data.items()}

    def _shallow_copy(self, obj: T) -> T:
        """Create a shallow copy of an object."""
        if isinstance(obj, dict):
            return obj.copy()  # type: ignore
        if isinstance(obj, list):
            return obj.copy()  # type: ignore
        if isinstance(obj, set):
            return obj.copy()  # type: ignore
        if isinstance(obj, tuple):
            return obj  # Tuples are immutable

        # Try copy.copy as fallback
        try:
            return copy.copy(obj)
        except (TypeError, AttributeError):
            return obj

    def _copy_dict(
        self,
        obj: Dict[str, Any],
        max_depth: int,
        preserve_ids: bool,
        custom_copiers: Optional[Dict[Type, Callable[[Any], Any]]],
        current_depth: int
    ) -> Dict[str, Any]:
        """Copy a dictionary."""
        result = {}

        if self.handle_circular:
            self._memo[id(obj)] = result

        for key, value in obj.items():
            # Copy key (usually string, but could be anything hashable)
            copied_key = key if isinstance(key, (str, int, float, bool)) else self.copy(
                key, max_depth, preserve_ids, custom_copiers, current_depth + 1
            )

            # Copy value
            copied_value = self.copy(
                value, max_depth, preserve_ids, custom_copiers, current_depth + 1
            )

            result[copied_key] = copied_value

        return result

    def _copy_list(
        self,
        obj: List[Any],
        max_depth: int,
        preserve_ids: bool,
        custom_copiers: Optional[Dict[Type, Callable[[Any], Any]]],
        current_depth: int
    ) -> List[Any]:
        """Copy a list."""
        result = []

        if self.handle_circular:
            self._memo[id(obj)] = result

        for item in obj:
            result.append(self.copy(
                item, max_depth, preserve_ids, custom_copiers, current_depth + 1
            ))

        return result

    def _copy_set(
        self,
        obj: Union[Set[Any], frozenset],
        max_depth: int,
        preserve_ids: bool,
        custom_copiers: Optional[Dict[Type, Callable[[Any], Any]]],
        current_depth: int
    ) -> Union[Set[Any], frozenset]:
        """Copy a set."""
        result = set()

        if self.handle_circular:
            self._memo[id(obj)] = result

        for item in obj:
            result.add(self.copy(
                item, max_depth, preserve_ids, custom_copiers, current_depth + 1
            ))

        return frozenset(result) if isinstance(obj, frozenset) else result

    def _copy_tuple(
        self,
        obj: tuple,
        max_depth: int,
        preserve_ids: bool,
        custom_copiers: Optional[Dict[Type, Callable[[Any], Any]]],
        current_depth: int
    ) -> tuple:
        """Copy a tuple."""
        # Tuples are immutable, but their contents may need copying
        return tuple(
            self.copy(item, max_depth, preserve_ids, custom_copiers, current_depth + 1)
            for item in obj
        )

    def _copy_dataclass(
        self,
        obj: Any,
        max_depth: int,
        preserve_ids: bool,
        custom_copiers: Optional[Dict[Type, Callable[[Any], Any]]],
        current_depth: int
    ) -> Any:
        """Copy a dataclass instance."""
        obj_type = type(obj)

        # Get field values
        field_values = {}
        for field in dataclass_fields(obj):
            value = getattr(obj, field.name)

            # Handle ID fields
            if field.name == 'id' and preserve_ids:
                field_values[field.name] = value
            else:
                field_values[field.name] = self.copy(
                    value, max_depth, preserve_ids, custom_copiers, current_depth + 1
                )

        # Create new instance
        result = obj_type(**field_values)

        if self.handle_circular:
            self._memo[id(obj)] = result

        return result

    def _copy_serializable(
        self,
        obj: Any,
        max_depth: int,
        preserve_ids: bool,
        custom_copiers: Optional[Dict[Type, Callable[[Any], Any]]],
        current_depth: int
    ) -> Any:
        """Copy using to_dict/from_dict methods."""
        try:
            data = obj.to_dict()

            # Handle ID preservation
            if preserve_ids and hasattr(obj, 'id'):
                data['id'] = obj.id

            # Copy nested data
            copied_data = self.copy(
                data, max_depth, preserve_ids, custom_copiers, current_depth + 1
            )

            return obj.__class__.from_dict(copied_data)
        except (TypeError, AttributeError, ValueError) as e:
            # Fall back to copy.deepcopy
            return copy.deepcopy(obj)


# Module-level convenience functions

_default_copier: Optional[DataCopier] = None


def get_copier() -> DataCopier:
    """Get the default data copier instance."""
    global _default_copier
    if _default_copier is None:
        _default_copier = DataCopier()
    return _default_copier


def deepcopy(obj: T, max_depth: int = 10, preserve_ids: bool = True) -> T:
    """
    Convenience function for deep copying.

    Args:
        obj: Object to copy
        max_depth: Maximum recursion depth
        preserve_ids: Whether to preserve ID fields

    Returns:
        Deep copy of the object
    """
    return get_copier().copy(obj, max_depth=max_depth, preserve_ids=preserve_ids)


def copy_entry(
    entry: Dict[str, Any],
    copy_senses: bool = True,
    copy_examples: bool = True,
    copy_relations: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for copying entry dictionaries.

    Args:
        entry: Entry dictionary to copy
        copy_senses: Whether to deep copy senses
        copy_examples: Whether to deep copy examples
        copy_relations: Whether to deep copy relations

    Returns:
        Copied entry dictionary
    """
    return get_copier().copy_entry(
        entry,
        copy_senses=copy_senses,
        copy_examples=copy_examples,
        copy_relations=copy_relations
    )


def copy_sense(
    sense: Dict[str, Any],
    copy_examples: bool = True,
    copy_definitions: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for copying sense dictionaries.

    Args:
        sense: Sense dictionary to copy
        copy_examples: Whether to deep copy examples
        copy_definitions: Whether to deep copy definitions

    Returns:
        Copied sense dictionary
    """
    return get_copier().copy_sense(
        sense,
        copy_examples=copy_examples,
        copy_definitions=copy_definitions
    )
