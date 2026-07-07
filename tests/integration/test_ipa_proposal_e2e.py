"""
End-to-End Integration Test for IPA Proposal Workflow.

Simulates an external IPA generation script submitting IPA proposals and direct modifications,
followed by lexicographer review (approve/reject) and history revision tracking.
"""

from __future__ import annotations

import pytest
import json
from typing import Any, Dict, List
from flask.testing import FlaskClient

from app.models.entry import Entry
from app.services.workset_service import WorksetService


def mock_external_ipa_script(
    client: FlaskClient,
    entries: List[Dict[str, str]],
    mode: str = "proposal",
    script_name: str = "external_ipa_g2p_v1.2",
) -> Dict[str, Any]:
    """
    Mock external script that generates IPA transcriptions for dictionary entries.
    
    IPA Rules (mocked G2P lookup):
    - 'cat' -> '/kæt/'
    - 'dog' -> '/dɒɡ/'
    - 'bird' -> '/bɜːd/'
    - default -> '/phonetic/'
    """
    ipa_dictionary = {
        "cat": "/kæt/",
        "dog": "/dɒɡ/",
        "bird": "/bɜːd/",
    }

    if mode == "proposal":
        proposals = []
        for e in entries:
            hw = e.get("headword", "").lower()
            ipa = ipa_dictionary.get(hw, "/phonetic/")
            proposals.append({
                "entry_id": e["id"],
                "proposal_type": "ipa",
                "field_name": "pronunciation",
                "proposed_value": {"ipa": ipa, "lang": "seh-fonipa"},
                "confidence": 0.98,
                "source_script": script_name,
                "headword": e.get("headword", ""),
            })

        response = client.post(
            "/api/worksets/proposals",
            json={
                "name": f"IPA Proposals — {script_name}",
                "source_script": script_name,
                "proposals": proposals,
            },
        )
        return response.get_json()

    elif mode == "direct":
        results = []
        for e in entries:
            hw = e.get("headword", "").lower()
            ipa = ipa_dictionary.get(hw, "/phonetic/")
            resp = client.post(
                f"/api/entries/{e['id']}/modify",
                json={
                    "ipa": ipa,
                    "lang": "seh-fonipa",
                    "source_script": script_name,
                },
            )
            results.append(resp.get_json())
        return {"success": True, "results": results}

    raise ValueError(f"Unknown mode {mode}")


@pytest.mark.integration
class TestIPAProposalE2E:
    """End-to-end integration tests for IPA external script proposals & review workflow."""

    def test_ipa_proposal_submission_and_approval(self, client: FlaskClient, monkeypatch: Any) -> None:
        """Test external script generating IPA proposals, submitting to Workset, and lexicographer approving."""
        # 1. Mock dictionary service entries
        test_entry_dict = {
            "id": "entry-cat-100",
            "headword": "cat",
            "lexical_unit": "cat",
            "grammatical_info": "Noun",
            "senses": [{"definition": "a small domesticated carnivorous mammal"}],
        }
        
        saved_entries: Dict[str, Dict[str, Any]] = {"entry-cat-100": dict(test_entry_dict)}

        class MockDictService:
            def get_entry(self, entry_id: str) -> Any:
                if entry_id in saved_entries:
                    d = saved_entries[entry_id]
                    mock_obj = MockEntry(d)
                    return mock_obj
                return None

            def update_entry(self, entry_id: str, entry_dict: Dict[str, Any]) -> Any:
                saved_entries[entry_id] = dict(entry_dict)
                return MockEntry(entry_dict)

        class MockEntry:
            def __init__(self, data: Dict[str, Any]) -> None:
                self.id = data.get("id")
                self.data = data

            def to_dict(self) -> Dict[str, Any]:
                return dict(self.data)

        mock_ds = MockDictService()
        monkeypatch.setattr("app.services.workset_service.get_dictionary_service", lambda: mock_ds)
        monkeypatch.setattr("app.api.entries.get_dictionary_service", lambda: mock_ds)

        # 2. External script generates and submits IPA proposal
        entries_to_process = [{"id": "entry-cat-100", "headword": "cat"}]
        result = mock_external_ipa_script(client, entries_to_process, mode="proposal")

        assert result["success"] is True
        assert "workset_id" in result
        workset_id = result["workset_id"]
        assert result["total_entries"] == 1

        # 3. Approve proposal via API
        approve_resp = client.post(
            f"/api/worksets/{workset_id}/entries/entry-cat-100/approve-proposal",
            json={"user_id": "lexicographer_1"},
        )
        assert approve_resp.status_code == 200
        approve_data = approve_resp.get_json()
        assert approve_data["success"] is True
        assert approve_data["status"] == "approved"
        assert approve_data["applied_value"] == {"ipa": "/kæt/", "lang": "seh-fonipa"}

        # 4. Verify dictionary entry pronunciation was updated in dictionary
        updated_entry_data = saved_entries["entry-cat-100"]
        assert "pronunciation" in updated_entry_data
        assert updated_entry_data["pronunciation"]["ipa"] == "/kæt/"

    def test_ipa_proposal_rejection(self, client: FlaskClient, monkeypatch: Any) -> None:
        """Test rejecting an IPA proposal without modifying entry data."""
        test_entry_dict = {
            "id": "entry-dog-200",
            "headword": "dog",
            "grammatical_info": "Noun",
            "senses": [{"definition": "a domesticated canid"}],
        }
        saved_entries: Dict[str, Dict[str, Any]] = {"entry-dog-200": dict(test_entry_dict)}

        class MockDictService:
            def get_entry(self, entry_id: str) -> Any:
                if entry_id in saved_entries:
                    return MockEntry(saved_entries[entry_id])
                return None

            def update_entry(self, entry_id: str, entry_dict: Dict[str, Any]) -> Any:
                saved_entries[entry_id] = dict(entry_dict)
                return MockEntry(entry_dict)

        class MockEntry:
            def __init__(self, data: Dict[str, Any]) -> None:
                self.id = data.get("id")
                self.data = data

            def to_dict(self) -> Dict[str, Any]:
                return dict(self.data)

        mock_ds = MockDictService()
        monkeypatch.setattr("app.services.workset_service.get_dictionary_service", lambda: mock_ds)
        monkeypatch.setattr("app.api.entries.get_dictionary_service", lambda: mock_ds)

        # External script generates and submits proposal
        entries_to_process = [{"id": "entry-dog-200", "headword": "dog"}]
        result = mock_external_ipa_script(client, entries_to_process, mode="proposal")

        workset_id = result["workset_id"]

        # Reject proposal
        reject_resp = client.post(
            f"/api/worksets/{workset_id}/entries/entry-dog-200/reject-proposal",
            json={"user_id": "lexicographer_1", "notes": "Phonetic transcript inaccurate"},
        )
        assert reject_resp.status_code == 200
        reject_data = reject_resp.get_json()
        assert reject_data["success"] is True
        assert reject_data["status"] == "rejected"

        # Verify entry pronunciation was NOT modified
        updated_entry_data = saved_entries["entry-dog-200"]
        assert "pronunciation" not in updated_entry_data

    def test_ipa_direct_modification(self, client: FlaskClient, monkeypatch: Any) -> None:
        """Test external script directly modifying an entry via API."""
        test_entry_dict = {
            "id": "entry-bird-300",
            "headword": "bird",
            "grammatical_info": "Noun",
            "senses": [{"definition": "a feathered vertebrate"}],
        }
        saved_entries: Dict[str, Dict[str, Any]] = {"entry-bird-300": dict(test_entry_dict)}

        class MockDictService:
            def get_entry(self, entry_id: str) -> Any:
                if entry_id in saved_entries:
                    return MockEntry(saved_entries[entry_id])
                return None

            def update_entry(self, entry_id: str, entry_dict: Dict[str, Any]) -> Any:
                saved_entries[entry_id] = dict(entry_dict)
                return MockEntry(entry_dict)

        class MockEntry:
            def __init__(self, data: Dict[str, Any]) -> None:
                self.id = data.get("id")
                self.data = data

            def to_dict(self) -> Dict[str, Any]:
                return dict(self.data)

        mock_ds = MockDictService()
        monkeypatch.setattr("app.services.workset_service.get_dictionary_service", lambda: mock_ds)
        monkeypatch.setattr("app.api.entries.get_dictionary_service", lambda: mock_ds)

        # Run external script in direct mode
        entries_to_process = [{"id": "entry-bird-300", "headword": "bird"}]
        result = mock_external_ipa_script(client, entries_to_process, mode="direct")

        assert result["success"] is True
        res_item = result["results"][0]
        assert res_item["success"] is True
        assert "pronunciation" in res_item["modified_fields"]

        # Verify entry updated immediately
        updated_data = saved_entries["entry-bird-300"]
        assert updated_data["pronunciation"]["ipa"] == "/bɜːd/"
