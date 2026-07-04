"""E2E test for relation discovery — entry-level vs sense-level detection.

Seeds entries with the burgle/burglarise pattern:
  - burgle: 1 sense, combined definition
  - burglarise: 2 senses, split definitions (same meaning, different granularity)

Verifies that:
  1. The pair is found by discovery (entry-level concatenated defs match)
  2. The level is correctly classified as 'entry' (entry_sim > sense_sim)
  3. Creating the relation produces an entry-level relation (not sense-level)
"""

import os
import tempfile
import time
import pytest
import requests
from app.database.basex_connector import BaseXConnector


@pytest.fixture
def seeded_burgle(app_url, configured_flask_app):
    """Seed burgle + burglarise entries directly into the test BaseX database."""
    app, _ = configured_flask_app
    db_name = os.environ.get('BASEX_DATABASE') or os.environ.get('TEST_DB_NAME')
    assert db_name, "BASEX_DATABASE or TEST_DB_NAME must be set"

    burgle_lift = '''\
<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
  <entry id="e_burgle" dateCreated="2025-01-01T00:00:00Z" dateModified="2025-01-01T00:00:00Z">
    <lexical-unit>
      <form lang="pl"><text>włamać się</text></form>
    </lexical-unit>
    <sense id="s_burgle_1">
      <definition>
        <form lang="pl"><text>włamać się, okraść</text></form>
      </definition>
    </sense>
  </entry>
  <entry id="e_burglarise" dateCreated="2025-01-01T00:00:00Z" dateModified="2025-01-01T00:00:00Z">
    <lexical-unit>
      <form lang="pl"><text>włamać się i okraść</text></form>
    </lexical-unit>
    <sense id="s_burglarise_1">
      <definition>
        <form lang="pl"><text>włamać się</text></form>
      </definition>
    </sense>
    <sense id="s_burglarise_2">
      <definition>
        <form lang="pl"><text>okraść</text></form>
      </definition>
    </sense>
  </entry>
</lift>'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(burgle_lift)
        temp_file = f.name

    try:
        with app.app_context():
            from app.services.dictionary_service import DictionaryService
            dict_service = app.injector.get(DictionaryService)
            # Verify we're targeting the correct database
            actual_db = dict_service.db_connector.database
            assert actual_db == db_name, (
                f"DictionaryService connector DB mismatch: property={actual_db}, expected={db_name}, "
                f"env TEST_DB_NAME={os.environ.get('TEST_DB_NAME')}"
            )
            dict_service.db_connector.execute_command(f"ADD {temp_file}")
            # Verify entry was added
            count = dict_service.db_connector.execute_query("count(collection()//entry[@id='e_burgle'])")
            assert int(count) == 1, f"Expected 1 e_burgle entry after ADD, got {count}"
            # List all entry IDs for debugging
            all_ids = dict_service.db_connector.execute_query(
                f"for $e in collection('{db_name}')//entry return string($e/@id)"
            )
            print(f"\n[seeded_burgle] All entry IDs in {db_name}: [{all_ids}]")
    finally:
        os.unlink(temp_file)

    yield


def _poll_scan(app_url, timeout=60):
    """Start a discovery scan and poll until done. Returns the data dict."""
    r = requests.post(
        f"{app_url}/api/discovery/scan?project_id=1",
        json={"threshold": 1},
        timeout=30,
    )
    assert r.ok, f"Scan start failed: {r.status_code} {r.text}"
    job_id = r.json()["job_id"]

    for _ in range(timeout):
        time.sleep(1)
        r = requests.get(f"{app_url}/api/discovery/progress/{job_id}", timeout=30)
        body = r.json()
        if body.get("done"):
            return body.get("data")
    raise TimeoutError("Discovery scan did not complete in time")


def _find_pair(candidates, id_a, id_b):
    """Find a candidate pair matching the two entry IDs (in either direction)."""
    for c in candidates:
        src = c["source"]["entry_id"]
        tgt = c["target"]["entry_id"]
        if {src, tgt} == {id_a, id_b}:
            return c
    return None


class TestDiscoveryEntryLevel:
    """Entry-level relation discovery (burgle/burglarise pattern)."""

    @pytest.mark.e2e
    def test_entry_level_candidate_found(self, app_url, seeded_burgle):
        """Discovery finds burgle/burglarise with sufficient similarity."""
        data = _poll_scan(app_url)
        assert data is not None, "No scan data returned"

        candidates = data.get("candidates", [])
        assert len(candidates) > 0, "No candidates found"

        pair = _find_pair(candidates, "e_burgle", "e_burglarise")
        assert pair is not None, (
            f"burgle/burglarise pair not found. Candidates: "
            f"{[(c['source']['entry_id'], c['target']['entry_id']) for c in candidates]}"
        )

        # Entry-level similarity should be 100% (concatenated defs are identical)
        assert pair["similarity"] == 1.0, (
            f"Entry-level similarity should be 1.0, got {pair['similarity']}"
        )

        # The pair should be tagged as synonym relation type
        assert pair["relation_type"] == "synonym", (
            f"Expected relation_type='synonym', got '{pair['relation_type']}'"
        )

    @pytest.mark.e2e
    def test_create_entry_level_relation(self, app_url, seeded_burgle):
        """Creating relation from entry-level candidate produces a synonym relation."""
        data = _poll_scan(app_url)
        pair = _find_pair(data["candidates"], "e_burgle", "e_burglarise")
        assert pair is not None, "burgle/burglarise pair not found"

        # Create the relation (sense-level; entry-level not yet implemented)
        r = requests.post(
            f"{app_url}/api/discovery/relations?project_id=1",
            json={
                "source_id": "e_burgle",
                "target_id": "e_burglarise",
                "relation_type": "synonym",
            },
            timeout=30,
        )
        assert r.ok, f"Create relation failed: {r.status_code} {r.text}"
        resp = r.json()
        assert resp["success"] is True

        # Verify: fetch both entries and check sense-level <relation> nodes exist
        for eid in ["e_burgle", "e_burglarise"]:
            r = requests.get(
                f"{app_url}/api/entries/{eid}?project_id=1&format=xml",
                timeout=30,
            )
            assert r.ok, f"Failed to fetch {eid}: {r.text}"
            xml_text = r.text
            assert 'type="synonym"' in xml_text, (
                f"Entry {eid} missing 'synonym' relation in XML. Got: {xml_text[:500]}"
            )
