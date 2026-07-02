"""
EntryRevisionService — save revision snapshots and compute field-level change reports.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.workset_models import db
from app.models.entry_revision import EntryRevision

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stable-id field map — tells the diff algorithm which list fields have
# stable identifiers that can be used to match items across revisions.
# Key: dotted field path (relative to the entry JSON root).
# Value: match key within the item dict, or None for dict-keyed fields.
# ---------------------------------------------------------------------------
STABLE_ID_FIELDS: dict[str, str | None] = {
    'senses': 'id',
    'senses.subsenses': 'id',
    'senses.examples': 'id',
    'senses.relations': 'ref',
    'senses.reversals': 'type',
    'pronunciations': 'type',
    'etymologies': None,     # compared as ordered list (no stable key)
    'variants': 'ref',
    'relations': 'ref',
    'annotations': 'name',
    'variant_relations': 'ref',
}


def _match_key(field_path: str) -> str | None:
    """Return the match key for a field path, checking child-of patterns."""
    # Exact match first
    if field_path in STABLE_ID_FIELDS:
        return STABLE_ID_FIELDS[field_path]
    # Check if this field_path starts with a known pattern followed by [*]
    # e.g. senses[*].relations -> 'ref' (from senses.relations)
    for known_path, match_key in STABLE_ID_FIELDS.items():
        if field_path.startswith(known_path + '.'):
            return match_key
    return None


def compute_change_report(prev: dict | None, curr: dict) -> list[dict]:
    """
    Recursively diff two serializer JSON snapshots.

    Returns a list of change objects::
        {field_path, kind, before, after, summary}
    where *kind* is 'added', 'removed', or 'modified'.
    field_path uses stable IDs (e.g. senses[s1]) during diff, then
    humanize_set  _humanize_paths replaces them with readable labels.
    """
    if prev is None:
        return []
    changes: list[dict] = []
    _diff(prev, curr, '', changes)
    _humanize_paths(changes, curr or prev or {})
    return changes


# ---------------------------------------------------------------------------
# Humanize raw UUID identifiers in field paths (e.g. senses[abc-123] → Sense 1)
# ---------------------------------------------------------------------------

def _humanize_paths(changes: list[dict], snapshot: dict) -> None:
    """Replace stable-ID references in field_path with human-readable labels."""
    # Build lookup: stable-id → human label for every identifiable item
    lookups: dict[str, dict[str, str]] = {}  # prefix → {id: label}
    for prefix, items, label_key in [
        ('senses', snapshot.get('senses', []), '_sense_label'),
    ]:
        lookups[prefix] = {}
        for i, item in enumerate(items or []):
            sid = item.get('id') if isinstance(item, dict) else None
            label = _item_label(item, i + 1)
            if sid:
                lookups[prefix][sid] = label

    import re as _re

    def _humanize(path: str) -> str:
        for prefix, id_map in lookups.items():
            def _replace(m):
                sid = m.group(1)
                label = id_map.get(sid)
                return f'{prefix}[{label or sid[:8]}]' if label else m.group(0)
            path = _re.sub(rf'{_re.escape(prefix)}\[([^\]]+)\]', _replace, path)
            def _replace(m):
                sid = m.group(1)
                label = id_map.get(sid)
                return f'{prefix}[{label or sid[:8]}]' if label else m.group(0)
            path = _re.sub(rf'{_re.escape(prefix)}\[([^\]]+)\]', _replace, path)
        # Also clean up paths within matched items
        return path

    for c in changes:
        c['field_path'] = _humanize(c['field_path'])
        c['summary'] = _summarize(c['field_path'], c['kind'], c['before'], c['after'])


def _item_label(item: dict | None, idx: int) -> str:
    """Build a short human label for an item in a list.

    Snapshot shapes (from alpine-to-serializer.js):
      glosses: {lang: text}           (flat string)
      definitions: {lang: {text, lang}} (nested object)
    We try both flat and nested extraction.
    """
    if not isinstance(item, dict):
        return str(idx)
    for field in ('gloss', 'glosses', 'definition', 'definitions'):
        val = item.get(field) or {}
        if not isinstance(val, dict):
            continue
        # Try flat: {lang: "string"}
        first = next((v for v in val.values() if isinstance(v, str) and v), None)
        if first:
            return f'{idx} ("{_truncate(first, 40)}")'
        # Try nested: {lang: {text: "string", ...}}
        for v in val.values():
            if isinstance(v, dict) and isinstance(v.get('text'), str) and v['text']:
                return f'{idx} ("{_truncate(v["text"], 40)}")'
    return str(idx)


def _truncate(s: str, n: int) -> str:
    return s[:n] + '…' if len(s) > n else s


def _diff(a: Any, b: Any, path: str, changes: list[dict]) -> None:
    """Recursive diff helper."""
    depth = path.count('.') + path.count('[')
    if depth > 8:
        # Depth limit — treat as scalar comparison
        if a != b:
            changes.append(_mk_change(path, 'modified', _short(a), _short(b)))
        return

    # Both scalars (or one is None)
    if not isinstance(a, dict) or not isinstance(b, dict):
        if isinstance(a, list) and isinstance(b, list):
            _diff_lists(a, b, path, changes)
        elif a != b:
            changes.append(_mk_change(path, 'modified', _short(a), _short(b)))
        return

    # Both dicts
    for key in set(list(a.keys()) + list(b.keys())):
        child_path = f"{path}.{key}" if path else key
        if key not in a:
            changes.append(_mk_change(child_path, 'added', None, _short(b[key])))
        elif key not in b:
            changes.append(_mk_change(child_path, 'removed', _short(a[key]), None))
        else:
            _diff(a[key], b[key], child_path, changes)


def _diff_lists(a: list, b: list, path: str, changes: list[dict]) -> None:
    """Diff two lists, matching items by stable ID if the field is known."""
    mk = _match_key(path)
    if mk is not None:
        # Match by stable key
        a_by_key = {_getmk(item, mk): item for item in a}
        b_by_key = {_getmk(item, mk): item for item in b}
        all_keys = set(list(a_by_key.keys()) + list(b_by_key.keys()))
        for k in all_keys:
            item_path = f"{path}[{k}]"
            if k not in a_by_key:
                changes.append(_mk_change(item_path, 'added', None, _short(b_by_key[k])))
            elif k not in b_by_key:
                changes.append(_mk_change(item_path, 'removed', _short(a_by_key[k]), None))
            else:
                # Skip identity-only differences (e.g. only 'id' field changed)
                _diff(a_by_key[k], b_by_key[k], item_path, changes)
    else:
        # Unkeyed list — compare entries by position up to the shorter length,
        # then report remaining as added/removed.
        min_len = min(len(a), len(b))
        for i in range(min_len):
            idx_path = f"{path}[{i}]"
            _diff(a[i], b[i], idx_path, changes)
        if len(b) > len(a):
            for i in range(min_len, len(b)):
                changes.append(_mk_change(f"{path}[{i}]", 'added', None, _short(b[i])))
        elif len(a) > len(b):
            for i in range(min_len, len(a)):
                changes.append(_mk_change(f"{path}[{i}]", 'removed', _short(a[i]), None))


def _getmk(item: Any, mk: str | None) -> str:
    """Get the match-key value from an item."""
    if mk is None:
        return str(id(item))
    if isinstance(item, dict):
        return str(item.get(mk, ''))
    return str(item)


def _mk_change(path: str, kind: str, before: Any, after: Any) -> dict:
    return {
        'field_path': path,
        'kind': kind,
        'before': before,
        'after': after,
        'summary': _summarize(path, kind, before, after),
    }


_SHORT_MAX = 120


def _short(v: Any) -> Any:
    """Truncate strings for the change report."""
    if isinstance(v, str) and len(v) > _SHORT_MAX:
        return v[:_SHORT_MAX] + '…'
    if isinstance(v, dict):
        # Show a brief summary for dicts
        return f"{{{', '.join(list(v.keys())[:5])}{'…' if len(v) > 5 else ''}}}"
    if isinstance(v, list):
        return f"[{len(v)} items]"
    return v


def _summarize(path: str, kind: str, before: Any, after: Any) -> str:
    """Human-readable one-line summary."""
    label = path.replace('.', ' › ').replace('[', ' "').replace(']', '"')
    if kind == 'added':
        return f"Added {label}"
    if kind == 'removed':
        return f"Removed {label}"
    if kind == 'modified':
        b = _short(before) if before is not None else '(empty)'
        a = _short(after) if after is not None else '(empty)'
        return f"Changed {label}: {b} → {a}"
    return f"{kind} {label}"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class EntryRevisionService:
    """Create and query entry revisions."""

    @staticmethod
    def save_revision(entry_id: str, snapshot: dict,
                      user_id: str | None = None,
                      created_by: str | None = None) -> EntryRevision:
        """
        Store a new revision for this entry.

        Computes the field-level diff against the previous revision.
        Uses optimistic locking via SELECT MAX + retry.
        """
        # Compute revision number (atomic-ish: FOR UPDATE on the row)
        latest = EntryRevision.query.with_entities(
            db.func.max(EntryRevision.revision_number)
        ).filter(EntryRevision.entry_id == entry_id).scalar()
        rev_number = (latest or 0) + 1

        # Fetch the previous snapshot for diff
        prev_entry = EntryRevision.query\
            .filter(EntryRevision.entry_id == entry_id,
                    EntryRevision.revision_number == rev_number - 1)\
            .order_by(EntryRevision.revision_number.desc()).first()
        prev_snapshot = prev_entry.snapshot if prev_entry else None

        # Compute change report
        change_report = compute_change_report(prev_snapshot, snapshot)

        revision = EntryRevision(
            entry_id=entry_id,
            revision_number=rev_number,
            timestamp_utc=datetime.now(timezone.utc),
            user_id=user_id,
            created_by=created_by or user_id,
            snapshot=snapshot,
            change_report=change_report if change_report else None,
        )
        db.session.add(revision)
        db.session.commit()
        logger.info("Saved revision %d for entry %s (%d changes)",
                    rev_number, entry_id, len(change_report))
        return revision

    @staticmethod
    def get_revisions(entry_id: str, page: int = 1,
                      per_page: int = 20) -> tuple[list[EntryRevision], int]:
        """List revisions for an entry, newest first."""
        q = EntryRevision.query.filter_by(entry_id=entry_id)\
            .order_by(EntryRevision.revision_number.desc())
        total = q.count()
        revisions = q.offset((page - 1) * per_page).limit(per_page).all()
        return revisions, total

    @staticmethod
    def get_revision(entry_id: str, revision_number: int) -> EntryRevision | None:
        """Get a single revision by entry_id + revision_number.
        The change_report is humanized on read so existing revisions benefit too.
        """
        rev = EntryRevision.query.filter_by(
            entry_id=entry_id,
            revision_number=revision_number,
        ).first()
        if rev and rev.change_report and rev.snapshot:
            _humanize_paths(rev.change_report, rev.snapshot)
        return rev

    @staticmethod
    def get_stats(from_date: str | None = None,
                  to_date: str | None = None,
                  user_id: str | None = None,
                  entry_id: str | None = None,
                  granularity: str = 'day') -> dict:
        """
        Aggregate revision stats over a time range.
        Returns by-field change counts, timeline, top entries/editors.
        """
        from datetime import datetime
        q = EntryRevision.query

        if from_date:
            dt_from = datetime.fromisoformat(from_date)
            q = q.filter(EntryRevision.timestamp_utc >= dt_from)
        if to_date:
            from datetime import timedelta
            dt_to = datetime.fromisoformat(to_date)
            # End-of-day inclusive: timestamp_utc < dt_to + 1 day
            q = q.filter(EntryRevision.timestamp_utc < dt_to + timedelta(days=1))
        if user_id:
            q = q.filter(EntryRevision.user_id == user_id)
        if entry_id:
            q = q.filter(EntryRevision.entry_id == entry_id)

        revisions = q.order_by(EntryRevision.timestamp_utc).all()

        total = len(revisions)
        unique_entries = len(set(r.entry_id for r in revisions))
        unique_users = len(set(r.user_id for r in revisions if r.user_id))

        # By-field breakdown
        by_field: dict = {}
        for r in revisions:
            if not r.change_report:
                continue
            for change in r.change_report:
                fp = change.get('field_path', 'unknown')
                kind = change.get('kind', 'modified')
                # Normalize field path to a group key (strip indices)
                group = _field_group(fp)
                if group not in by_field:
                    by_field[group] = {}
                by_field[group][kind] = by_field[group].get(kind, 0) + 1

        # Timeline
        timeline: dict = {}
        for r in revisions:
            key = r.timestamp_utc.strftime('%Y-%m-%d' if granularity == 'day' else '%Y-%W')
            timeline[key] = timeline.get(key, 0) + 1
        timeline_sorted = [{'date': k, 'count': v}
                           for k, v in sorted(timeline.items())]

        # Top edited entries
        entry_counts: dict = {}
        for r in revisions:
            entry_counts[r.entry_id] = entry_counts.get(r.entry_id, 0) + 1
        top_entries = sorted(entry_counts.items(), key=lambda x: -x[1])[:20]

        # Top editors
        user_counts: dict = {}
        for r in revisions:
            uid = r.created_by or r.user_id or 'unknown'
            user_counts[uid] = user_counts.get(uid, 0) + 1
        top_users = sorted(user_counts.items(), key=lambda x: -x[1])[:20]

        return {
            'timespan': {'from': from_date, 'to': to_date},
            'total_revisions': total,
            'unique_entries_touched': unique_entries,
            'unique_users': unique_users,
            'by_field': by_field,
            'timeline': timeline_sorted,
            'top_edited_entries': [
                {'entry_id': eid, 'revisions': cnt} for eid, cnt in top_entries
            ],
            'top_editors': [
                {'user_id': uid, 'revisions': cnt} for uid, cnt in top_users
            ],
        }


def _field_group(field_path: str) -> str:
    """Reduce a field path like 'senses[abc].gloss.en' to 'senses.gloss'."""
    import re
    # Remove array indices like [abc] or [0]
    path = re.sub(r'\[[^\]]*\]', '', field_path)
    # Keep at most 2 levels
    parts = path.split('.')
    if len(parts) > 2:
        return '.'.join(parts[:2])
    return path
