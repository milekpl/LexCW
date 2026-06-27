"""Range-element duplicate detection and de-duplication.

Real LIFT/FieldWorks exports contain duplicate ``<range-element>`` entries that the
lexicographer never sees and cannot remove in FieldWorks. Two kinds:

* **Exact duplicates** — same identity (``id``/``value``) *and* same ``guid``. These carry
  zero information; FieldWorks just emitted the element twice. They are safe to remove
  automatically (lossless). They were also the trigger for the Alpine ``x-for`` duplicate-key
  render bug (spec §11.2), so removing them from served ranges is defence-in-depth.

* **id conflicts** — same identity but *different* ``guid``. These are ambiguous (two genuinely
  distinct concepts, or a real conflict that needs merging). They are **flagged, never removed
  automatically** — the lexicographer decides.

Both helpers are pure and operate on the hierarchical range value shape
``[{'id'/'value', 'guid', 'children': [...], ...}]``.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _identity(value: Dict[str, Any]) -> Any:
    """The element's identity key — `id` preferred, falling back to `value`."""
    return value.get('id') or value.get('value')


def walk(values: List[Dict[str, Any]]):
    """Depth-first iterator over every element in the hierarchy."""
    for v in values or []:
        yield v
        yield from walk(v.get('children') or [])


def dedupe_exact_duplicates(
    values: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int]:
    """Remove exact duplicates — elements sharing both identity and ``guid`` — anywhere in
    the hierarchy, keeping the first occurrence.

    Lossless: removed elements are identical in identity+guid to a kept one.

    Returns ``(cleaned_values, removed_count)``. Input is not mutated.
    """
    seen: set = set()
    return _dedupe(values, seen)


def _dedupe(values: List[Dict[str, Any]], seen: set) -> Tuple[List[Dict[str, Any]], int]:
    cleaned: List[Dict[str, Any]] = []
    removed = 0
    for v in values or []:
        key = (_identity(v), v.get('guid'))
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        children = v.get('children')
        if children:
            new_children, child_removed = _dedupe(children, seen)
            removed += child_removed
            v = dict(v)
            v['children'] = new_children
        cleaned.append(v)
    return cleaned, removed


def find_id_conflicts(values: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find identities that appear with more than one distinct ``guid`` (same name, different
    guid) — the ambiguous duplicates that require a user decision.

    Returns a list of ``{'id', 'guids': [...sorted...], 'count'}`` for each conflicting identity.
    Exact (same-guid) duplicates do NOT appear here — only genuine id/guid conflicts.
    """
    by_id: Dict[Any, set] = {}
    for v in walk(values):
        ident = _identity(v)
        if ident is None:
            continue
        by_id.setdefault(ident, set()).add(v.get('guid'))
    conflicts = []
    for ident, guids in by_id.items():
        if len(guids) > 1:
            conflicts.append({
                'id': ident,
                'guids': sorted(g for g in guids if g is not None),
                'count': len(guids),
            })
    return conflicts


def summarize_duplicates(values: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One-call summary for the ranges editor: how many exact duplicates would be removed,
    and which identities have id/guid conflicts that need a manual decision."""
    _, exact_removed = dedupe_exact_duplicates(values)
    conflicts = find_id_conflicts(values)
    return {
        'exact_duplicate_count': exact_removed,
        'id_conflicts': conflicts,
        'has_duplicates': exact_removed > 0 or len(conflicts) > 0,
    }
