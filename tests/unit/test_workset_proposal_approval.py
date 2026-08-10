"""
Unit tests for workset proposal approval (B5 fix).

``approve_workset_entry_proposal`` used to call
``dictionary_service.update_entry(entry_id, entry_dict)`` positionally, but the
signature is ``update_entry(entry: Entry, ...)`` — so every approval crashed
with "'str' object has no attribute 'validate'". These tests pin the fixed
behavior: the fetched Entry is mutated in place (no from_dict rebuild, which
would duplicate variant relations) and the proposed field is applied.
"""

import json
from unittest.mock import MagicMock, patch

from app.models.entry import Entry
from app.services.workset_service import WorksetService


class TestApproveWorksetEntryProposal:
    def _approve(self, service, proposal, entry_id="entry-1"):
        entry = Entry.from_dict(
            {
                "id": entry_id,
                "lexical_unit": {"en": "hello"},
                "senses": [],
            }
        )

        mock_dict_service = MagicMock()
        mock_dict_service.get_entry.return_value = entry

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (
            json.dumps(proposal),
        )
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        from flask import Flask

        flask_app = Flask(__name__)
        flask_app.pg_pool = mock_pool

        with patch(
            "app.services.workset_service.get_dictionary_service",
            return_value=mock_dict_service,
        ), patch(
            "app.services.entry_revision_service.EntryRevisionService.save_revision",
            return_value=MagicMock(),
        ), flask_app.app_context():
            service.approve_workset_entry_proposal(workset_id=1, entry_id=entry_id)

        return entry, mock_dict_service

    def test_update_entry_receives_entry_object_with_proposed_value(self):
        """Approval must pass an Entry object (not (entry_id, dict)) and apply the proposal."""
        service = WorksetService()
        entry, mock_dict_service = self._approve(
            service,
            {
                "field_name": "grammatical_info",
                "proposed_value": "Noun",
                "proposal_type": "pos",
            },
        )

        call = mock_dict_service.update_entry.call_args
        assert call is not None, "update_entry was never called"
        entry_arg = call.args[0] if call.args else call.kwargs.get("entry")
        assert isinstance(entry_arg, Entry), (
            f"update_entry must receive an Entry object, got {type(entry_arg)}"
        )
        assert entry_arg.id == "entry-1"
        assert entry_arg.grammatical_info == "Noun", (
            "Proposed grammatical_info was not applied"
        )

    def test_update_entry_mutates_fetched_entry_in_place(self):
        """The fetched Entry must be mutated in place — a from_dict rebuild would
        duplicate variant relations (to_dict emits both 'relations' and the
        derived 'variant_relations')."""
        service = WorksetService()
        entry, mock_dict_service = self._approve(
            service,
            {
                "field_name": "grammatical_info",
                "proposed_value": "Noun",
                "proposal_type": "pos",
            },
        )

        entry_arg = mock_dict_service.update_entry.call_args.args[0]
        assert entry_arg is entry, (
            "update_entry must receive the same Entry instance that get_entry "
            "returned (in-place mutation), not a rebuilt copy"
        )

    def test_ipa_proposal_applies_pronunciations(self):
        """IPA proposals must write the model field 'pronunciations', not the
        non-existent 'pronunciation' (which was silently dropped)."""
        service = WorksetService()
        entry, _ = self._approve(
            service,
            {
                "field_name": "pronunciation",
                "proposed_value": "ˈhɛloʊ",
                "proposal_type": "ipa",
            },
        )

        assert entry.pronunciations == {"seh-fonipa": "ˈhɛloʊ"}, (
            f"IPA proposal not applied to pronunciations: {entry.pronunciations}"
        )
