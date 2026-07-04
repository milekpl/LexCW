"""
Unified Data Copier Utility — thin wrapper around copy.deepcopy.

Consolidates deep copy patterns from across the codebase.
This is deliberately a thin wrapper: the implementation delegates to
``copy.deepcopy()`` rather than reimplementing type dispatch with
hand-rolled depth limits, circular-reference memoization, and per-type
copiers.  ``copy.deepcopy`` is correct, tested, and handles all built-in
types plus the ``__deepcopy__`` protocol.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, TypeVar


T = TypeVar("T")


class DataCopier:
    """
    Thin wrapper around :func:`copy.deepcopy`.

    Provides a consistent import target for services that need deep copies
    of entry/sense/range data.  The implementation delegates entirely to
    :func:`copy.deepcopy`, which correctly handles circular references,
    all built-in types, and objects implementing ``__deepcopy__``.
    """

    def copy(self, obj: T, **kwargs: Any) -> T:
        """
        Create a deep copy of *obj*.

        All extra keyword arguments are accepted for backward compatibility
        but **ignored** — the stdlib ``copy.deepcopy`` does not need
        ``max_depth``, ``preserve_ids``, ``handle_circular``, or
        ``custom_copiers`` because it handles those concerns correctly
        by default.

        Args:
            obj: Object to copy.
            **kwargs: Ignored (backward compatibility).

        Returns:
            Deep copy of *obj*.
        """
        return copy.deepcopy(obj)


# ---------------------------------------------------------------------------
# Module-level convenience functions (backward-compatible API)
# ---------------------------------------------------------------------------

_default_copier: Optional[DataCopier] = None


def get_copier() -> DataCopier:
    """Return the shared DataCopier singleton."""
    global _default_copier
    if _default_copier is None:
        _default_copier = DataCopier()
    return _default_copier


def deepcopy(obj: T, **kwargs: Any) -> T:
    """
    Deep-copy *obj* via ``copy.deepcopy``.

    All extra keyword arguments are accepted for backward compatibility
    with code that passed ``max_depth`` or ``preserve_ids`` — they are
    **ignored**.

    Args:
        obj: Object to copy.
        **kwargs: Ignored (backward compatibility).

    Returns:
        Deep copy of *obj*.
    """
    return copy.deepcopy(obj)


def copy_entry(entry: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """
    Deep-copy an entry dictionary.

    Accepts keyword arguments (``copy_senses``, ``copy_examples``, etc.)
    for source-level compatibility with legacy callers, but **ignores**
    them because ``copy.deepcopy`` always copies everything.

    Args:
        entry: Entry dictionary to copy.
        **kwargs: Ignored (backward compatibility).

    Returns:
        Deep copy of *entry*.
    """
    return copy.deepcopy(entry)


def copy_sense(sense: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """
    Deep-copy a sense dictionary.

    Accepts keyword arguments for source-level compatibility but ignores
    them — ``copy.deepcopy`` copies everything.

    Args:
        sense: Sense dictionary to copy.
        **kwargs: Ignored (backward compatibility).

    Returns:
        Deep copy of *sense*.
    """
    return copy.deepcopy(sense)
