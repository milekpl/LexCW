"""Integration tests for ranges duplicate detection / de-duplication (spec §15.1).

The grammatical-info fixture (conftest pristine_ranges_data) seeds:
  * an EXACT duplicate (two `Pronoun` with the same id AND guid) — must be auto-removed
    from served ranges,
  * an id CONFLICT (`Pronoun` with a different guid) — must be flagged, never auto-removed.
"""
import requests
import pytest


def _flatten(values):
    out = []
    for v in values or []:
        out.append(v)
        out.extend(_flatten(v.get('children') or []))
    return out


@pytest.mark.integration
def test_duplicates_endpoint_reports_exact_and_conflict(app_url: str) -> None:
    r = requests.get(f"{app_url}/api/ranges-editor/grammatical-info/duplicates")
    assert r.ok, r.text
    data = r.json()['data']

    # One exact duplicate (the second identical Pronoun id+guid) is removable.
    assert data['exact_duplicate_count'] == 1, data
    assert data['has_duplicates'] is True

    # The same-id/different-guid Pronoun is flagged as a conflict needing a decision.
    conflicts = {c['id']: c for c in data['id_conflicts']}
    assert 'Pronoun' in conflicts, data
    assert conflicts['Pronoun']['count'] == 2  # two distinct guids
    assert len(conflicts['Pronoun']['guids']) == 2
    # Conflict is annotated with usage so the editor can offer to delete unreferenced ones.
    assert 'referenced' in conflicts['Pronoun']
    assert 'usage_count' in conflicts['Pronoun']


@pytest.mark.integration
def test_served_range_has_exact_duplicates_removed(app_url: str) -> None:
    r = requests.get(f"{app_url}/api/ranges-editor/grammatical-info")
    assert r.ok, r.text
    payload = r.json()
    values = (payload.get('data') or payload).get('values', [])
    pronouns = [v for v in _flatten(values) if (v.get('id') or v.get('value')) == 'Pronoun']

    # Exact duplicate removed (was 3 in the fixture: a1, a1, a2); the conflict pair remains.
    assert len(pronouns) == 2, f"expected 2 Pronoun after exact-dedup, got {len(pronouns)}"
    guids = sorted(p.get('guid') for p in pronouns)
    assert guids == [
        '5049f0e3-12a4-4e9f-97f7-6009108279a1',
        '5049f0e3-12a4-4e9f-97f7-6009108279a2',
    ], guids

    # Distinct non-Pronoun elements are untouched (no over-removal).
    ids = {v.get('id') for v in _flatten(values)}
    assert {'Noun', 'Verb', 'Adjective'}.issubset(ids)


@pytest.mark.integration
def test_clean_range_reports_no_duplicates(app_url: str) -> None:
    # lexical-relation fixture has no duplicates.
    r = requests.get(f"{app_url}/api/ranges-editor/lexical-relation/duplicates")
    assert r.ok, r.text
    data = r.json()['data']
    assert data['exact_duplicate_count'] == 0
    assert data['id_conflicts'] == []
    assert data['has_duplicates'] is False
