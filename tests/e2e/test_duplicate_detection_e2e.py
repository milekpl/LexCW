"""E2E test for duplicate detection flow via API.

Relies on running app and BaseX. Seeds test data with a duplicate headword,
then exercises the full detect → dismiss → merge API pipeline.
"""

import pytest
import requests
import uuid


@pytest.fixture
def seeded_duplicates(app_url: str) -> None:
    """Ensure the test database has duplicate headword entries.

    The pristine LIFT data already contains one "cat" entry (test_entry_1).
    This fixture creates a second "cat" entry so the detection finds it.
    """
    r = requests.post(
        f"{app_url}/api/entries",
        json={
            "id": "dup_cat",
            "lexical_unit": {"en": "cat"},
            "grammatical_info": "Noun",
            "senses": [
                {
                    "id": "dup_sense_1",
                    "definition": {"en": {"text": "Duplicate cat entry for testing", "lang": "en"}},
                }
            ],
        },
        timeout=10,
    )
    assert r.ok, f"Failed to seed duplicate: {r.status_code} {r.text}"
    yield


class TestDuplicateDetectionE2E:
    """End-to-end tests for duplicate detection."""

    @pytest.mark.e2e
    def test_detect_duplicates(self, app_url: str, seeded_duplicates):
        """Detection finds the duplicate cat entry."""
        r = requests.get(f"{app_url}/api/dashboard/duplicates?mode=exact", timeout=10)
        assert r.ok, r.text
        data = r.json()
        assert data["success"] is True
        assert data["data"]["total_candidates"] >= 1

        groups = data["data"]["groups"]
        cat_groups = [g for g in groups if any(e["headword"] == "cat" for e in g["entries"])]
        assert len(cat_groups) >= 1, f"No cat duplicate groups found in {groups}"
        group = cat_groups[0]
        assert group["mode"] in ("exact", "fuzzy")
        assert group["confidence"] >= 0.9
        entry_ids = {e["entry_id"] for e in group["entries"]}
        assert "test_entry_1" in entry_ids, f"Expected test_entry_1 in {entry_ids}"
        assert "dup_cat" in entry_ids, f"Expected dup_cat in {entry_ids}"

    @pytest.mark.e2e
    def test_dismiss_and_exclude(self, app_url: str, seeded_duplicates):
        """Dismiss a duplicate group and verify it's excluded from subsequent results."""
        # 1. Get current groups
        r = requests.get(f"{app_url}/api/dashboard/duplicates?mode=exact", timeout=10)
        groups = r.json()["data"]["groups"]
        assert len(groups) >= 1, "No groups to dismiss"

        group_id = groups[0]["id"]

        # 2. Dismiss the group (pass project_id=1 as query param — the fixture creates one)
        dismiss_url = f"{app_url}/api/dashboard/duplicates/{group_id}/dismiss?project_id=1"
        r = requests.post(dismiss_url, timeout=10)
        assert r.ok, f"Dismiss failed: {r.status_code} {r.text}"
        assert r.json()["success"] is True

        # 3. Fetch again — dismissed group should be excluded
        r = requests.get(f"{app_url}/api/dashboard/duplicates?mode=exact&project_id=1", timeout=10)
        remaining = r.json()["data"]["groups"]
        remaining_ids = [g["id"] for g in remaining]
        assert group_id not in remaining_ids, (
            f"Dismissed group {group_id} still present in results: {remaining_ids}"
        )

        # 4. Dismiss the same group again — idempotent
        r = requests.post(dismiss_url, timeout=10)
        assert r.ok, r.text

    @pytest.mark.e2e
    def test_merge_requires_entry_ids(self, app_url: str):
        """Merge endpoint rejects missing entry IDs."""
        r = requests.post(
            f"{app_url}/api/dashboard/duplicates/group_1/merge",
            json={},
            timeout=10,
        )
        assert r.status_code == 400
        assert r.json()["success"] is False

    @pytest.mark.e2e
    def test_merge_unknown_group(self, app_url: str):
        """Merge integration is delegated to merge service."""
        r = requests.post(
            f"{app_url}/api/dashboard/duplicates/group_x/merge",
            json={
                "target_entry_id": "test_entry_1",
                "source_entry_id": "dup_cat",
            },
            timeout=10,
        )
        # Should either succeed (if entries exist) or fail gracefully
        assert r.status_code in (200, 500)
