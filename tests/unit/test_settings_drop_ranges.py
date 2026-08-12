"""Settings drop-database endpoint: 'drop_ranges' must re-seed recommended ranges.

The action used to drop content and then do nothing ("Install ranges - this would
need to be implemented"); the UI (settings.html "Drop with ranges") expects the
recommended ranges back on the clean slate, so it now calls
DictionaryService.install_recommended_ranges() after drop_database_content().
"""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def drop_client(db_app):
    db_app.config["REQUIRE_AUTH"] = False
    db_app.config["WTF_CSRF_ENABLED"] = False
    svc = MagicMock()
    db_app.dict_service = svc
    yield db_app.test_client(), svc


def test_drop_ranges_installs_recommended(drop_client):
    client, svc = drop_client
    resp = client.post("/settings/drop-database", json={"action": "drop_ranges"})
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
    svc.drop_database_content.assert_called_once_with()
    svc.install_recommended_ranges.assert_called_once_with()


def test_drop_ranges_install_failure_is_reported(drop_client):
    client, svc = drop_client
    svc.install_recommended_ranges.side_effect = RuntimeError("ranges exploded")
    resp = client.post("/settings/drop-database", json={"action": "drop_ranges"})
    assert resp.status_code == 500
    assert resp.get_json()["success"] is False
    assert "ranges installation failed" in resp.get_json()["error"]


def test_plain_drop_does_not_install(drop_client):
    client, svc = drop_client
    resp = client.post("/settings/drop-database", json={"action": "drop"})
    assert resp.status_code == 200
    svc.drop_database_content.assert_called_once_with()
    svc.install_recommended_ranges.assert_not_called()
