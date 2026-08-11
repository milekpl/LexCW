"""
Integration tests for the backup/restore roundtrip and real undo/redo.

These exercise the ACTUAL BaseX roundtrip (backup -> mutate -> restore) that
unit tests can only mock, and verify that undo/redo actually restores entry
data (not just bookkeeping).

Requires a live BaseX server (the session-scoped ``basex_server`` fixture in
``tests/conftest.py`` provides one automatically).
"""

import json
import shutil
import tempfile
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


class TestBackupRoundtrip:
    """A real backup -> mutate -> restore roundtrip must restore the data."""

    def test_backup_restore_roundtrip_preserves_entries(self, app, client):
        with app.app_context():
            from flask import current_app
            from app.database.basex_connector import BaseXConnector
            from app.services.basex_backup_manager import BaseXBackupManager

            conn = current_app.injector.get(BaseXConnector)
            db_name = f"roundtrip_{uuid.uuid4().hex[:8]}"
            backup_dir = tempfile.mkdtemp(prefix="rt_backups_")
            try:
                conn.create_database(db_name)
                conn.add_resource(
                    "lift.xml",
                    "<lift version='0.13'>"
                    "<entry id='cat'><lexical-unit><form lang='en'>"
                    "<text>cat</text></form></lexical-unit></entry>"
                    "</lift>",
                    db_name=db_name,
                )
                conn.add_resource(
                    "dog.xml",
                    "<entry id='dog'><lexical-unit><form lang='en'>"
                    "<text>dog</text></form></lexical-unit></entry>",
                    db_name=db_name,
                )
                conn.add_resource(
                    "ranges.xml",
                    "<lift-ranges><range id='grammatical-info'/></lift-ranges>",
                    db_name=db_name,
                )

                mgr = BaseXBackupManager(
                    basex_connector=conn, backup_directory=backup_dir
                )
                backup = mgr.backup_database(db_name, backup_type="manual")
                backup_path = Path(backup.file_path)
                assert backup_path.exists() and backup_path.stat().st_size > 0

                # The backup file must be a single well-formed XML document
                # (multi-root backups cannot be re-imported by BaseX).
                backup_text = backup_path.read_text(encoding="utf-8")
                ET.fromstring(backup_text)
                assert "cat" in backup_text and "dog" in backup_text

                # Mutate the live DB: add junk entry, remove ranges
                conn.execute_command(
                    "xquery db:add('%s', <entry id='junk'><lexical-unit>"
                    "<form lang='en'><text>junk</text></form></lexical-unit>"
                    "</entry>, 'junk.xml')" % db_name
                )
                conn.execute_command(
                    "xquery delete node collection('%s')//lift-ranges" % db_name
                )

                # Restore — must bring back the pre-mutation state
                backup_id = backup.id if hasattr(backup, "id") else "roundtrip"
                result = mgr.restore_database(db_name, backup_id, str(backup_path))
                assert result is True

                ids = (
                    conn.execute_query(
                        "xquery collection('%s')//entry/@id/string()" % db_name
                    )
                    .strip()
                    .split()
                )
                assert set(ids) == {"cat", "dog"}, f"Unexpected entries after restore: {ids}"

                ranges = conn.execute_query(
                    "xquery collection('%s')//lift-ranges/range/@id/string()" % db_name
                ).strip()
                assert "grammatical-info" in ranges, "Ranges not restored"

                # No temp databases may be left behind
                dbs = conn.execute_query("xquery db:list()").strip().split()
                assert not any("_restore_" in d for d in dbs), f"Temp DBs left: {dbs}"
            finally:
                try:
                    conn.execute_command(f"DROP DB {db_name}")
                except Exception:
                    pass
                shutil.rmtree(backup_dir, ignore_errors=True)


class TestRealUndoRedo:
    """Undo/redo must restore actual entry data via the API."""

    def test_undo_redo_create_entry(self, app, client):
        """Undo of a create deletes the entry; redo re-creates it."""
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService
            from app.services.operation_history_service import OperationHistoryService

            ds = current_app.injector.get(DictionaryService)
            history = current_app.injector.get(OperationHistoryService)
            # Isolate: this test owns the undo stack.
            history.clear_history()

            entry_id = f"undo_{uuid.uuid4().hex[:8]}"
            try:
                entry = Entry.from_dict(
                    {
                        "id": entry_id,
                        "lexical_unit": {"en": "alpha"},
                        "senses": [],
                    }
                )
                ds.create_entry(entry, skip_validation=True)
                assert ds.entry_exists(entry_id)

                # Undo the create -> entry deleted
                resp = client.post("/api/backup/operations/undo")
                assert resp.status_code == 200, resp.data[:300]
                assert not ds.entry_exists(entry_id), "Undo did not delete the entry"

                # Redo the create -> entry re-created with the same data
                resp = client.post("/api/backup/operations/redo")
                assert resp.status_code == 200, resp.data[:300]
                restored = ds.get_entry(entry_id)
                assert restored is not None, "Redo did not re-create the entry"
                assert restored.id == entry_id
            finally:
                history.clear_history()
                try:
                    if ds.entry_exists(entry_id):
                        ds.delete_entry(entry_id, record_history=False)
                except Exception:
                    pass

    def test_undo_update_reconciles_reverse_relations(self, app, client):
        """Undo/redo of a relation change must also revert/restore the reverse
        relation on the OTHER entry (bidirectional consistency)."""
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService
            from app.services.operation_history_service import OperationHistoryService
            from app.services.backup_service import get_backup_service

            ds = current_app.injector.get(DictionaryService)
            history = current_app.injector.get(OperationHistoryService)
            history.clear_history()

            a_id = f"rel_a_{uuid.uuid4().hex[:8]}"
            b_id = f"rel_b_{uuid.uuid4().hex[:8]}"
            try:
                ds.create_entry(
                    Entry.from_dict(
                        {"id": a_id, "lexical_unit": {"en": "alpha"}, "senses": []}
                    ),
                    skip_validation=True,
                )
                ds.create_entry(
                    Entry.from_dict(
                        {"id": b_id, "lexical_unit": {"en": "beta"}, "senses": []}
                    ),
                    skip_validation=True,
                )

                def refs_to_b(entry) -> list:
                    return [
                        r for r in entry.relations if getattr(r, 'ref', None) == b_id
                    ]

                def refs_to_a(entry) -> list:
                    return [
                        r for r in entry.relations if getattr(r, 'ref', None) == a_id
                    ]

                # Add a bidirectional relation A -> B (symmetrical 'synonim').
                # This is the LAST recorded op, so undo will pop it.
                a = ds.get_entry(a_id)
                a.add_relation('synonim', b_id)
                ds.update_entry(a, skip_validation=True)

                b = ds.get_entry(b_id)
                assert refs_to_a(b), (
                    f"Reverse relation on B missing after forward add: {b.relations}"
                )

                service = get_backup_service()

                # Undo: A's relation removed AND B's reverse relation removed.
                op = service.undo_last_operation()
                assert op is not None
                a_after = ds.get_entry(a_id)
                assert not refs_to_b(a_after), (
                    f"A's relation not undone: {a_after.relations}"
                )
                b_after = ds.get_entry(b_id)
                assert not refs_to_a(b_after), (
                    f"Reverse relation on B not reverted by undo: {b_after.relations}"
                )

                # Redo: relation back on A AND reverse back on B.
                service.redo_last_operation()
                a_redo = ds.get_entry(a_id)
                assert refs_to_b(a_redo), (
                    f"A's relation not re-applied: {a_redo.relations}"
                )
                b_redo = ds.get_entry(b_id)
                assert refs_to_a(b_redo), (
                    f"Reverse relation on B not re-applied by redo: {b_redo.relations}"
                )
            finally:
                history.clear_history()
                for eid in (a_id, b_id):
                    try:
                        if ds.entry_exists(eid):
                            ds.delete_entry(eid, record_history=False)
                    except Exception:
                        pass

    def test_undo_update_restores_previous_state(self, app, client):
        """Undo of an update restores the pre-update entry data."""
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService
            from app.services.operation_history_service import OperationHistoryService

            ds = current_app.injector.get(DictionaryService)
            history = current_app.injector.get(OperationHistoryService)
            history.clear_history()

            entry_id = f"undo_upd_{uuid.uuid4().hex[:8]}"
            try:
                ds.create_entry(
                    Entry.from_dict(
                        {
                            "id": entry_id,
                            "lexical_unit": {"en": "alpha"},
                            "senses": [],
                        }
                    ),
                    skip_validation=True,
                )
                # Update the lexical unit
                entry = ds.get_entry(entry_id)
                entry.lexical_unit = {"en": "beta"}
                ds.update_entry(entry, skip_validation=True)

                current = ds.get_entry(entry_id)
                text = current.lexical_unit.get("en")
                assert text == "beta", f"Expected beta, got {text}"

                # Undo the update -> back to alpha
                resp = client.post("/api/backup/operations/undo")
                assert resp.status_code == 200, resp.data[:300]
                current = ds.get_entry(entry_id)
                text = current.lexical_unit.get("en")
                assert text == "alpha", f"Undo did not restore state, got {text}"

                # Redo -> beta again
                resp = client.post("/api/backup/operations/redo")
                assert resp.status_code == 200, resp.data[:300]
                current = ds.get_entry(entry_id)
                text = current.lexical_unit.get("en")
                assert text == "beta", f"Redo did not re-apply state, got {text}"
            finally:
                history.clear_history()
                try:
                    if ds.entry_exists(entry_id):
                        ds.delete_entry(entry_id, record_history=False)
                except Exception:
                    pass


@pytest.mark.integration
class TestRelationUndoConsistency:
    """Bidirectional consistency for create/delete undo and trait changes."""

    def _make_pair(self, app):
        from flask import current_app
        from app.models.entry import Entry
        from app.services.dictionary_service import DictionaryService

        ds = current_app.injector.get(DictionaryService)
        a_id = f"rc_a_{uuid.uuid4().hex[:8]}"
        b_id = f"rc_b_{uuid.uuid4().hex[:8]}"
        ds.create_entry(
            Entry.from_dict({"id": b_id, "lexical_unit": {"en": "beta"}, "senses": []}),
            skip_validation=True,
        )
        return ds, a_id, b_id

    def test_undo_create_removes_reverse_relations(self, app, client):
        """Undo of a create deletes the entry AND removes the reverse relations
        it added to other entries."""
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService
            from app.services.operation_history_service import OperationHistoryService
            from app.services.backup_service import get_backup_service

            ds = current_app.injector.get(DictionaryService)
            history = current_app.injector.get(OperationHistoryService)
            history.clear_history()

            ds, a_id, b_id = self._make_pair(app)
            try:
                a = Entry.from_dict(
                    {"id": a_id, "lexical_unit": {"en": "alpha"}, "senses": []}
                )
                a.add_relation('synonim', b_id)
                ds.create_entry(a, skip_validation=True)

                b = ds.get_entry(b_id)
                assert [r for r in b.relations if getattr(r, 'ref', None) == a_id], (
                    "create did not add the reverse relation on B"
                )

                service = get_backup_service()
                assert service.undo_last_operation() is not None

                assert not ds.entry_exists(a_id), "undo did not delete the entry"
                b_after = ds.get_entry(b_id)
                assert not [r for r in b_after.relations if getattr(r, 'ref', None) == a_id], (
                    "undo of create left a dangling reverse relation on B"
                )
            finally:
                history.clear_history()
                for eid in (a_id, b_id):
                    try:
                        if ds.entry_exists(eid):
                            ds.delete_entry(eid, record_history=False)
                    except Exception:
                        pass

    def test_trait_change_propagates_to_reverse_relation(self, app, client):
        """A trait-only change on a forward relation must update the reverse
        relation (trait-aware diff), and undo must revert it."""
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService
            from app.services.operation_history_service import OperationHistoryService
            from app.services.backup_service import get_backup_service

            ds = current_app.injector.get(DictionaryService)
            history = current_app.injector.get(OperationHistoryService)
            history.clear_history()

            ds, a_id, b_id = self._make_pair(app)
            try:
                ds.create_entry(
                    Entry.from_dict(
                        {"id": a_id, "lexical_unit": {"en": "alpha"}, "senses": []}
                    ),
                    skip_validation=True,
                )
                a = ds.get_entry(a_id)
                a.add_relation('synonim', b_id)
                # traits are stored as a plain dict on the Relation object
                a.relations[0].traits = {'confidence': 'high'}
                ds.update_entry(a, skip_validation=True)

                b = ds.get_entry(b_id)
                rev = [r for r in b.relations if getattr(r, 'ref', None) == a_id]
                assert rev, "reverse relation missing after forward add"
                assert getattr(rev[0], 'traits', {}).get('confidence') == 'high', (
                    f"reverse did not mirror the forward traits: {rev[0].traits}"
                )

                # Trait-only change on the forward -> reverse must be updated
                a = ds.get_entry(a_id)
                a.relations[0].traits = {'confidence': 'low'}
                ds.update_entry(a, skip_validation=True)

                b = ds.get_entry(b_id)
                rev = [r for r in b.relations if getattr(r, 'ref', None) == a_id]
                assert rev, "reverse relation missing after trait change"
                assert getattr(rev[0], 'traits', {}).get('confidence') == 'low', (
                    f"trait change did not propagate to reverse: {rev[0].traits}"
                )

                # Undo the trait change -> reverse back to 'high'
                service = get_backup_service()
                assert service.undo_last_operation() is not None
                b = ds.get_entry(b_id)
                rev = [r for r in b.relations if getattr(r, 'ref', None) == a_id]
                assert getattr(rev[0], 'traits', {}).get('confidence') == 'high', (
                    f"undo did not revert the reverse traits: {rev[0].traits}"
                )
            finally:
                history.clear_history()
                for eid in (a_id, b_id):
                    try:
                        if ds.entry_exists(eid):
                            ds.delete_entry(eid, record_history=False)
                    except Exception:
                        pass


@pytest.mark.integration
class TestRelationTraitEscaping:
    """Reverse relations must mirror traits with XML-special characters safely."""

    def test_trait_with_special_chars_propagates_to_reverse(self, app, client):
        """Trait values containing & < > ' must not break the generated XQuery,
        and the reverse relation must carry the exact trait value."""
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService

            ds = current_app.injector.get(DictionaryService)
            a_id = f"esc_a_{uuid.uuid4().hex[:8]}"
            b_id = f"esc_b_{uuid.uuid4().hex[:8]}"
            try:
                ds.create_entry(
                    Entry.from_dict(
                        {"id": b_id, "lexical_unit": {"en": "beta"}, "senses": []}
                    ),
                    skip_validation=True,
                )
                ds.create_entry(
                    Entry.from_dict(
                        {"id": a_id, "lexical_unit": {"en": "alpha"}, "senses": []}
                    ),
                    skip_validation=True,
                )

                tricky = "A & B <C> 'quoted' \"d\""
                a = ds.get_entry(a_id)
                a.add_relation('synonim', b_id)
                a.relations[0].traits = {'note': tricky}
                # Must NOT raise (previously generated malformed XML -> DatabaseError)
                ds.update_entry(a, skip_validation=True)

                b = ds.get_entry(b_id)
                rev = [r for r in b.relations if getattr(r, 'ref', None) == a_id]
                assert rev, "reverse relation missing"
                assert getattr(rev[0], 'traits', {}).get('note') == tricky, (
                    f"trait not round-tripped: {getattr(rev[0], 'traits', {})}"
                )
            finally:
                for eid in (a_id, b_id):
                    try:
                        if ds.entry_exists(eid):
                            ds.delete_entry(eid, record_history=False)
                    except Exception:
                        pass


@pytest.mark.integration
class TestMergeSplitUndoRedo:
    """Real data undo/redo for merge/split operations (re-split/re-merge)."""

    def _service(self, app):
        from flask import current_app
        from app.services.dictionary_service import DictionaryService
        from app.services.merge_split_service import MergeSplitService
        from app.services.operation_history_service import OperationHistoryService
        from app.services.backup_service import get_backup_service

        ds = current_app.injector.get(DictionaryService)
        mss = current_app.injector.get(MergeSplitService)
        history = current_app.injector.get(OperationHistoryService)
        history.clear_history()
        return ds, mss, history, get_backup_service()

    def test_undo_redo_split_entry(self, app, client):
        """Undo of a split deletes the new entry and restores the source; redo
        re-creates the split."""
        with app.app_context():
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService

            ds, mss, history, service = self._service(app)
            a_id = f"sp_a_{uuid.uuid4().hex[:8]}"
            new_id = None
            try:
                ds.create_entry(
                    Entry.from_dict({
                        "id": a_id, "lexical_unit": {"en": "alpha"},
                        "senses": [
                            {"id": "s1", "glosses": {"en": "one"}},
                            {"id": "s2", "glosses": {"en": "two"}},
                        ],
                    }),
                    skip_validation=True,
                )
                op = mss.split_entry(a_id, ["s2"], {"lexical_unit": {"en": "beta"}})
                new_id = op.target_id
                assert new_id and ds.entry_exists(new_id)
                assert len(ds.get_entry(a_id).senses) == 1

                # Undo: new entry deleted, source back to 2 senses
                assert service.undo_last_operation() is not None
                assert not ds.entry_exists(new_id), "undo did not delete the split entry"
                assert len(ds.get_entry(a_id).senses) == 2, (
                    "undo did not restore the source's senses"
                )

                # Redo: split re-applied
                service.redo_last_operation()
                assert ds.entry_exists(new_id), "redo did not re-create the split entry"
                assert len(ds.get_entry(a_id).senses) == 1
            finally:
                history.clear_history()
                for eid in (a_id, new_id):
                    if not eid:
                        continue
                    try:
                        if ds.entry_exists(eid):
                            ds.delete_entry(eid, record_history=False)
                    except Exception:
                        pass

    def test_undo_redo_merge_entries(self, app, client):
        """Undo of a merge restores both entries (re-creating a deleted source);
        redo re-merges."""
        with app.app_context():
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService

            ds, mss, history, service = self._service(app)
            a_id = f"mg_a_{uuid.uuid4().hex[:8]}"
            b_id = f"mg_b_{uuid.uuid4().hex[:8]}"
            try:
                ds.create_entry(
                    Entry.from_dict({
                        "id": a_id, "lexical_unit": {"en": "alpha"},
                        "senses": [
                            {"id": "a1", "glosses": {"en": "one"}},
                            {"id": "a2", "glosses": {"en": "two"}},
                        ],
                    }),
                    skip_validation=True,
                )
                ds.create_entry(
                    Entry.from_dict({
                        "id": b_id, "lexical_unit": {"en": "beta"},
                        "senses": [{"id": "b1", "glosses": {"en": "bee"}}],
                    }),
                    skip_validation=True,
                )
                mss.merge_entries(a_id, b_id, ["b1"])
                assert len(ds.get_entry(a_id).senses) == 3
                assert not ds.entry_exists(b_id), "source should be deleted when empty"

                # Undo: target restored, source re-created with its sense
                assert service.undo_last_operation() is not None
                assert len(ds.get_entry(a_id).senses) == 2, (
                    "undo did not restore the target's senses"
                )
                assert ds.entry_exists(b_id), "undo did not re-create the source"
                assert len(ds.get_entry(b_id).senses) == 1

                # Redo: merge re-applied
                service.redo_last_operation()
                assert len(ds.get_entry(a_id).senses) == 3
                assert not ds.entry_exists(b_id)
            finally:
                history.clear_history()
                for eid in (a_id, b_id):
                    try:
                        if ds.entry_exists(eid):
                            ds.delete_entry(eid, record_history=False)
                    except Exception:
                        pass

    def test_undo_redo_merge_senses(self, app, client):
        """Undo of a sense merge restores the merged senses; redo re-merges."""
        with app.app_context():
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService

            ds, mss, history, service = self._service(app)
            e_id = f"ms_e_{uuid.uuid4().hex[:8]}"
            try:
                ds.create_entry(
                    Entry.from_dict({
                        "id": e_id, "lexical_unit": {"en": "gamma"},
                        "senses": [
                            {"id": "g1", "glosses": {"en": "one"}},
                            {"id": "g2", "glosses": {"en": "two"}},
                        ],
                    }),
                    skip_validation=True,
                )
                mss.merge_senses(e_id, "g1", ["g2"])
                assert len(ds.get_entry(e_id).senses) == 1

                assert service.undo_last_operation() is not None
                assert len(ds.get_entry(e_id).senses) == 2, (
                    "undo did not restore the merged senses"
                )

                service.redo_last_operation()
                assert len(ds.get_entry(e_id).senses) == 1
            finally:
                history.clear_history()
                try:
                    if ds.entry_exists(e_id):
                        ds.delete_entry(e_id, record_history=False)
                except Exception:
                    pass


@pytest.mark.integration
class TestEditLossPrevention:
    """The four edit-loss fixes: serializer, double-write, autosave, concurrency."""

    def test_dict_backend_preserves_notes_and_subsenses(self, app, client):
        """FIX 1: a dict-backend update must NOT wipe entry/sense notes or
        subsenses (the server serializer now emits them)."""
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService

            ds = current_app.injector.get(DictionaryService)
            eid = f"loss_{uuid.uuid4().hex[:8]}"
            try:
                ds.create_entry(
                    Entry.from_dict({
                        "id": eid, "lexical_unit": {"en": "alpha"},
                        "notes": {"general": {"en": "ENTRY-NOTE-KEEP"}},
                        "senses": [{
                            "id": "s1", "glosses": {"en": "g"},
                            "notes": {"general": {"en": "SENSE-NOTE-KEEP"}},
                            "subsenses": [{"id": "ss1", "glosses": {"en": "sub"}}],
                        }],
                    }),
                    skip_validation=True,
                )

                # dict-backend update (the path that used to wipe fields)
                e = ds.get_entry(eid)
                e.lexical_unit = {"en": "beta"}
                ds.update_entry(e, skip_validation=True)

                e2 = ds.get_entry(eid)
                assert e2.lexical_unit.get("en") == "beta"
                entry_note = e2.notes.get("general", {}).get("en")
                if isinstance(entry_note, dict):
                    entry_note = entry_note.get("text")
                assert entry_note == "ENTRY-NOTE-KEEP", (
                    f"entry notes wiped: {e2.notes}"
                )
                sense_note = e2.senses[0].notes.get("general", {}).get("en")
                if isinstance(sense_note, dict):
                    sense_note = sense_note.get("text")
                assert sense_note == "SENSE-NOTE-KEEP", (
                    f"sense notes wiped: {e2.senses[0].notes}"
                )
                assert len(e2.senses[0].subsenses) == 1, (
                    f"subsenses wiped: {e2.senses[0].subsenses}"
                )
            finally:
                try:
                    if ds.entry_exists(eid):
                        ds.delete_entry(eid, record_history=False)
                except Exception:
                    pass

    def test_xml_update_version_conflict_returns_409(self, app, client):
        """FIX 4: saving with a stale base dateModified is rejected with 409."""
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService

            ds = current_app.injector.get(DictionaryService)
            eid = f"conf_{uuid.uuid4().hex[:8]}"
            try:
                ds.create_entry(
                    Entry.from_dict(
                        {"id": eid, "lexical_unit": {"en": "alpha"}, "senses": []}
                    ),
                    skip_validation=True,
                )
                current = ds.get_entry(eid)
                loaded_modified = current.date_modified

                # Another write happens after the client "loaded" the entry.
                # (A real concurrent save goes through the API, which stamps a
                # fresh date_modified; simulate that here.)
                e = ds.get_entry(eid)
                e.lexical_unit = {"en": "changed-by-other"}
                e.date_modified = "2099-01-01T00:00:00Z"
                ds.update_entry(e, skip_validation=True)

                # Client saves with its STALE base -> 409
                xml = (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    f'<entry id="{eid}"><lexical-unit>'
                    '<form lang="en"><text>client-write</text></form>'
                    '</lexical-unit></entry>'
                )
                resp = client.put(
                    f"/api/xml/entries/{eid}",
                    data=xml,
                    content_type="application/xml",
                    headers={"X-Base-Date-Modified": str(loaded_modified)},
                )
                assert resp.status_code == 409, f"expected 409, got {resp.status_code}"
                data = resp.get_json()
                assert data.get("error") == "version_conflict"

                # The other user's edit is untouched
                after = ds.get_entry(eid)
                assert after.lexical_unit.get("en") == "changed-by-other"
            finally:
                try:
                    if ds.entry_exists(eid):
                        ds.delete_entry(eid, record_history=False)
                except Exception:
                    pass


    def test_entry_form_renders_version_token(self, app, client):
        """FIX 4 wiring: the entry form must expose the load-time date_modified
        on the <form> element so submitForm can send X-Base-Date-Modified."""
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService

            ds = current_app.injector.get(DictionaryService)
            eid = f"wiring_{uuid.uuid4().hex[:8]}"
            try:
                ds.create_entry(
                    Entry.from_dict({"id": eid, "lexical_unit": {"en": "alpha"}, "senses": []}),
                    skip_validation=True,
                )
                # Production saves (API/client) stamp date_modified; simulate it
                # so the stored entry actually carries a version token.
                seeded = ds.get_entry(eid)
                seeded.date_modified = "2025-01-01T00:00:00Z"
                ds.update_entry(seeded, skip_validation=True)

                resp = client.get(f"/entries/{eid}/edit")
                assert resp.status_code == 200, f"edit page: {resp.status_code}"
                html = resp.get_data(as_text=True)
                # the token must be on the form element itself (submitForm reads it there)
                form_tag = html.split('<form id="entry-form"', 1)[1].split(">", 1)[0]
                assert "data-entry-modified=" in form_tag, (
                    f"data-entry-modified missing on #entry-form: {form_tag}"
                )
                assert "data-entry-modified=\"\"" not in form_tag, (
                    "data-entry-modified rendered empty — entry has no date_modified?"
                )
            finally:
                try:
                    if ds.entry_exists(eid):
                        ds.delete_entry(eid, record_history=False)
                except Exception:
                    pass


    def test_autosave_refreshes_version_token_no_false_conflict(self, app, client):
        """Autosave must keep the stored dateModified alive and return it as
        newVersion, so a manual save right after an autosave does NOT 409
        against the user's own autosave (the false-conflict edge)."""
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService

            ds = current_app.injector.get(DictionaryService)
            eid = f"auto_{uuid.uuid4().hex[:8]}"
            try:
                ds.create_entry(
                    Entry.from_dict({
                        "id": eid, "lexical_unit": {"en": "alpha"},
                        "senses": [{"id": "s1", "glosses": {"en": "g"}, "definition": {"en": "a meaning"}}],
                    }),
                    skip_validation=True,
                )
                seeded = ds.get_entry(eid)
                seeded.date_modified = "2025-01-01T00:00:00Z"
                ds.update_entry(seeded, skip_validation=True)

                # 1) autosave fires
                resp = client.post("/api/entry/autosave", json={
                    "entryData": {"id": eid, "lexical_unit": {"en": "alpha"},
                                  "senses": [{"id": "s1", "glosses": {"en": "g"}, "definition": {"en": "a meaning"}}]},
                    "version": "1.0",
                    "timestamp": "2025-01-01T00:00:00Z",
                })
                assert resp.status_code == 200, resp.get_json()
                data = resp.get_json()
                assert data["success"] is True
                new_version = data["newVersion"]
                assert new_version and "T" in new_version, (
                    f"newVersion must be an ISO token, got {new_version!r}"
                )

                # 2) the stored entry kept a version token == newVersion
                after = ds.get_entry(eid)
                assert str(after.date_modified) == str(new_version), (
                    f"stored date_modified {after.date_modified!r} != newVersion {new_version!r}"
                )

                # 3) a manual save carrying that token must NOT false-conflict
                xml = (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    f'<entry id="{eid}" dateModified="2025-02-02T00:00:00Z">'
                    '<lexical-unit><form lang="en"><text>manual</text></form>'
                    '</lexical-unit></entry>'
                )
                mresp = client.put(
                    f"/api/xml/entries/{eid}",
                    data=xml,
                    content_type="application/xml",
                    headers={"X-Base-Date-Modified": str(new_version)},
                )
                assert mresp.status_code == 200, (
                    f"manual save after autosave false-409'd: {mresp.status_code} "
                    f"{mresp.get_json()}"
                )
            finally:
                try:
                    if ds.entry_exists(eid):
                        ds.delete_entry(eid, record_history=False)
                except Exception:
                    pass


@pytest.mark.integration
class TestMergeSplitRealUndo:
    """Merge/split undo/redo must restore REAL data (not just move stacks)."""

    def test_split_undo_redo_restores_real_data(self, app, client):
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService
            from app.services.merge_split_service import MergeSplitService

            ds = current_app.injector.get(DictionaryService)
            mss = current_app.injector.get(MergeSplitService)
            eid = f"sp_{uuid.uuid4().hex[:6]}"
            try:
                ds.create_entry(Entry.from_dict({
                    "id": eid, "lexical_unit": {"en": "word"},
                    "senses": [
                        {"id": "s1", "glosses": {"en": "one"}, "definition": {"en": "d1"}},
                        {"id": "s2", "glosses": {"en": "two"}, "definition": {"en": "d2"}},
                    ],
                }), skip_validation=True, record_history=False)

                op = mss.split_entry(
                    eid, ["s2"], {"lexical_unit": {"en": "word2"}}
                )
                new_id = op.target_id
                assert len(ds.get_entry(eid).senses) == 1, "split moved the sense"
                assert ds.entry_exists(new_id)

                # UNDO: new entry deleted, source restored with BOTH senses
                assert mss.undo_last_operation() is True
                restored = ds.get_entry(eid)
                assert len(restored.senses) == 2, f"undo did not restore sense: {len(restored.senses)}"
                sense_ids = {s.id for s in restored.senses}
                assert sense_ids == {"s1", "s2"}
                assert not ds.entry_exists(new_id)

                # REDO: sense moves out again, new entry re-created (fresh id)
                assert mss.redo_last_operation() is True
                re_split = ds.get_entry(eid)
                assert len(re_split.senses) == 1 and re_split.senses[0].id == "s1"
                split_ids = ds.db_connector.execute_query(
                    f"xquery for $e in collection('{ds.db_connector.database}')"
                    f"//*:entry[starts-with(@id, '{eid}_split_')] return string($e/@id)"
                ).strip().split()
                assert split_ids, (
                    f"redo did not re-create the split entry: {split_ids}"
                )
            finally:
                for eid_cleanup in [eid, new_id]:
                    try:
                        if ds.entry_exists(eid_cleanup):
                            ds.delete_entry(eid_cleanup, record_history=False)
                    except Exception:
                        pass

    def test_merge_undo_redo_restores_real_data(self, app, client):
        with app.app_context():
            from flask import current_app
            from app.models.entry import Entry
            from app.services.dictionary_service import DictionaryService
            from app.services.merge_split_service import MergeSplitService

            ds = current_app.injector.get(DictionaryService)
            mss = current_app.injector.get(MergeSplitService)
            a_id = f"ma_{uuid.uuid4().hex[:6]}"
            b_id = f"mb_{uuid.uuid4().hex[:6]}"
            try:
                ds.create_entry(Entry.from_dict({
                    "id": a_id, "lexical_unit": {"en": "alpha"},
                    "senses": [
                        {"id": "a1", "glosses": {"en": "a one"}, "definition": {"en": "d1"}},
                        {"id": "a2", "glosses": {"en": "a two"}, "definition": {"en": "d2"}},
                    ],
                }), skip_validation=True, record_history=False)
                ds.create_entry(Entry.from_dict({
                    "id": b_id, "lexical_unit": {"en": "beta"},
                    "senses": [{"id": "b1", "glosses": {"en": "b one"}, "definition": {"en": "d3"}}],
                }), skip_validation=True, record_history=False)

                mss.merge_entries(a_id, b_id, ["b1"])
                assert len(ds.get_entry(a_id).senses) == 3
                assert not ds.entry_exists(b_id), "empty source entry deleted on merge"

                # UNDO: target restored, source re-created with its sense
                assert mss.undo_last_operation() is True
                assert len(ds.get_entry(a_id).senses) == 2
                assert ds.entry_exists(b_id)
                assert len(ds.get_entry(b_id).senses) == 1
                assert ds.get_entry(b_id).senses[0].id == "b1"

                # REDO: merge applied again
                assert mss.redo_last_operation() is True
                assert len(ds.get_entry(a_id).senses) == 3
                assert not ds.entry_exists(b_id)
            finally:
                for eid_cleanup in [a_id, b_id]:
                    try:
                        if ds.entry_exists(eid_cleanup):
                            ds.delete_entry(eid_cleanup, record_history=False)
                    except Exception:
                        pass
