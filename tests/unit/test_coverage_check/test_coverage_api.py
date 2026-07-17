"""
Integration tests for Coverage API endpoints.

Creates a minimal Flask app with just the coverage blueprint
so tests can run without BaseX.
"""
import io
import json
import pytest
from flask import Flask
from app.api.coverage import coverage_bp


@pytest.fixture(scope="module")
def client():
    """Create minimal Flask test client with coverage blueprint only."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "test"
    app.register_blueprint(coverage_bp)
    with app.test_client() as c:
        yield c


class TestWordNetLookupAPI:
    def test_wordnet_word_bank(self, client):
        resp = client.get("/api/coverage/wordnet/bank?language=en")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["word"] == "bank"
        assert data["synset_count"] >= 5
        assert data["entry"] is not None
        assert len(data["entry"]["senses"]) >= 5
        for s in data["entry"]["senses"]:
            assert "definition" in s
            assert s["id"].startswith("wn:")

    def test_wordnet_word_cat(self, client):
        resp = client.get("/api/coverage/wordnet/cat?language=en")
        data = resp.get_json()
        assert data["success"] is True
        assert data["synset_count"] >= 3
        assert any("feline" in s["definition"] for s in data["entry"]["senses"])

    def test_wordnet_word_with_polish(self, client):
        resp = client.get("/api/coverage/wordnet/cat?language=en&target_language=pl")
        data = resp.get_json()
        assert data["success"] is True
        assert data["synset_count"] >= 3

    def test_wordnet_nonexistent_word(self, client):
        resp = client.get("/api/coverage/wordnet/xyzqwk?language=en")
        data = resp.get_json()
        assert data["success"] is True
        assert data["synset_count"] == 0
        assert data["entry"] is None

    def test_wordnet_run(self, client):
        resp = client.get("/api/coverage/wordnet/run?language=en")
        data = resp.get_json()
        assert data["success"] is True
        assert data["synset_count"] >= 10


class TestTextCoverageAPI:
    def test_text_coverage_basic(self, client):
        resp = client.post("/api/coverage/text",
                           data=json.dumps({"text": "The cats are running."}),
                           content_type="application/json")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["entry_count"] > 0
        headwords = [e["headword"] for e in data["entries"]]
        assert "cat" in headwords

    def test_text_coverage_empty(self, client):
        resp = client.post("/api/coverage/text",
                           data=json.dumps({"text": ""}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_text_coverage_no_text(self, client):
        resp = client.post("/api/coverage/text",
                           data=json.dumps({}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_text_coverage_longer_text(self, client):
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "The dog barked at the fox. "
            "A cat sat on the mat watching the fox and the dog."
        )
        resp = client.post("/api/coverage/text",
                           data=json.dumps({"text": text}),
                           content_type="application/json")
        data = resp.get_json()
        assert data["success"] is True
        assert data["entry_count"] >= 5
        headwords = [e["headword"] for e in data["entries"]]
        assert "cat" in headwords
        assert "dog" in headwords
        assert "fox" in headwords


class TestResourceCoverageAPI:
    def test_text_resource_upload(self, client):
        data_upload = {
            "file": (io.BytesIO(b"cat\ndog\nrun\nbank\nhouse\n"), "words.txt"),
            "resource_type": "text",
            "language": "en",
        }
        resp = client.post("/api/coverage/resource",
                           data=data_upload,
                           content_type="multipart/form-data")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["entry_count"] == 5

    def test_subtlex_resource_upload(self, client):
        subtlex = "word\tLgCount\tCd\nbank\t2000\t1.5\ncat\t5000\t0.8\nrun\t8000\t2.1\n"
        data_upload = {
            "file": (io.BytesIO(subtlex.encode()), "subtlex.tsv"),
            "resource_type": "subtlex",
            "language": "en",
        }
        resp = client.post("/api/coverage/resource",
                           data=data_upload,
                           content_type="multipart/form-data")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["entry_count"] == 3

    def test_no_file(self, client):
        resp = client.post("/api/coverage/resource",
                           data={"resource_type": "text", "language": "en"},
                           content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_invalid_file_type(self, client):
        data_upload = {
            "file": (io.BytesIO(b"content"), "script.py"),
            "resource_type": "text",
            "language": "en",
        }
        resp = client.post("/api/coverage/resource",
                           data=data_upload,
                           content_type="multipart/form-data")
        assert resp.status_code == 400


class TestSystematicityAPI:
    def test_systematicity_no_dict(self, client):
        resp = client.get("/api/coverage/systematicity?language=en")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["total_checks"] > 0
        assert len(data["categories"]) > 0

    def test_systematicity_with_language(self, client):
        resp = client.get("/api/coverage/systematicity?language=pl")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True


class TestSenseAlignmentAPI:
    def test_alignment_no_dict(self, client):
        resp = client.get("/api/coverage/alignment?language=en")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["message"] == "No dictionary available"

    def test_alignment_single_word(self, client):
        resp = client.get("/api/coverage/alignment?language=en&word=bank")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["word"] == "bank"
        assert data["synset_count"] >= 5

    def test_alignment_nonexistent_word(self, client):
        resp = client.get("/api/coverage/alignment?language=en&word=xyzqwk")
        data = resp.get_json()
        assert data["success"] is True
        assert data["synset_count"] == 0
