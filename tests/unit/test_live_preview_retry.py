import json
from app.services.css_mapping_service import CSSMappingService


def test_live_preview_retry(monkeypatch, client):
    # Prepare fake render_entry to return no headword first, then a headword
    calls = {"count": 0}

    def fake_render_entry(self, entry_xml, profile=None, dict_service=None):
        if calls["count"] == 0:
            calls["count"] += 1
            return "<div>No headword</div>"
        return '<span class="headword"><span class="lexical-unit">RetryHeadword</span></span>'

    monkeypatch.setattr(CSSMappingService, "render_entry", fake_render_entry)

    # Monkeypatch the transformer to return valid LIFT XML with lexical-unit
    class FakeTransformer:
        def generate_lift_xml_from_form_data(self, data):
            return '<entry id="test"><lexical-unit><form lang="en"><text>RetryHeadword</text></form></lexical-unit></entry>'

    monkeypatch.setattr("app.utils.lift_to_html_transformer.LIFTToHTMLTransformer", lambda: FakeTransformer())

    # Monkeypatch DisplayProfileService to avoid DB access in unit test
    class FakeProfileService:
        def get_default_profile(self):
            class P: pass
            p = P()
            p.id = 1
            return p
        def create_from_registry_default(self, name, description):
            class P: pass
            p = P()
            p.id = 1
            return p
        def set_default_profile(self, profile_id):
            return None

    monkeypatch.setattr("app.services.display_profile_service.DisplayProfileService", lambda: FakeProfileService())

    # Call the live preview endpoint with minimal form data
    resp = client.post("/api/live-preview", json={"lexical_unit": "RetryHeadword", "senses": {}})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["debug"]["retry_attempted"] is True
    assert data["debug"]["retry_success"] is True
    assert data["debug"]["has_headword"] is True
    assert "RetryHeadword" in data["html"]
