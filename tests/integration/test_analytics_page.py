"""
Simple smoke test: verify the analytics page renders correctly.
"""
import pytest


@pytest.mark.integration
class TestAnalyticsSmoke:
    """Quick tests for the analytics template."""

    def test_analytics_page_returns_200(self, client):
        r = client.get("/workbench/analytics")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "Change Analytics" in html

    def test_analytics_page_has_vanilla_js(self, client):
        r = client.get("/workbench/analytics")
        html = r.get_data(as_text=True)
        assert "analyticsLoad" in html
        assert "analyticsPreset" in html
        assert "analytics-from" in html

    def test_analytics_page_has_stats_api_call(self, client):
        r = client.get("/workbench/analytics")
        html = r.get_data(as_text=True)
        assert "/api/revisions/stats" in html
        assert "total_revisions" in html
        assert "timeline" in html
