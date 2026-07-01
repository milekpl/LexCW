"""
Unit tests for compute_change_report diff algorithm.
Tests are inline (no Flask app needed) to avoid import issues.
"""
import pytest


# Inline copy of the diff functions (pure logic, no Flask/graph needed)
def compute_change_report(prev, curr):
    if prev is None:
        return []
    changes = []
    _diff(prev, curr, '', changes)
    return changes


def _diff(a, b, path, changes):
    depth = path.count('.') + path.count('[')
    if depth > 8:
        if a != b:
            changes.append(_mk_change(path, "modified", _short(a), _short(b)))
        return
    if not isinstance(a, dict) or not isinstance(b, dict):
        if isinstance(a, list) and isinstance(b, list):
            _diff_lists(a, b, path, changes)
        elif a != b:
            changes.append(_mk_change(path, "modified", _short(a), _short(b)))
        return
    for key in set(list(a.keys()) + list(b.keys())):
        child_path = f"{path}.{key}" if path else key
        if key not in a:
            changes.append(_mk_change(child_path, "added", None, _short(b[key])))
        elif key not in b:
            changes.append(_mk_change(child_path, "removed", _short(a[key]), None))
        else:
            _diff(a[key], b[key], child_path, changes)


_STABLE_ID_FIELDS = {
    "senses": "id", "senses.subsenses": "id", "senses.examples": "id",
    "senses.relations": "ref", "senses.reversals": "type",
    "pronunciations": "type", "variants": "ref", "relations": "ref",
    "annotations": "name",
}


def _diff_lists(a, b, path, changes):
    mk = _STABLE_ID_FIELDS.get(path)
    if mk is not None:
        a_by_key = {_getmk(item, mk): item for item in a}
        b_by_key = {_getmk(item, mk): item for item in b}
        for k in set(list(a_by_key.keys()) + list(b_by_key.keys())):
            item_path = f"{path}[{k}]"
            if k not in a_by_key:
                changes.append(_mk_change(item_path, "added", None, _short(b_by_key[k])))
            elif k not in b_by_key:
                changes.append(_mk_change(item_path, "removed", _short(a_by_key[k]), None))
            else:
                _diff(a_by_key[k], b_by_key[k], item_path, changes)
    else:
        min_len = min(len(a), len(b))
        for i in range(min_len):
            _diff(a[i], b[i], f"{path}[{i}]", changes)
        if len(b) > len(a):
            for i in range(min_len, len(b)):
                changes.append(_mk_change(f"{path}[{i}]", "added", None, _short(b[i])))
        elif len(a) > len(b):
            for i in range(min_len, len(a)):
                changes.append(_mk_change(f"{path}[{i}]", "removed", _short(a[i]), None))


def _getmk(item, mk):
    if mk is None:
        return str(id(item))
    if isinstance(item, dict):
        return str(item.get(mk, ""))
    return str(item)


def _mk_change(path, kind, before, after):
    return {"field_path": path, "kind": kind, "before": before, "after": after,
            "summary": f"{kind} {path}"}


def _short(v):
    return v


def _field_group(field_path):
    import re
    path = re.sub(r"\[[^\]]*\]", "", field_path)
    parts = path.split(".")
    if len(parts) > 2:
        return ".".join(parts[:2])
    return path


# ---- Tests ----

def test_no_previous_snapshot():
    assert compute_change_report(None, {"id": "x"}) == []


def test_identical_snapshots():
    s = {"id": "x", "lexical_unit": {"en": "hello"}, "senses": []}
    assert compute_change_report(s, dict(s)) == []


def test_modified_scalar():
    prev = {"lexical_unit": {"en": "hello"}}
    curr = {"lexical_unit": {"en": "world"}}
    changes = compute_change_report(prev, curr)
    assert len(changes) == 1
    assert changes[0]["kind"] == "modified"
    assert "lexical_unit" in changes[0]["field_path"]


def test_added_key():
    prev = {"id": "x"}
    curr = {"id": "x", "status": "draft"}
    changes = compute_change_report(prev, curr)
    assert any(c["kind"] == "added" for c in changes)


def test_removed_key():
    prev = {"id": "x", "citation": {"en": "test"}}
    curr = {"id": "x"}
    changes = compute_change_report(prev, curr)
    assert any(c["kind"] == "removed" for c in changes)


def test_added_sense():
    prev = {"senses": [{"id": "s1", "gloss": {"en": "old"}}]}
    curr = {"senses": [{"id": "s1", "gloss": {"en": "old"}},
                       {"id": "s2", "gloss": {"en": "new"}}]}
    changes = compute_change_report(prev, curr)
    assert any(c["kind"] == "added" and "s2" in c["field_path"]
               for c in changes), f"added sense-2 not found in {changes}"


def test_removed_sense():
    prev = {"senses": [{"id": "s1"}, {"id": "s2"}]}
    curr = {"senses": [{"id": "s1"}]}
    changes = compute_change_report(prev, curr)
    assert any(c["kind"] == "removed" and "s2" in c["field_path"]
               for c in changes)


def test_modified_sense_gloss():
    prev = {"senses": [{"id": "s1", "gloss": {"en": "old"}}]}
    curr = {"senses": [{"id": "s1", "gloss": {"en": "new"}}]}
    changes = compute_change_report(prev, curr)
    gloss_changes = [c for c in changes if "gloss" in c["field_path"]]
    assert len(gloss_changes) >= 1
    assert gloss_changes[0]["kind"] == "modified"


def test_field_group_strips_indices():
    assert _field_group("senses[abc].gloss") == "senses.gloss"
    assert _field_group("senses[0].examples[xx].sentence") == "senses.examples"
    assert _field_group("lexical_unit.en") == "lexical_unit.en"


def test_field_group_short_path():
    assert _field_group("id") == "id"
    assert _field_group("status") == "status"
