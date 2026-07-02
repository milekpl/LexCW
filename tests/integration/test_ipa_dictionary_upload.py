"""
Integration tests for IPA dictionary upload and configuration flow.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask.testing import FlaskClient


@pytest.mark.integration
def test_upload_and_set_ipa_dictionary_from_resources(client: FlaskClient) -> None:
    """Upload IPA dictionary files from app resources and set them as IPA dictionary."""
    project_id = 1
    with client.session_transaction() as sess:
        if sess.get("project_id"):
            project_id = int(sess["project_id"])

    dic_path = Path("app/data/dictionaries/ipa/ipa.dic")
    aff_path = Path("app/data/dictionaries/ipa/ipa.aff")

    assert dic_path.exists(), f"Missing IPA dictionary resource: {dic_path}"
    assert aff_path.exists(), f"Missing IPA affix resource: {aff_path}"

    with dic_path.open("rb") as dic_fp, aff_path.open("rb") as aff_fp:
        upload_resp = client.post(
            f"/api/projects/{project_id}/dictionaries/upload",
            data={
                "name": "IPA Resource Dictionary",
                "lang_code": "seh-fonipa",
                "dic_file": (dic_fp, "ipa.dic"),
                "aff_file": (aff_fp, "ipa.aff"),
            },
            content_type="multipart/form-data",
        )

    assert upload_resp.status_code == 200, upload_resp.get_data(as_text=True)
    payload = upload_resp.get_json()
    assert payload and payload.get("success") is True

    uploaded = payload["dictionary"]
    dict_id = uploaded["id"]
    assert uploaded["lang_code"] == "seh-fonipa"

    set_resp = client.put(f"/api/projects/{project_id}/dictionaries/{dict_id}/ipa")
    assert set_resp.status_code == 200, set_resp.get_data(as_text=True)

    list_resp = client.get(f"/api/projects/{project_id}/dictionaries")
    assert list_resp.status_code == 200
    listing = list_resp.get_json()
    assert listing
    assert listing.get("ipa_dictionary_id") == dict_id
